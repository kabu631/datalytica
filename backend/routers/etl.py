from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List
from database import get_db
from services.etl_service import (
    generate_etl_code,
    execute_etl_code,
    apply_pivot,
    apply_aggregate,
    apply_filter,
    apply_add_column,
    apply_rename,
    export_dataset
)

router = APIRouter()

class NLTransformGenerate(BaseModel):
    dataset_id: int
    instruction: str

class NLTransformExecute(BaseModel):
    dataset_id: int
    python_code: str

@router.post("/transform/generate")
def generate_nl_transform(req: NLTransformGenerate, db: Session = Depends(get_db)):
    """Generate pandas Python code for a natural language ETL instruction."""
    code = generate_etl_code(req.dataset_id, req.instruction, db)
    return {"python_code": code}

@router.post("/transform/execute")
def execute_nl_transform(req: NLTransformExecute, db: Session = Depends(get_db)):
    """Execute the user-approved pandas Python code."""
    res = execute_etl_code(req.dataset_id, req.python_code, "Natural Language ETL", db)
    return res

class PivotRequest(BaseModel):
    dataset_id: int
    index: str
    columns: str
    values: str
    aggfunc: str = "mean"

@router.post("/pivot")
def pivot_dataset(req: PivotRequest, db: Session = Depends(get_db)):
    """Pivot the dataset."""
    return apply_pivot(req.dataset_id, req.index, req.columns, req.values, req.aggfunc, db)

class AggregateRequest(BaseModel):
    dataset_id: int
    groupby: List[str]
    agg_map: Dict[str, str]

@router.post("/aggregate")
def aggregate_dataset(req: AggregateRequest, db: Session = Depends(get_db)):
    """Group by and aggregate."""
    return apply_aggregate(req.dataset_id, req.groupby, req.agg_map, db)

class FilterRequest(BaseModel):
    dataset_id: int
    query_string: str

@router.post("/filter")
def filter_dataset(req: FilterRequest, db: Session = Depends(get_db)):
    """Filter rows using a pandas query string."""
    return apply_filter(req.dataset_id, req.query_string, db)

class AddColumnRequest(BaseModel):
    dataset_id: int
    column_name: str
    formula: str

@router.post("/add_column")
def add_column(req: AddColumnRequest, db: Session = Depends(get_db)):
    """Add a new column using a formula."""
    return apply_add_column(req.dataset_id, req.column_name, req.formula, db)

class RenameRequest(BaseModel):
    dataset_id: int
    columns: Dict[str, str]

@router.post("/rename")
def rename_columns(req: RenameRequest, db: Session = Depends(get_db)):
    """Rename columns based on a mapping dictionary."""
    return apply_rename(req.dataset_id, req.columns, db)

class ExportRequest(BaseModel):
    dataset_id: int
    format: str

@router.post("/export")
def export_data(req: ExportRequest, db: Session = Depends(get_db)):
    """Export dataset to CSV or XLSX format."""
    return export_dataset(req.dataset_id, req.format, db)
