"""跨次对比快照：每次上传后保存各维度聚合，供下次环比。

存储优先用数据源自带的 engine（Mock 即 SQLite）；无 engine 时退回 JSON 文件。
所有异常都被吞掉，保证「存快照」永远不影响正常上传 / 分析。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ecommerce_ai.alerting.profiler import profile_table
from ecommerce_ai.alerting.rules import _aggregate
from ecommerce_ai.core.config import settings
from ecommerce_ai.data.source import get_data_source

_SNAP_TABLE = "alert_snapshots"
_JSON_NAME = "alert_snapshots.json"


def store_snapshot(name: str, df) -> None:
    """落库前调用：保存本次各维度聚合，供跨次对比。"""
    try:
        src = get_data_source()
        profile = profile_table(df)
        agg: dict[str, dict] = {m: _aggregate(df, profile, m) for m in profile.metric_cols}
        payload = {
            "name": name,
            "ts": datetime.now(timezone.utc).isoformat(),
            "metric_cols": profile.metric_cols,
            "dim_cols": profile.dim_cols,
            "agg": agg,
        }
        engine = getattr(src, "engine", None)
        if engine is not None:
            from sqlalchemy import text

            with engine.connect() as conn:
                conn.execute(text(
                    f"CREATE TABLE IF NOT EXISTS {_SNAP_TABLE} "
                    "(name TEXT, ts TEXT, payload TEXT)"
                ))
                conn.execute(
                    text(f"INSERT INTO {_SNAP_TABLE} (name, ts, payload) VALUES (:n, :t, :p)"),
                    {"n": name, "t": payload["ts"], "p": json.dumps(payload, ensure_ascii=False)},
                )
                conn.commit()
        else:
            _store_json(name, payload)
    except Exception as e:  # noqa: BLE001
        print(f"[snapshots] 存储失败(已忽略): {e}")


def get_previous(name: str) -> dict | None:
    """返回同名表最近一次「历史」快照（排除刚存入的当前这次）。"""
    try:
        src = get_data_source()
        engine = getattr(src, "engine", None)
        rows: list[str] = []
        if engine is not None:
            from sqlalchemy import text

            with engine.connect() as conn:
                r = conn.execute(
                    text(f"SELECT payload FROM {_SNAP_TABLE} WHERE name=:n ORDER BY ts DESC LIMIT 2"),
                    {"n": name},
                )
                rows = [row[0] for row in r.fetchall()]
        else:
            rows = _load_json(name)
        if len(rows) < 2:
            return None
        return json.loads(rows[-2])  # 倒数第二条 = 上一次上传
    except Exception:  # noqa: BLE001
        return None


def _store_json(name: str, payload: dict) -> None:
    p: Path = settings.abs(settings.upload_dir) / _JSON_NAME
    data: dict[str, list[str]] = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
    data.setdefault(name, []).append(json.dumps(payload, ensure_ascii=False))
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _load_json(name: str) -> list[str]:
    p: Path = settings.abs(settings.upload_dir) / _JSON_NAME
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get(name, [])
    except Exception:  # noqa: BLE001
        return []
