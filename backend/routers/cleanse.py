from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from database import get_db
from services.cleanse_service import scan_dataset, apply_cleansing

router = APIRouter()

@router.post("/scan/{dataset_id}")
def scan_data(dataset_id: int, db: Session = Depends(get_db)):
    """Generate pandas-based cleansing report + AI explanation."""
    return scan_dataset(dataset_id, db)

class CleanseOperation(BaseModel):
    type: str # drop_nulls, fill_mean, fill_median, fill_value, drop_duplicates, remove_outliers, standardize_format
    column: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class CleanseRequest(BaseModel):
    dataset_id: int
    operations: List[CleanseOperation]

@router.post("/apply")
def apply_cleanse(req: CleanseRequest, db: Session = Depends(get_db)):
    """Apply specific pandas cleansing operations."""
    ops = [op.dict() for op in req.operations]
    return apply_cleansing(req.dataset_id, ops, db)
