#!/usr/bin/env python3
"""
Cloud Run Log Analyzer
Analyzes Google Cloud Run HTTP requests and application stdout/stderr logs over a configurable timeframe.
Usage:
    python3 scripts/analyze_cloudrun_logs.py [--hours 24] [--project PROJECT_ID] [--service SERVICE_NAME]
"""

import argparse
import json
import os
import sys
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone

def fetch_logs(project_id, service_name, hours):
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ')

    filter_str = (
        f'resource.type="cloud_run_revision" AND '
        f'resource.labels.service_name="{service_name}" AND '
        f'timestamp >= "{start_time}"'
    )

    cmd = [
        'gcloud', 'logging', 'read',
        filter_str,
        f'--project={project_id}',
        '--limit=10000',
        '--format=json'
    ]

    print(f"🔍 Fetching Cloud Run logs for '{service_name}' in project '{project_id}' since {start_time}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logs = json.loads(res.stdout or "[]")
        return logs
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing gcloud command: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print("❌ Error parsing gcloud JSON output.", file=sys.stderr)
        return []

def analyze_logs(logs):
    request_logs = [log for log in logs if 'httpRequest' in log]
    app_logs = [log for log in logs if 'httpRequest' not in log]

    statuses = Counter()
    methods = Counter()
    paths = Counter()
    user_agents = Counter()
    ips = Counter()
    latencies = []

    for r in request_logs:
        hr = r['httpRequest']
        st = hr.get('status')
        statuses[st] += 1
        methods[hr.get('requestMethod', 'GET')] += 1
        
        url = hr.get('requestUrl', '')
        path = url.split('?')[0] if '?' in url else url
        if '://' in path:
            path = '/' + '/'.join(path.split('/')[3:])
        paths[path] += 1
        
        user_agents[hr.get('userAgent', 'Unknown')] += 1
        ips[hr.get('remoteIp', 'Unknown')] += 1
        
        lat_str = hr.get('latency', '0s')
        if lat_str.endswith('s'):
            try:
                lat_ms = float(lat_str[:-1]) * 1000
                latencies.append(lat_ms)
            except ValueError:
                pass

    error_logs = [log for log in app_logs if log.get('severity') in ('ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY')]
    app_severities = Counter(log.get('severity', 'DEFAULT') for log in app_logs)

    return {
        'total_logs': len(logs),
        'request_logs_count': len(request_logs),
        'app_logs_count': len(app_logs),
        'statuses': dict(statuses),
        'methods': dict(methods),
        'top_paths': paths.most_common(15),
        'top_ips': ips.most_common(10),
        'top_user_agents': user_agents.most_common(10),
        'latencies': latencies,
        'app_severities': dict(app_severities),
        'error_logs': error_logs
    }

def print_report(analysis):
    print("\n==========================================")
    print("📊 CLOUD RUN LOG ANALYSIS REPORT")
    print("==========================================")
    print(f"Total Log Entries: {analysis['total_logs']}")
    print(f"  └ HTTP Request Logs: {analysis['request_logs_count']}")
    print(f"  └ Application Logs:  {analysis['app_logs_count']}")

    print("\n📈 HTTP STATUS CODES:")
    for status, count in sorted(analysis['statuses'].items(), key=lambda x: x[1], reverse=True):
        emoji = "✅" if 200 <= status < 300 else ("🔀" if 300 <= status < 400 else ("⚠️" if 400 <= status < 500 else "🚨"))
        print(f"  {emoji} Status {status}: {count:4d} requests")

    print("\n🛤️ TOP REQUESTED PATHS:")
    for path, count in analysis['top_paths']:
        print(f"  {count:4d} reqs │ {path}")

    print("\n🌐 TOP CLIENT IPS:")
    for ip, count in analysis['top_ips']:
        print(f"  {count:4d} reqs │ {ip}")

    print("\n🤖 TOP USER AGENTS:")
    for ua, count in analysis['top_user_agents']:
        print(f"  {count:4d} reqs │ {ua[:90]}")

    if analysis['latencies']:
        lats = sorted(analysis['latencies'])
        avg = sum(lats) / len(lats)
        p50 = lats[len(lats) // 2]
        p90 = lats[int(len(lats) * 0.9)]
        p95 = lats[int(len(lats) * 0.95)]
        p99 = lats[int(len(lats) * 0.99)]
        print("\n⏱️ LATENCY DISTRIBUTION (ms):")
        print(f"  Avg: {avg:.2f}ms │ P50: {p50:.2f}ms │ P90: {p90:.2f}ms │ P95: {p95:.2f}ms │ P99: {p99:.2f}ms")

    print("\n🚨 APPLICATION LOG SEVERITIES:")
    for sev, count in analysis['app_severities'].items():
        print(f"  Severity [{sev}]: {count}")

    if analysis['error_logs']:
        print(f"\n❌ FOUND {len(analysis['error_logs'])} APPLICATION ERROR(S):")
        for idx, err in enumerate(analysis['error_logs'][:5], 1):
            ts = err.get('timestamp', '')
            payload = err.get('textPayload') or json.dumps(err.get('jsonPayload', {}))
            print(f"--- Error #{idx} [{ts}] ---")
            print(payload.strip())
    else:
        print("\n✨ No application ERROR logs found.")

    print("==========================================\n")

def main():
    parser = argparse.ArgumentParser(description="Analyze Cloud Run logs.")
    parser.add_argument("--hours", type=int, default=24, help="Timeframe in hours to analyze (default: 24)")
    parser.add_argument("--project", type=str, default=os.getenv("GOOGLE_CLOUD_PROJECT", "securemed-chat-494521"), help="GCP Project ID")
    parser.add_argument("--service", type=str, default="preconsult", help="Cloud Run service name")
    parser.add_argument("--json", action="store_true", help="Output raw analysis JSON")

    args = parser.parse_args()

    logs = fetch_logs(args.project, args.service, args.hours)
    if not logs:
        print("No logs retrieved.")
        sys.exit(0)

    analysis = analyze_logs(logs)

    if args.json:
        # Remove raw non-serializable objects if any
        analysis['error_logs'] = [log.get('textPayload') or log.get('jsonPayload') for log in analysis['error_logs']]
        print(json.dumps(analysis, indent=2))
    else:
        print_report(analysis)

if __name__ == "__main__":
    main()
