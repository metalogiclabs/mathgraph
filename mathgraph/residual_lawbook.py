"""Small SQLite residual lawbook helpers for autonomous compounding runs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ResidualLawbook:
    path: Path

    @classmethod
    def open(cls, path: str | Path) -> "ResidualLawbook":
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        book = cls(target)
        book.init()
        return book

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path))

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS run_summaries (run_id TEXT PRIMARY KEY, created_at TEXT, payload_json TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS episode_metrics (row_id TEXT PRIMARY KEY, run_id TEXT, episode INTEGER, payload_json TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS residual_obstructions (row_id TEXT PRIMARY KEY, run_id TEXT, obstruction_name TEXT, payload_json TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS terminal_audit (row_id TEXT PRIMARY KEY, run_id TEXT, payload_json TEXT NOT NULL)")
            conn.commit()

    def write_run_summary(self, run_id: str, payload: Mapping[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_summaries(run_id, created_at, payload_json) VALUES (?, ?, ?)",
                (run_id, utc_now(), json.dumps(dict(payload), sort_keys=True)),
            )
            conn.commit()

    def write_rows(self, table: str, run_id: str, rows: Iterable[Mapping[str, Any]]) -> int:
        allowed = {"episode_metrics", "residual_obstructions", "terminal_audit"}
        if table not in allowed:
            raise ValueError(f"unsupported residual lawbook table: {table}")
        count = 0
        with self.connect() as conn:
            for count, row in enumerate(rows, start=1):
                data = dict(row)
                row_id = str(data.get("row_id") or f"{run_id}:{table}:{count}")
                if table == "episode_metrics":
                    conn.execute(
                        "INSERT OR REPLACE INTO episode_metrics(row_id, run_id, episode, payload_json) VALUES (?, ?, ?, ?)",
                        (row_id, run_id, int(data.get("episode", 0) or 0), json.dumps(data, sort_keys=True)),
                    )
                elif table == "residual_obstructions":
                    conn.execute(
                        "INSERT OR REPLACE INTO residual_obstructions(row_id, run_id, obstruction_name, payload_json) VALUES (?, ?, ?, ?)",
                        (row_id, run_id, str(data.get("obstruction_name", "")), json.dumps(data, sort_keys=True)),
                    )
                else:
                    conn.execute(
                        "INSERT OR REPLACE INTO terminal_audit(row_id, run_id, payload_json) VALUES (?, ?, ?)",
                        (row_id, run_id, json.dumps(data, sort_keys=True)),
                    )
            conn.commit()
        return count


def write_repair_lawbook(sqlite_path: str | Path, repair_df: Any, obstruction_df: Any, metadata: Mapping[str, Any] | None = None) -> None:
    """Persist advisory repair/obstruction rows for later autonomous reuse."""

    metadata = dict(metadata or {})
    book = ResidualLawbook.open(sqlite_path)
    run_id = str(metadata.get("run_id") or "autonomous_v2")
    repair_rows = _records(repair_df)
    obstruction_rows = _records(obstruction_df)
    book.write_run_summary(run_id, {"metadata": metadata, "repair_rows": len(repair_rows), "obstruction_rows": len(obstruction_rows)})
    book.write_rows("episode_metrics", run_id, ({**row, **metadata} for row in repair_rows))
    book.write_rows("residual_obstructions", run_id, ({**row, **metadata} for row in obstruction_rows))


def load_repair_lawbook(sqlite_path: str | Path) -> pd.DataFrame:
    path = Path(sqlite_path)
    if not path.exists():
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    with sqlite3.connect(str(path)) as conn:
        for table in ("episode_metrics", "residual_obstructions"):
            try:
                for payload, in conn.execute(f"SELECT payload_json FROM {table}"):
                    rows.append(json.loads(payload))
            except sqlite3.Error:
                continue
    return pd.DataFrame(rows)


def recommend_from_lawbook(pair_features: Any, lawbook_df: pd.DataFrame, budget: int) -> list[Any]:
    """Return constructor indices/families suggested by prior advisory repair rows."""

    if lawbook_df is None or lawbook_df.empty:
        return []
    features = pair_features if isinstance(pair_features, Mapping) else {}
    basin = str(features.get("basin", ""))
    df = lawbook_df.copy()
    if basin and "basin" in df.columns:
        scoped = df[df["basin"].astype(str) == basin]
        if not scoped.empty:
            df = scoped
    gain_col = "marginal_gain" if "marginal_gain" in df.columns else None
    if gain_col:
        df["_gain"] = pd.to_numeric(df[gain_col], errors="coerce").fillna(0)
        df = df.sort_values("_gain", ascending=False)
    out: list[Any] = []
    for _, row in df.iterrows():
        value = row.get("constructor_idx", row.get("family", ""))
        if value not in out and value not in ("", None):
            out.append(value)
        if len(out) >= int(budget):
            break
    return out


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        try:
            records = value.to_dict("records")
            if isinstance(records, list):
                return [_jsonable(dict(row)) for row in records]
        except TypeError:
            pass
    return [_jsonable(dict(row)) for row in value]


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in row.items():
        if isinstance(value, (dict, list, tuple, str, int, float, bool)) or value is None:
            out[key] = value
        else:
            try:
                out[key] = value.item()
            except Exception:
                out[key] = str(value)
    return out
