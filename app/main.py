from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API", version="0.5.0-pressure-web")

# 1. Strict CORS Guest List - Matches your GitHub domain exactly
origins = [
    "https://o3possibility.github.io",
    "http://o3possibility.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://o3possibility.github.io",
        "http://o3possibility.github.io"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"], # Specific headers
)

# 2. Manual Preflight Handler - This kills the "Failed to Fetch" error
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    response = Response()
    origin = request.headers.get("Origin")
    if origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

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

@app.get("/")
def root():
    return {"message": "NORTH Engine Active", "docs": "/docs"}

@app.get("/health")
def health():
    return {"ok": True, "service": "north", "version": "0.5.0-pressure-web"}

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    client_ip = _get_client_ip(request)
    byok = bool(req.api_key and req.api_key.strip())

    # Abuse protection
    check_rate_limit(client_ip, byok=byok)

    # Evaluate under the chosen provider/model settings
    result = evaluate(
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
    return result
