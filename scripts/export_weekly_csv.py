"""Weekly exports for NORTH traces.

Reads JSONL logs in ./logs and produces:
- ./exports/north_events_<week>.csv (event-level)
- ./exports/north_sessions_<week>.csv (Ψ-lite session summary)

Ψ-lite is a pragmatic proxy for 'global identity coherence' over recent evaluations.
"""

import csv
import glob
import json
import os
import datetime as dt
from collections import defaultdict
from statistics import pvariance


def week_tag(d: dt.date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}_W{iso.week:02d}"


def read_events(log_dir: str) -> list[dict]:
    events = []
    for path in sorted(glob.glob(os.path.join(log_dir, "north_trace_*.jsonl"))):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def psi_lite(L_values: list[float]) -> float:
    """Map variance in admissibility to a 0..1 coherence proxy.

    - Low variance => high Ψ (stable region)
    - High variance => low Ψ (boundary/fracture region)
    """
    if not L_values:
        return 0.0
    if len(L_values) == 1:
        return 1.0
    var = pvariance(L_values)
    # Normalize with a pragmatic cap. For L in [0,1], variance rarely exceeds ~0.25 in practice.
    norm = min(var / 0.06, 1.0)  # 0.06 ~ noticeable volatility
    return round(1.0 - norm, 4)


def main():
    base = os.path.dirname(os.path.dirname(__file__))
    log_dir = os.path.join(base, "logs")
    out_dir = os.path.join(base, "exports")
    os.makedirs(out_dir, exist_ok=True)

    events = read_events(log_dir)
    if not events:
        print("No events found.")
        return

    today = dt.date.today()
    tag = week_tag(today)

    # Event-level CSV
    ev_path = os.path.join(out_dir, f"north_events_{tag}.csv")
    ev_fields = [
        "_ts_ms",
        "session_id",
        "branch_id",
        "parent_branch_id",
        "branch_depth",
        "read_index",
        "status",
        "event_type",
        "byok",
        "model_used",
        "I",
        "R",
        "Sem",
        "L",
        "tau",
        "rho",
        "tonic_id",
    ]
    with open(ev_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ev_fields)
        w.writeheader()
        for e in events:
            s = e.get("scores") or {}
            w.writerow({
                "_ts_ms": e.get("_ts_ms"),
                "session_id": e.get("session_id"),
                "branch_id": e.get("branch_id"),
                "parent_branch_id": e.get("parent_branch_id"),
                "branch_depth": e.get("branch_depth"),
                "read_index": e.get("read_index"),
                "status": e.get("status"),
                "event_type": e.get("event_type"),
                "byok": e.get("byok"),
                "model_used": e.get("model_used"),
                "I": s.get("I"),
                "R": s.get("R"),
                "Sem": s.get("Sem"),
                "L": s.get("L"),
                "tau": s.get("tau"),
                "rho": s.get("rho"),
                "tonic_id": e.get("tonic_id"),
            })

    # Session-level Ψ-lite summary
    by_session: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        sid = e.get("session_id") or "unknown"
        by_session[sid].append(e)

    sess_path = os.path.join(out_dir, f"north_sessions_{tag}.csv")
    sess_fields = [
        "session_id",
        "n_events",
        "n_branches",
        "refusal_rate",
        "psi_lite",
        "mean_L",
        "mean_rho",
    ]
    with open(sess_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sess_fields)
        w.writeheader()
        for sid, evs in by_session.items():
            Ls = []
            rhos = []
            statuses = []
            branches = set()
            for e in evs:
                s = e.get("scores") or {}
                if s.get("L") is not None:
                    Ls.append(float(s.get("L")))
                if s.get("rho") is not None:
                    rhos.append(float(s.get("rho")))
                if e.get("status"):
                    statuses.append(e.get("status"))
                if e.get("branch_id"):
                    branches.add(e.get("branch_id"))
            refusal_rate = (sum(1 for s in statuses if s == "REFUSAL") / len(statuses)) if statuses else 0.0
            mean_L = round(sum(Ls) / len(Ls), 4) if Ls else 0.0
            mean_rho = round(sum(rhos) / len(rhos), 4) if rhos else 0.0
            w.writerow({
                "session_id": sid,
                "n_events": len(evs),
                "n_branches": len(branches),
                "refusal_rate": round(refusal_rate, 4),
                "psi_lite": psi_lite(Ls),
                "mean_L": mean_L,
                "mean_rho": mean_rho,
            })

    print(f"Wrote: {ev_path}")
    print(f"Wrote: {sess_path}")


if __name__ == "__main__":
    main()
