from app.adapters.base import ModelAdapter

class MockAdapter(ModelAdapter):
    def generate(self, system: str, prompt: str) -> str:
        # Deterministic mock: demonstrates format only
        return (
            "[INTENT]\n"
            "Demonstrate the NORTH admissibility workflow in mock mode.\n\n"
            "[I] 0.65\n"
            "Grounded enough to evaluate (mock).\n\n"
            "[R] 0.62\n"
            "Coupling under chord tension (mock).\n\n"
            "[Sem] 0.66\n"
            "Coherence over time/scale (mock).\n\n"
            "[L]\n"
            "0.266\n\n"
            "[STATUS] REFUSAL\n\n"
            "[FUSED MEANING OBJECT]\n"
            "Mock strict-first: showing refusal as a valid state. Deploy with Ollama locally for real inference.\n\n"
            "[REPAIR/FEEDBACK]\n"
            "Provide more context, reduce recursion, or narrow scope to reduce torsion."
        )
