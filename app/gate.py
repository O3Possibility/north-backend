import re
import pandas as pd
import random
from typing import Any, Dict, Optional, List
import statistics
from app.branch_registry import create_branch
from app.config import settings
from app.torsion import TorsionInputs, calculate_rho, tau_from_rho
from app.chord import ConscienceChordEngine
from app.providers import get_adapter
from app.logging_utils import log_event

MAX_PASSES = 2

# --- UPDATED: STRICT HIERARCHICAL TEMPLATE ---
SYSTEM_TEMPLATE = """
You are the NORTH Admissibility Gate.

### CHORD (ACTIVE LENSES)
TONIC: {tonic}
BALLASTS:
{ballasts}

### PROTOCOL
1. INTENT: Summarize user goal using bold headers.
2. AUDIT: Use the TONIC and BALLAST lenses to score I, R, and Sem. 
3. OUTPUT: Strictly follow the hierarchical Markdown format below.

### OUTPUT FORMAT (STRICT)
[INTENT]
**User Goal:** [Brief summary]
**Primary Tension:** [Identify the structural conflict]

[I] 0.00
[R] 0.00
[Sem] 0.00
[L]

[STATUS] ADMISSIBLE | REFUSAL

[FUSED MEANING OBJECT]
### Core Conflict
[Describe the friction between short-term actions and long-term systemic integrity.]

### Framework Alignment
* **Tonic ({tonic_name}):** [How the Tonic views the act]
* **Ballasts:** * [Name 1]: [Contribution to logic]
  * [Name 2]: [Contribution to logic]

### Actionable Guidance
**[Final Status Justification]**
[Provide the final response here. Use bold text for emphasis on critical path changes.]

[REPAIR/FEEDBACK]
**Diagnostic Summary:** [Explain I/R/Sem scores]
**Framework Contribution:** [Identify specific frameworks from the Chord]
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
2) Preserve tension: do not smooth contradictions; surface them.
3) Name the specific frameworks from the Chord that caused the low score.

### CURRENT CHORD
TONIC:
{tonic}

BALLASTS:
{ballasts}

### PREVIOUS DRAFT
{draft}

### OUTPUT FORMAT (STRICT)
[INTENT]
**User Goal:** ...
[I] 0.00
[R] 0.00
[Sem] 0.00
[L]
[STATUS] ADMISSIBLE | REFUSAL

[FUSED MEANING OBJECT]
### Core Conflict
...
### Framework Alignment
* **Tonic ({tonic_name}):** ...
* **Ballasts:** ...
### Actionable Guidance
...

[REPAIR/FEEDBACK]
...
"""

def estimate_torsion_inputs(prompt: str) -> TorsionInputs:
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
    return float(m.group(1)) if m else None

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
    _pool_k = pool_k if pool_k is not None else settings.BALLAST_POOL_K
    
    chord = None
    tonic_doc = ""
    ballast_docs = []

    # --- CHORD RESOLUTION LOGIC ---
    try:
        engine = ConscienceChordEngine()
        chord_res = engine.get_chord(prompt, ballast_pool_k=_pool_k)
        if chord_res:
            chord = chord_res
            tonic_doc = chord["tonic"]["doc"]
            ballast_docs = [b["doc"] for b in chord["ballasts"]]
        else:
            raise ValueError("ChromaDB empty")
    except Exception:
        # Fallback to CSV
        try:
            df = pd.read_csv("MASTER_CANONICAL.csv")
            sample_size = min(len(df), 5)
            selected = df.sample(n=sample_size)
            
            # Clean ID extraction to prevent 'nan' strings breaking the UI
            tonic_id = str(selected.iloc[0].get("ID_MASTER", "T-01"))
            if tonic_id.lower() == "nan": tonic_id = "T-01"
            tonic_name = str(selected.iloc[0].get("Framework_Name", "Unknown Framework"))
            
            chord = {
                "tonic": {
                    "id": tonic_id,
                    "doc": f"Framework: {tonic_name}. Core Triad: {selected.iloc[0].get('Core_Triad')}. Blurb: {selected.iloc[0].get('Blurb')}",
                    "meta": {"name": tonic_name}
                },
                "ballasts": []
            }
            
            for i, row in selected.iloc[1:].iterrows():
                b_id = str(row.get("ID_MASTER", f"B-{i}"))
                if b_id.lower() == "nan": b_id = f"B-{i}"
                b_name = str(row.get("Framework_Name", "Unknown Framework"))
                
                chord["ballasts"].append({
                    "id": b_id,
                    "doc": f"Framework: {b_name}. Core Triad: {row.get('Core_Triad')}. Blurb: {row.get('Blurb')}",
                    "meta": {"name": b_name}
                })
                
            tonic_doc = chord["tonic"]["doc"]
            ballast_docs = [b["doc"] for b in chord["ballasts"]]
        except Exception as e2:
            print(f"FAILED ALL CHORD ATTEMPTS: {e2}")
            chord = {
                "tonic": {"id": "SYS-T01", "doc": "Triadic Systems Theory: Logic of three-axis constraints.", "meta": {"name": "Triadic Systems"}},
                "ballasts": [{"id": "SYS-B01", "doc": "Indicator Stability: Semantic drift measurement.", "meta": {"name": "Semantic Stability"}}]
            }
            tonic_doc = chord["tonic"]["doc"]
            ballast_docs = [b["doc"] for b in chord["ballasts"]]

    # Extract clean tonic name for the template formatting
    current_tonic_name = chord["tonic"]["meta"].get("name", "Unknown Framework")

    sys = SYSTEM_TEMPLATE.format(
        tonic=tonic_doc,
        ballasts="\n\n---\n\n".join(ballast_docs),
        base_tau=settings.BASE_TAU,
        tau=tau,
        rho=rho,
        rho_crit=settings.RHO_CRIT,
        tonic_name=current_tonic_name
    )

    adapter, provider_used = get_adapter(model_choice, provider_override=provider, api_key=api_key, model_name=model_name, api_base=api_base)
    raw1 = adapter.generate(system=sys, prompt=prompt)

    def parse_all(text: str):
        I, R, Sem, L = _parse_score(text, "I"), _parse_score(text, "R"), _parse_score(text, "Sem"), _parse_score(text, "L")
        status = _parse_status(text) or "ADMISSIBLE"
        if L is None and (I is not None and R is not None and Sem is not None):
            L = float(I * R * Sem)
        missing = [tag for tag, val in [("I", I), ("R", R), ("Sem", Sem), ("L", L)] if val is None]
        return I, R, Sem, L, status, missing

    I1, R1, Sem1, L1, status1, missing1 = parse_all(raw1)

    if rho >= settings.RHO_CRIT:
        event, status_final, raw_final = "TORSION_FRACTURE", "REFUSAL", raw1
        I, R, Sem, L, missing, L2, attempted_repair = I1, R1, Sem1, L1, missing1, None, False
    else:
        need_repair = (len(missing1) > 0) or (L1 is None) or (L1 < tau)
        attempted_repair = bool(need_repair and MAX_PASSES >= 2)
        raw_final, I, R, Sem, L, missing, L2 = raw1, I1, R1, Sem1, L1, missing1, None

        if attempted_repair:
            repair_sys = REPAIR_TEMPLATE.format(
                missing=", ".join(missing1) if missing1 else "none",
                L=L1 if L1 is not None else 0.0,
                tau=tau,
                rho=rho,
                rho_crit=settings.RHO_CRIT,
                tonic=tonic_doc,
                ballasts="\n\n---\n\n".join(ballast_docs),
                draft=raw1[:1800],
                tonic_name=current_tonic_name
            )
            raw2 = adapter.generate(system=repair_sys, prompt=prompt)
            I, R, Sem, L, status2, missing = parse_all(raw2)
            raw_final, L2 = raw2, L

        status_final = "ADMISSIBLE" if (L is not None and not missing and L >= tau) else "REFUSAL"
        if attempted_repair:
            event = "BOIL_UP" if status_final == "ADMISSIBLE" else "BOIL_FAIL"
        else:
            event = "STABLE_ADMISSIBLE" if status_final == "ADMISSIBLE" else "STABLE_REFUSAL"

    fmo = _extract_fmo(raw_final)
    
    # --- UPDATED: EXPLICIT LINEAGE PAYLOAD ---
    # We pass 'name' directly at the top level of the object so the frontend catches it easily.
    chord_payload = {
        "tonic": {
            "id": str(chord["tonic"]["id"]), 
            "name": str(chord["tonic"]["meta"].get("name", "Unknown")),
            "meta": chord["tonic"]["meta"]
        },
        "ballasts": [
            {
                "id": str(b["id"]), 
                "name": str(b["meta"].get("name", "Unknown")),
                "meta": b["meta"]
            } for b in chord["ballasts"]
        ],
    }

    return {
        "status": status_final,
        "model_used": provider_used,
        "fused_meaning_object": fmo,
        "raw_text": raw_final,
        "scores": {"I": I, "R": R, "Sem": Sem, "L": L, "tau": tau, "rho": rho, "rho_crit": settings.RHO_CRIT},
        "chord": chord_payload,
        "diagnostics": {"event_type": event, "attempted_repair": attempted_repair, "missing_scores": missing, "L_pass1": L1, "L_pass2": L2},
    }

def evaluate(prompt: str, model_choice: str = "default", provider: str | None = None, api_key: str | None = None,
             model_name: str | None = None, api_base: str | None = None, session_id: str | None = None,
             parent_branch_id: str | None = None, n_reads: int = 1) -> Dict[str, Any]:
    ti = estimate_torsion_inputs(prompt)
    rho = calculate_rho(ti)
    tau = tau_from_rho(settings.BASE_TAU, rho, settings.TAU_BUMP_MAX)
    pool_k = int(settings.BALLAST_POOL_K * (1.8 if rho > 0.6 else 1.4 if rho > 0.35 else 1.0))
    
    branch = create_branch(session_id=session_id, parent_branch_id=parent_branch_id)
    reads = max(1, min(int(n_reads or 1), 3))
    read_payloads = []

    for idx in range(reads):
        rp = _evaluate_single_read(prompt, model_choice, rho, tau, provider, api_key, model_name, api_base, pool_k)
        rp["read_index"] = idx
        read_payloads.append(rp)
        
        cp = rp.get("chord")
        log_event({
            "session_id": branch.session_id, "branch_id": branch.branch_id, "parent_branch_id": branch.parent_branch_id,
            "read_index": idx, "prompt": prompt, "status": rp.get("status"), "scores": rp.get("scores"),
            "tonic_id": cp["tonic"]["id"] if cp else None,
            "ballast_ids": [b["id"] for b in cp.get("ballasts", [])] if cp else None,
            "byok": bool(api_key and api_key.strip()),
        })

    best = max(read_payloads, key=lambda r: (r.get("scores", {}).get("L") or -1.0))
    final_status = "REFUSAL" if any(r["diagnostics"]["event_type"] == "TORSION_FRACTURE" for r in read_payloads) else \
                   ("ADMISSIBLE" if sum(1 for r in read_payloads if r["status"] == "ADMISSIBLE") > (len(read_payloads)/2) else "REFUSAL")

    return {
        "status": final_status, "model_used": best.get("model_used"), "fused_meaning_object": best.get("fused_meaning_object"),
        "raw_text": best.get("raw_text"), "scores": best.get("scores"), "chord": best.get("chord"),
        "branch": {"session_id": branch.session_id, "branch_id": branch.branch_id, "depth": branch.depth},
        "diagnostics": {"reads": reads, "event_type": best.get("diagnostics", {}).get("event_type")},
        "reads": read_payloads if reads > 1 else None,
    }
