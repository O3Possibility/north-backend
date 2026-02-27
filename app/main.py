from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Core Logic Imports - Ensure these exist in your /app directory
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.0-pressure-web")

# Hardened CORS: Explicitly allowing the headers and methods used in script.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
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
    # Essential for Render deployments to track actual user IPs
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    client_ip = _get_client_ip(request)
    byok = bool(req.api_key and req.api_key.strip())

    # Protect token costs / Prevent abuse
    check_rate_limit(client_ip, byok=byok)

    try:
        # Re-route to the 500-framework internal gate
        # This matches the payload keys generated in the evaluatePrompt JS function
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
        # Crucial: Returns the specific error string (e.g., "MockAdapter" failure) 
        # so the JS errorBox can display it accurately.
        raise HTTPException(status_code=500, detail=str(e))
