import pandas as pd
import numpy as np
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Dataset, DatasetColumn, PipelineStep
from services.data_service import load_dataframe, save_dataframe
from services.ai_service import AIService

def _get_dataset(dataset_id: int, db: Session) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

def scan_dataset(dataset_id: int, db: Session) -> dict:
    """Computes a full cleansing report purely using pandas, then requests AI explanation."""
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    total_rows = len(df)
    
    # 1. Null Report
    null_counts = df.isna().sum()
    null_report = [
        {
            "column": str(col),
            "null_count": int(count),
            "null_pct": float(count / total_rows * 100) if total_rows > 0 else 0.0
        }
        for col, count in null_counts.items() if count > 0
    ]
    
    # 2. Duplicate Rows
    duplicate_rows = int(df.duplicated().sum())
    
    # 3. Outlier Report (IQR method)
    outlier_report = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty: continue
        
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = int(((series < lower_bound) | (series > upper_bound)).sum())
        if outliers > 0:
            outlier_report.append({
                "column": str(col),
                "outlier_count": outliers,
                "method": "IQR"
            })
            
    # 4. Type Mismatches & 5. Format Issues
    type_mismatch = []
    format_issues = []
    
    for col in df.columns:
        if df[col].dtype == object:
            non_nulls = df[col].dropna()
            if non_nulls.empty: continue
            
            # Check for mixed numeric/text
            is_numeric = non_nulls.astype(str).str.isnumeric()
            num_pct = is_numeric.mean()
            if 0.1 < num_pct < 0.9:
                type_mismatch.append({"column": str(col), "issue": "Mix of numeric and text values"})
            
            # Check for inconsistent dates
            try:
                pd.to_datetime(non_nulls, errors='raise')
            except Exception:
                date_like = non_nulls.astype(str).str.match(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}')
                if date_like.mean() > 0.5:
                    format_issues.append({"column": str(col), "issue": "Inconsistent date formats or invalid dates"})

    raw_report = {
        "null_report": null_report,
        "duplicate_rows": duplicate_rows,
        "outlier_report": outlier_report,
        "type_mismatch": type_mismatch,
        "format_issues": format_issues
    }
    
    # Ask AI to explain the pandas report
    prompt = f"Here is the pandas-generated cleansing report for dataset '{ds.name}':\n" \
             f"{json.dumps(raw_report, indent=2)}\n\n" \
             f"Provide a plain-English explanation of these data quality issues to the user. " \
             f"You MUST only explain the issues found in the JSON."
             
    with AIService(db) as ai:
        ai_explanation = ai.complete(
            system_prompt="You summarize data quality issues based ONLY on the provided JSON report. Never hallucinate.",
            user_prompt=prompt
        )
        
    return {
        "raw_report": raw_report,
        "ai_explanation": ai_explanation
    }


def apply_cleansing(dataset_id: int, operations: list, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    rows_before = len(df)
    
    python_code_lines = []
    applied_ops = []
    
    for op in operations:
        op_type = op.get("type")
        col = op.get("column")
        params = op.get("params", {})
        
        if op_type == "drop_nulls":
            if col:
                df = df.dropna(subset=[col])
                python_code_lines.append(f"df = df.dropna(subset=['{col}'])")
            else:
                df = df.dropna()
                python_code_lines.append("df = df.dropna()")
            applied_ops.append(op)
            
        elif op_type == "fill_mean" and col:
            val = df[col].mean()
            df[col] = df[col].fillna(val)
            python_code_lines.append(f"df['{col}'] = df['{col}'].fillna(df['{col}'].mean())")
            applied_ops.append(op)
            
        elif op_type == "fill_median" and col:
            val = df[col].median()
            df[col] = df[col].fillna(val)
            python_code_lines.append(f"df['{col}'] = df['{col}'].fillna(df['{col}'].median())")
            applied_ops.append(op)
            
        elif op_type == "fill_value" and col:
            val = params.get("value")
            if isinstance(val, str):
                python_code_lines.append(f"df['{col}'] = df['{col}'].fillna('{val}')")
            else:
                python_code_lines.append(f"df['{col}'] = df['{col}'].fillna({val})")
            df[col] = df[col].fillna(val)
            applied_ops.append(op)
            
        elif op_type == "drop_duplicates":
            df = df.drop_duplicates()
            python_code_lines.append("df = df.drop_duplicates()")
            applied_ops.append(op)
            
        elif op_type == "remove_outliers" and col:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            df = df[(df[col] >= lower) & (df[col] <= upper)]
            
            code = (
                f"Q1 = df['{col}'].quantile(0.25)\n"
                f"Q3 = df['{col}'].quantile(0.75)\n"
                f"IQR = Q3 - Q1\n"
                f"df = df[(df['{col}'] >= (Q1 - 1.5 * IQR)) & (df['{col}'] <= (Q3 + 1.5 * IQR))]"
            )
            python_code_lines.append(code)
            applied_ops.append(op)
            
        elif op_type == "standardize_format" and col:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip().str.lower()
                python_code_lines.append(f"df['{col}'] = df['{col}'].astype(str).str.strip().str.lower()")
                applied_ops.append(op)
    
    full_python_code = "\n".join(python_code_lines)
    
    # Save the cleansed data
    res = save_dataframe(df)
    rows_after = res["row_count"]
    
    ds.row_count = rows_after
    ds.column_count = res["column_count"]
    ds.sqlite_table_name = res["sqlite_table_name"]
    ds.status = "cleansed"
    
    # Re-calculate DatasetColumn schema
    db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).delete()
    for col_meta in res["columns"]:
        db.add(DatasetColumn(
            dataset_id=dataset_id,
            column_name=col_meta["column_name"],
            detected_type=col_meta["detected_type"],
            null_count=col_meta["null_count"],
            null_pct=col_meta["null_pct"],
            unique_count=col_meta["unique_count"],
            sample_values=col_meta["sample_values"]
        ))
        
    step = PipelineStep(
        dataset_id=dataset_id,
        step_type="cleanse",
        description=f"Applied {len(applied_ops)} cleansing operations.",
        python_code=full_python_code,
        rows_before=rows_before,
        rows_after=rows_after
    )
    db.add(step)
    db.commit()
    
    return {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "operations_applied": applied_ops,
        "python_code": full_python_code
    }
