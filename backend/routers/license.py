from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db
from models import AppConfig
from services.license_service import (
    SECRET, get_machine_id, validate_key, generate_key,
    is_admin_mode, activate_admin
)

router = APIRouter()


@router.get("/machine-id")
def read_machine_id():
    return {"machine_id": get_machine_id()}


@router.get("/status")
def license_status(db: Session = Depends(get_db)):
    if is_admin_mode():
        return {"valid": True, "plan": "admin", "expiry": "unlimited"}

    config = db.query(AppConfig).filter(AppConfig.key == "LICENSE_KEY").first()
    if not config or not config.value:
        return {"valid": False, "error": "No license key found"}

    return validate_key(config.value)


class ValidateRequest(BaseModel):
    key: str


@router.post("/validate")
def validate_license(req: ValidateRequest, db: Session = Depends(get_db)):
    result = validate_key(req.key)
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    config = db.query(AppConfig).filter(AppConfig.key == "LICENSE_KEY").first()
    if config:
        config.value = req.key
    else:
        config = AppConfig(key="LICENSE_KEY", value=req.key)
        db.add(config)
    db.commit()

    return result


class GenerateRequest(BaseModel):
    secret: str
    machine_id: str
    plan: str = "pro"
    days: int = 365


@router.post("/generate")
def generate_license(req: GenerateRequest):
    """Generate a customer license key. Requires the master SECRET."""
    if req.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    expiry = (datetime.now() + timedelta(days=req.days)).strftime("%Y-%m-%d")
    key = generate_key(req.machine_id, req.plan, expiry)
    return {"key": key, "machine_id": req.machine_id, "plan": req.plan, "expiry": expiry}


class AdminActivateRequest(BaseModel):
    secret: str


@router.post("/activate-admin")
def activate_admin_mode(req: AdminActivateRequest):
    """Activate admin (license-bypass) mode on this machine. Requires the master SECRET."""
    if req.secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    activate_admin()
    return {"message": "Admin mode activated. Restart not required."}
