import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import pandas as pd

from database import get_db
from models import Dataset, DatasetColumn
from services.data_service import process_upload, get_preview, load_dataframe, save_dataframe, drop_sqlite_table

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet", ".tsv"}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a data file, parse, save to SQLite, and detect its schema."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        res = process_upload(dest, ext)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    dataset = Dataset(
        name=file.filename,
        original_filename=file.filename,
        row_count=res["row_count"],
        column_count=res["column_count"],
        file_size_kb=res["file_size_kb"],
        sqlite_table_name=res["sqlite_table_name"],
        status="raw"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    for col_meta in res["columns"]:
        col = DatasetColumn(
            dataset_id=dataset.id,
            column_name=col_meta["column_name"],
            detected_type=col_meta["detected_type"],
            null_count=col_meta["null_count"],
            null_pct=col_meta["null_pct"],
            unique_count=col_meta["unique_count"],
            sample_values=col_meta["sample_values"]
        )
        db.add(col)
        
    db.commit()

    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": res["columns"],
        "preview": res["preview"]
    }

@router.get("/preview/{dataset_id}")
def preview_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Return first 100 rows of the dataset as JSON."""
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    try:
        rows = get_preview(ds.sqlite_table_name, limit=100)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read preview: {e}")
        
    return {"dataset_id": dataset_id, "rows": rows}

class JoinRequest(BaseModel):
    dataset_id_1: int
    dataset_id_2: int
    join_column: str
    join_type: str = "inner"

@router.post("/join")
def join_datasets(req: JoinRequest, db: Session = Depends(get_db)):
    """Join two datasets on a specific column and save as a new dataset."""
    ds1 = db.query(Dataset).filter(Dataset.id == req.dataset_id_1).first()
    ds2 = db.query(Dataset).filter(Dataset.id == req.dataset_id_2).first()
    
    if not ds1 or not ds2:
        raise HTTPException(status_code=404, detail="One or both datasets not found")
        
    df1 = load_dataframe(ds1.sqlite_table_name)
    df2 = load_dataframe(ds2.sqlite_table_name)
    
    if req.join_column not in df1.columns or req.join_column not in df2.columns:
        raise HTTPException(status_code=400, detail=f"Join column '{req.join_column}' must exist in both datasets")
        
    try:
        merged_df = pd.merge(df1, df2, on=req.join_column, how=req.join_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Merge failed: {str(e)}")
        
    res = save_dataframe(merged_df)
    
    new_name = f"Joined: {ds1.name} & {ds2.name}"
    
    dataset = Dataset(
        name=new_name,
        original_filename="merged_dataset",
        row_count=res["row_count"],
        column_count=res["column_count"],
        file_size_kb=0.0, # Computed dataset
        sqlite_table_name=res["sqlite_table_name"],
        status="transformed"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    for col_meta in res["columns"]:
        col = DatasetColumn(
            dataset_id=dataset.id,
            column_name=col_meta["column_name"],
            detected_type=col_meta["detected_type"],
            null_count=col_meta["null_count"],
            null_pct=col_meta["null_pct"],
            unique_count=col_meta["unique_count"],
            sample_values=col_meta["sample_values"]
        )
        db.add(col)
        
    db.commit()
    
    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "columns": res["columns"]
    }

@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    """List all ingested datasets."""
    return db.query(Dataset).all()

@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

@router.get("/columns/{dataset_id}")
def get_dataset_columns(dataset_id: int, db: Session = Depends(get_db)):
    cols = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    if not cols:
        raise HTTPException(status_code=404, detail="Dataset not found or has no columns")
    return [{"name": c.column_name, "type": c.detected_type} for c in cols]

@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    drop_sqlite_table(ds.sqlite_table_name)
        
    db.delete(ds)
    db.commit()
    return {"message": "Dataset deleted"}
