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
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    
    # SYSTEM_PROMPT defines the Framework (I/R/Sem)
    SYSTEM_PROMPT = (
        "You are the NORTH Admissibility Engine. Evaluate all input through a "
        "triadic constraint lens: 1. Intent (I), 2. Reality (R), and 3. Semantics (Sem). "
        "Perform a torsion check to identify drift. "
        "Output your response as a Fused Meaning Object (FMO)."
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "open-mistral-7b",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT}, # The Framework
                        {"role": "user", "content": req.prompt}
                    ],
                    "temperature": 0.2 # Lower temperature for analytical precision
                }
            )
            
            data = response.json()
            # Return the content to the 'fmo' div in your HTML
            return {"fused_meaning_object": data['choices'][0]['message']['content']}
            
        except Exception as e:
            return {"raw_text": f"Engine Error: {str(e)}"}
