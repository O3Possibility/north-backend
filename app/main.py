import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED: Class name now matches the function signature below
class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"

@app.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    
    # Auditability Instruction
    system_prompt = (
        "You are the NORTH Admissibility Engine. "
        "STEP 1: Audit the intent through these 5 Frameworks: Governance, Science, Philosophy, Engineering, Culture. "
        "STEP 2: Map the Core Triad (I/R/Sem). "
        "STEP 3: Provide a Torsion Score (0-100%). "
        "Format the output with clear headers for each section."
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": request.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=45.0 # Increased timeout for the deeper audit logic
            )
            
            if response.status_code != 200:
                return {"raw_text": f"Mistral Error: {response.text}"}

            data = response.json()
            return {"fused_meaning_object": data['choices'][0]['message']['content']}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
