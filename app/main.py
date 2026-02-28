from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "mistral"
    provider: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    session_id: str | None = None
    parent_branch_id: str | None = None
    n_reads: int = 1

# Dual routing to ensure the trailing slash from JS works
@app.post("/evaluate/")
@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    xff = request.headers.get("x-forwarded-for")
    client_ip = xff.split(",")[0].strip() if xff else request.client.host
    
    check_rate_limit(client_ip, byok=bool(req.api_key))

    try:
        # Executes your full 5-framework chord engine
        return evaluate(
            prompt=req.prompt,
            model_choice=req.model,
            provider=req.provider,
            api_key=req.api_key,
            model_name=req.model_name,
            session_id=req.session_id,
            parent_branch_id=req.parent_branch_id,
            n_reads=req.n_reads
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
