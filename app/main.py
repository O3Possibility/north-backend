import os
import httpx
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup logging to see the exact Mistral response in Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NORTH Conscience API", version="0.6.0-direct-sync")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://o3possibility.github.io", "http://o3possibility.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b" # Mistral's standard stable model

@app.get("/health")
def health():
    return {"ok": True, "service": "north"}

@app.post("/evaluate")
async def evaluate(request: EvaluationRequest):
    # Enforce the 5 Frameworks and Triadic Mapping in the System Prompt
    SYSTEM_INSTRUCTIONS = (
        "Output your analysis in this EXACT format:\n\n"
        "### 1. AUDITABLE FRAMEWORKS\n"
        "- Governance, Science, Philosophy, Engineering, Culture\n\n"
        "### 2. TRIADIC MAPPING (I/R/Sem)\n"
        "- **Intent (I)**: [Analysis]\n"
        "- **Reality (R)**: [Analysis]\n"
        "- **Semantics (Sem)**: [Analysis]\n\n"
        "### 3. TORSION SCORE\n"
        "SCORE: [0-100]% | [Brief justification for drift]\n\n"
        "### 4. FUSED MEANING OBJECT (FMO)\n"
        "[Final Admissibility Statement]"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"},
            json={
                "model": "open-mistral-7b",
                "messages": [
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": request.prompt}
                ],
                "temperature": 0.1 # Low temp for high precision
            }
        )
        # ... existing return logic ...
