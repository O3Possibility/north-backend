from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.gate import evaluate
from app.ratelimit import check_rate_limit

app = FastAPI(title="NORTH Conscience API")

# Hardened CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
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
    return {"status": "online"}

# Using both paths to prevent the 405 redirect error
@app.post("/evaluate")
@app.post("/evaluate/")
async def eval_endpoint(req: EvaluateRequest, request: Request):
    xff = request.headers.get("x-forwarded-for")
    client_ip = xff.split(",")[0].strip() if xff else request.client.host
    
    check_rate_limit(client_ip, byok=bool(req.api_key))

    try:
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
