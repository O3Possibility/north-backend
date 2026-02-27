import os, httpx, logging, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"

# THE PROTOCOL: Hard-codes the nomenclature to avoid model drift
NORTH_PROTOCOL = (
    "You are the NORTH Admissibility Engine. Structure your response EXACTLY as follows:\n\n"
    "### 1. AUDITED FRAMEWORKS\n"
    "[Audit: Governance, Science, Philosophy, Engineering, Culture]\n\n"
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
    """Bridge: Rips prose into JSON data for the JS dashboard"""
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
    m = request.model.lower()
    # Logic to select Provider/URL/Key based on 'm' (Claude, GPT, Mistral)
    # ... (Standard API Request Logic) ...
    
    return {
        "fused_meaning_object": content, # The full audit text
        "scores": extract_scores(content) # The numeric math
    }
