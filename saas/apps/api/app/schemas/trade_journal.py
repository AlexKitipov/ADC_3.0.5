"""Trade journal artifact API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


JournalArtifactType = Literal[
    "trades",
    "pending_orders",
    "equity_curve",
    "drawdown",
    "rewards",
    "performance",
    "actions",
]


class TradeJournalEntry(BaseModel):
    """One row imported from the CSV/JSON trade journal artifact."""

    id: str
    row_number: int
    source: str = "trades"
    entry_date: str | None = None
    exit_date: str | None = None
    type: str | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    size: float | None = None
    pnl: float | None = None
    exit_reason: str | None = None
    balance_after: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class TradeJournalArtifact(BaseModel):
    """Metadata for a journal-managed artifact on disk."""

    name: str
    artifact_type: JournalArtifactType
    path: str
    exists: bool
    size_bytes: int | None = None
    modified_at: datetime | None = None
    row_count: int | None = None
    content_type: str


class TradeJournalRelationshipSummary(BaseModel):
    """Explain journal boundaries across database rows, broker orders, and files."""

    persisted_trade_rows: str
    broker_order_records: str
    journal_artifacts: str


class TradeJournalSummary(BaseModel):
    """Collection response for journal browsing."""

    entries: list[TradeJournalEntry]
    artifacts: list[TradeJournalArtifact]
    db_trade_count: int
    open_db_trade_count: int
    closed_db_trade_count: int
    relationships: TradeJournalRelationshipSummary


class TradeJournalImportSummary(BaseModel):
    """Result of importing a CSV/JSON artifact into the journal folder."""

    artifact: TradeJournalArtifact
    rows_imported: int | None = None
    replaced_existing: bool
    message: str


class TradeJournalExportMetadata(BaseModel):
    """Metadata describing the generated export archive."""

    filename: str
    path: str
    size_bytes: int
    artifact_count: int
    created_at: datetime
    download_url: str


__all__ = [
    "JournalArtifactType",
    "TradeJournalArtifact",
    "TradeJournalEntry",
    "TradeJournalExportMetadata",
    "TradeJournalImportSummary",
    "TradeJournalRelationshipSummary",
    "TradeJournalSummary",
]
