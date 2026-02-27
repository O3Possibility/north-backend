import os, re, httpx, logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Re-integrating the actual gate logic from your app/gate.py
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH_CORE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"
    session_id: Optional[str] = None
    parent_branch_id: Optional[str] = None
    n_reads: int = 1

def extract_hardened_scores(text: str):
    """Targets digits explicitly to handle formatting like 0.4/1.0 or 40%."""
    try:
        def get_val(pattern, content):
            match = re.search(pattern, content)
            return match.group(1) if match else "0.00"

        return {
            "I": get_val(r"Indicative \(I\):\s*([\d\.]+)", text),
            "R": get_val(r"Relational \(R\):\s*([\d\.]+)", text),
            "Sem": get_val(r"Semantic \(Sem\):\s*([\d\.]+)", text),
            "rho": float(get_val(r"Score:\s*(\d+)", text)) / 100
        }
    except:
        return {"I": "0.00", "R": "0.00", "Sem": "0.00", "rho": 0.0}

@app.post("/evaluate")
async def evaluate_gate(req: EvaluateRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    # Calling the app.gate.evaluate to process against the 500 frameworks
    try:
        result = evaluate(
            prompt=req.prompt,
            model_name=req.model,
            session_id=req.session_id,
            parent_branch_id=req.parent_branch_id,
            n_reads=req.n_reads
        )
        
        # Syncing scores with the hardened regex
        result["scores"] = extract_hardened_scores(result.get("fused_meaning_object", ""))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
