#!/usr/bin/env python3
"""
Cloudflare Configuration & Analytics Analyzer
Queries Cloudflare API for Zone status, active Rulesets, WAF custom rules, DNS records,
and attempts GraphQL Firewall/Analytics queries.
Usage:
    python3 scripts/analyze_cloudflare_logs.py [--hours 24]
"""

import argparse
import os
import sys
import json
from datetime import datetime, timedelta, timezone
try:
    import requests
except ImportError:
    print("❌ 'requests' module not installed. Run 'pip install requests'", file=sys.stderr)
    sys.exit(1)

def load_env():
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip("\"'")
                    os.environ.setdefault(k, v)

def get_cloudflare_info(token, zone_id):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    report = {}

    # 1. Zone Info
    res_zone = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}", headers=headers)
    if res_zone.status_code == 200:
        zone_data = res_zone.json().get("result", {})
        report["zone"] = {
            "name": zone_data.get("name"),
            "status": zone_data.get("status"),
            "paused": zone_data.get("paused"),
            "name_servers": zone_data.get("name_servers", []),
            "plan": zone_data.get("plan", {}).get("name")
        }
    else:
        report["zone_error"] = res_zone.text

    # 2. DNS Records
    res_dns = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers)
    if res_dns.status_code == 200:
        dns_records = res_dns.json().get("result", [])
        report["dns_records"] = [
            {
                "name": r.get("name"),
                "type": r.get("type"),
                "content": r.get("content"),
                "proxied": r.get("proxied")
            }
            for r in dns_records
        ]

    # 3. Active Rulesets
    res_rules = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets", headers=headers)
    if res_rules.status_code == 200:
        rulesets = res_rules.json().get("result", [])
        report["rulesets"] = [
            {
                "name": r.get("name"),
                "phase": r.get("phase"),
                "kind": r.get("kind"),
                "description": r.get("description")
            }
            for r in rulesets
        ]

    # 4. GraphQL Firewall Events query
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    query_fw = f"""
    query {{
      viewer {{
        zones(filter: {{zoneTag: "{zone_id}"}}) {{
          firewallEventsAdaptive(limit: 100, filter: {{datetime_gt: "{start_time}"}}) {{
            action
            clientIP
            clientRequestHTTPHost
            clientRequestPath
            datetime
            rayName
            clientCountryName
            ruleId
            source
          }}
        }}
      }}
    }}
    """
    res_gql = requests.post("https://api.cloudflare.com/client/v4/graphql", headers=headers, json={"query": query_fw})
    gql_data = res_gql.json()
    if res_gql.status_code == 200 and gql_data.get("data"):
        zone_gql = gql_data["data"]["viewer"]["zones"][0] if gql_data["data"]["viewer"]["zones"] else {}
        report["firewall_events"] = zone_gql.get("firewallEventsAdaptive", [])
    else:
        report["graphql_notice"] = gql_data.get("errors", [])

    return report

def print_cloudflare_report(report):
    print("\n==========================================")
    print("☁️ CLOUDFLARE CONFIGURATION & ANALYTICS REPORT")
    print("==========================================")
    
    if "zone" in report:
        z = report["zone"]
        print(f"Zone Name:   {z['name']}")
        print(f"Status:      {z['status']} (Plan: {z['plan']})")
        print(f"Proxied:     {'Paused' if z['paused'] else 'Active'}")
    elif "zone_error" in report:
        print(f"❌ Zone Lookup Error: {report['zone_error']}")

    if "dns_records" in report:
        print("\n📌 ACTIVE DNS RECORDS:")
        for r in report["dns_records"]:
            proxy_str = "☁️ Proxied" if r["proxied"] else "🌐 DNS Only"
            print(f"  [{r['type']}] {r['name']} -> {r['content']} ({proxy_str})")

    if "rulesets" in report:
        print("\n🛡️ DEPLOYED RULESETS:")
        for rs in report["rulesets"]:
            print(f"  • {rs['name']} (Phase: {rs['phase']})")

    if "firewall_events" in report:
        fw_events = report["firewall_events"]
        print(f"\n🧱 FIREWALL EVENTS (Last 24h): {len(fw_events)} events blocked/challenged")
        for ev in fw_events[:10]:
            print(f"  [{ev.get('action')}] {ev.get('datetime')} | IP: {ev.get('clientIP')} | Path: {ev.get('clientRequestPath')}")
    elif "graphql_notice" in report:
        print("\nℹ️ Cloudflare GraphQL Analytics Scope Notice:")
        for err in report["graphql_notice"]:
            msg = err.get("message", "")
            if "analytics.read" in msg:
                print("  • Token needs 'Zone > Analytics > Read' permission to query GraphQL request logs directly.")
                print("  • Request logs are routed to Cloud Run origin and fully analyzed in Cloud Run logs.")
            else:
                print(f"  • {msg}")

    print("==========================================\n")

def main():
    load_env()
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID")

    if not token or not zone_id:
        print("❌ CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID environment variables must be set.", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Analyze Cloudflare configuration and logs.")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    report = get_cloudflare_info(token, zone_id)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_cloudflare_report(report)

if __name__ == "__main__":
    main()
