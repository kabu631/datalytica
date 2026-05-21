from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from services.chart_service import recommend_chart, generate_chart

router = APIRouter()

class RecommendRequest(BaseModel):
    dataset_id: int
    question: str

@router.post("/recommend")
def recommend(req: RecommendRequest, db: Session = Depends(get_db)):
    """Ask AI for chart recommendations based on column schemas and a natural language query."""
    return recommend_chart(req.dataset_id, req.question, db)

class GenerateRequest(BaseModel):
    dataset_id: int
    chart_type: str
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    color_column: Optional[str] = None
    title: Optional[str] = None
    filters: Optional[str] = None

@router.post("/generate")
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    """Generate a Plotly JSON schema and python code dynamically based on given parameters."""
    return generate_chart(
        req.dataset_id, 
        req.chart_type, 
        req.x_column, 
        req.y_column, 
        req.color_column, 
        req.title, 
        req.filters, 
        db
    )
