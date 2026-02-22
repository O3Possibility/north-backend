import math
from dataclasses import dataclass

@dataclass(frozen=True)
class TorsionInputs:
    scope: float
    fidelity: float
    stability: float
    recursion_depth: int

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def calculate_rho(inputs: TorsionInputs) -> float:
    # Strict-first sensor: monotonic, bounded-ish, recursion-sensitive
    scope = clamp(inputs.scope, 0.0, 1.0)
    fidelity = clamp(inputs.fidelity, 0.0, 1.0)
    stability = clamp(inputs.stability, 0.1, 1.0)
    rd = max(0, int(inputs.recursion_depth))

    intent_volume = scope * fidelity
    twist_density = intent_volume / stability

    # Recursion grows nonlinearly but damped (prevents wild blowups)
    recursion_gain = 1.0 + math.log(rd + 1.0) ** 1.6
    rho = twist_density * recursion_gain
    return float(rho)

def tau_from_rho(base_tau: float, rho: float, bump_max: float) -> float:
    # Adaptive τ: more torsion => stricter threshold, capped
    bump = clamp(rho * 0.22, 0.0, bump_max)
    return clamp(base_tau + bump, 0.0, 0.95)
