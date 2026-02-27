from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Core Logic Imports
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.0-pressure-web")

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
    api_base: str | None = None # Matched to your script.js payload
    api_key: str | None = None
    session_id: str | None = None
    parent_branch_id: str | None = None
    n_reads: int | None = 1

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    # IP extraction for rate limiting
    xff = request.headers.get("x-forwarded-for")
    client_ip = xff.split(",")[0].strip() if xff else request.client.host
    
    check_rate_limit(client_ip, byok=bool(req.api_key))

    try:
        # Re-route to your gate.py logic
        return evaluate(
            prompt=req.prompt,
            model_choice=req.model,
            provider=req.provider,
            api_key=req.api_key,
            model_name=req.model_name,
            api_base=req.api_base,
            session_id=req.session_id,
            parent_branch_id=req.parent_branch_id,
            n_reads=req.n_reads or 1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
