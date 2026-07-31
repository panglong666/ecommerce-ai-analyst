"""文档加载器：txt/md/csv/pdf/docx -> 纯文本。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_text(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".txt", ".md"):
        return p.read_text(encoding="utf-8")
    if ext == ".csv":
        df = pd.read_csv(p)
        return df.to_string(index=False)
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(p)
        return df.to_string(index=False)
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(p))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:  # noqa: BLE001
            return f"[PDF 解析失败: {e}]"
    if ext == ".docx":
        try:
            import docx2txt

            return docx2txt.process(str(p))
        except Exception as e:  # noqa: BLE001
            return f"[DOCX 解析失败: {e}]"
    raise ValueError(f"不支持的文档格式: {ext}（支持 txt/md/csv/xlsx/pdf/docx）")
