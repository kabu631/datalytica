"""
Data service — data I/O, schema detection, and SQLite persistence.
"""
import os
import uuid
import json
import chardet
import pandas as pd
from sqlalchemy import text
from database import engine

def detect_encoding(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw_data = f.read(10000)
    result = chardet.detect(raw_data)
    return result["encoding"] or "utf-8"

def load_dataframe_from_file(file_path: str, ext: str) -> pd.DataFrame:
    """Load a file into a pandas DataFrame based on its type."""
    ft = ext.lstrip(".").lower()
    if ft in ["csv", "tsv"]:
        encoding = detect_encoding(file_path)
        sep = "\t" if ft == "tsv" else ","
        return pd.read_csv(file_path, sep=sep, encoding=encoding)
    elif ft in ["xlsx", "xls"]:
        return pd.read_excel(file_path)
    elif ft == "json":
        return pd.read_json(file_path)
    elif ft == "parquet":
        return pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ft}")

def infer_column_type(df: pd.DataFrame, col: str) -> str:
    series = df[col]
    
    # Try converting to numeric
    try:
        numeric_series = pd.to_numeric(series, errors="raise")
        if pd.api.types.is_bool_dtype(numeric_series) or set(numeric_series.dropna().unique()).issubset({0, 1}):
            return "boolean"
        return "numeric"
    except (ValueError, TypeError):
        pass

    # Try datetime
    try:
        pd.to_datetime(series, errors="raise")
        return "datetime"
    except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime):
        pass

    # Categorical logic: if unique < 20 and < 5% of rows -> categorical
    unique_count = series.nunique()
    total = len(series)
    if unique_count < 20 and (total == 0 or (unique_count / total) < 0.05):
        return "categorical"
    
    return "text"

def process_upload(file_path: str, ext: str) -> dict:
    df = load_dataframe_from_file(file_path, ext)
    df.columns = df.columns.astype(str)

    sqlite_table_name = f"data_{uuid.uuid4().hex[:8]}"
    with engine.begin() as conn:
        df.to_sql(sqlite_table_name, con=conn, index=False, if_exists="replace")
    
    file_size_kb = os.path.getsize(file_path) / 1024.0
    row_count = len(df)
    
    columns_meta = []
    for col in df.columns:
        col_type = infer_column_type(df, col)
        null_count = int(df[col].isna().sum())
        null_pct = (null_count / row_count) * 100 if row_count > 0 else 0.0
        unique_count = int(df[col].nunique())
        sample = df[col].dropna().head(5).astype(str).tolist()
        
        columns_meta.append({
            "column_name": col,
            "detected_type": col_type,
            "null_count": null_count,
            "null_pct": float(null_pct),
            "unique_count": unique_count,
            "sample_values": json.dumps(sample)
        })
        
    preview_df = df.head(10).where(pd.notnull(df), None)
    
    return {
        "row_count": row_count,
        "column_count": len(df.columns),
        "file_size_kb": float(file_size_kb),
        "sqlite_table_name": sqlite_table_name,
        "columns": columns_meta,
        "preview": preview_df.to_dict(orient="records")
    }

def get_preview(sqlite_table_name: str, limit: int = 100) -> list:
    query = text(f"SELECT * FROM {sqlite_table_name} LIMIT {limit}")
    with engine.connect() as conn:
        df = pd.read_sql(query, con=conn)
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")

def load_dataframe(sqlite_table_name: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_table(sqlite_table_name, con=conn)

def save_dataframe(df: pd.DataFrame) -> dict:
    sqlite_table_name = f"data_{uuid.uuid4().hex[:8]}"
    df.columns = df.columns.astype(str)
    with engine.begin() as conn:
        df.to_sql(sqlite_table_name, con=conn, index=False, if_exists="replace")
    
    row_count = len(df)
    columns_meta = []
    for col in df.columns:
        col_type = infer_column_type(df, col)
        null_count = int(df[col].isna().sum())
        null_pct = (null_count / row_count) * 100 if row_count > 0 else 0.0
        unique_count = int(df[col].nunique())
        sample = df[col].dropna().head(5).astype(str).tolist()
        
        columns_meta.append({
            "column_name": col,
            "detected_type": col_type,
            "null_count": null_count,
            "null_pct": float(null_pct),
            "unique_count": unique_count,
            "sample_values": json.dumps(sample)
        })
        
    return {
        "row_count": row_count,
        "column_count": len(df.columns),
        "sqlite_table_name": sqlite_table_name,
        "columns": columns_meta
    }

def drop_sqlite_table(sqlite_table_name: str):
    try:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {sqlite_table_name}"))
    except Exception:
        pass
