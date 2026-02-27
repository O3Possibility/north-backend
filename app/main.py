from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from app.gate import evaluate
from app.ratelimit import check_rate_limit

# Setup basic logging to help you see errors in Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NORTH Conscience API", version="0.5.0-pressure-web")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://o3possibility.github.io",
        "http://o3possibility.github.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "default"
    n_reads: int | None = 1

@app.get("/health")
def health():
    return {"ok": True, "service": "north"}

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    client_ip = _get_client_ip(request)
    
    # 1. Bypass rate limit if it's causing the 500
    try:
        check_rate_limit(client_ip, byok=False)
    except Exception as e:
        logger.error(f"Rate Limit System Error: {e}")
        # We continue so the app doesn't die just because Redis is missing

    # 2. Guarded Evaluation
    try:
        result = evaluate(
            req.prompt,
            req.model,
            n_reads=req.n_reads or 1,
        )
        return result
    except Exception as e:
        logger.error(f"Evaluation Logic Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
