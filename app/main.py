from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.0-pressure-web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production to your GitHub Pages domain
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "default"  # legacy override
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
    # Prefer X-Forwarded-For when behind Render/Fly/Cloudflare
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        # take the first (original client)
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

@app.post("/evaluate")
def eval_endpoint(req: EvaluateRequest, request: Request):
    client_ip = _get_client_ip(request)
    byok = bool(req.api_key and req.api_key.strip())

    # Basic abuse protection so token costs can't spike unexpectedly.
    check_rate_limit(client_ip, byok=byok)

    # Evaluate under the chosen provider/model settings.
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
    if __name__ == "__main__":
import os
import uvicorn

port = int(os.environ.get("PORT", "8000"))
uvicorn.run("app.main:app", host="0.0.0.0", port=port)
