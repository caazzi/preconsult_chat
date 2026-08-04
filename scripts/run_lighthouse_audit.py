#!/usr/bin/env python3
"""
Lighthouse Audit Runner & Analyzer

Runs Google Lighthouse audits on a target URL for both Mobile and Desktop profiles,
saves HTML and JSON reports, and prints a formatted terminal summary of Performance,
Core Web Vitals, and Optimization Opportunities.

Usage:
    python3 scripts/run_lighthouse_audit.py [URL] [OPTIONS]

Examples:
    python3 scripts/run_lighthouse_audit.py
    python3 scripts/run_lighthouse_audit.py https://pre-consult.org --preset mobile
    python3 scripts/run_lighthouse_audit.py https://pre-consult.org --preset desktop
    python3 scripts/run_lighthouse_audit.py https://pre-consult.org --output-dir ./reports
"""

import argparse
import json
import os
import shutil
import subprocess


def find_chrome():
    """Locates an available Google Chrome or Chromium executable."""
    candidates = ["google-chrome", "chromium-browser", "chromium", "google-chrome-stable"]
    for cmd in candidates:
        path = shutil.which(cmd)
        if path:
            return path
    return None


def run_lighthouse(url, preset, output_prefix, chrome_path):
    """Executes lighthouse CLI via npx for a given preset."""
    env = os.environ.copy()
    if chrome_path:
        env["CHROME_PATH"] = chrome_path

    cmd = [
        "npx",
        "lighthouse@11",
        url,
        "--output=json,html",
        f"--output-path={output_prefix}",
        '--chrome-flags=--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage',
        "--quiet"
    ]

    if preset == "desktop":
        cmd.append("--preset=desktop")

    print(f"🚀 Running Lighthouse audit for [{preset.upper()}] on {url}...")
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    json_path = f"{output_prefix}.report.json"
    html_path = f"{output_prefix}.report.html"

    if not os.path.exists(json_path):
        print(f"❌ Error running Lighthouse for {preset}: {res.stderr or res.stdout}")
        return None, None

    return json_path, html_path


def parse_and_summarize(json_path, label):
    """Parses a Lighthouse JSON report and prints a detailed terminal summary."""
    if not os.path.exists(json_path):
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cats = data.get("categories", {})
    audits = data.get("audits", {})

    print("\n" + "=" * 60)
    print(f" 📊 LIGHTHOUSE AUDIT REPORT: {label.upper()}")
    print("=" * 60)
    
    print("\n--- CATEGORY SCORES ---")
    for cid, cat in cats.items():
        score = cat.get("score")
        score_pct = f"{score * 100:.0f}/100" if score is not None else "N/A"
        print(f"  - {cat.get('title'):<25}: {score_pct}")

    print("\n--- CORE PERFORMANCE METRICS ---")
    key_metrics = [
        ("first-contentful-paint", "First Contentful Paint"),
        ("largest-contentful-paint", "Largest Contentful Paint"),
        ("total-blocking-time", "Total Blocking Time"),
        ("cumulative-layout-shift", "Cumulative Layout Shift"),
        ("speed-index", "Speed Index"),
        ("interactive", "Time to Interactive"),
        ("server-response-time", "Server Response Time (TTFB)")
    ]
    for km_id, km_title in key_metrics:
        if km_id in audits:
            a = audits[km_id]
            val = a.get("displayValue", f"{a.get('numericValue', 0):.2f}")
            score = a.get("score", 0)
            score_str = f"[{score * 100:.0f}/100]" if score is not None else ""
            print(f"  - {km_title:<30}: {val:<15} {score_str}")

    print("\n--- TOP OPTIMIZATION OPPORTUNITIES ---")
    opps = []
    for aid, a in audits.items():
        if a.get("details", {}).get("type") == "opportunity":
            wasted_ms = a.get("details", {}).get("overallSavingsMs", 0)
            wasted_bytes = a.get("details", {}).get("overallSavingsBytes", 0)
            if wasted_ms > 0 or wasted_bytes > 0:
                opps.append((wasted_ms, wasted_bytes, a.get("title"), a.get("displayValue", "")))

    opps.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if opps:
        for wasted_ms, wasted_bytes, title, disp in opps[:5]:
            savings = []
            if wasted_ms > 0:
                savings.append(f"{wasted_ms:.0f} ms")
            if wasted_bytes > 0:
                savings.append(f"{wasted_bytes / 1024:.1f} KB")
            print(f"  - {title}: Saves ~{', '.join(savings)} ({disp})")
    else:
        print("  - No major automated opportunities flagged.")

    print("\n--- NETWORK ASSET BREAKDOWN ---")
    network_items = audits.get("network-requests", {}).get("details", {}).get("items", [])
    if network_items:
        by_type = {}
        total_transfer = 0
        for item in network_items:
            rtype = item.get("resourceType", "other")
            tsize = item.get("transferSize", 0)
            by_type.setdefault(rtype, {"count": 0, "transfer": 0})
            by_type[rtype]["count"] += 1
            by_type[rtype]["transfer"] += tsize
            total_transfer += tsize

        for rtype, stat in by_type.items():
            print(f"  - {rtype:<15}: {stat['count']:>2} requests | Transfer: {stat['transfer'] / 1024:>7.1f} KB")
        print(f"  Total Network Payload: {total_transfer / 1024:.1f} KB across {len(network_items)} requests")


def main():
    parser = argparse.ArgumentParser(description="Run Lighthouse audits and generate performance reports.")
    parser.add_argument("url", nargs="?", default="https://pre-consult.org", help="Target URL to audit")
    parser.add_argument("--output-dir", default=".", help="Directory to save report artifacts")
    parser.add_argument("--preset", choices=["mobile", "desktop", "both"], default="both", help="Audit profile preset")

    args = parser.parse_args()

    chrome_path = find_chrome()
    if not chrome_path:
        print("⚠️ Warning: No local Chrome/Chromium installation found. Lighthouse may use fallback.")

    os.makedirs(args.output_dir, exist_ok=True)
    presets = ["mobile", "desktop"] if args.preset == "both" else [args.preset]

    for p in presets:
        prefix = os.path.join(args.output_dir, f"lighthouse-{p}")
        json_file, html_file = run_lighthouse(args.url, p, prefix, chrome_path)
        if json_file:
            parse_and_summarize(json_file, p)
            print(f"\n📁 Saved HTML Report: {html_file}")
            print(f"📁 Saved JSON Report: {json_file}")

    print("\n✅ Lighthouse audit completed successfully.")


if __name__ == "__main__":
    main()
