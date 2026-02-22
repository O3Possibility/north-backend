import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    # Storage
    CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./db/north_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "triadic_systems")

    # Chord selection
    TONIC_K: int = int(os.getenv("TONIC_K", "1"))
    BALLAST_POOL_K: int = int(os.getenv("BALLAST_POOL_K", "180"))   # strict-first: larger pool
    BALLAST_N: int = int(os.getenv("BALLAST_N", "4"))

    ENFORCE_DIVERSITY: bool = os.getenv("ENFORCE_DIVERSITY", "true").lower() == "true"
    DIVERSITY_KEYS: tuple = ("Regime_Type", "Macro_Region", "Lineage_Cluster")
    TORSION_PARSE_FLAG: str = os.getenv("TORSION_PARSE_FLAG", "torsional_kit")

    # Strict-first gate defaults (tune later, don't tune daily)
    BASE_TAU: float = float(os.getenv("BASE_TAU", "0.72"))          # strict-first baseline
    RHO_CRIT: float = float(os.getenv("RHO_CRIT", "0.85"))          # hard fracture line
    TAU_BUMP_MAX: float = float(os.getenv("TAU_BUMP_MAX", "0.18"))  # max tau bump from torsion

    # Logging (trace)
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")
    ENABLE_LOGS: bool = os.getenv("ENABLE_LOGS", "true").lower() == "true"

    # Model provider
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "mock")  # mock | ollama | mistral
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    MAX_PREDICT: int = int(os.getenv("MAX_PREDICT", "240"))

    # Mistral API (OpenAI-compatible)
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    MISTRAL_BASE_URL: str = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")

    # Basic abuse protection (in-memory; resets on server restart)
    # Defaults are conservative for early public testing.
    RATE_PER_MIN: int = int(os.getenv("RATE_PER_MIN", "12"))              # requests per minute per IP
    DAILY_LIMIT_PER_IP: int = int(os.getenv("DAILY_LIMIT_PER_IP", "120")) # requests per day per IP
    DAILY_LIMIT_BYOK: int = int(os.getenv("DAILY_LIMIT_BYOK", "600"))     # if user supplies own API key

settings = Settings()
