import json
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
import numpy as np
import pandas as pd
import re
from pathlib import Path
from database import engine
from models import Base
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, DataFile, ImageFile, ImageProcessingHistory, AnalysisHistory, CleaningHistory, AnalysisPlan
from auth import create_access_token, decode_access_token
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from config import get_list_env, is_production_env, load_env_file
from ai_provider import AIProviderError, get_active_ai_provider, get_ai_provider_status
from image_service import (
    IMAGE_MAX_UPLOAD_SIZE,
    apply_image_processing,
    build_image_quality_report,
    get_image_storage_path,
    guess_image_mime_type,
    image_to_data_url,
    load_image_from_bytes,
    load_image_from_path,
    normalize_image_storage_name,
    normalize_image_variant_stem,
    deserialize_ocr_payload,
    run_image_ocr,
    sanitize_image_filename,
    save_image_to_path,
    serialize_ocr_payload,
)

#
load_env_file()

# 用户注册数据模型
class UserRegister(BaseModel):
    username: str
    password: str

# 用户登录数据模型
class UserLogin(BaseModel):
    username: str
    password: str

class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


class UserPasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

# 数据清洗请求数据模型，包含缺失值处理策略、固定填充值和是否删除重复行等字段
class TypeConversionRule(BaseModel):
    column: str
    target_type: str


class CleaningRequest(BaseModel):
    missing_strategy: str = "none"
    fill_value: str | None = None
    remove_duplicates: bool = False
    outlier_strategy: str = "none"
    type_conversions: list[TypeConversionRule] = Field(default_factory=list)


class CleaningRollbackRequest(BaseModel):
    history_id: int


class QueryFilterRule(BaseModel):
    column: str
    operator: str
    value: Any | None = None
    second_value: Any | None = None


class QuerySortRule(BaseModel):
    column: str
    direction: str = "asc"


class QueryPreviewRequest(BaseModel):
    filters: list[QueryFilterRule] = Field(default_factory=list)
    sort: list[QuerySortRule] = Field(default_factory=list)
    limit: int = 20
    offset: int = 0


class GroupMetricRule(BaseModel):
    column: str
    aggregations: list[str] = Field(default_factory=list)


class GroupByRequest(BaseModel):
    filters: list[QueryFilterRule] = Field(default_factory=list)
    group_columns: list[str] = Field(default_factory=list)
    metrics: list[GroupMetricRule] = Field(default_factory=list)
    limit: int = 50


class DistributionRequest(BaseModel):
    filters: list[QueryFilterRule] = Field(default_factory=list)
    column: str
    mode: str = "auto"
    bins: int = 8
    include_cumulative: bool = True
    sort_mode: str = "default"
    limit: int = 20


class PredictionRequest(BaseModel):
    target_column: str = Field(..., min_length=1)
    feature_column: str | None = None
    periods: int = Field(6, ge=1, le=60)


class GroupByPlanState(BaseModel):
    primary_group_column: str = ""
    secondary_group_column: str = ""
    metric_column: str = ""
    metric_aggregation: str = "count"
    metrics: list[GroupMetricRule] = Field(default_factory=list)
    limit: int = 20


class DistributionPlanState(BaseModel):
    column: str = ""
    mode: str = "auto"
    bins: int = 8
    include_cumulative: bool = True
    sort_mode: str = "default"
    limit: int = 20


class CorrelationPlanState(BaseModel):
    view: str = "heatmap"
    abs_threshold: float = 0


class ChartPlanState(BaseModel):
    column: str = ""
    chart_type: str = ""


class AnalysisPlanState(BaseModel):
    query: QueryPreviewRequest = Field(default_factory=QueryPreviewRequest)
    groupby: GroupByPlanState = Field(default_factory=GroupByPlanState)
    distribution: DistributionPlanState = Field(default_factory=DistributionPlanState)
    correlation: CorrelationPlanState = Field(default_factory=CorrelationPlanState)
    chart: ChartPlanState = Field(default_factory=ChartPlanState)


class AnalysisPlanSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    plan: AnalysisPlanState


class AIConversationMessage(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=1, max_length=4000)


class AIWorkspaceState(BaseModel):
    active_section: str | None = None
    current_column: str | None = None
    current_chart_type: str | None = None


class AIAssistantRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    conversation: list[AIConversationMessage] = Field(default_factory=list)
    workspace_state: AIWorkspaceState = Field(default_factory=AIWorkspaceState)


class ImageProcessingRequest(BaseModel):
    grayscale: bool = False
    binary_threshold: int | None = Field(None, ge=0, le=255)
    rotate_degrees: float = 0.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    brightness: float = Field(1.0, ge=0.2, le=3.0)
    contrast: float = Field(1.0, ge=0.2, le=3.0)
    sharpen: bool = False
    denoise: bool = False
    crop_x: int | None = Field(None, ge=0, le=4096)
    crop_y: int | None = Field(None, ge=0, le=4096)
    crop_width: int | None = Field(None, ge=1, le=4096)
    crop_height: int | None = Field(None, ge=1, le=4096)
    target_width: int | None = Field(None, ge=1, le=4096)
    target_height: int | None = Field(None, ge=1, le=4096)
    preserve_aspect: bool = True
    output_format: str = "png"

# 读取CSV文件，尝试多种编码格式
def read_csv_file(file_path: str):
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312"]
    for encoding in encodings:
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(file_path)

# 定义支持的图表类型和默认图表类型，分别针对数值字段和类别字段，提供多种可选的图表类型以满足不同的数据展示需求
NUMERIC_CHART_TYPES = [
    "auto",
    "histogram",
    "line",
    "area",
    "bar",
    "scatter",
    "boxplot",
]
NUMERIC_DEFAULT_CHART = "histogram"

# 定义支持的图表类型和默认图表类型，分别针对数值字段和类别字段，提供多种可选的图表类型以满足不同的数据展示需求
CATEGORICAL_CHART_TYPES = [
    "auto",
    "bar",
    "horizontal_bar",
    "pie",
    "donut",
    "rose",
    "treemap",
]
CATEGORICAL_DEFAULT_CHART = "bar"

# 定义支持的缺失值处理策略列表，提供多种选项以满足不同的数据清洗需求
CLEANING_MISSING_STRATEGIES = [
    "none",
    "drop_rows",
    "fill_median_mode",
    "fill_fixed",
]
OUTLIER_STRATEGIES = [
    "none",
    "drop_iqr_rows",
]
OUTLIER_SAMPLE_LIMIT = 5
OUTLIER_MIN_UNIQUE_VALUES = 20
OUTLIER_MIN_UNIQUE_RATIO = 0.01
OUTLIER_HIGH_SKEWNESS = 1.5
OUTLIER_HIGH_RATIO = 0.08
TYPE_CONVERSION_TARGETS = [
    "numeric",
    "datetime",
    "text",
]
QUERY_FILTER_OPERATORS = [
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "in",
    "between",
    "is_null",
    "not_null",
]
QUERY_SORT_DIRECTIONS = [
    "asc",
    "desc",
]
GROUP_AGGREGATIONS = [
    "count",
    "sum",
    "mean",
    "min",
    "max",
    "median",
]
DISTRIBUTION_MODES = [
    "auto",
    "categorical",
    "numeric",
]
DISTRIBUTION_SORT_MODES = [
    "default",
    "frequency_desc",
]
AI_SUPPORTED_ACTION_TYPES = {
    "navigate",
    "chart",
    "distribution",
    "groupby",
    "quality",
    "dictionary",
    "correlation",
}
AI_SUPPORTED_TARGET_SECTIONS = {
    "overview",
    "preparation",
    "exploration",
    "visualization",
    "assets",
}
USER_ROLES = {"user", "admin"}
AI_MAX_PREVIEW_ROWS = 5
AI_MAX_FIELD_PROFILES = 8
AI_MAX_ISSUE_COLUMNS = 5
AI_MAX_ACTIONS = 3
AI_MAX_CONVERSATION_TURNS = 6

# 判断一个 Series 是否可以被视为数值类型，允许一定比例的非数值数据，以适应实际数据中的异常值或混杂类型
def _is_numeric_series(series: pd.Series) -> bool:
    non_null = series.dropna()
    if non_null.empty:
        return False

    if pd.api.types.is_numeric_dtype(series):
        return True

    converted = pd.to_numeric(non_null, errors="coerce")
    valid_ratio = converted.notna().sum() / len(non_null)
    return valid_ratio >= 0.8

# 将 DataFrame 的列分为数值列和类别列，返回两个列表，分别包含数值列和类别列的名称
def _split_chartable_columns(df: pd.DataFrame):
    numeric_cols = []
    categorical_cols = []

    for column in df.columns:
        if _is_numeric_series(df[column]):
            numeric_cols.append(column)
        else:
            categorical_cols.append(column)

    return numeric_cols, categorical_cols

# 构建图表数据时，如果用户请求的图表类型不受支持，返回一个包含支持的图表类型列表的错误信息
def _get_chart_support_error(column_kind: str, supported_types: list[str]) -> HTTPException:
    labels = ", ".join(supported_types)
    return HTTPException(
        status_code=400,
        detail=f"当前{column_kind}字段支持的图表类型: {labels}",
    )

# 根据列的数据类型和用户请求的图表类型，构建适合前端展示的图表数据结构，支持数值字段的多种图表类型（如直方图、折线图、面积图、柱状图、散点图、箱线图）和类别字段的多种图表类型（如柱状图、横向柱状图、饼图、环形图、玫瑰图、树图）
def _build_numeric_chart(column: str, values: pd.Series, chart_type: str):
    resolved_type = NUMERIC_DEFAULT_CHART if chart_type == "auto" else chart_type

    if resolved_type not in NUMERIC_CHART_TYPES:
        raise _get_chart_support_error("数值", NUMERIC_CHART_TYPES)

    if resolved_type == "histogram":
        grouped = pd.cut(values, bins=min(8, max(3, values.nunique())))
        freq = grouped.value_counts().sort_index()
        return {
            "type": "bar",
            "column_kind": "numeric",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": NUMERIC_CHART_TYPES,
            "x": [str(interval) for interval in freq.index],
            "y": freq.values.astype(int).tolist(),
            "title": f"{column} 分布直方图",
        }

    sampled = values.head(100)
    axis_labels = sampled.index.astype(str).tolist()

    if resolved_type == "line":
        return {
            "type": "line",
            "column_kind": "numeric",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": NUMERIC_CHART_TYPES,
            "x": axis_labels,
            "y": sampled.tolist(),
            "title": f"{column} 折线图",
        }

    if resolved_type == "area":
        return {
            "type": "area",
            "column_kind": "numeric",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": NUMERIC_CHART_TYPES,
            "x": axis_labels,
            "y": sampled.tolist(),
            "title": f"{column} 面积图",
        }

    if resolved_type == "bar":
        return {
            "type": "bar",
            "column_kind": "numeric",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": NUMERIC_CHART_TYPES,
            "x": axis_labels[:30],
            "y": sampled.head(30).tolist(),
            "title": f"{column} 柱状图",
        }

    if resolved_type == "scatter":
        return {
            "type": "scatter",
            "column_kind": "numeric",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": NUMERIC_CHART_TYPES,
            "x": axis_labels,
            "y": sampled.tolist(),
            "title": f"{column} 散点图",
        }

    if resolved_type == "boxplot":
        summary = values.describe(percentiles=[0.25, 0.5, 0.75])
        return {
            "type": "boxplot",
            "column_kind": "numeric",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": NUMERIC_CHART_TYPES,
            "x": [column],
            "data": [[
                float(summary["min"]),
                float(summary["25%"]),
                float(summary["50%"]),
                float(summary["75%"]),
                float(summary["max"]),
            ]],
            "title": f"{column} 箱线图",
        }

    raise _get_chart_support_error("数值", NUMERIC_CHART_TYPES)

# 根据列的数据类型和用户请求的图表类型，构建适合前端展示的图表数据结构，支持数值字段的多种图表类型（如直方图、折线图、面积图、柱状图、散点图、箱线图）和类别字段的多种图表类型（如柱状图、横向柱状图、饼图、环形图、玫瑰图、树图）
def _build_categorical_chart(column: str, series: pd.Series, chart_type: str):
    resolved_type = CATEGORICAL_DEFAULT_CHART if chart_type == "auto" else chart_type

    if resolved_type not in CATEGORICAL_CHART_TYPES:
        raise _get_chart_support_error("类别", CATEGORICAL_CHART_TYPES)

    counts = series.astype(str).value_counts().head(12)
    data_items = [{"name": key, "value": int(value)} for key, value in counts.items()]

    if resolved_type == "bar":
        return {
            "type": "bar",
            "column_kind": "categorical",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": CATEGORICAL_CHART_TYPES,
            "x": counts.index.tolist(),
            "y": counts.values.astype(int).tolist(),
            "title": f"{column} 类别分布柱状图",
        }

    if resolved_type == "horizontal_bar":
        return {
            "type": "bar",
            "orientation": "horizontal",
            "column_kind": "categorical",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": CATEGORICAL_CHART_TYPES,
            "categories": counts.index.tolist(),
            "values": counts.values.astype(int).tolist(),
            "title": f"{column} 横向柱状图",
        }

    if resolved_type == "pie":
        return {
            "type": "pie",
            "column_kind": "categorical",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": CATEGORICAL_CHART_TYPES,
            "data": data_items,
            "title": f"{column} 饼图",
        }

    if resolved_type == "donut":
        return {
            "type": "pie",
            "radius": ["38%", "68%"],
            "column_kind": "categorical",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": CATEGORICAL_CHART_TYPES,
            "data": data_items,
            "title": f"{column} 环形图",
        }

    if resolved_type == "rose":
        return {
            "type": "pie",
            "radius": ["22%", "72%"],
            "rose_type": "area",
            "column_kind": "categorical",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": CATEGORICAL_CHART_TYPES,
            "data": data_items,
            "title": f"{column} 玫瑰图",
        }

    if resolved_type == "treemap":
        return {
            "type": "treemap",
            "column_kind": "categorical",
            "requested_type": chart_type,
            "resolved_type": resolved_type,
            "supported_chart_types": CATEGORICAL_CHART_TYPES,
            "data": data_items,
            "title": f"{column} 树图",
        }

    raise _get_chart_support_error("类别", CATEGORICAL_CHART_TYPES)


def _format_prediction_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(num):
        return None
    return round(num, 4)


def _format_prediction_label(value: float, feature_kind: str, step_index: int) -> str:
    if feature_kind == "datetime":
        try:
            timestamp = pd.to_datetime(value, unit="s")
            if timestamp.hour or timestamp.minute or timestamp.second:
                return timestamp.strftime("%Y-%m-%d %H:%M")
            return timestamp.strftime("%Y-%m-%d")
        except Exception:
            return f"预测 {step_index}"

    if feature_kind == "numeric":
        rounded = round(float(value), 4)
        if float(rounded).is_integer():
            return str(int(rounded))
        return str(rounded)

    return f"第 {int(round(value)) + 1} 项"


def _resolve_prediction_feature(df: pd.DataFrame, request: PredictionRequest):
    feature_column = (request.feature_column or "").strip()

    if not feature_column:
        x_values = pd.Series(np.arange(len(df), dtype=float), index=df.index)
        return x_values, "index", "行号序列", feature_column

    if feature_column not in df.columns:
        raise HTTPException(status_code=400, detail="预测依据字段不存在")

    raw_feature = df[feature_column]
    if pd.api.types.is_datetime64_any_dtype(raw_feature):
        datetime_feature = pd.to_datetime(raw_feature, errors="coerce")
        timestamp_feature = datetime_feature.map(
            lambda item: item.timestamp() if pd.notna(item) else np.nan
        )
        return timestamp_feature, "datetime", feature_column, feature_column

    numeric_feature = pd.to_numeric(raw_feature, errors="coerce")
    numeric_ratio = numeric_feature.notna().sum() / max(len(raw_feature), 1)
    if numeric_ratio >= 0.8:
        return numeric_feature, "numeric", feature_column, feature_column

    datetime_feature = pd.to_datetime(raw_feature, errors="coerce")
    datetime_ratio = datetime_feature.notna().sum() / max(len(raw_feature), 1)
    if datetime_ratio >= 0.8:
        timestamp_feature = datetime_feature.map(
            lambda item: item.timestamp() if pd.notna(item) else np.nan
        )
        return timestamp_feature, "datetime", feature_column, feature_column

    raise HTTPException(
        status_code=400,
        detail="预测依据字段需要是数值字段或日期时间字段，也可以留空使用行号序列",
    )


def _infer_prediction_step(x_values: np.ndarray, feature_kind: str) -> float:
    sorted_unique = np.unique(np.sort(x_values))
    if len(sorted_unique) < 2:
        return 1.0

    diffs = np.diff(sorted_unique)
    diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
    if len(diffs) == 0:
        return 1.0

    step = float(np.median(diffs))
    if not np.isfinite(step) or step <= 0:
        return 86400.0 if feature_kind == "datetime" else 1.0
    return step


def _build_prediction_payload(df: pd.DataFrame, request: PredictionRequest):
    target_column = request.target_column.strip()
    if target_column not in df.columns:
        raise HTTPException(status_code=400, detail="预测目标字段不存在")

    target_values = pd.to_numeric(df[target_column], errors="coerce")
    if target_values.notna().sum() < 3:
        raise HTTPException(status_code=400, detail="预测目标字段至少需要 3 条有效数值")

    feature_values, feature_kind, feature_label, feature_column = _resolve_prediction_feature(
        df,
        request,
    )
    model_df = pd.DataFrame(
        {
            "x": feature_values,
            "y": target_values,
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()

    if len(model_df) < 3:
        raise HTTPException(status_code=400, detail="可用于建模的数据不足，至少需要 3 条有效记录")

    model_df = model_df.sort_values("x").reset_index(drop=True)
    x = model_df["x"].astype(float).to_numpy()
    y = model_df["y"].astype(float).to_numpy()

    if np.ptp(x) == 0:
        raise HTTPException(status_code=400, detail="预测依据字段没有变化，无法建立趋势模型")

    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    residuals = y - fitted
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(np.square(residuals))))
    ss_res = float(np.sum(np.square(residuals)))
    ss_tot = float(np.sum(np.square(y - np.mean(y))))
    r2 = None if ss_tot == 0 else float(1 - ss_res / ss_tot)

    step = _infer_prediction_step(x, feature_kind)
    future_x = np.array([x[-1] + step * index for index in range(1, request.periods + 1)])
    future_y = slope * future_x + intercept

    historical_tail = model_df.tail(120)
    historical = [
        {
            "label": _format_prediction_label(float(row.x), feature_kind, index + 1),
            "value": _format_prediction_number(row.y),
        }
        for index, row in enumerate(historical_tail.itertuples(index=False))
    ]
    forecast = [
        {
            "label": _format_prediction_label(float(value), feature_kind, index + 1),
            "value": _format_prediction_number(future_y[index]),
        }
        for index, value in enumerate(future_x)
    ]

    slope_abs = abs(float(slope))
    y_scale = max(float(np.nanstd(y)), 1.0)
    x_scale = max(float(np.nanstd(x)), 1.0)
    normalized_slope = slope_abs * x_scale / y_scale
    if normalized_slope < 0.03:
        trend = "平稳"
    elif slope > 0:
        trend = "上升"
    else:
        trend = "下降"

    if r2 is None:
        confidence_label = "样本波动较小"
    elif r2 >= 0.7:
        confidence_label = "拟合度较高"
    elif r2 >= 0.4:
        confidence_label = "拟合度中等"
    else:
        confidence_label = "拟合度偏低"

    return {
        "target_column": target_column,
        "feature_column": feature_column,
        "feature_label": feature_label,
        "feature_kind": feature_kind,
        "periods": request.periods,
        "model_name": "线性回归预测",
        "method": "linear_regression",
        "trend": trend,
        "confidence_label": confidence_label,
        "metrics": {
            "sample_count": int(len(model_df)),
            "mae": _format_prediction_number(mae),
            "rmse": _format_prediction_number(rmse),
            "r2": _format_prediction_number(r2),
            "slope": _format_prediction_number(slope),
        },
        "historical": historical,
        "forecast": forecast,
    }

# 创建数据库表
Base.metadata.create_all(bind=engine)


def _ensure_user_system_columns():
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    dialect = engine.dialect.name
    is_sqlite = dialect == "sqlite"
    quote = "`" if dialect in {"mysql", "mariadb"} else '"'

    column_definitions = {
        "role": f"{quote}role{quote} VARCHAR(20) NOT NULL DEFAULT 'user'",
        "is_active": f"{quote}is_active{quote} BOOLEAN NOT NULL DEFAULT 1",
        "created_at": f"{quote}created_at{quote} DATETIME" if is_sqlite else f"{quote}created_at{quote} DATETIME DEFAULT CURRENT_TIMESTAMP",
        "last_login_at": f"{quote}last_login_at{quote} DATETIME NULL",
    }

    with engine.begin() as connection:
        for column_name, column_sql in column_definitions.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_sql}"))

        connection.execute(text(f"UPDATE users SET {quote}role{quote} = 'user' WHERE {quote}role{quote} IS NULL OR {quote}role{quote} = ''"))
        connection.execute(text(f"UPDATE users SET {quote}is_active{quote} = 1 WHERE {quote}is_active{quote} IS NULL"))
        if is_sqlite and "created_at" not in existing_columns:
            connection.execute(text(f"UPDATE users SET {quote}created_at{quote} = CURRENT_TIMESTAMP WHERE {quote}created_at{quote} IS NULL"))


def _ensure_admin_entry():
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == "admin").first()
        if admin_exists:
            return

        first_user = db.query(User).order_by(User.id.asc()).first()
        if first_user:
            first_user.role = "admin"
            first_user.is_active = True
            db.commit()
    finally:
        db.close()

# 创建 FastAPI 实例
app = FastAPI()


@app.on_event("startup")
def run_startup_housekeeping():
    _ensure_user_system_columns()
    _ensure_admin_entry()
    _migrate_generated_file_names()

# 获取允许的 CORS 来源列表，支持从环境变量配置
DEFAULT_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
]
DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# 从环境变量读取允许的 CORS 来源，支持逗号分隔的列表，去除多余空格和斜杠，并去重
def _get_allowed_origins():
    origins = get_list_env("CORS_ALLOW_ORIGINS")
    if origins:
        return list(dict.fromkeys(origins))

    if is_production_env():
        raise RuntimeError("CORS_ALLOW_ORIGINS must be set when APP_ENV=production.")

    return DEFAULT_CORS_ORIGINS

# 从环境变量读取允许的主机列表，支持逗号分隔的列表，去除多余空格和斜杠，并去重
def _get_allowed_hosts():
    hosts = get_list_env("ALLOWED_HOSTS")
    if hosts:
        return list(dict.fromkeys(hosts))

    if is_production_env():
        raise RuntimeError("ALLOWED_HOSTS must be set when APP_ENV=production.")

    return DEFAULT_ALLOWED_HOSTS

# 🚀 启动后端服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_get_allowed_hosts())

# 安全认证
security = HTTPBearer()

# 获取数据库连接
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 获取当前用户信息
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    db_user = db.query(User).filter(User.username == payload["sub"]).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="用户不存在")

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    return db_user


def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def _serialize_user(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": bool(user.is_active),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }

# 创建上传目录
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = (BASE_DIR / "data").resolve()
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 上传文件时验证和清理文件名，确保安全且符合要求
def _sanitize_uploaded_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="文件名无效")

    safe_name = Path(filename).name.strip()
    safe_name = INVALID_FILENAME_CHARS.sub("_", safe_name)
    safe_name = re.sub(r"\s+", " ", safe_name)

    if safe_name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="文件名无效")

    if not safe_name.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持上传 CSV 文件")

    if len(safe_name) > 200:
        suffix = Path(safe_name).suffix
        stem_max_length = max(1, 200 - len(suffix))
        safe_name = f"{Path(safe_name).stem[:stem_max_length]}{suffix}"

    return safe_name

# 存储文件时再次验证文件名，确保安全且不包含路径信息
def _normalize_storage_filename(filename: str) -> str:
    safe_name = Path(filename).name
    if safe_name != filename or safe_name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="文件名无效")
    return safe_name

# 获取存储路径，确保路径安全且在上传目录内
def _get_storage_path(filename: str) -> Path:
    safe_name = _normalize_storage_filename(filename)
    file_path = (UPLOAD_DIR / safe_name).resolve()

    if file_path.parent != UPLOAD_DIR:
        raise HTTPException(status_code=400, detail="文件路径无效")

    return file_path

# 获取用户文件记录，检查记录是否存在
def _get_user_file_record(db: Session, current_user: User, filename: str):
    safe_name = _normalize_storage_filename(filename)
    record = db.query(DataFile).filter(
        DataFile.user_id == current_user.id,
        DataFile.stored_name == safe_name
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="文件记录不存在")

    return record

# 获取用户文件记录和存储路径，检查文件是否存在（可选）
def _get_user_file(
    db: Session,
    current_user: User,
    filename: str,
    require_disk_file: bool = True
):
    record = _get_user_file_record(db, current_user, filename)
    file_path = _get_storage_path(record.stored_name)

    if require_disk_file and not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return record, file_path


def _get_user_image_record(db: Session, current_user: User, filename: str):
    safe_name = normalize_image_storage_name(filename)
    record = db.query(ImageFile).filter(
        ImageFile.user_id == current_user.id,
        ImageFile.stored_name == safe_name
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="图片记录不存在")

    return record


def _get_user_image(
    db: Session,
    current_user: User,
    filename: str,
    require_disk_file: bool = True,
):
    record = _get_user_image_record(db, current_user, filename)
    file_path = get_image_storage_path(record.stored_name)

    if require_disk_file and not file_path.exists():
        raise HTTPException(status_code=404, detail="图片文件不存在")

    return record, file_path


def _build_image_payload(record: ImageFile):
    return {
        "id": record.id,
        "name": record.stored_name,
        "original_name": record.original_name,
        "size": int(record.file_size or 0),
        "width": int(record.width or 0),
        "height": int(record.height or 0),
        "mime_type": record.mime_type,
        "source_image_id": record.source_image_id,
        "operation_summary": record.operation_summary,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _get_unique_image_names(
    db: Session,
    current_user: User,
    desired_original_name: str,
) -> tuple[str, str]:
    original_name = desired_original_name
    stem = Path(desired_original_name).stem
    suffix = Path(desired_original_name).suffix or ".png"
    index = 1

    while True:
        stored_name = f"{current_user.id}_{original_name}"
        exists = db.query(ImageFile.id).filter(ImageFile.stored_name == stored_name).first()
        if not exists:
            return original_name, stored_name
        index += 1
        original_name = f"{stem}{index}{suffix}"


def _build_processed_image_names(
    db: Session,
    current_user: User,
    source_record: ImageFile,
    suffix: str = "处理版",
) -> tuple[str, str]:
    base_name = normalize_image_variant_stem(source_record.original_name)
    extension = Path(source_record.original_name).suffix.lower() or ".png"
    desired_name = f"{base_name}_{suffix}{extension}"
    return _get_unique_image_names(db, current_user, desired_name)


def _log_image_history(
    db: Session,
    *,
    current_user: User,
    source_image_id: int,
    action_type: str,
    operation_summary: str,
    result_image_id: int | None = None,
    result_payload: dict[str, Any] | None = None,
    exported: bool = False,
):
    history = ImageProcessingHistory(
        user_id=current_user.id,
        source_image_id=source_image_id,
        result_image_id=result_image_id,
        action_type=action_type,
        operation_summary=operation_summary,
        result_payload=serialize_ocr_payload(result_payload) if result_payload else None,
        exported=exported,
    )
    db.add(history)
    db.flush()
    return history


def _serialize_image_history_item(
    item: ImageProcessingHistory,
    *,
    source_name_map: dict[int, str] | None = None,
    result_name_map: dict[int, str] | None = None,
) -> dict[str, Any]:
    return {
        "id": item.id,
        "action_type": item.action_type,
        "operation_summary": item.operation_summary,
        "exported": bool(item.exported),
        "ocr_result": deserialize_ocr_payload(item.result_payload),
        "source_image_id": item.source_image_id,
        "source_image_name": (source_name_map or {}).get(item.source_image_id),
        "result_image_id": item.result_image_id,
        "result_image_name": (result_name_map or {}).get(item.result_image_id),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _serialize_analysis_history_item(history: AnalysisHistory, file: DataFile) -> dict[str, Any]:
    return {
        "id": history.id,
        "file_name": file.original_name,
        "stored_name": file.stored_name,
        "column_name": history.column_name,
        "chart_type": history.chart_type,
        "created_at": history.created_at.isoformat() if history.created_at else None,
    }


def _get_schema_path(stored_name: str) -> Path:
    safe_name = _normalize_storage_filename(stored_name)
    schema_path = (UPLOAD_DIR / f"{safe_name}.schema.json").resolve()

    if schema_path.parent != UPLOAD_DIR:
        raise HTTPException(status_code=400, detail="文件路径无效")

    return schema_path


def _load_schema_map(stored_name: str) -> dict[str, str]:
    schema_path = _get_schema_path(stored_name)
    if not schema_path.exists():
        return {}

    try:
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {
                str(column): str(target_type)
                for column, target_type in raw.items()
                if str(target_type) in TYPE_CONVERSION_TARGETS
            }
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}

    return {}


def _save_schema_map(stored_name: str, schema_map: dict[str, str]):
    schema_path = _get_schema_path(stored_name)
    filtered_map = {
        str(column): str(target_type)
        for column, target_type in schema_map.items()
        if str(target_type) in TYPE_CONVERSION_TARGETS
    }

    if not filtered_map:
        if schema_path.exists():
            schema_path.unlink(missing_ok=True)
        return

    schema_path.write_text(
        json.dumps(filtered_map, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def _convert_series_to_type(series: pd.Series, target_type: str) -> pd.Series:
    if target_type == "numeric":
        return pd.to_numeric(series, errors="coerce")
    if target_type == "datetime":
        return pd.to_datetime(series, errors="coerce")
    if target_type == "text":
        return series.astype("string")

    raise HTTPException(status_code=400, detail="不支持的类型转换目标")


def _apply_schema_to_dataframe(df: pd.DataFrame, schema_map: dict[str, str]):
    normalized_df = df.copy()

    for column, target_type in schema_map.items():
        if column not in normalized_df.columns:
            continue
        normalized_df[column] = _convert_series_to_type(normalized_df[column], target_type)

    return normalized_df


def _load_dataframe_with_schema(file_path: Path, stored_name: str):
    df = read_csv_file(str(file_path))
    return _apply_schema_to_dataframe(df, _load_schema_map(stored_name))

# 根据列的数据类型，检测列是数值类型、类别类型还是空列，返回对应的字符串标签
def _detect_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "empty"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if _is_numeric_series(series):
        return "numeric"
    return "categorical"


def _round_float(value: float) -> float:
    return round(float(value), 6)


def _format_distribution_scalar(value: Any):
    if pd.isna(value):
        return "缺失值"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (int, float)):
        rounded = _round_float(value)
        return int(rounded) if float(rounded).is_integer() else rounded
    return str(value)


def _format_distribution_interval(interval: pd.Interval) -> str:
    left = _format_distribution_scalar(interval.left)
    right = _format_distribution_scalar(interval.right)
    left_bracket = "[" if interval.closed_left else "("
    right_bracket = "]" if interval.closed_right else ")"
    return f"{left_bracket}{left}, {right}{right_bracket}"


def _build_outlier_bounds(
    *,
    method: str,
    method_label: str,
    note: str,
    lower_bound: float | None = None,
    upper_bound: float | None = None,
    q1: float | None = None,
    q3: float | None = None,
    iqr: float | None = None,
    skewness: float | None = None,
    unique_count: int | None = None,
    unique_ratio: float | None = None,
):
    bounds = {
        "method": method,
        "method_label": method_label,
        "note": note,
    }

    if lower_bound is not None:
        bounds["lower_bound"] = _round_float(lower_bound)
    if upper_bound is not None:
        bounds["upper_bound"] = _round_float(upper_bound)
    if q1 is not None:
        bounds["q1"] = _round_float(q1)
    if q3 is not None:
        bounds["q3"] = _round_float(q3)
    if iqr is not None:
        bounds["iqr"] = _round_float(iqr)
    if skewness is not None and not pd.isna(skewness):
        bounds["skewness"] = _round_float(skewness)
    if unique_count is not None:
        bounds["unique_count"] = int(unique_count)
    if unique_ratio is not None and not pd.isna(unique_ratio):
        bounds["unique_ratio"] = _round_float(unique_ratio)

    return bounds

# 使用 IQR 方法检测数值列中的异常值，首先检查列是否适合数值分析，然后根据数据的分布特征选择合适的检测方法（经典 IQR、对数 IQR 或尾部分位数），最后返回一个布尔掩码标识异常值的位置，以及相关的统计信息和样本记录供前端展示
def _get_iqr_outlier_mask(series: pd.Series):
    if not _is_numeric_series(series):
        return pd.Series(False, index=series.index), None, []

    numeric_series = pd.to_numeric(series, errors="coerce")
    valid_values = numeric_series.dropna()
    if valid_values.empty:
        return pd.Series(False, index=series.index), None, []

    unique_count = int(valid_values.nunique())
    unique_ratio = unique_count / len(valid_values) if len(valid_values) else 0
    skewness = float(valid_values.skew()) if len(valid_values) >= 3 else 0.0

    if (
        unique_count <= OUTLIER_MIN_UNIQUE_VALUES
        or unique_ratio <= OUTLIER_MIN_UNIQUE_RATIO
    ):
        return (
            pd.Series(False, index=series.index),
            _build_outlier_bounds(
                method="skip_low_cardinality",
                method_label="跳过检测",
                note="该字段取值较少，更像离散业务字段，默认不做异常候选检测",
                skewness=skewness,
                unique_count=unique_count,
                unique_ratio=unique_ratio,
            ),
            [],
        )

    q1 = valid_values.quantile(0.25)
    q3 = valid_values.quantile(0.75)
    iqr = q3 - q1
    classic_lower = q1 - 1.5 * iqr
    classic_upper = q3 + 1.5 * iqr
    classic_mask = (
        numeric_series.notna()
        & ((numeric_series < classic_lower) | (numeric_series > classic_upper))
    )
    classic_ratio = float(classic_mask.mean())

    method = "iqr"
    method_label = "经典 IQR"
    note = "使用 Q1 / Q3 与 1.5 IQR 识别统计上的极端值候选"
    lower_bound = classic_lower
    upper_bound = classic_upper
    outlier_mask = classic_mask

    if (valid_values >= 0).all() and skewness >= OUTLIER_HIGH_SKEWNESS:
        transformed_values = pd.Series(
            np.log1p(valid_values.to_numpy()),
            index=valid_values.index
        )
        transformed_q1 = transformed_values.quantile(0.25)
        transformed_q3 = transformed_values.quantile(0.75)
        transformed_iqr = transformed_q3 - transformed_q1
        lower_bound = max(0.0, float(np.expm1(transformed_q1 - 1.5 * transformed_iqr)))
        upper_bound = float(np.expm1(transformed_q3 + 1.5 * transformed_iqr))
        outlier_mask = (
            numeric_series.notna()
            & ((numeric_series < lower_bound) | (numeric_series > upper_bound))
        )
        method = "log_iqr"
        method_label = "对数 IQR"
        note = "该字段右偏明显，先做对数压缩再检测，避免把正常大单误判成异常"
    elif classic_ratio >= OUTLIER_HIGH_RATIO and abs(skewness) >= 1.0:
        outlier_mask = pd.Series(False, index=series.index)
        lower_bound = None
        upper_bound = None
        method = "skip_unstable_global_rule"
        method_label = "跳过检测"
        note = "该字段全局波动较大，自动阈值不稳定，默认不直接标记候选异常"

    bounds = _build_outlier_bounds(
        method=method,
        method_label=method_label,
        note=note,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        q1=q1,
        q3=q3,
        iqr=iqr,
        skewness=skewness,
        unique_count=unique_count,
        unique_ratio=unique_ratio,
    )
    sample_rows = []
    if outlier_mask.any():
        for row_index, value in numeric_series[outlier_mask].head(OUTLIER_SAMPLE_LIMIT).items():
            sample_rows.append({
                "row_index": int(row_index) + 1,
                "value": _round_float(value),
            })

    return outlier_mask, bounds, sample_rows

# 构建数据质量报告，统计每列的基本信息（如数据类型、缺失值数量和比例、唯一值数量等），以及整体数据集的行数、列数、缺失单元格总数、包含缺失值的列数和重复行数等指标，为前端提供全面的数据质量概览
def _build_quality_report(df: pd.DataFrame):
    row_count = int(len(df))
    columns = []
    outlier_row_mask = pd.Series(False, index=df.index)

    for column in df.columns:
        series = df[column]
        missing_count = int(series.isna().sum())
        missing_ratio = (missing_count / row_count) if row_count else 0
        outlier_mask, outlier_bounds, outlier_samples = _get_iqr_outlier_mask(series)
        outlier_count = int(outlier_mask.sum())
        outlier_ratio = (outlier_count / row_count) if row_count else 0
        outlier_row_mask = outlier_row_mask | outlier_mask

        columns.append({
            "name": column,
            "dtype": str(series.dtype),
            "detected_type": _detect_column_type(series),
            "missing_count": missing_count,
            "missing_ratio": round(missing_ratio, 4),
            "unique_count": int(series.dropna().nunique()),
            "outlier_count": outlier_count,
            "outlier_ratio": round(outlier_ratio, 4),
            "outlier_bounds": outlier_bounds,
            "outlier_samples": outlier_samples,
        })

    return {
        "row_count": row_count,
        "column_count": int(len(df.columns)),
        "missing_cell_count": int(df.isna().sum().sum()),
        "columns_with_missing": int(sum(item["missing_count"] > 0 for item in columns)),
        "duplicate_row_count": int(df.duplicated().sum()),
        "outlier_cell_count": int(sum(item["outlier_count"] for item in columns)),
        "outlier_row_count": int(outlier_row_mask.sum()),
        "columns_with_outliers": int(sum(item["outlier_count"] > 0 for item in columns)),
        "columns": columns,
        "supported_missing_strategies": CLEANING_MISSING_STRATEGIES,
        "supported_outlier_strategies": OUTLIER_STRATEGIES,
    }


def _build_field_sample_values(series: pd.Series, limit: int = 4) -> list[str]:
    non_null = series.dropna()
    if non_null.empty:
        return []

    sample_values = []
    seen = set()
    for value in non_null.tolist():
        formatted = str(_format_distribution_scalar(value))
        if formatted in seen:
            continue
        seen.add(formatted)
        sample_values.append(formatted)
        if len(sample_values) >= limit:
            break

    return sample_values


def _build_top_values(series: pd.Series, non_null_count: int, limit: int = 3) -> list[dict[str, Any]]:
    if non_null_count <= 0:
        return []

    counts = series.dropna().astype("string").value_counts().head(limit)
    result = []
    for value, count in counts.items():
        result.append({
            "value": value,
            "count": int(count),
            "percentage": round((int(count) / non_null_count) * 100, 2),
        })
    return result


def _build_field_role_hint(
    detected_type: str,
    non_null_count: int,
    unique_count: int,
    unique_ratio: float,
) -> str:
    if detected_type == "empty":
        return "空列"
    if non_null_count >= 10 and unique_count == non_null_count and unique_ratio >= 0.95:
        return "高唯一标识字段"
    if detected_type == "datetime":
        return "时间字段"
    if detected_type == "numeric":
        if unique_count <= 20 or unique_ratio <= 0.12:
            return "离散数值字段"
        return "连续数值字段"
    if unique_count <= 20 or unique_ratio <= 0.2:
        return "典型类别字段"
    return "高基数字段"


def _build_field_recommended_uses(
    detected_type: str,
    unique_count: int,
    unique_ratio: float,
) -> list[str]:
    uses = ["查询筛选"]

    if detected_type == "empty":
        return uses

    uses.append("数据清洗")
    uses.append("频数分布")

    if detected_type in {"categorical", "datetime"}:
        uses.append("分组统计")
    elif detected_type == "numeric" and (unique_count <= 20 or unique_ratio <= 0.2):
        uses.append("分组统计")

    if detected_type in {"numeric", "categorical"}:
        uses.append("图表分析")

    if detected_type == "numeric" and unique_count >= 3:
        uses.append("相关性分析")

    return uses


def _build_field_profile_summary(
    *,
    column: str,
    detected_type: str,
    non_null_count: int,
    missing_ratio: float,
    unique_count: int,
    sample_values: list[str],
    numeric_summary: dict[str, Any] | None = None,
    datetime_summary: dict[str, Any] | None = None,
    top_values: list[dict[str, Any]] | None = None,
) -> str:
    missing_text = f"缺失率 {round(missing_ratio * 100, 2)}%"

    if detected_type == "empty":
        return f"{column} 当前为空列，建议检查源数据或在清洗时决定是否保留。"

    if detected_type == "numeric" and numeric_summary:
        return (
            f"{column} 是数值字段，{missing_text}，共有 {unique_count} 个不同取值，"
            f"范围约 {numeric_summary.get('min')} ~ {numeric_summary.get('max')}。"
        )

    if detected_type == "datetime" and datetime_summary:
        return (
            f"{column} 是时间字段，{missing_text}，时间范围约 "
            f"{datetime_summary.get('min')} ~ {datetime_summary.get('max')}。"
        )

    top_value = top_values[0]["value"] if top_values else (sample_values[0] if sample_values else "暂无样本")
    return (
        f"{column} 是类别字段，{missing_text}，共有 {unique_count} 个不同取值，"
        f"常见值示例：{top_value}。"
    )


def _build_field_profiles(df: pd.DataFrame):
    row_count = int(len(df))
    profiles = []
    type_counts = {
        "numeric": 0,
        "categorical": 0,
        "datetime": 0,
        "empty": 0,
    }

    analysis_payload = _build_analysis_payload(df)
    statistics = analysis_payload.get("statistics", {})

    for column in df.columns:
        series = df[column]
        detected_type = _detect_column_type(series)
        type_counts[detected_type] = type_counts.get(detected_type, 0) + 1

        missing_count = int(series.isna().sum())
        non_null_count = max(0, row_count - missing_count)
        missing_ratio = (missing_count / row_count) if row_count else 0
        unique_count = int(series.dropna().nunique())
        unique_ratio = (unique_count / non_null_count) if non_null_count else 0
        sample_values = _build_field_sample_values(series)
        top_values = _build_top_values(series, non_null_count) if detected_type in {"categorical", "datetime"} else []

        numeric_summary = None
        if detected_type == "numeric":
            stats = statistics.get(column, {})
            numeric_summary = {
                "min": _format_distribution_scalar(stats.get("min")),
                "max": _format_distribution_scalar(stats.get("max")),
                "mean": _round_float(stats.get("mean")) if stats.get("mean") is not None and not pd.isna(stats.get("mean")) else None,
                "median": _round_float(stats.get("50%")) if stats.get("50%") is not None and not pd.isna(stats.get("50%")) else None,
                "std": _round_float(stats.get("std")) if stats.get("std") is not None and not pd.isna(stats.get("std")) else None,
            }

        datetime_summary = None
        if detected_type == "datetime":
            valid_datetimes = pd.to_datetime(series, errors="coerce").dropna()
            if not valid_datetimes.empty:
                datetime_summary = {
                    "min": _format_distribution_scalar(valid_datetimes.min()),
                    "max": _format_distribution_scalar(valid_datetimes.max()),
                }

        profiles.append({
            "name": column,
            "dtype": str(series.dtype),
            "detected_type": detected_type,
            "role_hint": _build_field_role_hint(
                detected_type,
                non_null_count,
                unique_count,
                unique_ratio,
            ),
            "non_null_count": non_null_count,
            "missing_count": missing_count,
            "missing_ratio": round(missing_ratio, 4),
            "unique_count": unique_count,
            "unique_ratio": round(unique_ratio, 4),
            "sample_values": sample_values,
            "top_values": top_values,
            "numeric_summary": numeric_summary,
            "datetime_summary": datetime_summary,
            "recommended_uses": _build_field_recommended_uses(
                detected_type,
                unique_count,
                unique_ratio,
            ),
            "summary": _build_field_profile_summary(
                column=column,
                detected_type=detected_type,
                non_null_count=non_null_count,
                missing_ratio=missing_ratio,
                unique_count=unique_count,
                sample_values=sample_values,
                numeric_summary=numeric_summary,
                datetime_summary=datetime_summary,
                top_values=top_values,
            ),
        })

    return {
        "row_count": row_count,
        "field_count": int(len(df.columns)),
        "type_counts": type_counts,
        "profiles": profiles,
    }


def _validate_cleaning_request(request: CleaningRequest):
    if request.missing_strategy not in CLEANING_MISSING_STRATEGIES:
        raise HTTPException(status_code=400, detail="???????????")

    if request.missing_strategy == "fill_fixed" and request.fill_value is None:
        raise HTTPException(status_code=400, detail="?????????")

    if request.outlier_strategy not in OUTLIER_STRATEGIES:
        raise HTTPException(status_code=400, detail="???????????")


def _has_cleaning_operation(request: CleaningRequest) -> bool:
    return (
        request.missing_strategy != "none"
        or request.remove_duplicates
        or request.outlier_strategy != "none"
        or bool(request.type_conversions)
    )


def _stringify_dataframe(df: pd.DataFrame) -> list[dict]:
    display_df = df.copy()

    for column in display_df.columns:
        if pd.api.types.is_datetime64_any_dtype(display_df[column]):
            display_df[column] = display_df[column].dt.strftime("%Y-%m-%d %H:%M:%S")

    display_df = display_df.where(pd.notna(display_df), "")
    return display_df.to_dict(orient="records")


def _prepare_export_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    export_df = df.copy()

    for column in export_df.columns:
        if pd.api.types.is_datetime64_any_dtype(export_df[column]):
            export_df[column] = export_df[column].dt.strftime("%Y-%m-%d %H:%M:%S")

    return export_df.where(pd.notna(export_df), "")


def _cleanup_temp_file(path_str: str):
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        pass


def _build_export_filename(record: DataFile, suffix: str) -> str:
    source_name = record.original_name or record.stored_name
    stem = Path(source_name).stem.strip() or "dataset"
    safe_stem = INVALID_FILENAME_CHARS.sub("_", stem)
    safe_stem = re.sub(r"\s+", "_", safe_stem).strip("._") or "dataset"
    safe_stem = safe_stem[:80]
    safe_suffix = re.sub(r"[^A-Za-z0-9_-]+", "_", suffix).strip("_") or "export"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_stem}_{safe_suffix}_{timestamp}.csv"


def _normalize_versioned_stem(file_name: str) -> str:
    stem = Path(file_name).stem.strip() or "dataset"
    normalized = re.sub(
        r"([_-](?:cleaned|clean|rollback)(?:\d+)?(?:[_-]\d{1,8}){0,4})+$",
        "",
        stem,
        flags=re.IGNORECASE,
    ).strip("._-")
    return normalized or stem or "dataset"


def _build_rollback_filenames(current_user: User, source_record: DataFile) -> tuple[str, str]:
    base_name = _normalize_versioned_stem(source_record.original_name or source_record.stored_name)
    counter = 1

    while True:
        suffix = "rollback" if counter == 1 else f"rollback{counter}"
        rollback_original_name = _sanitize_uploaded_filename(f"{base_name}_{suffix}.csv")
        stored_name = f"{current_user.id}_{rollback_original_name}"
        if not _get_storage_path(stored_name).exists():
            return rollback_original_name, stored_name
        counter += 1


def _infer_generated_result_kind(history: CleaningHistory) -> str:
    try:
        operations = json.loads(history.operation_summary or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        operations = []

    for item in operations:
        if isinstance(item, dict) and item.get("type") == "rollback":
            return "rollback"

    return "clean"


def _allocate_short_generated_filenames(
    user_id: int,
    source_name: str,
    version_kind: str,
    occupied_names: set[str]
) -> tuple[str, str]:
    base_name = _normalize_versioned_stem(source_name)
    counter = 1

    while True:
        suffix = version_kind if counter == 1 else f"{version_kind}{counter}"
        original_name = _sanitize_uploaded_filename(f"{base_name}_{suffix}.csv")
        stored_name = f"{user_id}_{original_name}"
        if stored_name not in occupied_names:
            occupied_names.add(stored_name)
            return original_name, stored_name
        counter += 1


def _move_versioned_file_artifacts(old_stored_name: str, new_stored_name: str):
    old_file_path = _get_storage_path(old_stored_name)
    new_file_path = _get_storage_path(new_stored_name)
    if old_file_path.exists() and old_file_path != new_file_path:
        old_file_path.replace(new_file_path)

    old_schema_path = _get_schema_path(old_stored_name)
    new_schema_path = _get_schema_path(new_stored_name)
    if old_schema_path.exists() and old_schema_path != new_schema_path:
        old_schema_path.replace(new_schema_path)


def _migrate_generated_file_names():
    db = SessionLocal()

    try:
        histories = (
            db.query(CleaningHistory)
            .order_by(CleaningHistory.created_at.asc(), CleaningHistory.id.asc())
            .all()
        )
        if not histories:
            return

        all_records = db.query(DataFile).all()
        records_by_id = {record.id: record for record in all_records}
        generated_result_ids = {history.result_file_id for history in histories}
        occupied_names = {
            record.stored_name
            for record in all_records
            if record.id not in generated_result_ids
        }

        rename_plans = []
        for history in histories:
            result_record = records_by_id.get(history.result_file_id)
            source_record = records_by_id.get(history.source_file_id)
            if not result_record or not source_record:
                continue

            current_path = _get_storage_path(result_record.stored_name)
            if not current_path.exists():
                continue

            version_kind = _infer_generated_result_kind(history)
            target_original_name, target_stored_name = _allocate_short_generated_filenames(
                user_id=result_record.user_id,
                source_name=source_record.original_name or source_record.stored_name,
                version_kind=version_kind,
                occupied_names=occupied_names,
            )

            if (
                result_record.original_name == target_original_name
                and result_record.stored_name == target_stored_name
            ):
                continue

            rename_plans.append({
                "record": result_record,
                "current_stored_name": result_record.stored_name,
                "target_stored_name": target_stored_name,
                "target_original_name": target_original_name,
                "temp_stored_name": f"__rename__{result_record.id}.csv",
            })

        if not rename_plans:
            return

        for plan in rename_plans:
            _move_versioned_file_artifacts(
                plan["current_stored_name"],
                plan["temp_stored_name"],
            )

        for plan in rename_plans:
            _move_versioned_file_artifacts(
                plan["temp_stored_name"],
                plan["target_stored_name"],
            )
            plan["record"].stored_name = plan["target_stored_name"]
            plan["record"].original_name = plan["target_original_name"]

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[startup] generated filename migration skipped: {exc}")
    finally:
        db.close()


def _create_csv_export_response(
    df: pd.DataFrame,
    record: DataFile,
    suffix: str,
    background_tasks: BackgroundTasks
):
    export_df = _prepare_export_dataframe(df)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    temp_path = Path(temp_file.name)
    temp_file.close()

    export_df.to_csv(temp_path, index=False, encoding="utf-8-sig")
    background_tasks.add_task(_cleanup_temp_file, str(temp_path))

    return FileResponse(
        path=temp_path,
        media_type="text/csv; charset=utf-8",
        filename=_build_export_filename(record, suffix),
    )


def _build_analysis_payload(df: pd.DataFrame):
    numeric_cols, categorical_cols = _split_chartable_columns(df)
    numeric_df = (
        df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        if numeric_cols
        else pd.DataFrame()
    )
    stats = numeric_df.describe().to_dict() if not numeric_df.empty else {}
    correlation = numeric_df.corr().to_dict() if not numeric_df.empty else {}

    return {
        "columns": df.columns.tolist(),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "statistics": stats,
        "correlation": correlation,
        "chart_support": {
            "numeric": NUMERIC_CHART_TYPES,
            "categorical": CATEGORICAL_CHART_TYPES,
        },
    }


def _build_statistics_dataframe(analysis_payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for name, stats in analysis_payload.get("statistics", {}).items():
        rows.append({
            "字段": name,
            "count": stats.get("count"),
            "mean": stats.get("mean"),
            "std": stats.get("std"),
            "min": stats.get("min"),
            "25%": stats.get("25%"),
            "50%": stats.get("50%"),
            "75%": stats.get("75%"),
            "max": stats.get("max"),
        })

    return pd.DataFrame(rows)


def _build_correlation_dataframe(analysis_payload: dict[str, Any]) -> pd.DataFrame:
    numeric_columns = analysis_payload.get("numeric_columns", [])
    correlation = analysis_payload.get("correlation", {})

    if not numeric_columns or not correlation:
        return pd.DataFrame(columns=["字段"])

    correlation_df = pd.DataFrame(correlation).reindex(
        index=numeric_columns,
        columns=numeric_columns
    )
    correlation_df.index.name = "字段"
    return correlation_df.reset_index()


def _load_analysis_plan_config(plan: AnalysisPlan) -> dict[str, Any]:
    try:
        return json.loads(plan.plan_config or "{}")
    except json.JSONDecodeError:
        return {}


def _build_analysis_plan_summary(plan_config: dict[str, Any]) -> dict[str, Any]:
    query_config = plan_config.get("query", {})
    groupby_config = plan_config.get("groupby", {})
    distribution_config = plan_config.get("distribution", {})
    chart_config = plan_config.get("chart", {})

    group_columns = [
        column
        for column in [
            groupby_config.get("primary_group_column"),
            groupby_config.get("secondary_group_column"),
        ]
        if column
    ]

    return {
        "query_filter_count": len(query_config.get("filters", [])),
        "has_sort": bool(query_config.get("sort")),
        "group_column_count": len(group_columns),
        "group_metric_count": len(groupby_config.get("metrics", [])),
        "distribution_column": distribution_config.get("column") or None,
        "chart_column": chart_config.get("column") or None,
    }


def _serialize_analysis_plan(plan: AnalysisPlan, file: DataFile) -> dict[str, Any]:
    config = _load_analysis_plan_config(plan)
    return {
        "id": plan.id,
        "name": plan.name,
        "file_name": file.original_name,
        "stored_name": file.stored_name,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        "config": config,
        "summary": _build_analysis_plan_summary(config),
    }


def _parse_cleaning_operations(operation_summary: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(operation_summary or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _serialize_cleaning_history(
    history: CleaningHistory,
    source_file: DataFile,
    result_file: DataFile,
    relation: str
) -> dict[str, Any]:
    operations = _parse_cleaning_operations(history.operation_summary)
    return {
        "id": history.id,
        "relation": relation,
        "source_file_name": source_file.original_name,
        "source_stored_name": source_file.stored_name,
        "result_file_name": result_file.original_name,
        "result_stored_name": result_file.stored_name,
        "created_at": history.created_at.isoformat() if history.created_at else None,
        "operations": operations,
        "operation_labels": [
            item.get("label")
            for item in operations
            if isinstance(item, dict) and item.get("label")
        ],
    }


def _truncate_ai_text(value: Any, limit: int = 600) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}…"


def _build_ai_dataset_context(
    record: DataFile,
    file_path: Path,
    workspace_state: AIWorkspaceState,
) -> dict[str, Any]:
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    analysis_payload = _build_analysis_payload(df)
    quality_report = _build_quality_report(df)
    field_profiles_report = _build_field_profiles(df)

    preview_rows = _stringify_dataframe(df.head(AI_MAX_PREVIEW_ROWS))
    top_missing_columns = sorted(
        [
            {
                "name": item["name"],
                "missing_count": item["missing_count"],
                "missing_ratio": item["missing_ratio"],
            }
            for item in quality_report["columns"]
            if item["missing_count"] > 0
        ],
        key=lambda item: item["missing_count"],
        reverse=True,
    )[:AI_MAX_ISSUE_COLUMNS]
    top_outlier_columns = sorted(
        [
            {
                "name": item["name"],
                "outlier_count": item["outlier_count"],
                "outlier_ratio": item["outlier_ratio"],
                "method": item.get("outlier_bounds", {}).get("method"),
                "note": item.get("outlier_bounds", {}).get("note"),
            }
            for item in quality_report["columns"]
            if item["outlier_count"] > 0
        ],
        key=lambda item: item["outlier_count"],
        reverse=True,
    )[:AI_MAX_ISSUE_COLUMNS]
    field_profiles = []
    for item in field_profiles_report.get("profiles", [])[:AI_MAX_FIELD_PROFILES]:
        field_profiles.append(
            {
                "name": item.get("name"),
                "detected_type": item.get("detected_type"),
                "role_hint": item.get("role_hint"),
                "missing_ratio": item.get("missing_ratio"),
                "unique_count": item.get("unique_count"),
                "recommended_uses": item.get("recommended_uses", [])[:4],
                "summary": _truncate_ai_text(item.get("summary"), 180),
            }
        )

    return {
        "file_name": record.original_name,
        "stored_name": record.stored_name,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": df.columns.tolist(),
        "numeric_columns": analysis_payload.get("numeric_columns", []),
        "categorical_columns": analysis_payload.get("categorical_columns", []),
        "preview_rows": preview_rows,
        "quality_summary": {
            "missing_cell_count": quality_report.get("missing_cell_count", 0),
            "columns_with_missing": quality_report.get("columns_with_missing", 0),
            "duplicate_row_count": quality_report.get("duplicate_row_count", 0),
            "outlier_row_count": quality_report.get("outlier_row_count", 0),
            "outlier_cell_count": quality_report.get("outlier_cell_count", 0),
            "top_missing_columns": top_missing_columns,
            "top_outlier_columns": top_outlier_columns,
        },
        "field_profiles": field_profiles,
        "workspace_state": {
            "active_section": workspace_state.active_section or "",
            "current_column": workspace_state.current_column or "",
            "current_chart_type": workspace_state.current_chart_type or "",
        },
    }


def _build_ai_conversation_context(messages: list[AIConversationMessage]) -> list[dict[str, str]]:
    normalized_messages = []
    for item in messages[-AI_MAX_CONVERSATION_TURNS:]:
        role = item.role.strip().lower()
        if role not in {"user", "assistant"}:
            continue
        normalized_messages.append(
            {
                "role": role,
                "content": _truncate_ai_text(item.content, 600),
            }
        )
    return normalized_messages


def _build_ai_system_prompt() -> str:
    return """
You are the AI assistant inside a structured-data analysis platform.
Your job is to help users understand tabular datasets, suggest sensible next steps, and recommend which built-in analysis module to use next.

Rules:
1. Only use the dataset context and conversation provided by the backend.
2. Do not invent columns, filters, charts, or statistics that are not present in the context.
3. Keep advice practical for beginner-friendly data analysis.
4. Prefer suggesting built-in modules instead of asking users to write code.
5. Return only a JSON object.
6. When the user asks in Chinese or the dataset context is in Chinese, answer in concise Simplified Chinese by default.
7. When the user asks for explanation or presentation guidance, prioritize clear, presentation-friendly wording.

The JSON object must contain:
- answer: string
- insights: string[]
- cautions: string[]
- suggested_actions: action[]

Each action object must contain:
- label: string
- action_type: one of ["navigate", "chart", "distribution", "groupby", "quality", "dictionary", "correlation"]
- target_section: one of ["overview", "preparation", "exploration", "visualization", "assets"]
- description: string
- params: object

Action rules:
- chart params: { column, chart_type }
- distribution params: { column, mode }
- groupby params: { primary_group_column, secondary_group_column, metric_column, metric_aggregation }
- quality / dictionary / correlation / navigate may use an empty params object

Keep suggested_actions to at most 3.
Keep insights to at most 4.
Keep cautions to at most 3.
""".strip()


def _build_ai_user_prompt(
    dataset_context: dict[str, Any],
    user_request: AIAssistantRequest,
) -> str:
    payload = {
        "user_question": user_request.question.strip(),
        "conversation": _build_ai_conversation_context(user_request.conversation),
        "dataset_context": dataset_context,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _sanitize_ai_action(
    item: Any,
    available_columns: set[str],
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    action_type = str(item.get("action_type") or "").strip().lower()
    if action_type not in AI_SUPPORTED_ACTION_TYPES:
        return None

    params = item.get("params") if isinstance(item.get("params"), dict) else {}
    target_section = str(item.get("target_section") or "").strip().lower()
    label = _truncate_ai_text(item.get("label"), 80) or "AI 建议"
    description = _truncate_ai_text(item.get("description"), 160)

    normalized_params: dict[str, Any] = {}

    if action_type == "chart":
        column = str(params.get("column") or "").strip()
        if column not in available_columns:
            return None
        normalized_params["column"] = column
        chart_type = str(params.get("chart_type") or "auto").strip().lower()
        if chart_type:
            normalized_params["chart_type"] = chart_type
        target_section = "visualization"
    elif action_type == "distribution":
        column = str(params.get("column") or "").strip()
        if column not in available_columns:
            return None
        normalized_params["column"] = column
        mode = str(params.get("mode") or "auto").strip().lower()
        if mode in {"auto", "categorical", "numeric"}:
            normalized_params["mode"] = mode
        target_section = "exploration"
    elif action_type == "groupby":
        primary_group_column = str(params.get("primary_group_column") or "").strip()
        if primary_group_column not in available_columns:
            return None
        normalized_params["primary_group_column"] = primary_group_column

        secondary_group_column = str(params.get("secondary_group_column") or "").strip()
        if secondary_group_column in available_columns and secondary_group_column != primary_group_column:
            normalized_params["secondary_group_column"] = secondary_group_column

        metric_column = str(params.get("metric_column") or "").strip()
        if metric_column in available_columns:
            normalized_params["metric_column"] = metric_column

        metric_aggregation = str(params.get("metric_aggregation") or "count").strip().lower()
        if metric_aggregation in GROUP_AGGREGATIONS:
            normalized_params["metric_aggregation"] = metric_aggregation

        target_section = "exploration"
    elif action_type == "quality":
        target_section = "preparation"
    elif action_type == "dictionary":
        target_section = "overview"
    elif action_type == "correlation":
        target_section = "visualization"
    else:
        if target_section not in AI_SUPPORTED_TARGET_SECTIONS:
            target_section = "overview"

    if target_section not in AI_SUPPORTED_TARGET_SECTIONS:
        target_section = "overview"

    return {
        "label": label,
        "action_type": action_type,
        "target_section": target_section,
        "description": description,
        "params": normalized_params,
    }


def _normalize_ai_response(
    response_json: dict[str, Any],
    dataset_context: dict[str, Any],
) -> dict[str, Any]:
    available_columns = set(dataset_context.get("columns", []))
    answer = _truncate_ai_text(response_json.get("answer"), 1200)
    if not answer:
        answer = "我已经根据当前数据概况整理出一版建议，你可以先查看下方的重点发现和推荐操作。"

    insights = [
        _truncate_ai_text(item, 180)
        for item in (response_json.get("insights") or [])
        if str(item).strip()
    ][:4]
    cautions = [
        _truncate_ai_text(item, 180)
        for item in (response_json.get("cautions") or [])
        if str(item).strip()
    ][:3]

    suggested_actions = []
    for raw_action in response_json.get("suggested_actions") or []:
        normalized_action = _sanitize_ai_action(raw_action, available_columns)
        if normalized_action:
            suggested_actions.append(normalized_action)
        if len(suggested_actions) >= AI_MAX_ACTIONS:
            break

    return {
        "answer": answer,
        "insights": insights,
        "cautions": cautions,
        "suggested_actions": suggested_actions,
        "context_summary": {
            "file_name": dataset_context.get("file_name"),
            "row_count": dataset_context.get("row_count"),
            "column_count": dataset_context.get("column_count"),
            "numeric_column_count": len(dataset_context.get("numeric_columns", [])),
            "categorical_column_count": len(dataset_context.get("categorical_columns", [])),
        },
    }


def _coerce_query_scalar(value: Any, series: pd.Series, column: str):
    if value is None:
        raise HTTPException(status_code=400, detail=f"字段 {column} 缺少查询值")

    if pd.api.types.is_datetime64_any_dtype(series):
        converted = pd.to_datetime(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(converted):
            raise HTTPException(status_code=400, detail=f"字段 {column} 的查询值无法识别为日期时间")
        return converted

    if _is_numeric_series(series):
        converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(converted):
            raise HTTPException(status_code=400, detail=f"字段 {column} 的查询值无法识别为数值")
        return float(converted)

    return str(value).strip()


def _get_query_comparison_series(series: pd.Series, operator: str, column: str):
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    if _is_numeric_series(series):
        return pd.to_numeric(series, errors="coerce")

    if operator in {"gt", "gte", "lt", "lte", "between"}:
        raise HTTPException(status_code=400, detail=f"字段 {column} 仅支持等值、包含或空值查询")

    return series.astype("string")


def _normalize_in_values(value: Any, column: str) -> list[Any]:
    if isinstance(value, list):
        raw_values = value
    elif isinstance(value, str):
        raw_values = [item.strip() for item in value.split(",") if item.strip()]
    else:
        raw_values = [value]

    if not raw_values:
        raise HTTPException(status_code=400, detail=f"字段 {column} 缺少集合查询值")

    return raw_values


def _apply_query_filters(df: pd.DataFrame, rules: list[QueryFilterRule]):
    filtered_df = df.copy()
    applied_filters = []

    for rule in rules or []:
        column = rule.column.strip()
        operator = rule.operator.strip().lower()

        if column not in filtered_df.columns:
            raise HTTPException(status_code=400, detail=f"字段 {column} 不存在")
        if operator not in QUERY_FILTER_OPERATORS:
            raise HTTPException(status_code=400, detail=f"字段 {column} 使用了不支持的查询操作")

        series = filtered_df[column]

        if operator == "is_null":
            mask = series.isna()
        elif operator == "not_null":
            mask = series.notna()
        elif operator == "contains":
            if rule.value in {None, ""}:
                raise HTTPException(status_code=400, detail=f"字段 {column} 缺少包含查询值")
            mask = series.astype("string").str.contains(str(rule.value), case=False, na=False)
        elif operator == "in":
            raw_values = _normalize_in_values(rule.value, column)
            comparison_series = _get_query_comparison_series(series, "eq", column)
            converted_values = [
                _coerce_query_scalar(item, series, column)
                for item in raw_values
            ]
            mask = comparison_series.isin(converted_values)
        elif operator == "between":
            lower = _coerce_query_scalar(rule.value, series, column)
            upper = _coerce_query_scalar(rule.second_value, series, column)
            comparison_series = _get_query_comparison_series(series, operator, column)
            if lower > upper:
                lower, upper = upper, lower
            mask = comparison_series.between(lower, upper, inclusive="both")
        else:
            comparison_series = _get_query_comparison_series(series, operator, column)
            operand = _coerce_query_scalar(rule.value, series, column)

            if operator == "eq":
                mask = comparison_series == operand
            elif operator == "ne":
                mask = comparison_series != operand
            elif operator == "gt":
                mask = comparison_series > operand
            elif operator == "gte":
                mask = comparison_series >= operand
            elif operator == "lt":
                mask = comparison_series < operand
            elif operator == "lte":
                mask = comparison_series <= operand
            else:
                raise HTTPException(status_code=400, detail=f"字段 {column} 使用了不支持的查询操作")

        filtered_df = filtered_df.loc[mask.fillna(False)].copy()
        applied_filters.append({
            "column": column,
            "operator": operator,
            "value": rule.value,
            "second_value": rule.second_value,
        })

    return filtered_df, applied_filters


def _apply_query_sort(df: pd.DataFrame, rules: list[QuerySortRule]):
    if not rules:
        return df, []

    sort_df = df.copy()
    applied_sort = []
    sort_columns = []
    ascending_flags = []

    for rule in rules:
        column = rule.column.strip()
        direction = rule.direction.strip().lower()

        if column not in sort_df.columns:
            raise HTTPException(status_code=400, detail=f"排序字段 {column} 不存在")
        if direction not in QUERY_SORT_DIRECTIONS:
            raise HTTPException(status_code=400, detail=f"排序字段 {column} 使用了不支持的方向")

        sort_columns.append(column)
        ascending_flags.append(direction == "asc")
        applied_sort.append({
            "column": column,
            "direction": direction,
        })

    try:
        sorted_df = sort_df.sort_values(
            by=sort_columns,
            ascending=ascending_flags,
            na_position="last",
            kind="mergesort"
        )
    except TypeError:
        fallback_df = sort_df.copy()
        for column in sort_columns:
            if not (
                pd.api.types.is_datetime64_any_dtype(fallback_df[column])
                or _is_numeric_series(fallback_df[column])
            ):
                fallback_df[column] = fallback_df[column].astype("string")
        sorted_df = fallback_df.sort_values(
            by=sort_columns,
            ascending=ascending_flags,
            na_position="last",
            kind="mergesort"
        )

    return sorted_df, applied_sort


def _build_query_preview_payload(df: pd.DataFrame, request: QueryPreviewRequest):
    limit = max(1, min(int(request.limit), 100))
    offset = max(0, int(request.offset))

    filtered_df, applied_filters = _apply_query_filters(df, request.filters)
    sorted_df, applied_sort = _apply_query_sort(filtered_df, request.sort)
    paged_df = sorted_df.iloc[offset:offset + limit]

    return {
        "columns": sorted_df.columns.tolist(),
        "data": _stringify_dataframe(paged_df),
        "total_rows": int(len(df)),
        "filtered_rows": int(len(sorted_df)),
        "limit": limit,
        "offset": offset,
        "has_next": offset + limit < len(sorted_df),
        "has_prev": offset > 0,
        "applied_filters": applied_filters,
        "applied_sort": applied_sort,
    }


def _normalize_group_columns(df: pd.DataFrame, group_columns: list[str]):
    normalized_columns = []
    used_columns = set()

    for raw_column in group_columns or []:
        column = raw_column.strip()
        if not column:
            continue
        if column not in df.columns:
            raise HTTPException(status_code=400, detail=f"分组字段 {column} 不存在")
        if column in used_columns:
            raise HTTPException(status_code=400, detail=f"分组字段 {column} 重复添加")

        used_columns.add(column)
        normalized_columns.append(column)

    if not normalized_columns:
        raise HTTPException(status_code=400, detail="请先选择至少一个分组字段")

    return normalized_columns


def _normalize_group_metrics(df: pd.DataFrame, metrics: list[GroupMetricRule]):
    normalized_metrics = []

    for metric in metrics or []:
        column = metric.column.strip()
        aggregations = []
        used_aggregations = set()

        if not column:
            raise HTTPException(status_code=400, detail="请选择需要统计的字段")
        if column not in df.columns:
            raise HTTPException(status_code=400, detail=f"统计字段 {column} 不存在")

        for raw_agg in metric.aggregations:
            agg = raw_agg.strip().lower()
            if agg not in GROUP_AGGREGATIONS:
                raise HTTPException(status_code=400, detail=f"字段 {column} 使用了不支持的聚合方式")
            if agg in used_aggregations:
                continue
            used_aggregations.add(agg)
            aggregations.append(agg)

        if not aggregations:
            raise HTTPException(status_code=400, detail=f"字段 {column} 至少需要一种聚合方式")

        if any(agg in {"sum", "mean", "median"} for agg in aggregations):
            if not _is_numeric_series(df[column]):
                raise HTTPException(status_code=400, detail=f"字段 {column} 仅支持 count/min/max，不能做数值聚合")

        normalized_metrics.append({
            "column": column,
            "aggregations": aggregations,
        })

    return normalized_metrics


def _build_groupby_result_dataframe(df: pd.DataFrame, request: GroupByRequest):
    filtered_df, applied_filters = _apply_query_filters(df, request.filters)
    group_columns = _normalize_group_columns(filtered_df, request.group_columns)
    metrics = _normalize_group_metrics(filtered_df, request.metrics)

    if filtered_df.empty:
        empty_df = pd.DataFrame(columns=group_columns + ["row_count"])
        return empty_df, {
            "group_columns": group_columns,
            "filtered_rows": 0,
            "applied_filters": applied_filters,
        }

    grouped = filtered_df.groupby(group_columns, dropna=False)
    result_df = grouped.size().to_frame("row_count")

    for metric in metrics:
        column = metric["column"]
        aggregations = metric["aggregations"]
        metric_series = filtered_df[column]

        if _is_numeric_series(metric_series):
            metric_frame = filtered_df.copy()
            metric_frame[column] = pd.to_numeric(metric_frame[column], errors="coerce")
        else:
            metric_frame = filtered_df

        metric_grouped = metric_frame.groupby(group_columns, dropna=False)[column]

        for agg in aggregations:
            result_column_name = f"{column}_{agg}"
            if agg == "count":
                result_df[result_column_name] = metric_grouped.count()
            elif agg == "sum":
                result_df[result_column_name] = metric_grouped.sum(min_count=1)
            elif agg == "mean":
                result_df[result_column_name] = metric_grouped.mean()
            elif agg == "min":
                result_df[result_column_name] = metric_grouped.min()
            elif agg == "max":
                result_df[result_column_name] = metric_grouped.max()
            elif agg == "median":
                result_df[result_column_name] = metric_grouped.median()

    result_df = result_df.reset_index()
    result_df = result_df.sort_values(
        by="row_count",
        ascending=False,
        kind="mergesort"
    )

    return result_df, {
        "group_columns": group_columns,
        "filtered_rows": int(len(filtered_df)),
        "applied_filters": applied_filters,
    }


def _build_groupby_payload(df: pd.DataFrame, request: GroupByRequest):
    limit = max(1, min(int(request.limit), 100))
    result_df, metadata = _build_groupby_result_dataframe(df, request)

    if result_df.empty:
        return {
            "group_columns": metadata["group_columns"],
            "metric_columns": [],
            "columns": result_df.columns.tolist(),
            "data": [],
            "filtered_rows": metadata["filtered_rows"],
            "group_count": 0,
            "displayed_group_count": 0,
            "limit": limit,
            "has_more": False,
            "applied_filters": metadata["applied_filters"],
        }
    total_group_count = int(len(result_df))
    result_df = result_df.head(limit)
    displayed_group_count = int(len(result_df))

    return {
        "group_columns": metadata["group_columns"],
        "metric_columns": [
            column for column in result_df.columns if column not in metadata["group_columns"]
        ],
        "columns": result_df.columns.tolist(),
        "data": _stringify_dataframe(result_df),
        "filtered_rows": metadata["filtered_rows"],
        "group_count": total_group_count,
        "displayed_group_count": displayed_group_count,
        "limit": limit,
        "has_more": total_group_count > displayed_group_count,
        "applied_filters": metadata["applied_filters"],
    }


def _resolve_distribution_mode(series: pd.Series, mode: str):
    normalized_mode = mode.strip().lower()
    if normalized_mode not in DISTRIBUTION_MODES:
        raise HTTPException(status_code=400, detail="不支持的频数分布分析模式")

    detected_type = _detect_column_type(series)
    resolved_mode = normalized_mode
    if normalized_mode == "auto":
        resolved_mode = "numeric" if detected_type == "numeric" else "categorical"

    if resolved_mode == "numeric" and detected_type != "numeric":
        raise HTTPException(status_code=400, detail="当前字段不适合做数值分箱分布分析")
    if detected_type == "empty":
        raise HTTPException(status_code=400, detail="当前字段没有可用于频数分布分析的数据")

    return detected_type, resolved_mode


def _build_empty_distribution_payload(
    column: str,
    detected_type: str,
    resolved_mode: str,
    applied_filters: list[dict],
    limit: int,
    include_cumulative: bool,
    bins: int | None = None
):
    return {
        "column": column,
        "detected_type": detected_type,
        "resolved_mode": resolved_mode,
        "filtered_rows": 0,
        "analyzed_rows": 0,
        "missing_rows": 0,
        "bucket_count": 0,
        "displayed_bucket_count": 0,
        "limit": limit,
        "bins": bins,
        "include_cumulative": include_cumulative,
        "has_more": False,
        "rows": [],
        "chart": {
            "categories": [],
            "counts": [],
            "cumulative_percentages": [],
        },
        "applied_filters": applied_filters,
    }


def _build_categorical_distribution_payload(
    column: str,
    series: pd.Series,
    applied_filters: list[dict],
    sort_mode: str,
    limit: int,
    include_cumulative: bool
):
    working_series = series.copy()
    if pd.api.types.is_datetime64_any_dtype(working_series):
        display_series = working_series.dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        display_series = working_series.astype("string")

    display_series = display_series.fillna("缺失值")
    counts = display_series.value_counts(dropna=False)

    if sort_mode == "frequency_desc":
        counts = counts.sort_values(ascending=False, kind="mergesort")
    else:
        counts = counts.sort_index(kind="mergesort")

    total_bucket_count = int(len(counts))
    displayed_counts = counts.head(limit)
    analyzed_rows = int(len(display_series))
    missing_rows = int(series.isna().sum())
    cumulative_counts = displayed_counts.cumsum()

    rows = []
    for label, count in displayed_counts.items():
        current_count = int(count)
        current_cumulative = int(cumulative_counts.loc[label])
        rows.append({
            "bucket": str(label),
            "count": current_count,
            "percentage": round((current_count / analyzed_rows) * 100, 2) if analyzed_rows else 0,
            "cumulative_count": current_cumulative if include_cumulative else None,
            "cumulative_percentage": (
                round((current_cumulative / analyzed_rows) * 100, 2)
                if include_cumulative and analyzed_rows
                else None
            ),
        })

    return {
        "column": column,
        "detected_type": _detect_column_type(series),
        "resolved_mode": "categorical",
        "filtered_rows": int(len(series)),
        "analyzed_rows": analyzed_rows,
        "missing_rows": missing_rows,
        "bucket_count": total_bucket_count,
        "displayed_bucket_count": int(len(displayed_counts)),
        "limit": limit,
        "bins": None,
        "include_cumulative": include_cumulative,
        "has_more": total_bucket_count > len(displayed_counts),
        "rows": rows,
        "chart": {
            "categories": [str(label) for label in displayed_counts.index.tolist()],
            "counts": displayed_counts.astype(int).tolist(),
            "cumulative_percentages": [
                row["cumulative_percentage"] for row in rows
            ] if include_cumulative else [],
        },
        "applied_filters": applied_filters,
    }


def _build_numeric_distribution_payload(
    column: str,
    series: pd.Series,
    applied_filters: list[dict],
    bins: int,
    sort_mode: str,
    limit: int,
    include_cumulative: bool
):
    numeric_series = pd.to_numeric(series, errors="coerce")
    valid_values = numeric_series.dropna()
    missing_rows = int(numeric_series.isna().sum())
    analyzed_rows = int(len(valid_values))

    if valid_values.empty:
        return _build_empty_distribution_payload(
            column=column,
            detected_type="numeric",
            resolved_mode="numeric",
            applied_filters=applied_filters,
            limit=limit,
            include_cumulative=include_cumulative,
            bins=bins,
        ) | {
            "filtered_rows": int(len(series)),
            "missing_rows": missing_rows,
        }

    if valid_values.nunique() <= 1:
        single_value = valid_values.iloc[0]
        rows = [{
            "bucket": f"= {_format_distribution_scalar(single_value)}",
            "count": analyzed_rows,
            "percentage": 100.0,
            "cumulative_count": analyzed_rows if include_cumulative else None,
            "cumulative_percentage": 100.0 if include_cumulative else None,
            "lower_bound": _format_distribution_scalar(single_value),
            "upper_bound": _format_distribution_scalar(single_value),
        }]

        return {
            "column": column,
            "detected_type": "numeric",
            "resolved_mode": "numeric",
            "filtered_rows": int(len(series)),
            "analyzed_rows": analyzed_rows,
            "missing_rows": missing_rows,
            "bucket_count": 1,
            "displayed_bucket_count": 1,
            "limit": limit,
            "bins": 1,
            "include_cumulative": include_cumulative,
            "has_more": False,
            "rows": rows,
            "chart": {
                "categories": [rows[0]["bucket"]],
                "counts": [analyzed_rows],
                "cumulative_percentages": [100.0] if include_cumulative else [],
            },
            "applied_filters": applied_filters,
        }

    effective_bins = max(3, min(int(bins), 20))
    bucketed = pd.cut(
        valid_values,
        bins=min(effective_bins, analyzed_rows),
        duplicates="drop"
    )
    counts = bucketed.value_counts(sort=False)

    if sort_mode == "frequency_desc":
        counts = counts.sort_values(ascending=False, kind="mergesort")
    else:
        counts = counts.sort_index()

    total_bucket_count = int(len(counts))
    displayed_counts = counts.head(limit)
    cumulative_counts = displayed_counts.cumsum()

    rows = []
    for interval, count in displayed_counts.items():
        current_count = int(count)
        current_cumulative = int(cumulative_counts.loc[interval])
        rows.append({
            "bucket": _format_distribution_interval(interval),
            "count": current_count,
            "percentage": round((current_count / analyzed_rows) * 100, 2) if analyzed_rows else 0,
            "cumulative_count": current_cumulative if include_cumulative else None,
            "cumulative_percentage": (
                round((current_cumulative / analyzed_rows) * 100, 2)
                if include_cumulative and analyzed_rows
                else None
            ),
            "lower_bound": _format_distribution_scalar(interval.left),
            "upper_bound": _format_distribution_scalar(interval.right),
        })

    return {
        "column": column,
        "detected_type": "numeric",
        "resolved_mode": "numeric",
        "filtered_rows": int(len(series)),
        "analyzed_rows": analyzed_rows,
        "missing_rows": missing_rows,
        "bucket_count": total_bucket_count,
        "displayed_bucket_count": int(len(displayed_counts)),
        "limit": limit,
        "bins": int(len(counts)),
        "include_cumulative": include_cumulative,
        "has_more": total_bucket_count > len(displayed_counts),
        "rows": rows,
        "chart": {
            "categories": [row["bucket"] for row in rows],
            "counts": [row["count"] for row in rows],
            "cumulative_percentages": [
                row["cumulative_percentage"] for row in rows
            ] if include_cumulative else [],
        },
        "applied_filters": applied_filters,
    }


def _build_distribution_payload(
    df: pd.DataFrame,
    request: DistributionRequest,
    limit_override: int | None = None
):
    column = request.column.strip()
    sort_mode = request.sort_mode.strip().lower()
    limit = (
        max(1, int(limit_override))
        if limit_override is not None
        else max(1, min(int(request.limit), 50))
    )
    bins = max(3, min(int(request.bins), 20))

    if not column:
        raise HTTPException(status_code=400, detail="请选择需要分析分布的字段")
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"字段 {column} 不存在")
    if sort_mode not in DISTRIBUTION_SORT_MODES:
        raise HTTPException(status_code=400, detail="不支持的频数分布排序方式")

    source_series = df[column]
    detected_type, resolved_mode = _resolve_distribution_mode(source_series, request.mode)
    filtered_df, applied_filters = _apply_query_filters(df, request.filters)

    if filtered_df.empty:
        return _build_empty_distribution_payload(
            column=column,
            detected_type=detected_type,
            resolved_mode=resolved_mode,
            applied_filters=applied_filters,
            limit=limit,
            include_cumulative=request.include_cumulative,
            bins=bins if resolved_mode == "numeric" else None,
        )

    filtered_series = filtered_df[column]
    if resolved_mode == "numeric":
        return _build_numeric_distribution_payload(
            column=column,
            series=filtered_series,
            applied_filters=applied_filters,
            bins=bins,
            sort_mode=sort_mode,
            limit=limit,
            include_cumulative=request.include_cumulative,
        )

    return _build_categorical_distribution_payload(
        column=column,
        series=filtered_series,
        applied_filters=applied_filters,
        sort_mode=sort_mode,
        limit=limit,
        include_cumulative=request.include_cumulative,
    )


def _build_outlier_detail_payload(df: pd.DataFrame, column: str):
    if column not in df.columns:
        raise HTTPException(status_code=400, detail="字段不存在")

    series = df[column]
    if not _is_numeric_series(series):
        raise HTTPException(status_code=400, detail="当前字段暂不支持异常值检测")

    outlier_mask, bounds, samples = _get_iqr_outlier_mask(series)
    detail_df = df.loc[outlier_mask].copy().head(OUTLIER_SAMPLE_LIMIT)

    if not detail_df.empty:
        detail_df.insert(0, "_row_number", detail_df.index + 1)

    return {
        "column": column,
        "count": int(outlier_mask.sum()),
        "bounds": bounds,
        "samples": samples,
        "columns": detail_df.columns.tolist(),
        "rows": _stringify_dataframe(detail_df),
    }


def _normalize_type_conversion_rules(df: pd.DataFrame, rules: list[TypeConversionRule]):
    normalized_rules = []
    used_columns = set()

    for rule in rules or []:
        column = rule.column.strip()
        target_type = rule.target_type.strip()

        if not column:
            raise HTTPException(status_code=400, detail="请选择需要转换的字段")
        if column not in df.columns:
            raise HTTPException(status_code=400, detail=f"字段 {column} 不存在")
        if target_type not in TYPE_CONVERSION_TARGETS:
            raise HTTPException(status_code=400, detail="不支持的类型转换目标")
        if column in used_columns:
            raise HTTPException(status_code=400, detail=f"字段 {column} 重复设置了转换规则")

        used_columns.add(column)
        normalized_rules.append({
            "column": column,
            "target_type": target_type,
        })

    return normalized_rules


def _apply_cleaning_steps(
    df: pd.DataFrame,
    request: CleaningRequest,
    base_schema_map: dict[str, str] | None = None
):
    _validate_cleaning_request(request)

    if not _has_cleaning_operation(request):
        raise HTTPException(status_code=400, detail="请先选择至少一种清洗方式")

    cleaned_df = df.copy()
    operations = []
    schema_map = dict(base_schema_map or {})
    conversion_rules = _normalize_type_conversion_rules(cleaned_df, request.type_conversions)

    if conversion_rules:
        conversion_operations = []

        for rule in conversion_rules:
            column = rule["column"]
            target_type = rule["target_type"]
            original_series = cleaned_df[column]
            source_non_null = int(original_series.notna().sum())
            converted_series = _convert_series_to_type(original_series, target_type)
            valid_count = int(converted_series.notna().sum())
            invalid_count = max(0, source_non_null - valid_count)

            if source_non_null > 0 and valid_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"字段 {column} 无法转换为 {target_type}"
                )

            cleaned_df[column] = converted_series
            schema_map[column] = target_type
            conversion_operations.append({
                "column": column,
                "target_type": target_type,
                "source_non_null": source_non_null,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
            })

        operations.append({
            "type": "conversion",
            "strategy": "type_conversion",
            "label": "执行数据类型转换",
            "columns": conversion_operations,
        })

    if request.missing_strategy == "drop_rows":
        removed_rows = int(cleaned_df.isna().any(axis=1).sum())
        cleaned_df = cleaned_df.dropna().reset_index(drop=True)
        operations.append({
            "type": "missing",
            "strategy": "drop_rows",
            "label": "删除含缺失值的行",
            "affected_rows": removed_rows,
        })
    elif request.missing_strategy == "fill_median_mode":
        filled_columns = []

        for column in cleaned_df.columns:
            series = cleaned_df[column]
            missing_count = int(series.isna().sum())
            if missing_count == 0:
                continue

            if _is_numeric_series(series):
                numeric_series = pd.to_numeric(series, errors="coerce")
                fill_value = numeric_series.median()
                if pd.isna(fill_value):
                    continue
                cleaned_df[column] = numeric_series.fillna(fill_value)
                fill_method = "median"
            else:
                modes = series.mode(dropna=True)
                fill_value = modes.iloc[0] if not modes.empty else "未知"
                cleaned_df[column] = series.fillna(fill_value)
                fill_method = "mode"

            filled_columns.append({
                "column": column,
                "method": fill_method,
                "filled_count": missing_count,
            })

        operations.append({
            "type": "missing",
            "strategy": "fill_median_mode",
            "label": "数值列用中位数填充，类别列用众数填充",
            "columns": filled_columns,
        })
    elif request.missing_strategy == "fill_fixed":
        affected_cells = int(cleaned_df.isna().sum().sum())
        cleaned_df = cleaned_df.fillna(request.fill_value)
        operations.append({
            "type": "missing",
            "strategy": "fill_fixed",
            "label": "使用固定值填充缺失项",
            "fill_value": request.fill_value,
            "affected_cells": affected_cells,
        })

    if request.remove_duplicates:
        duplicate_count = int(cleaned_df.duplicated().sum())
        cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
        operations.append({
            "type": "duplicate",
            "strategy": "drop_duplicates",
            "label": "删除重复行",
            "affected_rows": duplicate_count,
        })

    if request.outlier_strategy == "drop_iqr_rows":
        outlier_row_mask = pd.Series(False, index=cleaned_df.index)
        detected_columns = []

        for column in cleaned_df.columns:
            outlier_mask, bounds, samples = _get_iqr_outlier_mask(cleaned_df[column])
            outlier_count = int(outlier_mask.sum())
            if outlier_count <= 0:
                continue

            outlier_row_mask = outlier_row_mask | outlier_mask
            detected_columns.append({
                "column": column,
                "affected_rows": outlier_count,
                "bounds": bounds,
                "samples": samples,
            })

        removed_rows = int(outlier_row_mask.sum())
        if removed_rows > 0:
            cleaned_df = cleaned_df.loc[~outlier_row_mask].reset_index(drop=True)

        operations.append({
            "type": "outlier",
            "strategy": "drop_iqr_rows",
            "label": "按统计规则删除候选异常所在行",
            "affected_rows": removed_rows,
            "columns": detected_columns,
        })

    if cleaned_df.empty:
        raise HTTPException(status_code=400, detail="清洗后数据为空，请调整清洗策略")

    return cleaned_df, operations, schema_map


def _strip_clean_name_suffix(name: str) -> str:
    normalized = name.strip()
    patterns = [re.compile(r"([_-](?:cleaned|clean|rollback)(?:\d+)?(?:[_-]\d{1,8}){0,4})$", re.IGNORECASE)]

    changed = True
    while normalized and changed:
        changed = False
        for pattern in patterns:
            next_value = pattern.sub("", normalized).rstrip(" _-")
            if next_value != normalized:
                normalized = next_value
                changed = True

    return normalized or "dataset"


def _build_cleaned_filenames(current_user: User, source_record: DataFile):
    source_stem = Path(source_record.original_name).stem or "dataset"
    base_name = _strip_clean_name_suffix(source_stem)

    counter = 1
    while True:
        cleaned_original_name = _sanitize_uploaded_filename(
            f"{base_name}_{'clean' if counter == 1 else f'clean{counter}'}.csv"
        )
        stored_name = f"{current_user.id}_{cleaned_original_name}"
        if not _get_storage_path(stored_name).exists():
            return cleaned_original_name, stored_name
        counter += 1

# 根路径，测试后端是否启动成功
@app.get("/")
def root():
    return {"msg": "后端启动成功"}

# 文件上传接口
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    safe_original_name = _sanitize_uploaded_filename(file.filename)
    stored_filename = f"{current_user.id}_{safe_original_name}"
    file_path = _get_storage_path(stored_filename)

    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="上传文件不能为空")

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="上传文件不能超过 50 MB")

    existing = db.query(DataFile).filter(
        DataFile.user_id == current_user.id,
        DataFile.stored_name == stored_filename
    ).first()

    try:
        with file_path.open("wb") as f:
            f.write(content)
        _get_schema_path(stored_filename).unlink(missing_ok=True)

        if existing:
            existing.original_name = safe_original_name
            existing.file_size = len(content)
        else:
            new_file = DataFile(
                user_id=current_user.id,
                stored_name=stored_filename,
                original_name=safe_original_name,
                file_size=len(content)
            )
            db.add(new_file)

        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        if not existing and file_path.exists():
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="文件上传失败")

    return {
        "filename": stored_filename,
        "original_filename": safe_original_name,
        "msg": "上传成功"
    }

# 列出已上传文件接口
@app.get("/files")
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = (
        db.query(DataFile)
        .filter(DataFile.user_id == current_user.id)
        .order_by(DataFile.created_at.desc())
        .all()
    )

    files = [
        {
            "name": item.stored_name,
            "original_name": item.original_name,
            "size": item.file_size,
            "created_at": item.created_at.isoformat() if item.created_at else None
        }
        for item in records
    ]

    return {"files": files}


@app.post("/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        safe_original_name = sanitize_image_filename(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="上传的图片不能为空")

    if len(content) > IMAGE_MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"图片大小不能超过 {IMAGE_MAX_UPLOAD_SIZE // (1024 * 1024)}MB")

    try:
        image = load_image_from_bytes(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    original_name, stored_name = _get_unique_image_names(db, current_user, safe_original_name)
    file_path = get_image_storage_path(stored_name)

    try:
        file_path.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="图片保存失败") from exc

    mime_type = guess_image_mime_type(original_name)
    image_record = ImageFile(
        user_id=current_user.id,
        stored_name=stored_name,
        original_name=original_name,
        file_size=len(content),
        width=image.width,
        height=image.height,
        mime_type=mime_type,
    )
    db.add(image_record)
    db.flush()
    _log_image_history(
        db,
        current_user=current_user,
        source_image_id=image_record.id,
        action_type="upload",
        operation_summary="上传原始图片",
    )
    db.commit()
    db.refresh(image_record)

    return {
        "msg": "图片上传成功",
        "image": _build_image_payload(image_record),
        "quality_report": build_image_quality_report(image, len(content)),
    }


@app.get("/images")
def list_images(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = (
        db.query(ImageFile)
        .filter(ImageFile.user_id == current_user.id)
        .order_by(ImageFile.created_at.desc())
        .all()
    )

    return {"images": [_build_image_payload(item) for item in records]}


@app.get("/images/file/{filename}")
def get_image_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_image(db, current_user, filename)
    return FileResponse(
        path=file_path,
        media_type=record.mime_type or guess_image_mime_type(record.original_name),
        filename=record.original_name,
    )


@app.get("/images/meta/{filename}")
def get_image_metadata(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_image(db, current_user, filename)
    try:
        image = load_image_from_path(file_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "image": _build_image_payload(record),
        "quality_report": build_image_quality_report(image, record.file_size),
    }


@app.get("/images/history/{filename}")
def get_image_history(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record = _get_user_image_record(db, current_user, filename)
    history_items = (
        db.query(ImageProcessingHistory)
        .filter(
            ImageProcessingHistory.user_id == current_user.id,
            (
                (ImageProcessingHistory.source_image_id == record.id)
                | (ImageProcessingHistory.result_image_id == record.id)
            ),
        )
        .order_by(ImageProcessingHistory.created_at.desc(), ImageProcessingHistory.id.desc())
        .all()
    )
    related_image_ids = {
        image_id
        for item in history_items
        for image_id in (item.source_image_id, item.result_image_id)
        if image_id
    }
    related_images = (
        db.query(ImageFile.id, ImageFile.original_name)
        .filter(ImageFile.id.in_(related_image_ids))
        .all()
        if related_image_ids
        else []
    )
    image_name_map = {item.id: item.original_name for item in related_images}
    return {
        "history": [
            _serialize_image_history_item(
                item,
                source_name_map=image_name_map,
                result_name_map=image_name_map,
            )
            for item in history_items
        ]
    }


@app.post("/images/process/preview/{filename}")
def preview_image_processing(
    filename: str,
    request: ImageProcessingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_image(db, current_user, filename)

    try:
        source_image = load_image_from_path(file_path)
        processed_image, operations = apply_image_processing(
            source_image,
            grayscale=request.grayscale,
            binary_threshold=request.binary_threshold,
            rotate_degrees=request.rotate_degrees,
            flip_horizontal=request.flip_horizontal,
            flip_vertical=request.flip_vertical,
            brightness=request.brightness,
            contrast=request.contrast,
            sharpen=request.sharpen,
            denoise=request.denoise,
            crop_x=request.crop_x,
            crop_y=request.crop_y,
            crop_width=request.crop_width,
            crop_height=request.crop_height,
            target_width=request.target_width,
            target_height=request.target_height,
            preserve_aspect=request.preserve_aspect,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    preview_data_url = image_to_data_url(processed_image)

    return {
        "source_image": _build_image_payload(record),
        "preview_data_url": preview_data_url,
        "operation_summary": operations,
        "quality_report": build_image_quality_report(processed_image),
        "preview_size": {
            "width": processed_image.width,
            "height": processed_image.height,
        },
    }


@app.post("/images/process/apply/{filename}")
def apply_image_processing_result(
    filename: str,
    request: ImageProcessingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source_record, file_path = _get_user_image(db, current_user, filename)

    try:
        source_image = load_image_from_path(file_path)
        processed_image, operations = apply_image_processing(
            source_image,
            grayscale=request.grayscale,
            binary_threshold=request.binary_threshold,
            rotate_degrees=request.rotate_degrees,
            flip_horizontal=request.flip_horizontal,
            flip_vertical=request.flip_vertical,
            brightness=request.brightness,
            contrast=request.contrast,
            sharpen=request.sharpen,
            denoise=request.denoise,
            crop_x=request.crop_x,
            crop_y=request.crop_y,
            crop_width=request.crop_width,
            crop_height=request.crop_height,
            target_width=request.target_width,
            target_height=request.target_height,
            preserve_aspect=request.preserve_aspect,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    format_suffix = request.output_format.lower().strip()
    format_extension = {
        "png": ".png",
        "jpg": ".jpg",
        "jpeg": ".jpg",
        "webp": ".webp",
        "bmp": ".bmp",
    }.get(format_suffix)
    if not format_extension:
        raise HTTPException(status_code=400, detail="不支持的输出图片格式")

    base_name = normalize_image_variant_stem(source_record.original_name)
    desired_name = f"{base_name}_处理版{format_extension}"
    result_original_name, result_stored_name = _get_unique_image_names(
        db,
        current_user,
        desired_name,
    )
    result_path = get_image_storage_path(result_stored_name)

    try:
        save_image_to_path(processed_image, result_path, fmt=format_suffix)
        file_size = result_path.stat().st_size
    except OSError as exc:
        raise HTTPException(status_code=500, detail="处理后的图片保存失败") from exc

    result_record = ImageFile(
        user_id=current_user.id,
        stored_name=result_stored_name,
        original_name=result_original_name,
        file_size=int(file_size),
        width=processed_image.width,
        height=processed_image.height,
        mime_type=guess_image_mime_type(result_original_name),
        source_image_id=source_record.id,
        operation_summary="、".join(operations),
    )
    db.add(result_record)
    db.flush()
    _log_image_history(
        db,
        current_user=current_user,
        source_image_id=source_record.id,
        result_image_id=result_record.id,
        action_type="process_save",
        operation_summary="、".join(operations),
    )
    db.commit()
    db.refresh(result_record)

    return {
        "msg": "图片处理完成，已另存为新图片",
        "image": _build_image_payload(result_record),
        "quality_report": build_image_quality_report(processed_image, file_size),
        "operation_summary": operations,
    }


@app.post("/images/ocr/{filename}")
def run_image_ocr_analysis(
    filename: str,
    request: ImageProcessingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_image(db, current_user, filename)

    try:
        source_image = load_image_from_path(file_path)
        processed_image, operations = apply_image_processing(
            source_image,
            grayscale=request.grayscale,
            binary_threshold=request.binary_threshold,
            rotate_degrees=request.rotate_degrees,
            flip_horizontal=request.flip_horizontal,
            flip_vertical=request.flip_vertical,
            brightness=request.brightness,
            contrast=request.contrast,
            sharpen=request.sharpen,
            denoise=request.denoise,
            crop_x=request.crop_x,
            crop_y=request.crop_y,
            crop_width=request.crop_width,
            crop_height=request.crop_height,
            target_width=request.target_width,
            target_height=request.target_height,
            preserve_aspect=request.preserve_aspect,
        )
        ocr_result = run_image_ocr(processed_image)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    history = _log_image_history(
        db,
        current_user=current_user,
        source_image_id=record.id,
        action_type="ocr",
        operation_summary="、".join(operations),
        result_payload=ocr_result,
    )
    db.commit()

    return {
        "image": _build_image_payload(record),
        "history_id": history.id,
        "operation_summary": operations,
        "quality_report": build_image_quality_report(processed_image),
        "preview_data_url": image_to_data_url(processed_image),
        "ocr_result": ocr_result,
    }


@app.post("/images/history/{history_id}/mark-exported")
def mark_image_history_exported(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = (
        db.query(ImageProcessingHistory)
        .filter(
            ImageProcessingHistory.id == history_id,
            ImageProcessingHistory.user_id == current_user.id,
        )
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="图片处理历史不存在")

    history.exported = True
    db.commit()
    return {"msg": "导出状态已更新"}


@app.post("/images/history/{history_id}/rollback")
def rollback_image_history(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history = (
        db.query(ImageProcessingHistory)
        .filter(
            ImageProcessingHistory.id == history_id,
            ImageProcessingHistory.user_id == current_user.id,
        )
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="图片处理历史不存在")

    source_record = (
        db.query(ImageFile)
        .filter(
            ImageFile.id == history.source_image_id,
            ImageFile.user_id == current_user.id,
        )
        .first()
    )
    if not source_record:
        raise HTTPException(status_code=404, detail="历史来源图片不存在")

    source_path = get_image_storage_path(source_record.stored_name)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="历史来源图片文件不存在")

    extension = Path(source_record.original_name).suffix.lower() or ".png"
    desired_name = f"{normalize_image_variant_stem(source_record.original_name)}_回滚版{extension}"
    result_original_name, result_stored_name = _get_unique_image_names(
        db,
        current_user,
        desired_name,
    )
    result_path = get_image_storage_path(result_stored_name)

    try:
        shutil.copyfile(source_path, result_path)
        file_size = result_path.stat().st_size
    except OSError as exc:
        raise HTTPException(status_code=500, detail="回滚图片保存失败") from exc

    result_record = ImageFile(
        user_id=current_user.id,
        stored_name=result_stored_name,
        original_name=result_original_name,
        file_size=int(file_size),
        width=int(source_record.width or 0),
        height=int(source_record.height or 0),
        mime_type=source_record.mime_type,
        source_image_id=source_record.id,
        operation_summary=f"基于历史记录 {history.id} 回滚生成",
    )
    db.add(result_record)
    db.flush()
    _log_image_history(
        db,
        current_user=current_user,
        source_image_id=source_record.id,
        result_image_id=result_record.id,
        action_type="rollback",
        operation_summary=f"从历史记录 {history.id} 回滚生成新图片",
    )
    db.commit()
    db.refresh(result_record)

    return {
        "msg": "已根据历史记录回滚并另存为新图片",
        "image": _build_image_payload(result_record),
    }


@app.delete("/images/{filename}")
def delete_image_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_image(db, current_user, filename, require_disk_file=False)

    if file_path.exists():
        file_path.unlink()

    db.query(ImageProcessingHistory).filter(
        (ImageProcessingHistory.source_image_id == record.id)
        | (ImageProcessingHistory.result_image_id == record.id)
    ).delete(synchronize_session=False)
    db.delete(record)
    db.commit()

    return {"msg": "图片删除成功"}

# 📊 数据分析接口（读取CSV）
@app.get("/preview/{filename}")
def preview_data(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)

    return {
        "columns": df.columns.tolist(),
        "data": _stringify_dataframe(df.head(10))
    }

# 文件删除接口
@app.delete("/files/{filename}")
def delete_file(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(
        db,
        current_user,
        filename,
        require_disk_file=False
    )

    if file_path.exists():
        file_path.unlink()
    _get_schema_path(record.stored_name).unlink(missing_ok=True)

    db.query(AnalysisHistory).filter(AnalysisHistory.file_id == record.id).delete()
    db.query(CleaningHistory).filter(
        (CleaningHistory.source_file_id == record.id)
        | (CleaningHistory.result_file_id == record.id)
    ).delete(synchronize_session=False)
    db.query(AnalysisPlan).filter(AnalysisPlan.file_id == record.id).delete()
    db.delete(record)
    db.commit()

    return {"msg": "文件删除成功"}

# 数据质量报告接口
@app.get("/quality/{filename}")
def get_quality_report(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    return _build_quality_report(df)


@app.get("/field-profiles/{filename}")
def get_field_profiles(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    return _build_field_profiles(df)

# 数据清洗预览接口
@app.get("/quality/{filename}/outliers")
def get_outlier_detail(
    filename: str,
    column: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    return _build_outlier_detail_payload(df, column)


@app.post("/query/preview/{filename}")
def query_preview(
    filename: str,
    request: QueryPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    return _build_query_preview_payload(df, request)


@app.post("/groupby/analyze/{filename}")
def groupby_analyze(
    filename: str,
    request: GroupByRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    return _build_groupby_payload(df, request)


@app.post("/distribution/analyze/{filename}")
def distribution_analyze(
    filename: str,
    request: DistributionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    return _build_distribution_payload(df, request)


@app.post("/clean/preview/{filename}")
def preview_cleaning(
    filename: str,
    request: CleaningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source_record, file_path = _get_user_file(db, current_user, filename)
    source_schema_map = _load_schema_map(source_record.stored_name)
    source_df = _load_dataframe_with_schema(file_path, source_record.stored_name)
    cleaned_df, operations, result_schema_map = _apply_cleaning_steps(
        source_df,
        request,
        base_schema_map=source_schema_map
    )
    result_preview_df = _apply_schema_to_dataframe(cleaned_df, result_schema_map)

    return {
        "operations": operations,
        "source_summary": _build_quality_report(source_df),
        "result_summary": _build_quality_report(result_preview_df),
        "columns": result_preview_df.columns.tolist(),
        "data": _stringify_dataframe(result_preview_df.head(10))
    }

# 数据清洗应用接口
@app.post("/clean/apply/{filename}")
def apply_cleaning(
    filename: str,
    request: CleaningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    source_record, file_path = _get_user_file(db, current_user, filename)
    source_schema_map = _load_schema_map(source_record.stored_name)
    source_df = _load_dataframe_with_schema(file_path, source_record.stored_name)
    cleaned_df, operations, result_schema_map = _apply_cleaning_steps(
        source_df,
        request,
        base_schema_map=source_schema_map
    )

    cleaned_original_name, stored_name = _build_cleaned_filenames(current_user, source_record)
    cleaned_path = _get_storage_path(stored_name)

    try:
        cleaned_df.to_csv(cleaned_path, index=False, encoding="utf-8-sig")
        _save_schema_map(stored_name, result_schema_map)
        cleaned_size = cleaned_path.stat().st_size

        result_record = DataFile(
            user_id=current_user.id,
            stored_name=stored_name,
            original_name=cleaned_original_name,
            file_size=cleaned_size
        )
        db.add(result_record)
        db.flush()

        db.add(CleaningHistory(
            user_id=current_user.id,
            source_file_id=source_record.id,
            result_file_id=result_record.id,
            operation_summary=json.dumps(operations, ensure_ascii=False)
        ))
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        if cleaned_path.exists():
            cleaned_path.unlink(missing_ok=True)
        _get_schema_path(stored_name).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="\u6e05\u6d17\u7ed3\u679c\u4fdd\u5b58\u5931\u8d25")

    return {
        "msg": "\u6e05\u6d17\u5b8c\u6210\uff0c\u5df2\u53e6\u5b58\u4e3a\u65b0\u6587\u4ef6",
        "filename": stored_name,
        "original_filename": cleaned_original_name,
        "operations": operations
    }


@app.get("/cleaning/history/{filename}")
def get_cleaning_history(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, _ = _get_user_file(db, current_user, filename, require_disk_file=False)

    lineage = []
    visited_history_ids = set()
    current_result_id = record.id

    while True:
        history = (
            db.query(CleaningHistory)
            .filter(
                CleaningHistory.user_id == current_user.id,
                CleaningHistory.result_file_id == current_result_id,
            )
            .order_by(CleaningHistory.created_at.desc())
            .first()
        )

        if not history or history.id in visited_history_ids:
            break

        source_file = (
            db.query(DataFile)
            .filter(
                DataFile.id == history.source_file_id,
                DataFile.user_id == current_user.id,
            )
            .first()
        )
        result_file = (
            db.query(DataFile)
            .filter(
                DataFile.id == history.result_file_id,
                DataFile.user_id == current_user.id,
            )
            .first()
        )

        if not source_file or not result_file:
            break

        lineage.append(
            _serialize_cleaning_history(
                history,
                source_file,
                result_file,
                relation="ancestor",
            )
        )
        visited_history_ids.add(history.id)
        current_result_id = history.source_file_id

    lineage.reverse()

    descendants = []
    child_histories = (
        db.query(CleaningHistory)
        .filter(
            CleaningHistory.user_id == current_user.id,
            CleaningHistory.source_file_id == record.id,
        )
        .order_by(CleaningHistory.created_at.desc())
        .all()
    )

    for history in child_histories:
        source_file = (
            db.query(DataFile)
            .filter(
                DataFile.id == history.source_file_id,
                DataFile.user_id == current_user.id,
            )
            .first()
        )
        result_file = (
            db.query(DataFile)
            .filter(
                DataFile.id == history.result_file_id,
                DataFile.user_id == current_user.id,
            )
            .first()
        )
        if source_file and result_file:
            descendants.append(
                _serialize_cleaning_history(
                    history,
                    source_file,
                    result_file,
                    relation="descendant",
                )
            )

    return {
        "current_file": {
            "name": record.original_name,
            "stored_name": record.stored_name,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
        "lineage": lineage,
        "descendants": descendants,
        "can_rollback": bool(lineage),
    }


@app.post("/cleaning/rollback/{filename}")
def rollback_cleaning(
    filename: str,
    request: CleaningRollbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_record, _ = _get_user_file(db, current_user, filename, require_disk_file=False)

    lineage_history_ids = set()
    current_result_id = current_record.id
    while True:
        history = (
            db.query(CleaningHistory)
            .filter(
                CleaningHistory.user_id == current_user.id,
                CleaningHistory.result_file_id == current_result_id,
            )
            .order_by(CleaningHistory.created_at.desc())
            .first()
        )
        if not history or history.id in lineage_history_ids:
            break
        lineage_history_ids.add(history.id)
        current_result_id = history.source_file_id

    if request.history_id not in lineage_history_ids:
        raise HTTPException(status_code=400, detail="只能回滚当前文件所在清洗链路中的历史步骤")

    history = (
        db.query(CleaningHistory)
        .filter(
            CleaningHistory.id == request.history_id,
            CleaningHistory.user_id == current_user.id,
        )
        .first()
    )
    if not history:
        raise HTTPException(status_code=404, detail="清洗历史不存在")

    target_record = (
        db.query(DataFile)
        .filter(
            DataFile.id == history.source_file_id,
            DataFile.user_id == current_user.id,
        )
        .first()
    )
    if not target_record:
        raise HTTPException(status_code=404, detail="找不到要回滚到的源文件")

    source_path = _get_storage_path(target_record.stored_name)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="源文件不存在，无法回滚")

    rollback_original_name, stored_name = _build_rollback_filenames(current_user, target_record)
    rollback_path = _get_storage_path(stored_name)

    try:
        shutil.copyfile(source_path, rollback_path)
        source_schema_map = _load_schema_map(target_record.stored_name)
        _save_schema_map(stored_name, source_schema_map)
        rollback_size = rollback_path.stat().st_size

        result_record = DataFile(
            user_id=current_user.id,
            stored_name=stored_name,
            original_name=rollback_original_name,
            file_size=rollback_size
        )
        db.add(result_record)
        db.flush()

        rollback_operations = [{
            "type": "rollback",
            "strategy": "rollback_to_history_source",
            "label": f"回滚到 {target_record.original_name}",
            "source_history_id": history.id,
            "restored_from": target_record.original_name,
        }]
        db.add(CleaningHistory(
            user_id=current_user.id,
            source_file_id=current_record.id,
            result_file_id=result_record.id,
            operation_summary=json.dumps(rollback_operations, ensure_ascii=False)
        ))
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        if rollback_path.exists():
            rollback_path.unlink(missing_ok=True)
        _get_schema_path(stored_name).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="回滚文件保存失败")

    return {
        "msg": "已按所选历史节点生成回滚文件",
        "filename": stored_name,
        "original_filename": rollback_original_name,
    }

# 数据分析接口（分析CSV文件，返回列信息、统计指标、相关性矩阵和图表支持类型等数据）
@app.post("/export/query/{filename}")
def export_query_result(
    filename: str,
    request: QueryPreviewRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    filtered_df, _ = _apply_query_filters(df, request.filters)
    sorted_df, _ = _apply_query_sort(filtered_df, request.sort)
    return _create_csv_export_response(
        sorted_df,
        record,
        "query_result",
        background_tasks,
    )


@app.post("/export/groupby/{filename}")
def export_groupby_result(
    filename: str,
    request: GroupByRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    result_df, _ = _build_groupby_result_dataframe(df, request)
    return _create_csv_export_response(
        result_df,
        record,
        "group_statistics",
        background_tasks,
    )


@app.post("/export/distribution/{filename}")
def export_distribution_result(
    filename: str,
    request: DistributionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    payload = _build_distribution_payload(
        df,
        request,
        limit_override=max(1, len(df)),
    )
    export_df = pd.DataFrame(payload.get("rows", []))
    return _create_csv_export_response(
        export_df,
        record,
        "distribution",
        background_tasks,
    )


@app.get("/export/statistics/{filename}")
def export_statistics_result(
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    analysis_payload = _build_analysis_payload(df)
    export_df = _build_statistics_dataframe(analysis_payload)
    return _create_csv_export_response(
        export_df,
        record,
        "statistics",
        background_tasks,
    )


@app.get("/export/correlation/{filename}")
def export_correlation_result(
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, record.stored_name)
    analysis_payload = _build_analysis_payload(df)
    export_df = _build_correlation_dataframe(analysis_payload)
    return _create_csv_export_response(
        export_df,
        record,
        "correlation_matrix",
        background_tasks,
    )


@app.get("/analyze/{filename}")
def analyze_data(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)

    try:
        df = _load_dataframe_with_schema(file_path, record.stored_name)

        return _build_analysis_payload(df)

    except Exception:
        raise HTTPException(status_code=500, detail="数据分析失败")
    
# 📊 数据分析接口（图表数据）
@app.get("/chart/{filename}")
def get_chart_data(
    filename: str,
    column: str,
    chart_type: str = "auto",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, file_record.stored_name)

    if column not in df.columns:
        raise HTTPException(status_code=400, detail="\u5b57\u6bb5\u4e0d\u5b58\u5728")

    series = df[column].dropna()
    if series.empty:
        raise HTTPException(status_code=400, detail="\u8be5\u5b57\u6bb5\u6ca1\u6709\u53ef\u7528\u4e8e\u7ed8\u56fe\u7684\u6570\u636e")

    if _is_numeric_series(df[column]):
        values = pd.to_numeric(series, errors="coerce").dropna()
        if values.empty:
            raise HTTPException(status_code=400, detail="\u8be5\u6570\u503c\u5b57\u6bb5\u6ca1\u6709\u6709\u6548\u6570\u636e")
        chart_result = _build_numeric_chart(column, values, chart_type)
    else:
        chart_result = _build_categorical_chart(column, series, chart_type)

    history = AnalysisHistory(
        user_id=current_user.id,
        file_id=file_record.id,
        column_name=column,
        chart_type=chart_result["resolved_type"]
    )
    db.add(history)
    db.commit()

    return chart_result


@app.post("/predict/{filename}")
def predict_data(
    filename: str,
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_record, file_path = _get_user_file(db, current_user, filename)
    df = _load_dataframe_with_schema(file_path, file_record.stored_name)

    return _build_prediction_payload(df, request)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

# 用户注册接口
@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    username = user.username.strip()

    if not username or not user.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    is_first_user = db.query(User.id).first() is None
    hashed_pwd = hash_password(user.password)
    db_user = User(
        username=username,
        password=hashed_pwd,
        role="admin" if is_first_user else "user",
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "msg": "注册成功",
        "user": _serialize_user(db_user),
    }


# 用户登录接口，成功后返回 JWT 令牌
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    username = user.username.strip()

    if not username or not user.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    db_user = db.query(User).filter(User.username == username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    db_user.last_login_at = datetime.now()
    db.commit()
    db.refresh(db_user)

    token = create_access_token({"sub": db_user.username, "role": db_user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": db_user.username,
        "role": db_user.role,
        "user": _serialize_user(db_user),
    }

# 获取当前用户信息接口
@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)


@app.get("/account/summary")
def get_account_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "file_count": db.query(DataFile).filter(DataFile.user_id == current_user.id).count(),
        "image_count": db.query(ImageFile).filter(ImageFile.user_id == current_user.id).count(),
        "analysis_count": db.query(AnalysisHistory).filter(AnalysisHistory.user_id == current_user.id).count(),
        "cleaning_count": db.query(CleaningHistory).filter(CleaningHistory.user_id == current_user.id).count(),
        "plan_count": db.query(AnalysisPlan).filter(AnalysisPlan.user_id == current_user.id).count(),
    }


def _get_recent_analysis_records(
    db: Session,
    current_user: User,
    limit: int,
) -> list[dict[str, Any]]:
    records = (
        db.query(AnalysisHistory, DataFile)
        .join(DataFile, AnalysisHistory.file_id == DataFile.id)
        .filter(AnalysisHistory.user_id == current_user.id)
        .order_by(AnalysisHistory.created_at.desc(), AnalysisHistory.id.desc())
        .limit(limit)
        .all()
    )

    return [_serialize_analysis_history_item(history, file) for history, file in records]


def _get_recent_image_history_records(
    db: Session,
    current_user: User,
    limit: int,
) -> list[dict[str, Any]]:
    history_items = (
        db.query(ImageProcessingHistory)
        .filter(ImageProcessingHistory.user_id == current_user.id)
        .order_by(ImageProcessingHistory.created_at.desc(), ImageProcessingHistory.id.desc())
        .limit(limit)
        .all()
    )
    related_image_ids = {
        image_id
        for item in history_items
        for image_id in (item.source_image_id, item.result_image_id)
        if image_id
    }
    related_images = (
        db.query(ImageFile.id, ImageFile.original_name)
        .filter(
            ImageFile.user_id == current_user.id,
            ImageFile.id.in_(related_image_ids),
        )
        .all()
        if related_image_ids
        else []
    )
    image_name_map = {item.id: item.original_name for item in related_images}

    return [
        _serialize_image_history_item(
            item,
            source_name_map=image_name_map,
            result_name_map=image_name_map,
        )
        for item in history_items
    ]


def _build_account_activity_series(
    db: Session,
    current_user: User,
    days: int,
) -> list[dict[str, Any]]:
    days = max(7, min(days, 30))
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)
    start_at = datetime.combine(start_date, datetime.min.time())
    buckets = [
        {
            "date": (start_date + timedelta(days=index)).isoformat(),
            "label": (start_date + timedelta(days=index)).strftime("%m/%d"),
            "analysis": 0,
            "image": 0,
            "cleaning": 0,
            "asset": 0,
            "plan": 0,
            "total": 0,
        }
        for index in range(days)
    ]
    bucket_map = {item["date"]: item for item in buckets}

    def add_point(occurred_at: datetime | None, key: str):
        if not occurred_at:
            return

        bucket = bucket_map.get(occurred_at.date().isoformat())
        if not bucket:
            return

        bucket[key] += 1
        bucket["total"] += 1

    activity_sources = [
        (AnalysisHistory, AnalysisHistory.created_at, "analysis"),
        (ImageProcessingHistory, ImageProcessingHistory.created_at, "image"),
        (CleaningHistory, CleaningHistory.created_at, "cleaning"),
        (DataFile, DataFile.created_at, "asset"),
        (AnalysisPlan, AnalysisPlan.updated_at, "plan"),
    ]

    for model, timestamp_column, key in activity_sources:
        rows = (
            db.query(timestamp_column)
            .filter(
                model.user_id == current_user.id,
                timestamp_column >= start_at,
            )
            .all()
        )
        for row in rows:
            add_point(row[0], key)

    return buckets


@app.get("/account/activity")
def get_account_activity(
    limit: int = 10,
    days: int = 14,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    limit = max(1, min(limit, 20))
    days = max(7, min(days, 30))

    return {
        "recent_analysis": _get_recent_analysis_records(db, current_user, limit),
        "recent_image_history": _get_recent_image_history_records(db, current_user, limit),
        "activity_series": _build_account_activity_series(db, current_user, days),
    }


@app.patch("/account/password")
def change_current_user_password(
    request: UserPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    old_password = request.old_password.strip()
    new_password = request.new_password.strip()

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="旧密码和新密码不能为空")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少需要 6 位")

    db_user = db.query(User).filter(User.id == current_user.id).first()
    if not db_user or not verify_password(old_password, db_user.password):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    db_user.password = hash_password(new_password)
    db.commit()

    return {"msg": "密码已更新"}


@app.get("/admin/summary")
def get_admin_summary(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == "admin").count()
    file_count = db.query(DataFile).count()
    image_count = db.query(ImageFile).count()
    analysis_count = db.query(AnalysisHistory).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "disabled_users": max(total_users - active_users, 0),
        "admin_users": admin_users,
        "file_count": file_count,
        "image_count": image_count,
        "analysis_count": analysis_count,
    }


@app.get("/admin/users")
def list_admin_users(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    query = db.query(User)
    if q:
        keyword = f"%{q.strip()}%"
        query = query.filter(User.username.like(keyword))

    total = query.count()
    users = (
        query.order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "users": [_serialize_user(user) for user in users],
    }


@app.patch("/admin/users/{user_id}")
def update_admin_user(
    user_id: int,
    request: AdminUserUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if request.role is not None:
        role = request.role.strip().lower()
        if role not in USER_ROLES:
            raise HTTPException(status_code=400, detail="角色只能是 user 或 admin")
        if target_user.id == current_admin.id and role != "admin":
            raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
        target_user.role = role

    if request.is_active is not None:
        if target_user.id == current_admin.id and not request.is_active:
            raise HTTPException(status_code=400, detail="不能禁用自己的账号")
        target_user.is_active = request.is_active

    if request.password is not None:
        new_password = request.password.strip()
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="新密码至少需要 6 位")
        target_user.password = hash_password(new_password)

    db.commit()
    db.refresh(target_user)

    return {
        "msg": "用户信息已更新",
        "user": _serialize_user(target_user),
    }

# 获取分析历史接口，返回用户的分析记录列表，包含文件名、字段名、图表类型和分析时间等信息
@app.get("/history")
def get_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    limit = max(1, min(limit, 100))

    records = (
        db.query(AnalysisHistory, DataFile)
        .join(DataFile, AnalysisHistory.file_id == DataFile.id)
        .filter(AnalysisHistory.user_id == current_user.id)
        .order_by(AnalysisHistory.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "records": [
            _serialize_analysis_history_item(history, file)
            for history, file in records
        ]
    }


@app.get("/plans")
def get_analysis_plans(
    filename: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = (
        db.query(AnalysisPlan, DataFile)
        .join(DataFile, AnalysisPlan.file_id == DataFile.id)
        .filter(AnalysisPlan.user_id == current_user.id)
    )

    if filename:
        record, _ = _get_user_file(db, current_user, filename, require_disk_file=False)
        query = query.filter(AnalysisPlan.file_id == record.id)

    records = (
        query.order_by(AnalysisPlan.updated_at.desc(), AnalysisPlan.created_at.desc())
        .all()
    )

    return {
        "plans": [
            _serialize_analysis_plan(plan, file)
            for plan, file in records
        ]
    }


@app.post("/plans/{filename}")
def save_analysis_plan(
    filename: str,
    request: AnalysisPlanSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, _ = _get_user_file(db, current_user, filename, require_disk_file=False)
    plan_name = request.name.strip()

    if not plan_name:
        raise HTTPException(status_code=400, detail="方案名称不能为空")

    plan_config = json.dumps(request.plan.model_dump(), ensure_ascii=False)
    existing = (
        db.query(AnalysisPlan)
        .filter(
            AnalysisPlan.user_id == current_user.id,
            AnalysisPlan.file_id == record.id,
            AnalysisPlan.name == plan_name,
        )
        .first()
    )

    now = datetime.now()

    if existing:
        existing.plan_config = plan_config
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return {
            "msg": "分析方案已更新",
            "plan": _serialize_analysis_plan(existing, record),
        }

    plan = AnalysisPlan(
        user_id=current_user.id,
        file_id=record.id,
        name=plan_name,
        plan_config=plan_config,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return {
        "msg": "分析方案已保存",
        "plan": _serialize_analysis_plan(plan, record),
    }


@app.delete("/plans/{plan_id}")
def delete_analysis_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = (
        db.query(AnalysisPlan)
        .filter(
            AnalysisPlan.id == plan_id,
            AnalysisPlan.user_id == current_user.id,
        )
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="分析方案不存在")

    db.delete(plan)
    db.commit()

    return {"msg": "分析方案已删除"}

# 仪表盘数据接口，返回用户文件和分析历史的统计信息
@app.get("/ai/status")
def get_ai_status():
    status = get_ai_provider_status()
    return {
        "enabled": status.enabled,
        "provider": status.provider,
        "model": status.model,
        "message": status.message,
    }


@app.post("/ai/assistant/{filename}")
def run_ai_assistant(
    filename: str,
    request: AIAssistantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record, file_path = _get_user_file(db, current_user, filename)
    provider_status = get_ai_provider_status()

    if not provider_status.enabled:
        raise HTTPException(
            status_code=503,
            detail="AI 助手尚未完成配置，请先设置 AI_PROVIDER、AI_API_KEY 和 AI_MODEL",
        )

    dataset_context = _build_ai_dataset_context(record, file_path, request.workspace_state)
    system_prompt = _build_ai_system_prompt()
    user_prompt = _build_ai_user_prompt(dataset_context, request)

    try:
        provider = get_active_ai_provider()
        raw_response = provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=f"AI 提供商调用失败：{exc}") from exc

    normalized_response = _normalize_ai_response(raw_response, dataset_context)
    return {
        "provider": provider_status.provider,
        "model": provider_status.model,
        **normalized_response,
    }


@app.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_count = db.query(DataFile).filter(DataFile.user_id == current_user.id).count()
    history_count = db.query(AnalysisHistory).filter(AnalysisHistory.user_id == current_user.id).count()

    latest_file = (
        db.query(DataFile)
        .filter(DataFile.user_id == current_user.id)
        .order_by(DataFile.created_at.desc())
        .first()
    )

    return {
        "file_count": file_count,
        "history_count": history_count,
        "latest_file": latest_file.original_name if latest_file else None
    }
