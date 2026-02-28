import re
from typing import Any, Dict, Optional, List
import statistics
from app.branch_registry import create_branch
from app.config import settings
from app.torsion import TorsionInputs, calculate_rho, tau_from_rho
from app.chord import ConscienceChordEngine
from app.providers import get_adapter
from app.logging_utils import log_event

MAX_PASSES = 2  # draft + 1 repair (keeps latency reasonable)

SYSTEM_TEMPLATE = """
You are the NORTH Admissibility Gate.
Evaluate the user's prompt through a 5-note chord of sense-making frameworks.

### CURRENT CHORD (YOUR LENSES)
TONIC (Primary):
{tonic}

BALLAST (Supporting):
{ballasts}

### SENSOR CONTEXT
- Base τ: {base_tau} | Adaptive τ: {tau}
- Torsion ρ: {rho} | ρcrit: {rho_crit}

### EVALUATION PROTOCOL
1) INTENT: Summarize intent in one sentence.
2) MAP I/R/Sem: 
   - I (Indicative): Factual floor and feasibility.
   - R (Relational): Ethical/safe coupling across the chord.
   - Sem (Semantic): Coherent meaning across scale.
3) COMPUTE: L = I * R * Sem.
4) DECISION: If ρ >= ρcrit or L < τ => REFUSAL.

### OUTPUT FORMAT (STRICT)
[INTENT]
...
[I] 0.00
[R] 0.00
[Sem] 0.00
[L]
...
[STATUS] ADMISSIBLE | REFUSAL
[FUSED MEANING OBJECT]
START by stating: "Evaluated via [Tonic Name] and [Ballast Names]."
Provide a clear, legible response filtered through these frameworks. Avoid excessive jargon.
[REPAIR/FEEDBACK]
Explain the specific logic behind your I, R, and Sem scores.
"""

REPAIR_TEMPLATE = """
You are the NORTH Admissibility Gate running a **REPAIR PASS**.
The previous draft failed admissibility (L: {L} < τ: {tau}).

### FAILURE DIAGNOSTICS
- Missing/Low Scores: {missing}
- Torsion ρ: {rho} (ρcrit: {rho_crit})

### REPAIR RULES
1) Preserve tension: surface contradictions, don't smooth them.
2) Name the specific frameworks from the Chord that caused the low score.
3) Adjust the Fused Meaning Object to be clearer and more grounded.

### CURRENT CHORD
TONIC:
{tonic}
BALLAST:
{ballasts}

### PREVIOUS DRAFT
{draft}

### OUTPUT FORMAT (STRICT)
[INTENT]\n...
[I] 0.00\n[R] 0.00\n[Sem] 0.00\n[L]\n...
[STATUS] ADMISSIBLE | REFUSAL\n[FUSED MEANING OBJECT]\n...
[REPAIR/FEEDBACK]\n...
"""

REPAIR_TEMPLATE = """
You are the NORTH Admissibility Gate running a **REPAIR PASS**.
The previous draft FAILED admissibility.

### FAILURE DIAGNOSTICS
- Missing scores: {missing}
- L: {L}
- τ: {tau}
- ρ: {rho} (ρcrit: {rho_crit})

### REPAIR RULES
1) Do NOT add new ungrounded factual claims.
2) Reduce overshoot. Prefer clarity over breadth.
3) If uncertainty is high, say so explicitly and ask one targeted question.
4) Preserve tension: do not smooth contradictions; surface them.
5) Respect the chord as *lenses*, not prescriptions. Do not introduce culturally-specific mandates unless asked.

### CURRENT CHORD (unchanged)
TONIC:
{tonic}

BALLAST:
{ballasts}

### PREVIOUS DRAFT (for repair)
{draft}

### OUTPUT FORMAT (STRICT)
[INTENT]\n...
[I] 0.00-1.00\n...
[R] 0.00-1.00\n...
[Sem] 0.00-1.00\n...
[L]\n...
[STATUS] ADMISSIBLE | REFUSAL\n[FUSED MEANING OBJECT]\n...
[REPAIR/FEEDBACK]\n...
"""

def estimate_torsion_inputs(prompt: str) -> TorsionInputs:
    # Simple first-pass estimator: tune later against benchmarks.
    p = prompt.lower().strip()

    high = ["bypass","exploit","hack","weapon","harm","fraud","manipulate","deceive","security","surveillance"]
    scope = min(1.0, 0.22 + 0.11 * sum(t in p for t in high))

    fidelity_terms = ["step-by-step","exact","code","script","commands","how do i","instructions"]
    fidelity = min(1.0, 0.18 + 0.12 * sum(t in p for t in fidelity_terms))

    recursion_terms = ["evaluate itself","recursive","self-referential","about this system","about the gate","conscience","north","triadic"]
    recursion_depth = sum(t in p for t in recursion_terms)

    stability = max(0.2, min(1.0, 0.86 - 0.06 * sum(t in p for t in high)))
    return TorsionInputs(scope=scope, fidelity=fidelity, stability=stability, recursion_depth=recursion_depth)

def _parse_score(text: str, tag: str) -> Optional[float]:
    m = re.search(rf"\[{re.escape(tag)}\]\s*([01](?:\.\d+)?)", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None

def _parse_status(text: str) -> Optional[str]:
    m = re.search(r"\[STATUS\]\s*(ADMISSIBLE|REFUSAL)", text, re.IGNORECASE)
    return m.group(1).upper() if m else None

def _extract_fmo(text: str) -> str:
    m = re.search(r"\[FUSED MEANING OBJECT\]\s*(.*?)(?:\n\[REPAIR/FEEDBACK\]|\Z)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()

def _evaluate_single_read(
    prompt: str,
    model_choice: str,
    rho: float,
    tau: float,
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    api_base: str | None = None,
    pool_k: int | None = None,
) -> Dict[str, Any]:
    """Evaluate a single chord read: select chord, run draft->repair loop, return read payload + diagnostics."""

    # Strict-first: expand ballast pool as torsion rises
    _pool_k = pool_k if pool_k is not None else settings.BALLAST_POOL_K

    chord = None
    tonic_doc = "(Chord unavailable: missing ChromaDB index.)"
    ballast_docs = []

    try:
        engine = ConscienceChordEngine()
        chord = engine.get_chord(prompt, ballast_pool_k=_pool_k)
        tonic_doc = chord["tonic"]["doc"]
        ballast_docs = [b["doc"] for b in chord["ballasts"]]
    except Exception:
        chord = None

    sys = SYSTEM_TEMPLATE.format(
        tonic=tonic_doc,
        ballasts="\n\n---\n\n".join(ballast_docs) if ballast_docs else "(No ballast frameworks available.)",
        base_tau=settings.BASE_TAU,
        tau=tau,
        rho=rho,
        rho_crit=settings.RHO_CRIT,
    )

    adapter, provider_used = get_adapter(model_choice, provider_override=provider, api_key=api_key, model_name=model_name, api_base=api_base)

    # PASS 1
    raw1 = adapter.generate(system=sys, prompt=prompt)

    def parse_all(text: str):
        I = _parse_score(text, "I")
        R = _parse_score(text, "R")
        Sem = _parse_score(text, "Sem")
        L = _parse_score(text, "L")
        status = _parse_status(text) or "ADMISSIBLE"
        if L is None and (I is not None and R is not None and Sem is not None):
            L = float(I * R * Sem)
        missing = []
        for tag, val in [("I", I), ("R", R), ("Sem", Sem), ("L", L)]:
            if val is None:
                missing.append(tag)
        return I, R, Sem, L, status, missing

    I1, R1, Sem1, L1, status1, missing1 = parse_all(raw1)

    # Torsion fracture short-circuit
    if rho >= settings.RHO_CRIT:
        event = "TORSION_FRACTURE"
        status_final = "REFUSAL"
        raw_final = raw1
        I, R, Sem, L, missing = I1, R1, Sem1, L1, missing1
        L2 = None
        attempted_repair = False
    else:
        need_repair = (len(missing1) > 0) or (L1 is None) or (L1 < tau)
        attempted_repair = bool(need_repair and MAX_PASSES >= 2)
        raw_final = raw1
        I, R, Sem, L, missing = I1, R1, Sem1, L1, missing1
        L2 = None

        if attempted_repair:
            repair_sys = REPAIR_TEMPLATE.format(
                missing=", ".join(missing1) if missing1 else "none",
                L=L1,
                tau=tau,
                rho=rho,
                rho_crit=settings.RHO_CRIT,
                tonic=tonic_doc,
                ballasts="\n\n---\n\n".join(ballast_docs) if ballast_docs else "(No ballast frameworks available.)",
                draft=raw1[:1800],
            )
            raw2 = adapter.generate(system=repair_sys, prompt=prompt)
            I2, R2, Sem2, L2p, status2, missing2 = parse_all(raw2)
            raw_final = raw2
            I, R, Sem, L, missing = I2, R2, Sem2, L2p, missing2
            L2 = L2p

        # Final thresholding
        if L is None or len(missing) > 0:
            status_final = "REFUSAL"
        elif L < tau:
            status_final = "REFUSAL"
        else:
            status_final = "ADMISSIBLE"

        if attempted_repair:
            # Phase-change events
            if (L1 is None or L1 < tau or len(missing1) > 0) and status_final == "ADMISSIBLE":
                event = "BOIL_UP"
            elif status_final == "REFUSAL":
                event = "BOIL_FAIL"
            else:
                event = "REPAIR_NOOP"
        else:
            event = "STABLE_ADMISSIBLE" if status_final == "ADMISSIBLE" else "STABLE_REFUSAL"

    fmo = _extract_fmo(raw_final)

    chord_payload = None
    if chord is not None:
        chord_payload = {
            "tonic": {"id": chord["tonic"]["id"], "meta": chord["tonic"]["meta"]},
            "ballasts": [{"id": b["id"], "meta": b["meta"]} for b in chord["ballasts"]],
        }

    return {
        "status": status_final,
        "model_used": provider_used,
        "fused_meaning_object": fmo,
        "raw_text": raw_final,
        "scores": {"I": I, "R": R, "Sem": Sem, "L": L, "tau": tau, "rho": rho, "rho_crit": settings.RHO_CRIT},
        "chord": chord_payload,
        "diagnostics": {
            "event_type": event,
            "attempted_repair": attempted_repair,
            "missing_scores": missing,
            "L_pass1": L1,
            "L_pass2": L2,
        },
    }


def evaluate(
    prompt: str,
    model_choice: str = "default",
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    api_base: str | None = None,
    session_id: str | None = None,
    parent_branch_id: str | None = None,
    n_reads: int = 1,
) -> Dict[str, Any]:
    """Evaluate a prompt under NORTH. Supports multi-read aperture sampling + branching trace."""
    ti = estimate_torsion_inputs(prompt)
    rho = calculate_rho(ti)
    tau = tau_from_rho(settings.BASE_TAU, rho, settings.TAU_BUMP_MAX)

    # Strict-first: expand ballast pool as torsion rises
    pool_k = settings.BALLAST_POOL_K
    if rho > 0.35:
        pool_k = int(pool_k * 1.4)
    if rho > 0.60:
        pool_k = int(pool_k * 1.8)
    # Branch lineage
    branch = create_branch(session_id=session_id, parent_branch_id=parent_branch_id)

    # Clamp reads to keep latency controlled
    reads = max(1, min(int(n_reads or 1), 3))
    read_payloads: List[Dict[str, Any]] = []

    for idx in range(reads):
        rp = _evaluate_single_read(
            prompt=prompt,
            model_choice=model_choice,
            rho=rho,
            tau=tau,
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            api_base=api_base,
            pool_k=pool_k,
        )
        rp["read_index"] = idx
        read_payloads.append(rp)

        # Per-read log line (same branch_id)
        chord_payload = rp.get("chord")
        log_event({
            "session_id": branch.session_id,
            "branch_id": branch.branch_id,
            "parent_branch_id": branch.parent_branch_id,
            "branch_depth": branch.depth,
            "read_index": idx,
            "prompt": prompt,
            "model_choice": model_choice,
            "provider": provider,
            "model_used": rp.get("model_used"),
            "status": rp.get("status"),
            "scores": rp.get("scores"),
            "event_type": rp.get("diagnostics", {}).get("event_type"),
            "missing_scores": rp.get("diagnostics", {}).get("missing_scores"),
            "L_pass1": rp.get("diagnostics", {}).get("L_pass1"),
            "L_pass2": rp.get("diagnostics", {}).get("L_pass2"),
            "tonic_id": chord_payload["tonic"]["id"] if chord_payload else None,
            "ballast_ids": [b["id"] for b in chord_payload.get("ballasts", [])] if chord_payload else None,
            "byok": bool(api_key and api_key.strip()),
        })

    # Aggregate aperture metrics
    Ls = [r.get("scores", {}).get("L") for r in read_payloads if r.get("scores", {}).get("L") is not None]
    statuses = [r.get("status") for r in read_payloads]
    refusal_rate = (sum(1 for s in statuses if s == "REFUSAL") / len(statuses)) if statuses else 0.0
    deltaL = statistics.pvariance(Ls) if len(Ls) >= 2 else 0.0

    # Choose a "best" read: highest L if available, else first
    best = read_payloads[0]
    if Ls:
        best = max(read_payloads, key=lambda r: (r.get("scores", {}).get("L") or -1.0))

    # Conservative consensus
    if any(r.get("diagnostics", {}).get("event_type") == "TORSION_FRACTURE" for r in read_payloads):
        final_status = "REFUSAL"
    else:
        admissible_votes = sum(1 for s in statuses if s == "ADMISSIBLE")
        final_status = "ADMISSIBLE" if admissible_votes > (len(statuses) / 2) else "REFUSAL"

    payload = {
        "status": final_status,
        "model_used": best.get("model_used"),
        "fused_meaning_object": best.get("fused_meaning_object"),
        "raw_text": best.get("raw_text"),
        "scores": best.get("scores"),
        "chord": best.get("chord"),
        "branch": {
            "session_id": branch.session_id,
            "branch_id": branch.branch_id,
            "parent_branch_id": branch.parent_branch_id,
            "depth": branch.depth,
        },
        "diagnostics": {
            "reads": reads,
            "refusal_rate": refusal_rate,
            "deltaL": deltaL,
            "event_type": best.get("diagnostics", {}).get("event_type"),
        },
        "reads": read_payloads if reads > 1 else None,
    }

    return payload
