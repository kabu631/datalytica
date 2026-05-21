import pandas as pd
import numpy as np
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Dataset
from services.data_service import load_dataframe
from services.ai_service import AIService

def _get_dataset(dataset_id: int, db: Session) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

def compute_eda_full(dataset_id: int, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    total_rows = len(df)
    
    # 1. Summary
    memory_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)
    summary = {
        "row_count": total_rows,
        "column_count": len(df.columns),
        "memory_mb": round(memory_usage, 2),
        "duplicate_rows": int(df.duplicated().sum())
    }
    
    # 2. Numeric Stats & 5. Distributions
    numeric_stats = {}
    distributions = {}
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
            
        numeric_stats[col] = {
            "mean": float(series.mean()),
            "median": float(series.median()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "min": float(series.min()),
            "max": float(series.max()),
            "q25": float(series.quantile(0.25)),
            "q75": float(series.quantile(0.75)),
            "skewness": float(series.skew()) if len(series) > 2 else 0.0,
            "kurtosis": float(series.kurt()) if len(series) > 3 else 0.0,
            "null_count": int(df[col].isna().sum()),
            "null_pct": float(df[col].isna().sum() / total_rows * 100) if total_rows > 0 else 0.0
        }
        
        # Calculate distribution bins (histogram)
        counts, bin_edges = np.histogram(series, bins=min(20, len(series.unique()) if len(series.unique()) > 1 else 10))
        distributions[col] = {
            "bins": [float(b) for b in bin_edges],
            "counts": [int(c) for c in counts]
        }
        
    # 3. Categorical Stats & 5. Distributions
    categorical_stats = {}
    
    cat_cols = df.select_dtypes(exclude=[np.number]).columns
    for col in cat_cols:
        series = df[col].dropna()
        if series.empty:
            continue
            
        value_counts = series.value_counts()
        
        categorical_stats[col] = {
            "unique_count": int(series.nunique()),
            "top_value": str(value_counts.index[0]) if not value_counts.empty else None,
            "top_freq": int(value_counts.iloc[0]) if not value_counts.empty else 0,
            "value_counts": value_counts.head(10).to_dict(),
            "null_count": int(df[col].isna().sum())
        }
        
        # Calculate distribution (bar chart style) for top 15 values
        top_cats = value_counts.head(15)
        distributions[col] = {
            "bins": [str(b) for b in top_cats.index],
            "counts": [int(c) for c in top_cats.values]
        }
        
    # 4. Correlations (Pearson matrix on numeric columns + top pairs)
    correlations = {"matrix": [], "columns": [], "top_pairs": []}
    if len(numeric_cols) > 1:
        corr_matrix = df[numeric_cols].corr().fillna(0)
        correlations["columns"] = list(corr_matrix.columns)
        correlations["matrix"] = corr_matrix.values.tolist()
        
        # Get top pairs (excluding self-correlation)
        pairs = corr_matrix.unstack().reset_index()
        pairs.columns = ['col1', 'col2', 'r']
        pairs = pairs[pairs['col1'] != pairs['col2']]
        pairs['abs_r'] = pairs['r'].abs()
        pairs = pairs.sort_values(by='abs_r', ascending=False)
        
        # Drop duplicates pairs (A-B and B-A)
        pairs['pair'] = pairs.apply(lambda row: tuple(sorted([row['col1'], row['col2']])), axis=1)
        pairs = pairs.drop_duplicates(subset='pair').head(10)
        
        for _, row in pairs.iterrows():
            correlations["top_pairs"].append({
                "col1": str(row['col1']),
                "col2": str(row['col2']),
                "r": float(row['r'])
            })
            
    raw_stats = {
        "summary": summary,
        "numeric_stats": numeric_stats,
        "categorical_stats": categorical_stats,
        "correlations": correlations,
        "distributions": distributions
    }
    
    # Generate AI Insights
    # Truncate distributions so prompt isn't excessively huge
    prompt_stats = {
        "summary": summary,
        "numeric_stats": numeric_stats,
        "categorical_stats": categorical_stats,
        "correlations_top_pairs": correlations["top_pairs"]
    }
    
    prompt = f"Given these computed statistics:\n{json.dumps(prompt_stats, default=str)}\n\n" \
             f"Write exactly 5 insight statements. Each statement MUST cite a specific column name " \
             f"and a specific numeric value from the stats JSON. Do not add any fact not present in the JSON. " \
             f"Format: numbered list, one sentence each, plain English."
             
    with AIService(db) as ai:
        ai_insights = ai.complete(
            system_prompt="You are a strict data analyst. You only cite data from the provided JSON. You never hallucinate.",
            user_prompt=prompt
        )
        
    return {
        "raw_stats": raw_stats,
        "ai_insights": ai_insights
    }
