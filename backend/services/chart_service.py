import pandas as pd
import plotly.express as px
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Dataset, DatasetColumn
from services.data_service import load_dataframe
from services.ai_service import AIService

def _get_dataset(dataset_id: int, db: Session) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

def recommend_chart(dataset_id: int, question: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    cols = db.query(DatasetColumn).filter(DatasetColumn.dataset_id == dataset_id).all()
    col_info = [{"name": c.column_name, "type": c.detected_type} for c in cols]
    
    prompt = f"Given columns {json.dumps(col_info)},\n" \
             f"what is the best chart type to answer: '{question}'?\n" \
             f"Output ONLY a valid JSON object with exact keys: chart_type, x_column, y_column, color_column, reason.\n" \
             f"Available chart types: bar, line, scatter, pie, histogram, heatmap, box, area.\n" \
             f"If a dimension is not needed (e.g. pie chart might not need y_column if it counts x), set it to null.\n" \
             f"Ensure the column names actually exist in the provided list."
             
    with AIService(db) as ai:
        ai_resp = ai.complete(
            system_prompt="You are a data visualization expert. You reply with valid JSON only. Never explain or hallucinate.",
            user_prompt=prompt
        )
        
    try:
        text = ai_resp.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return {
            "chart_type": "bar",
            "x_column": None,
            "y_column": None,
            "color_column": None,
            "reason": "Failed to parse AI JSON. Raw output: " + ai_resp
        }

def generate_chart(dataset_id: int, chart_type: str, x_col: str, y_col: str, color_col: str, title: str, filters: str, db: Session) -> dict:
    ds = _get_dataset(dataset_id, db)
    df = load_dataframe(ds.sqlite_table_name)
    
    code_lines = ["import plotly.express as px"]
    
    if filters:
        try:
            df = df.query(filters)
            code_lines.append(f"df = df.query('{filters}')")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Filter query failed: {e}")
            
    kwargs = {}
    if x_col: kwargs['x'] = x_col
    if y_col: kwargs['y'] = y_col
    if color_col: kwargs['color'] = color_col
    if title: kwargs['title'] = title

    kwargs_str = ", ".join([f"{k}='{v}'" for k, v in kwargs.items()])
    
    try:
        if chart_type == "bar":
            fig = px.bar(df, **kwargs)
            code_lines.append(f"fig = px.bar(df, {kwargs_str})")
        elif chart_type == "line":
            fig = px.line(df, **kwargs)
            code_lines.append(f"fig = px.line(df, {kwargs_str})")
        elif chart_type == "scatter":
            fig = px.scatter(df, **kwargs)
            code_lines.append(f"fig = px.scatter(df, {kwargs_str})")
        elif chart_type == "pie":
            pie_kwargs = {}
            if y_col: pie_kwargs['values'] = y_col
            if x_col: pie_kwargs['names'] = x_col
            if title: pie_kwargs['title'] = title
            pie_kwargs_str = ", ".join([f"{k}='{v}'" for k, v in pie_kwargs.items()])
            fig = px.pie(df, **pie_kwargs)
            code_lines.append(f"fig = px.pie(df, {pie_kwargs_str})")
        elif chart_type == "histogram":
            fig = px.histogram(df, **kwargs)
            code_lines.append(f"fig = px.histogram(df, {kwargs_str})")
        elif chart_type == "heatmap":
            fig = px.density_heatmap(df, **kwargs)
            code_lines.append(f"fig = px.density_heatmap(df, {kwargs_str})")
        elif chart_type == "box":
            fig = px.box(df, **kwargs)
            code_lines.append(f"fig = px.box(df, {kwargs_str})")
        elif chart_type == "area":
            fig = px.area(df, **kwargs)
            code_lines.append(f"fig = px.area(df, {kwargs_str})")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported chart type: {chart_type}")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Chart generation failed: {e}")
        
    return {
        "plotly_json": json.loads(fig.to_json()),
        "python_code": "\n".join(code_lines)
    }
