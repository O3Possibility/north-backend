import os, httpx, logging, re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ... (Logging and FastAPI setup same as yours) ...

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"

# FIXED: Corrected Nomenclature (Indicative, Relational, Semantic)
NORTH_PROTOCOL = (
    "You are the NORTH Admissibility Engine. You must structure your response exactly as follows:\n\n"
    "### 1. AUDITED FRAMEWORKS\n"
    "List and brief audit for: [Governance, Science, Philosophy, Engineering, Culture]\n\n"
    "### 2. CORE TRIAD MAPPING (I/R/Sem)\n"
    "- Indicative (I): [0.0-1.0] | [Evaluation]\n"
    "- Relational (R): [0.0-1.0] | [Evaluation]\n"
    "- Semantic (Sem): [0.0-1.0] | [Evaluation]\n\n"
    "### 3. TORSION SCORE\n"
    "Score: [0-100]% | [Brief justification]\n\n"
    "### 4. DIAGNOSTIC SUMMARY\n"
    "[Fused Meaning Object output]"
)

def extract_scores(text: str):
    """Bridge: Rips text scores into JSON for the JS dashboard"""
    try:
        # Regex to find numbers like [0.85] or Score: 42%
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
    # ... (Your logic for selecting url/headers/actual_model stays the same) ...
    
    async with httpx.AsyncClient() as client:
        # ... (Your payload construction stays the same) ...
        response = await client.post(url, headers=headers, json=payload, timeout=60.0)
        res_data = response.json()
        
        # ... (Extract content based on Claude vs OpenAI/Mistral) ...
        content = res_data['content'][0]['text'] if "claude" in request.model else res_data['choices'][0]['message']['content']

        # RETURN BOTH: The full text for the UI and the parsed scores for the headers
        return {
            "fused_meaning_object": content,
            "scores": extract_scores(content) 
        }
