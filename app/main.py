import os, re, httpx, logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="NORTH_CORE")

# FIX: Comprehensive CORS to stop the "Connectivity Failure" boomerang
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"
    session_id: Optional[str] = None
    parent_branch_id: Optional[str] = None
    n_reads: int = 1

NORTH_PROTOCOL = (
    "You are the NORTH Admissibility Engine. Structure your response EXACTLY as follows:\n\n"
    "### 1. AUDITED FRAMEWORKS\n"
    "Audit for: [Governance, Science, Philosophy, Engineering, Culture]\n\n"
    "### 2. CORE TRIAD MAPPING (I/R/Sem)\n"
    "- Indicative (I): [0.0-1.0] | [Brief assessment]\n"
    "- Relational (R): [0.0-1.0] | [Brief assessment]\n"
    "- Semantic (Sem): [0.0-1.0] | [Brief assessment]\n\n"
    "### 3. TORSION SCORE\n"
    "Score: [0-100]% | [Justification]\n\n"
    "### 4. DIAGNOSTIC SUMMARY\n"
    "[Fused Meaning Object Output]"
)

def extract_scores(text: str):
    try:
        i = re.search(r"Indicative \(I\): ([\d\.]+)", text)
        r = re.search(r"Relational \(R\): ([\d\.]+)", text)
        sem = re.search(r"Semantic \(Sem\): ([\d\.]+)", text)
        torsion = re.search(r"Score: (\d+)%", text)
        return {
            "I": i.group(1) if i else "0.00",
            "R": r.group(1) if r else "0.00",
            "Sem": sem.group(1) if sem else "0.00",
            "rho": float(torsion.group(1))/100 if torsion else 0.0
        }
    except:
        return {"I": "0.00", "R": "0.00", "Sem": "0.00", "rho": 0.0}

@app.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    # API Routing Logic
    m = request.model.lower()
    if "gpt" in m:
        url = "https://api.openai.com/v1/chat/completions"
        key = os.getenv("OPENAI_API_KEY")
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"model": "gpt-4o", "messages": [{"role": "system", "content": NORTH_PROTOCOL}, {"role": "user", "content": request.prompt}]}
    elif "claude" in m:
        url = "https://api.anthropic.com/v1/messages"
        key = os.getenv("ANTHROPIC_API_KEY")
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        payload = {"model": "claude-3-5-sonnet-20240620", "max_tokens": 1024, "system": NORTH_PROTOCOL, "messages": [{"role": "user", "content": request.prompt}]}
    else:
        url = "https://api.mistral.ai/v1/chat/completions"
        key = os.getenv("MISTRAL_API_KEY")
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"model": "open-mistral-7b", "messages": [{"role": "system", "content": NORTH_PROTOCOL}, {"role": "user", "content": request.prompt}]}

    if not key:
        raise HTTPException(status_code=500, detail="API Key missing on server.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            res_data = response.json()
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=str(res_data))

            content = res_data['content'][0]['text'] if "claude" in m else res_data['choices'][0]['message']['content']
            
            return {
                "fused_meaning_object": content,
                "scores": extract_scores(content),
                "branch": {"branch_id": f"br_{os.urandom(4).hex()}"}
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
