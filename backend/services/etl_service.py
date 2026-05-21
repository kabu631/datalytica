import pandas as pd
import os
import uuid
import re
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Dataset, DatasetColumn, PipelineStep
from services.data_service import load_dataframe, save_dataframe
from services.ai_service import AIService

def _get_dataset(dataset_id: int, db: Session) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

def generate_etl_code(dataset_id: int, instruction: str, db: Session) -> str:
    """Send natural language instruction to AI to generate pandas code."""
    ds = _get_dataset(dataset_id, db)
    cols = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    col_info = [{"name": c.column_name, "type": c.detected_type} for c in cols]
    
    # We must explicitly prompt for valid python and no markdown, but models often include it.
    prompt = f"Given DataFrame df with columns {col_info},\n" \
             f"generate ONLY Python pandas code for: {instruction}.\n" \
             f"Return ONLY valid Python. No explanations. No imports. " \
             f"Result must be stored back in df."
    
    with AIService(db) as ai:
        code = ai.complete(system_prompt="You are a strict python code generator.", user_prompt=prompt)
    
    # Extract Python code from AI response — handles explanation text before/after code fences
    code = code.strip()
    match = re.search(r'```python\s*(.*?)\s*```', code, re.DOTALL)
    if not match:
        match = re.search(r'```\s*(.*?)\s*```', code, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: strip leading/trailing fence markers if no complete block found
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()

def _log_and_save(dataset_id: int, original_df: pd.DataFrame, new_df: pd.DataFrame, description: str, python_code: str, step_type: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    rows_before = len(original_df)
    
    # Save the transformed dataframe to SQLite
    res = save_dataframe(new_df)
    rows_after = res["row_count"]
    
    # Update Dataset metadata
    ds.row_count = res["row_count"]
    ds.column_count = res["column_count"]
    ds.sqlite_table_name = res["sqlite_table_name"]
    ds.status = "transformed"
    
    # Replace columns
    db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).delete()
    for col_meta in res["columns"]:
        col = DatasetColumn(
            dataset_id=dataset_id,
            column_name=col_meta["column_name"],
            detected_type=col_meta["detected_type"],
            null_count=col_meta["null_count"],
            null_pct=col_meta["null_pct"],
            unique_count=col_meta["unique_count"],
            sample_values=col_meta["sample_values"]
        )
        db.add(col)
        
    # Log the step
    step = PipelineStep(
        dataset_id=dataset_id,
        step_type=step_type,
        description=description,
        python_code=python_code,
        rows_before=rows_before,
        rows_after=rows_after
    )
    db.add(step)
    db.commit()
    
    preview = new_df.head(10).where(pd.notnull(new_df), None).to_dict(orient="records")
    return {
        "python_code": python_code,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "preview": preview
    }

def execute_etl_code(dataset_id: int, python_code: str, description: str, db: Session) -> dict:
    """Execute the AI-generated or manually provided Python pandas code."""
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    # Create a sandboxed execution namespace
    namespace = {"df": df, "pd": pd}
    try:
        exec(python_code, namespace)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Code execution failed: {str(e)}")
        
    new_df = namespace.get("df")
    if not isinstance(new_df, pd.DataFrame):
        raise HTTPException(status_code=400, detail="Execution result is not a DataFrame. Ensure the code assigns the result back to 'df'.")
        
    return _log_and_save(dataset_id, df, new_df, description, python_code, "nl_etl", db)

def apply_pivot(dataset_id: int, index: str, columns: str, values: str, aggfunc: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    code = f"df = df.pivot_table(index='{index}', columns='{columns}', values='{values}', aggfunc='{aggfunc}').reset_index()"
    try:
        new_df = df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc).reset_index()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _log_and_save(dataset_id, df, new_df, "Pivot dataset", code, "pivot", db)

def apply_aggregate(dataset_id: int, groupby: list, agg_map: dict, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    code = f"df = df.groupby({groupby}).agg({agg_map}).reset_index()"
    try:
        new_df = df.groupby(groupby).agg(agg_map).reset_index()
        # Flatten MultiIndex columns if present
        if isinstance(new_df.columns, pd.MultiIndex):
            new_df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in new_df.columns.values]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _log_and_save(dataset_id, df, new_df, "Aggregate dataset", code, "aggregate", db)

def apply_filter(dataset_id: int, query_string: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    code = f"df = df.query('{query_string}')"
    try:
        new_df = df.query(query_string)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _log_and_save(dataset_id, df, new_df, f"Filter: {query_string}", code, "filter", db)

def apply_add_column(dataset_id: int, column_name: str, formula: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    code = f"df['{column_name}'] = df.eval('{formula}')"
    try:
        df_copy = df.copy()
        df_copy[column_name] = df_copy.eval(formula)
        new_df = df_copy
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _log_and_save(dataset_id, df, new_df, f"Add column: {column_name}", code, "add_column", db)

def apply_rename(dataset_id: int, columns_map: dict, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    code = f"df = df.rename(columns={columns_map})"
    try:
        new_df = df.rename(columns=columns_map)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _log_and_save(dataset_id, df, new_df, "Rename columns", code, "rename", db)

def export_dataset(dataset_id: int, format: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)
    
    filename = f"export_{ds.name}_{uuid.uuid4().hex[:6]}.{format}"
    path = os.path.join(export_dir, filename)
    path = os.path.abspath(path)
    
    try:
        if format == "csv":
            df.to_csv(path, index=False)
        elif format == "xlsx":
            df.to_excel(path, index=False)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"message": "Export successful", "path": path}
