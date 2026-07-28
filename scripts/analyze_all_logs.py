#!/usr/bin/env python3
"""
Combined Log & Infrastructure Analyzer for Cloud Run and Cloudflare.
Runs both Cloud Run and Cloudflare log analyses for the past N hours.
Usage:
    python3 scripts/analyze_all_logs.py [--hours 24]
"""

import os
import sys
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cr_script = os.path.join(script_dir, "analyze_cloudrun_logs.py")
    cf_script = os.path.join(script_dir, "analyze_cloudflare_logs.py")

    hours = 24
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        hours = int(sys.argv[1])

    print("\n=======================================================")
    print(f"🚀 RUNNING UNIFIED INFRASTRUCTURE LOG ANALYSIS (LAST {hours}H)")
    print("=======================================================")

    print("\n-------------------------------------------------------")
    print("1. CLOUD RUN LOGS (GCP LOGGING)")
    print("-------------------------------------------------------")
    subprocess.run([sys.executable, cr_script, "--hours", str(hours)])

    print("\n-------------------------------------------------------")
    print("2. CLOUDFLARE CONFIGURATION & ANALYTICS")
    print("-------------------------------------------------------")
    subprocess.run([sys.executable, cf_script])

if __name__ == "__main__":
    main()
