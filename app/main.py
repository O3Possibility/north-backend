import os
import httpx
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup logging to see the exact Mistral response in Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NORTH Conscience API", version="0.6.0-direct-sync")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://o3possibility.github.io", "http://o3possibility.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b" # Mistral's standard stable model

@app.get("/health")
def health():
    return {"ok": True, "service": "north"}

@app.post("/evaluate")
async def eval_endpoint(req: EvaluateRequest):
    # 1. Meticulous Key Retrieval
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    
    if not api_key:
        logger.error("MISTRAL_API_KEY is missing from Render Environment Variables.")
        return {"raw_text": "Backend Error: API Key not configured."}

    # 2. Direct Call to Mistral (Bypassing internal app.gate to fix 401)
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Sending request to Mistral for prompt: {req.prompt[:20]}...")
            
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": req.model,
                    "messages": [{"role": "user", "content": req.prompt}],
                    "temperature": 0.7
                },
                timeout=30.0
            )

            # 3. Meticulous Error Handling
            if response.status_code == 401:
                logger.error("Mistral 401: Key is invalid or billing hasn't synced.")
                return {"raw_text": "Model Error: 401 Unauthorized. Verify your Mistral Key in Render."}
            
            if response.status_code != 200:
                logger.error(f"Mistral Error {response.status_code}: {response.text}")
                return {"raw_text": f"Engine Error {response.status_code}: {response.text}"}

            data = response.json()
            return {
                "fused_meaning_object": data['choices'][0]['message']['content'],
                "status": "success"
            }

        except Exception as e:
            logger.error(f"System Error: {str(e)}")
            return {"raw_text": f"Connectivity Error: {str(e)}"}
