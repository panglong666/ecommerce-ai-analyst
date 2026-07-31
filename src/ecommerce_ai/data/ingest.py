"""用户上传数据接入：CSV/Excel -> 校验 -> 落库 -> 刷新 schema。"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ecommerce_ai.core.config import settings
from ecommerce_ai.core.models import DatasetInfo
from ecommerce_ai.data.source import get_data_source

_MAX_ROWS = 200_000


def _sanitize_table_name(filename: str) -> str:
    stem = Path(filename).stem
    name = re.sub(r"[^0-9a-zA-Z_\u4e00-\u9fa5]", "_", stem)
    if not name:
        name = "uploaded"
    if name[0].isdigit():
        name = "t_" + name
    return name.lower()[:40]


def _read_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    raise ValueError(f"不支持的结构化文件格式: {suffix}（支持 csv/xlsx）")


def ingest_structured_file(path: str | Path, table_name: str | None = None) -> DatasetInfo:
    """上传 CSV/Excel -> 落库为新表，立即可被 NL2SQL 查询。"""
    p = Path(path)
    df = _read_file(p)
    if len(df) > _MAX_ROWS:
        df = df.head(_MAX_ROWS)
    if df.empty:
        raise ValueError("文件为空或无可读数据")
    # 列名清理
    df.columns = [str(c).strip() or f"col_{i}" for i, c in enumerate(df.columns)]
    name = table_name or _sanitize_table_name(p.name)
    src = get_data_source()
    info = src.ingest_dataframe(df, name)
    print(f"[ingest] 已导入表 {name}（{info.rows} 行，{len(info.columns)} 列）")
    return info


def save_upload(content: bytes, filename: str) -> Path:
    """把上传内容存到 upload_dir，返回路径。"""
    upload_dir = settings.abs(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    p = upload_dir / filename
    p.write_bytes(content)
    return p
