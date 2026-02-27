import os
import re
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# CRITICAL: Restoring the link to your actual 500-framework logic
from app.gate import evaluate 
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.1-hardened")

# Hardened CORS for production stability
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"
    api_key: Optional[str] = None
    session_id: Optional[str] = None
    parent_branch_id: Optional[str] = None
    n_reads: int = 1

def _get_client_ip(request: Request) -> str:
    """Extracts IP for rate-limiting protection."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    """
    The Unified Gatekeeper. 
    Synchronizes incoming prompts with the 500-framework app.gate module.
    """
    client_ip = _get_client_ip(request)
    byok = bool(req.api_key and req.api_key.strip())

    # 1. Protect the system from token spikes
    check_rate_limit(client_ip, byok=byok)

    # 2. Re-route to the internal 'evaluate' function in app/gate.py.
    # This is the ONLY way to hit the 500 frameworks you built.
    try:
        # We pass the full context to ensure lineage (session/parent_branch) is preserved.
        result = evaluate(
            prompt=req.prompt,
            model=req.model,
            api_key=req.api_key or os.getenv("MISTRAL_API_KEY"),
            session_id=req.session_id,
            parent_branch_id=req.parent_branch_id,
            n_reads=req.n_reads or 1
        )
        
        # 3. Hardened Score Extraction Logic
        # This fixes the "0.4/1.0" or "40%" errors that were breaking your UI.
        raw_text = result.get("fused_meaning_object", "")
        
        # Regex refined to grab only the digit, ignoring suffixes like /1.0 or %
        def clean_match(pattern, text):
            match = re.search(pattern, text)
            return match.group(1) if match else "0.00"

        result["scores"] = {
            "I": clean_match(r"Indicative \(I\):\s*([\d\.]+)", raw_text),
            "R": clean_match(r"Relational \(R\):\s*([\d\.]+)", raw_text),
            "Sem": clean_match(r"Semantic \(Sem\):\s*([\d\.]+)", raw_text),
            "rho": float(clean_match(r"Score:\s*(\d+)", raw_text)) / 100
        }

        return result

    except Exception as e:
        # Detailed error reporting to stop the 'Connectivity Failure' mystery
        raise HTTPException(status_code=500, detail=f"Gate Error: {str(e)}")

@app.get("/health")
def health():
    return {"ok": True, "service": "north", "version": "0.5.1-hardened"}
