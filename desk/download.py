"""Download 4 years of public history from data.binance.vision.

Every file is checked against Binance's own .CHECKSUM (sha256) and logged in
data/manifest.csv with its URL and download time, so each number has a source.

Run:  python -m desk.download
"""

import csv
import hashlib
import io
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from desk.config import HISTORY_END, HISTORY_START, MARKETS, PERPS

BASE = "https://data.binance.vision/data"
RAW = Path("data/raw")
MANIFEST = Path("data/manifest.csv")


def months(start: date, end: date):
    """Yield (year, month) for every full month between start and end."""
    y, m = start.year, start.month
    while (y, m) < (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def days_of_last_month(end: date):
    d = end.replace(day=1)
    while d <= end:
        yield d
        d += timedelta(days=1)


def all_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def build_jobs():
    """List every (url, local path) we need."""
    jobs = []
    for spec in MARKETS.values():
        market, symbol = spec["hist"]
        for y, m in months(HISTORY_START, HISTORY_END):
            name = f"{symbol}-1h-{y}-{m:02d}.zip"
            jobs.append((f"{BASE}/{market}/monthly/klines/{symbol}/1h/{name}", RAW / market / "klines" / name))
        for d in days_of_last_month(HISTORY_END):
            name = f"{symbol}-1h-{d.isoformat()}.zip"
            jobs.append((f"{BASE}/{market}/daily/klines/{symbol}/1h/{name}", RAW / market / "klines" / name))

    for symbol in PERPS:
        for y, m in months(HISTORY_START, HISTORY_END):
            name = f"{symbol}-fundingRate-{y}-{m:02d}.zip"
            jobs.append((f"{BASE}/futures/um/monthly/fundingRate/{symbol}/{name}", RAW / "funding" / name))
        # open interest + long/short ratios: only published as daily files
        for d in all_days(HISTORY_START, HISTORY_END):
            name = f"{symbol}-metrics-{d.isoformat()}.zip"
            jobs.append((f"{BASE}/futures/um/daily/metrics/{symbol}/{name}", RAW / "metrics" / name))

    # Real gold perp (short history) for cross-checking PAXG against XAU
    for y, m in months(date(2025, 12, 1), HISTORY_END):
        name = f"XAUUSDT-1h-{y}-{m:02d}.zip"
        jobs.append((f"{BASE}/futures/um/monthly/klines/XAUUSDT/1h/{name}", RAW / "futures/um" / "klines" / name))
    return jobs


def fetch(url: str, tries: int = 4) -> bytes | None:
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2**i)
        except Exception:
            time.sleep(2**i)
    raise RuntimeError(f"failed after {tries} tries: {url}")


def download_one(job):
    url, path = job
    if path.exists():
        return url, path, "cached", ""
    data = fetch(url)
    if data is None:
        return url, path, "missing", ""
    expected = (fetch(url + ".CHECKSUM") or b"").decode().split()
    actual = hashlib.sha256(data).hexdigest()
    if expected and expected[0] != actual:
        return url, path, "BAD_CHECKSUM", actual
    zipfile.ZipFile(io.BytesIO(data)).testzip()  # raises if corrupt
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return url, path, "ok", actual


def main():
    jobs = build_jobs()
    print(f"{len(jobs)} files to check")
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    new_file = not MANIFEST.exists()
    counts = {}
    with MANIFEST.open("a", newline="") as f, ThreadPoolExecutor(16) as pool:
        w = csv.writer(f)
        if new_file:
            w.writerow(["url", "local_path", "status", "sha256", "downloaded_at_utc"])
        for url, path, status, sha in pool.map(download_one, jobs):
            counts[status] = counts.get(status, 0) + 1
            if status != "cached":
                w.writerow([url, str(path), status, sha, datetime.now(timezone.utc).isoformat(timespec="seconds")])
    print(counts)
    if counts.get("BAD_CHECKSUM"):
        sys.exit("checksum mismatch: see data/manifest.csv")


if __name__ == "__main__":
    main()
