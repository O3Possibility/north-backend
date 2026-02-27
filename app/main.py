from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Note: Keeping your existing imports for evaluate and rate limiting
# Ensure app/gate.py and app/ratelimit.py are present in your environment
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.1-sync")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "default"
    provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    session_id: str | None = None
    parent_branch_id: str | None = None
    n_reads: int = 1

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    # Determine IP for rate limiting
    xff = request.headers.get("x-forwarded-for")
    client_ip = xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")
    
    byok = bool(req.api_key and req.api_key.strip())
    check_rate_limit(client_ip, byok=byok)

    try:
        # Pass all parameters required by your script.js logic
        return evaluate(
            req.prompt,
            req.model,
            provider=req.provider,
            api_key=req.api_key,
            model_name=req.model_name,
            session_id=req.session_id,
            parent_branch_id=req.parent_branch_id,
            n_reads=req.n_reads
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
