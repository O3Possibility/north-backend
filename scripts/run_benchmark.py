"""
Run a local benchmark against NORTH (raw vs gated), log results to CSV.

Requires backend running locally:
  uvicorn app.main:app --reload

Usage:
  python scripts/run_benchmark.py --api http://127.0.0.1:8000 --bench ../benchmarks/benchmark_100.jsonl --out ../benchmarks/results.csv
"""

import argparse, json, csv, time, requests
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True, help="API base, e.g. http://127.0.0.1:8000")
    ap.add_argument("--bench", required=True, help="Path to benchmark JSONL")
    ap.add_argument("--out", required=True, help="Output CSV path")
    args = ap.parse_args()

    bench_path = Path(args.bench)
    out_path = Path(args.out)
    rows = []

    for line in bench_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        pid = item.get("id")
        prompt = item.get("prompt")
        bucket = item.get("bucket")

        t0 = time.time()
        r = requests.post(f"{args.api}/evaluate", json={"prompt": prompt, "model": "ollama"})
        ms = int((time.time() - t0) * 1000)
        r.raise_for_status()
        data = r.json()

        rows.append({
            "id": pid,
            "bucket": bucket,
            "ms": ms,
            "status": data.get("status"),
            "I": data.get("scores",{}).get("I"),
            "R": data.get("scores",{}).get("R"),
            "Sem": data.get("scores",{}).get("Sem"),
            "L": data.get("scores",{}).get("L"),
            "tau": data.get("scores",{}).get("tau"),
            "rho": data.get("scores",{}).get("rho"),
            "rho_crit": data.get("scores",{}).get("rho_crit"),
            "tonic_id": (data.get("chord") or {}).get("tonic",{}).get("id"),
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        for row in rows:
            w.writerow(row)

    print(f"Wrote {len(rows)} rows -> {out_path}")

if __name__ == "__main__":
    main()
