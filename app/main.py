import os
import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

# Logging for Render debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NORTH Engine Multi-Router")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    prompt: str
    model: str = "open-mistral-7b"

# Define the Frameworks and Triad as a constant to ensure they are always injected
NORTH_PROTOCOL = (
    "You are the NORTH Admissibility Engine. You must structure your response exactly as follows:\n\n"
    "### 1. AUDITED FRAMEWORKS\n"
    "List and brief audit for: [Governance, Science, Philosophy, Engineering, Culture]\n\n"
    "### 2. CORE TRIAD MAPPING (I/R/Sem)\n"
    "- Intent (I): [Evaluation of goal]\n"
    "- Reality (R): [Evaluation of physical/empirical constraints]\n"
    "- Semantics (Sem): [Evaluation of linguistic precision]\n\n"
    "### 3. TORSION SCORE\n"
    "Score: [0-100]% | [Brief justification]\n\n"
    "### 4. DIAGNOSTIC SUMMARY\n"
    "[Fused Meaning Object output]"
)

@app.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    # Determine the engine based on the model string from frontend
    model_choice = request.model.lower()
    
    # 1. Configuration Selection
    if "claude" in model_choice:
        url = "https://api.anthropic.com/v1/messages"
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        # Actual model name for Anthropic
        actual_model = "claude-3-5-sonnet-20240620"
    elif "gpt" in model_choice:
        url = "https://api.openai.com/v1/chat/completions"
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        headers = {"Authorization": f"Bearer {api_key}"}
        actual_model = "gpt-4o"
    else:
        url = "https://api.mistral.ai/v1/chat/completions"
        api_key = os.getenv("MISTRAL_API_KEY", "").strip()
        headers = {"Authorization": f"Bearer {api_key}"}
        actual_model = "open-mistral-7b"

    if not api_key:
        logger.error(f"Missing API Key for {model_choice}")
        raise HTTPException(status_code=500, detail=f"API Key for {model_choice} not configured.")

    async with httpx.AsyncClient() as client:
        try:
            # 2. Payload Construction (Anthropic vs OpenAI/Mistral)
            if "claude" in model_choice:
                payload = {
                    "model": actual_model,
                    "max_tokens": 4096,
                    "system": NORTH_PROTOCOL,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "temperature": 0.1
                }
            else:
                payload = {
                    "model": actual_model,
                    "messages": [
                        {"role": "system", "content": NORTH_PROTOCOL},
                        {"role": "user", "content": request.prompt}
                    ],
                    "temperature": 0.1
                }

            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            
            if response.status_code != 200:
                logger.error(f"Provider Error: {response.text}")
                return {"raw_text": f"Provider {model_choice} Error: {response.status_code}"}

            # 3. Response Parsing
            res_data = response.json()
            if "claude" in model_choice:
                content = res_data['content'][0]['text']
            else:
                content = res_data['choices'][0]['message']['content']

            return {"fused_meaning_object": content}

        except Exception as e:
            logger.error(f"System Crash: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
