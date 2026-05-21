from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import AppConfig

router = APIRouter()

_READABLE_KEYS = ("AI_PROVIDER", "OLLAMA_MODEL", "OLLAMA_GENERATE_URL")


@router.get("/")
def get_config(db: Session = Depends(get_db)):
    """Return current AI config (never exposes the raw API key)."""
    result = {}
    for key in _READABLE_KEYS:
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        result[key] = row.value if row else None

    key_row = db.query(AppConfig).filter(AppConfig.key == "DEEPSEEK_API_KEY").first()
    result["HAS_DEEPSEEK_KEY"] = bool(key_row and key_row.value)
    return result


class SetConfigRequest(BaseModel):
    ai_provider: str
    deepseek_api_key: str = ""
    ollama_model: str = "mistral"
    ollama_url: str = ""


@router.post("/")
def set_config(req: SetConfigRequest, db: Session = Depends(get_db)):
    """Persist AI provider settings to AppConfig."""
    def _upsert(key: str, value: str):
        if not value:
            return
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        if row:
            row.value = value
        else:
            db.add(AppConfig(key=key, value=value))

    _upsert("AI_PROVIDER", req.ai_provider)
    _upsert("DEEPSEEK_API_KEY", req.deepseek_api_key)
    _upsert("OLLAMA_MODEL", req.ollama_model)
    _upsert("OLLAMA_GENERATE_URL", req.ollama_url)
    db.commit()
    return {"message": "Settings saved"}
