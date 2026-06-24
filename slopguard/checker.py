"""
checker.py — talks to the real package registries and answers one question:
does this package actually exist?

This is the entire "detection" logic. Everything else in slopguard is just
finding package names and formatting the answer.
"""
from __future__ import annotations
import urllib.request
import urllib.error
import json
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 6  # seconds — fail fast, don't hang CI


@dataclass
class PackageResult:
    name: str
    ecosystem: str          # "pypi" or "npm"
    exists: bool
    source_file: str
    detail: str = ""        # extra context, e.g. "published 2 days ago"


def _get(url: str) -> tuple[int, dict | None]:
    """Tiny HTTP GET helper. Returns (status_code, json_body_or_None)."""
    req = urllib.request.Request(url, headers={"User-Agent": "slopguard/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        # network hiccup — treat as "unknown", never as "doesn't exist"
        return -1, None


def check_pypi(name: str, source_file: str) -> PackageResult:
    status, body = _get(f"https://pypi.org/pypi/{name}/json")
    if status == 200:
        detail = ""
        if body and "releases" in body:
            n_releases = len(body["releases"])
            detail = f"{n_releases} release(s) on PyPI"
        return PackageResult(name, "pypi", True, source_file, detail)
    if status == 404:
        return PackageResult(name, "pypi", False, source_file, "no PyPI project with this exact name")
    # network error / rate limit — don't false-flag, mark as exists=True with a note
    return PackageResult(name, "pypi", True, source_file, "could not verify (network) — skipped")


def check_npm(name: str, source_file: str) -> PackageResult:
    status, body = _get(f"https://registry.npmjs.org/{name}")
    if status == 200:
        detail = ""
        if body and "time" in body and "created" in body["time"]:
            detail = f"first published {body['time']['created'][:10]}"
        return PackageResult(name, "npm", True, source_file, detail)
    if status == 404:
        return PackageResult(name, "npm", False, source_file, "no npm package with this exact name")
    return PackageResult(name, "npm", True, source_file, "could not verify (network) — skipped")


def check_all(packages: list[tuple[str, str, str]], max_workers: int = 8) -> list[PackageResult]:
    """
    packages: list of (name, ecosystem, source_file)
    Runs checks concurrently — without this, checking 80 packages one-by-one
    over the network would take a minute instead of a few seconds.
    """
    results: list[PackageResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = []
        for name, eco, src in packages:
            fn = check_pypi if eco == "pypi" else check_npm
            futures.append(pool.submit(fn, name, src))
        for f in as_completed(futures):
            results.append(f.result())
    return results
