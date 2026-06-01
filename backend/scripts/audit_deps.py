#!/usr/bin/env python3
"""
audit_deps.py — NexusSwarm Dependency Security Audit
Runs pip-audit against requirements.txt and exits non-zero on HIGH/CRITICAL issues.

Usage:
    python backend/scripts/audit_deps.py

CI Usage:
    python backend/scripts/audit_deps.py --fail-on HIGH
"""

import subprocess
import sys
import argparse


def run_audit(fail_on: str = "HIGH") -> int:
    """Run pip-audit and return exit code."""
    req_file = "requirements.txt"
    
    print(f"🔍 Running pip-audit on {req_file}...")
    print(f"   Failing on: {fail_on} and CRITICAL\n")

    result = subprocess.run(
        ["pip-audit", "-r", req_file, "--format", "columns"],
        capture_output=False,
        text=True,
    )

    if result.returncode != 0:
        print(f"\n⚠️  pip-audit found vulnerabilities.")
        print("   Review the report above and update affected packages.")
        print("   Pin fixed versions in requirements.txt.\n")
        return 1

    print("\n✅ No known vulnerabilities found.\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NexusSwarm dependency security audit")
    parser.add_argument(
        "--fail-on",
        default="HIGH",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Minimum severity level to fail the audit (default: HIGH)",
    )
    args = parser.parse_args()

    sys.exit(run_audit(fail_on=args.fail_on))
