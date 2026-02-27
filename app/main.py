from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Core Logic Imports
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.0-pressure-web")

# Hardened CORS to prevent "Failed to fetch" due to preflight rejection
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
    api_base: str | None = None
    api_key: str | None = None
    session_id: str | None = None
    parent_branch_id: str | None = None
    n_reads: int | None = 1

@app.get("/health")
def health():
    return {"ok": True, "service": "north", "version": "0.5.0-pressure-web"}

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    client_ip = _get_client_ip(request)
    byok = bool(req.api_key and req.api_key.strip())

    # Protect token costs
    check_rate_limit(client_ip, byok=byok)

    try:
        # Re-route to the 500-framework internal gate
        return evaluate(
            req.prompt,
            req.model,
            provider=req.provider,
            api_key=req.api_key,
            model_name=req.model_name,
            api_base=req.api_base,
            session_id=req.session_id,
            parent_branch_id=req.parent_branch_id,
            n_reads=req.n_reads or 1,
        )
    except Exception as e:
        # This captures the "MockAdapter" or any internal engine errors
        raise HTTPException(status_code=500, detail=str(e))
