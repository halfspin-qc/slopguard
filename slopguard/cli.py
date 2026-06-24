"""
cli.py — the `slopguard` command. Scans a project, checks every declared
dependency against the real registry, reports anything that doesn't exist.
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

from .parsers import collect_packages
from .checker import check_all

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="slopguard",
        description="Check whether every declared dependency in this project actually exists on its registry.",
    )
    parser.add_argument("path", nargs="?", default=".", help="Project directory to scan (default: current dir)")
    parser.add_argument("--quiet", action="store_true", help="Only print problems, suppress the OK list")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"{RED}Path not found: {root}{RESET}")
        return 2

    print(f"{BOLD}slopguard{RESET} — scanning {root}")
    t0 = time.time()

    packages = collect_packages(root)
    if not packages:
        print(f"{YELLOW}No requirements.txt, pyproject.toml, or package.json found.{RESET}")
        return 0

    print(f"Found {len(packages)} declared dependencies. Checking against npm + PyPI...\n")
    results = check_all(packages)
    results.sort(key=lambda r: (r.exists, r.ecosystem, r.name.lower()))

    missing = [r for r in results if not r.exists]
    verified = [r for r in results if r.exists and "could not verify" not in r.detail]
    unverifiable = [r for r in results if r.exists and "could not verify" in r.detail]

    if missing:
        print(f"{RED}{BOLD}⚠ {len(missing)} package(s) NOT FOUND on their registry:{RESET}")
        for r in missing:
            print(f"  {RED}✗{RESET} {BOLD}{r.name}{RESET} [{r.ecosystem}] — declared in {DIM}{r.source_file}{RESET}")
            print(f"      {r.detail}")
        print()
        print(f"  {YELLOW}This is exactly the pattern attackers exploit: registering a plausible{RESET}")
        print(f"  {YELLOW}but nonexistent package name an AI tool suggested, hoping someone installs it.{RESET}")
        print(f"  {YELLOW}Before installing, double-check the name and consider it untrusted.{RESET}\n")

    if not args.quiet and verified:
        print(f"{GREEN}✓ {len(verified)} package(s) verified on registry{RESET}")
        for r in verified:
            extra = f" {DIM}({r.detail}){RESET}" if r.detail else ""
            print(f"  {GREEN}✓{RESET} {r.name} [{r.ecosystem}]{extra}")
        print()

    if unverifiable:
        print(f"{YELLOW}? {len(unverifiable)} package(s) could not be verified (network issue) — not flagged{RESET}\n")

    elapsed = time.time() - t0
    print(f"{DIM}Scanned {len(packages)} packages in {elapsed:.1f}s{RESET}")

    if missing:
        print(f"\n{RED}{BOLD}slopguard found {len(missing)} suspicious package(s). Failing.{RESET}")
        return 1

    print(f"{GREEN}{BOLD}All declared dependencies verified. Clean.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
