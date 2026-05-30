"""Trade journal artifact browsing, import, and export endpoints."""

from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Trade, User
from app.schemas import (
    JournalArtifactType,
    TradeJournalArtifact,
    TradeJournalEntry,
    TradeJournalExportMetadata,
    TradeJournalImportSummary,
    TradeJournalRelationshipSummary,
    TradeJournalSummary,
)
from app.security import get_current_user
from app.services.trade_journal import TradeJournal, TRADE_COLUMNS

router = APIRouter()

_ARTIFACT_CONTENT_TYPES: dict[str, str] = {
    "trades": "text/csv",
    "pending_orders": "text/csv",
    "equity_curve": "text/csv",
    "drawdown": "text/csv",
    "rewards": "text/csv",
    "performance": "application/json",
    "actions": "text/csv",
}


def _journal(output_dir: str, suffix: str) -> TradeJournal:
    return TradeJournal(_safe_output_dir(output_dir), suffix=suffix)


def _safe_output_dir(output_dir: str) -> Path:
    path = Path(output_dir or "simulation_output")
    if path.is_absolute() or ".." in path.parts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="output_dir must be a relative path inside the application workspace.",
        )
    return path


def _artifact_paths(journal: TradeJournal) -> dict[str, Path]:
    return {
        "trades": journal.paths.trades_path,
        "pending_orders": journal.paths.pending_orders_path,
        "equity_curve": journal.paths.equity_curve_path,
        "drawdown": journal.paths.drawdown_path,
        "rewards": journal.paths.rewards_path,
        "performance": journal.paths.performance_path,
        "actions": journal.paths.action_journal_path,
    }


def _artifact_metadata(name: str, path: Path) -> TradeJournalArtifact:
    exists = path.exists()
    stat = path.stat() if exists else None
    return TradeJournalArtifact(
        name=name,
        artifact_type=name,  # type: ignore[arg-type]
        path=str(path),
        exists=exists,
        size_bytes=stat.st_size if stat else None,
        modified_at=datetime.utcfromtimestamp(stat.st_mtime) if stat else None,
        row_count=_count_rows(path) if exists else None,
        content_type=_ARTIFACT_CONTENT_TYPES[name],
    )


def _count_rows(path: Path) -> int | None:
    try:
        if path.suffix.lower() == ".csv":
            return int(len(pd.read_csv(path)))
        if path.suffix.lower() == ".json":
            data = pd.read_json(path)
            return int(len(data)) if not data.empty else None
    except (OSError, ValueError):
        return None
    return None


def _load_trade_entries(path: Path) -> list[TradeJournalEntry]:
    if not path.exists():
        return []
    try:
        if path.suffix.lower() == ".json":
            frame = pd.read_json(path)
        else:
            frame = pd.read_csv(path)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Trade journal artifact could not be parsed: {exc}",
        ) from exc

    entries: list[TradeJournalEntry] = []
    for row_number, row in enumerate(frame.to_dict(orient="records"), start=1):
        raw = _json_ready(row)
        entries.append(
            TradeJournalEntry(
                id=str(row_number),
                row_number=row_number,
                entry_date=_string_or_none(raw.get("entry_date")),
                exit_date=_string_or_none(raw.get("exit_date")),
                type=_string_or_none(raw.get("type")),
                entry_price=_float_or_none(raw.get("entry_price")),
                exit_price=_float_or_none(raw.get("exit_price")),
                size=_float_or_none(raw.get("size")),
                pnl=_float_or_none(raw.get("pnl")),
                exit_reason=_string_or_none(raw.get("exit_reason")),
                balance_after=_float_or_none(raw.get("balance_after")),
                raw=raw,
            )
        )
    return entries


def _json_ready(row: dict[str, Any]) -> dict[str, Any]:
    return {key: (None if pd.isna(value) else value) for key, value in row.items()}


def _string_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _relationships() -> TradeJournalRelationshipSummary:
    return TradeJournalRelationshipSummary(
        persisted_trade_rows="Rows in the trades database table are user-scoped records created by /trades/open and /trades/close for simple P&L tracking.",
        broker_order_records="Broker/order records come from the mock order-management layer and represent executable or simulated orders; they do not automatically create persisted Trade rows.",
        journal_artifacts="CSV/JSON journal artifacts are files emitted by simulations or imported through this API for archival, audit, and reporting workflows.",
    )


@router.get("", response_model=TradeJournalSummary)
def list_trade_journal(
    output_dir: str = Query("simulation_output"),
    suffix: str = Query("v2"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeJournalSummary:
    """List journal entries, managed artifacts, and boundary documentation."""

    journal = _journal(output_dir, suffix)
    paths = _artifact_paths(journal)
    entries = _load_trade_entries(paths["trades"])
    db_query = db.query(Trade).filter(Trade.user_id == current_user.id)
    return TradeJournalSummary(
        entries=entries,
        artifacts=[_artifact_metadata(name, path) for name, path in paths.items()],
        db_trade_count=db_query.count(),
        open_db_trade_count=db_query.filter(Trade.status == "open").count(),
        closed_db_trade_count=db_query.filter(Trade.status == "closed").count(),
        relationships=_relationships(),
    )


@router.post("/import", response_model=TradeJournalImportSummary)
def import_trade_journal_artifact(
    artifact_type: JournalArtifactType = Query("trades"),
    output_dir: str = Query("simulation_output"),
    suffix: str = Query("v2"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> TradeJournalImportSummary:
    """Import a CSV or JSON trade journal artifact into the managed journal path."""

    del current_user
    journal = _journal(output_dir, suffix)
    journal.ensure_directories()
    path = _artifact_paths(journal)[artifact_type]
    expected_suffix = ".json" if artifact_type == "performance" else ".csv"
    if not file.filename or Path(file.filename).suffix.lower() != expected_suffix:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{artifact_type} imports require a {expected_suffix} file.",
        )

    replaced_existing = path.exists()
    with path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    rows_imported = _count_rows(path)
    return TradeJournalImportSummary(
        artifact=_artifact_metadata(artifact_type, path),
        rows_imported=rows_imported,
        replaced_existing=replaced_existing,
        message=f"Imported {artifact_type} artifact to {path}.",
    )


@router.get("/export", response_model=None)
def export_trade_journal(
    output_dir: str = Query("simulation_output"),
    suffix: str = Query("v2"),
    download: bool = Query(False),
    current_user: User = Depends(get_current_user),
) -> TradeJournalExportMetadata | FileResponse:
    """Create an archive of existing journal artifacts or download it."""

    del current_user
    journal = _journal(output_dir, suffix)
    export_dir = journal.journal_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    archive_path = export_dir / f"trade_journal_{suffix or 'default'}.zip"
    artifact_paths = [path for path in _artifact_paths(journal).values() if path.exists()]
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in artifact_paths:
            archive.write(path, arcname=path.name)
    if download:
        return FileResponse(
            archive_path,
            media_type="application/zip",
            filename=archive_path.name,
        )
    stat = archive_path.stat()
    return TradeJournalExportMetadata(
        filename=archive_path.name,
        path=str(archive_path),
        size_bytes=stat.st_size,
        artifact_count=len(artifact_paths),
        created_at=datetime.utcfromtimestamp(stat.st_mtime),
        download_url=f"/api/v1/trade-journal/export?output_dir={output_dir}&suffix={suffix}&download=true",
    )


@router.get("/{entry_id}", response_model=TradeJournalEntry)
def get_trade_journal_entry(
    entry_id: str,
    output_dir: str = Query("simulation_output"),
    suffix: str = Query("v2"),
    current_user: User = Depends(get_current_user),
) -> TradeJournalEntry:
    """Return one row from the imported or generated trade journal artifact."""

    del current_user
    entries = _load_trade_entries(_artifact_paths(_journal(output_dir, suffix))["trades"])
    for entry in entries:
        if entry.id == entry_id:
            return entry
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
