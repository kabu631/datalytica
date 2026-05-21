from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.eda_service import compute_eda_full

router = APIRouter()

@router.get("/full/{dataset_id}")
def get_eda_full(dataset_id: int, db: Session = Depends(get_db)):
    """Compute complete EDA stats via pandas and generate AI insights."""
    return compute_eda_full(dataset_id, db)
