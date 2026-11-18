import argparse
import os
import sys
import time

import pandas as pd
import requests

sys.path.append(os.path.dirname(__file__))
from replay import DATA_PATH, build_message


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True, help="base URL, e.g. https://xxx.onrender.com")
    p.add_argument("--n", type=int, default=200, help="number of readings to send")
    p.add_argument("--timeout", type=float, default=30)
    args = p.parse_args()

    base = args.url.rstrip("/")
    session = requests.Session()

    # Wake the service first and record how long the wake-up takes
    t0 = time.time()
    r = session.get(base + "/health", timeout=120)
    print(f"Health: HTTP {r.status_code} in {time.time() - t0:.1f} s -> {r.json()}")

    df = pd.read_csv(DATA_PATH).head(args.n)
    latencies, errors = [], 0
    start = time.time()
    for _, row in df.iterrows():
        message = build_message(row)
        t = time.time()
        try:
            resp = session.post(base + "/readings", json=message, timeout=args.timeout)
            resp.raise_for_status()
            latencies.append((time.time() - t) * 1000)
        except Exception as e:
            errors += 1
            print("error:", type(e).__name__)
    total = time.time() - start

    print(f"\nSent: {len(df)}  OK: {len(latencies)}  Errors: {errors}")
    print(f"Total time: {total:.1f} s  Throughput: {len(latencies) / total:.2f} readings/s")
    if latencies:
        latencies.sort()
        pick = lambda q: latencies[min(len(latencies) - 1, int(q / 100 * len(latencies)))]
        print(f"Latency per request (ms): mean {sum(latencies) / len(latencies):.0f}, "
              f"median {pick(50):.0f}, p95 {pick(95):.0f}, max {latencies[-1]:.0f}")


if __name__ == "__main__":
    main()