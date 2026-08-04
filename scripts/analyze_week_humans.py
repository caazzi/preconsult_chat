#!/usr/bin/env python3
"""
Human-vs-Bot Access Analyzer for PreConsult.

Distinguishes genuine human sessions from bot/scanner traffic in Cloud Run logs
over a configurable window (default: last 7 days).

A "human session" is defined as a distinct IP making >= MIN_HUMAN_REQS requests
with a passed status AND engaging with the app (interactive _event/, WebSocket 101
handshakes, and/or a real asset graph) while avoiding scanner-only probe paths.

Usage:
    python3 scripts/analyze_week_humans.py [--days 7] [--project PROJECT_ID] [--service SERVICE_NAME] [--json]
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta, timezone

# ---- Tuning knobs (PM-adjustable) ----
MIN_HUMAN_REQS = 5          # min requests from an IP to be considered a session
MIN_HUMAN_DAY_WIDTH = 2     # min number of distinct days before counting as recurring
MAX_GENUINE_ASSET_RATIO = 0.7   # max share of successful non-probe requests
# ---------------------------------------------------------------------------

BOT_UA_MARKERS = [
    "server", "scan", "bot", "crawl", "spider", "curl", "lighthouse", "python",
    "go-http", "httpx", "zgrab", "nuclei", "masscan", "wget", "aiohttp",
    "headless", "semrush", "ahrefs", "majestic", "ndtsystem", "gptbot",
    "claudebot", "dataforseo",
]

# Paths that strongly indicate vulnerability/exploit scanning, regardless of UA.
SCAN_PATH_MARKERS = [
    "wp-admin", "wp-login", "wp-includes", "xmlrpc", "wp-", ".env", ".git",
    "phpinfo", "test.php", "info.php", "passwd", "credentials", "phpmyadmin",
    "adminer", "config.php", ".php", "shell", "backup", "sql", ".bak",
]

# Interactive / real-engagement signals.
INTERACTIVE_MARKERS = ["/_event/", "/graphql", "/socket.io", "websocket"]


def fetch_logs(project_id, service_name, days):
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    filter_str = (
        f'resource.type="cloud_run_revision" AND '
        f'resource.labels.service_name="{service_name}" AND '
        f'timestamp >= "{start_time}"'
    )
    cmd = [
        "gcloud", "logging", "read", filter_str,
        f"--project={project_id}",
        "--limit=50000",
        "--order=asc",
        "--format=json",
    ]
    print(f"🔍 Fetching '{service_name}' logs in '{project_id}' since {start_time}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout or "[]")
    except subprocess.CalledProcessError as e:
        print(f"❌ gcloud error: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print("❌ Failed to parse gcloud JSON output.", file=sys.stderr)
        return []


def clean_path(url):
    path = urllib.parse.urlsplit(url).path or "/"
    return path


def is_bot_ua(ua):
    ua = (ua or "").lower()
    return any(m in ua for m in BOT_UA_MARKERS)


def is_probe_path(path):
    lp = path.lower()
    return any(m in lp for m in SCAN_PATH_MARKERS)


def is_interactive(path):
    return any(m in path.lower() for m in INTERACTIVE_MARKERS)


def analyze(logs):
    req = [log for log in logs if "httpRequest" in log]
    app = [log for log in logs if "httpRequest" not in log]

    # ---- Global overview ----
    status = Counter()
    method = Counter()
    host = Counter()
    day = Counter()
    for log in req:
        hr = log["httpRequest"]
        try:
            status[int(hr.get("status"))] += 1
        except (TypeError, ValueError):
            status[-1] += 1
        method[hr.get("requestMethod", "GET")] += 1
        u = hr.get("requestUrl", "")
        host[urllib.parse.urlsplit(u).netloc or "-"] += 1
        if log.get("timestamp"):
            day[log["timestamp"][:10]] += 1

    ua_flagged = len([log for log in req if is_bot_ua(log["httpRequest"].get("userAgent", ""))])

    # ---- Per-IP behavior ----
    ip_days = {}
    ip_ok = {}
    ip_probe = {}
    ip_interactive = {}
    ip_ws101 = {}
    ip_ua_bot = {}
    for log in req:
        hr = log["httpRequest"]
        ip = hr.get("remoteIp", "?")
        path = clean_path(hr.get("requestUrl", ""))
        st = hr.get("status")
        d = log.get("timestamp", "")[:10] if log.get("timestamp") else ""
        ip_days.setdefault(ip, set()).add(d)
        ip_ok.setdefault(ip, 0)
        ip_probe.setdefault(ip, 0)
        ip_interactive.setdefault(ip, 0)
        ip_ws101.setdefault(ip, 0)
        ip_ua_bot.setdefault(ip, 0)
        if st in (200, 206, 101):
            ip_ok[ip] += 1
        if is_probe_path(path):
            ip_probe[ip] += 1
        if is_interactive(path):
            ip_interactive[ip] += 1
        if st == 101:
            ip_ws101[ip] += 1
        if is_bot_ua(hr.get("userAgent", "")):
            ip_ua_bot[ip] += 1

    human_ips = []
    all_ip_counts = Counter(log["httpRequest"].get("remoteIp", "?") for log in req)
    for ip, total in all_ip_counts.items():
        ok = ip_ok.get(ip, 0)
        probe = ip_probe.get(ip, 0)
        interactive = ip_interactive.get(ip, 0)
        ws101 = ip_ws101.get(ip, 0)
        n_days = len(ip_days.get(ip, set()))
        ua_bot = ip_ua_bot.get(ip, 0)

        # Recurring + many probe hits => scanner; UA-bot dominant => scan/probe.
        if probe >= total * 0.5 or ua_bot >= total * 0.5:
            continue
        # A human session must either engage interactively (live WebSocket 101,
        # _event/ or graphql calls) or return on multiple distinct days. Plain
        # high-volume single-day page-load IPs (load-testers/uptime pings) are
        # excluded.
        engaged = (interactive > 0) or (ws101 > 0) or (n_days >= 2)
        if total >= MIN_HUMAN_REQS and engaged and ok > probe:

            human_ips.append({
                "ip": ip,
                "requests": total,
                "success": ok,
                "probe": probe,
                "interactive": interactive,
                "websocket_101": ws101,
                "days": n_days,
                "days_list": sorted(ip_days.get(ip, set())),
            })

    # ---- App errors ----
    severities = Counter(log.get("severity", "DEFAULT") for log in app)
    error_logs = [
        (log.get("textPayload") or json.dumps(log.get("jsonPayload", "")))
        for log in app
        if log.get("severity") in ("ERROR", "CRITICAL", "ALERT", "EMERGENCY")
    ]

    return {
        "window_start": req[0].get("timestamp", "") if req else "",
        "window_end": req[-1].get("timestamp", "") if req else "",
        "total_requests": len(req),
        "total_ips": len(all_ip_counts),
        "days": {d: day[d] for d in sorted(day)},
        "status": dict(sorted(status.items(), key=lambda x: -x[1])),
        "methods": dict(method),
        "hosts": host.most_common(10),
        "estimated_bots": ua_flagged,
        "human_sessions": human_ips,
        "human_request_share": round(100.0 * sum(h["requests"] for h in human_ips) / len(req), 1) if req else 0,
        "app_severities": dict(severities),
        "app_error_count": len(error_logs),
        "app_error_samples": error_logs[:5],
    }


def print_report(a):
    print("\n" + "=" * 60)
    print("  HUMAN-vs-BOT ACCESS REPORT")
    print("=" * 60)
    print(f"Window: {a['window_start'][:19]}  ->  {a['window_end'][:19]}")
    print(f"Total requests: {a['total_requests']}  |  Distinct IPs: {a['total_ips']}")

    print("\n📅 DAILY VOLUME:")
    for d, c in a["days"].items():
        print(f"   {d}  {c:5d}")

    print("\n📈 HTTP STATUS:")
    for st, c in a["status"].items():
        emoji = "✅" if 199 < st < 300 else ("⚠️" if 399 < st < 500 else ("🔀" if 299 < st < 400 else ("🚨" if st >= 500 else "❓")))
        print(f"   {emoji} {st}: {c}")

    print("\n🌐 HOSTS:")
    for h, c in a["hosts"]:
        print(f"   {c:5d}  {h}")

    ua_bot = a["estimated_bots"]
    print(f"\n🤖 Clearly bot-flagged (UA): {ua_bot} ({round(100*ua_bot/max(a['total_requests'],1),1)}%)")
    print(f"\n🧍 HUMAN SESSIONS: {len(a['human_sessions'])}  (share of requests: {a['human_request_share']}%)")
    for h in sorted(a["human_sessions"], key=lambda x: -x["requests"]):
        print(f"   • {h['ip']:<18} reqs={h['requests']:4d} ok={h['success']:3d} "
              f"probe={h['probe']:3d} ws101={h['websocket_101']:2d} interact={h['interactive']:2d} "
              f"days={h['days']} [{', '.join(h['days_list'])}]")

    print(f"\n🚨 APP ERRORS: {a['app_error_count']}")
    for s in a["app_error_samples"][:3]:
        print("   -", s.splitlines()[-1][:130] if s else "")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Human-vs-bot access analyzer for PreConsult.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze (default: 7)")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT", "securemed-chat-494521"))
    parser.add_argument("--service", type=str, default="preconsult")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON")
    args = parser.parse_args()

    logs = fetch_logs(args.project, args.service, args.days)
    if not logs:
        print("No logs retrieved.")
        return
    analysis = analyze(logs)
    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print_report(analysis)


if __name__ == "__main__":
    main()
