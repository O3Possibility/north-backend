import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class BranchInfo:
    branch_id: str
    session_id: str
    parent_branch_id: Optional[str]
    depth: int
    created_at: float


def _db_path() -> str:
    # Keep it local and cheap. This is Phase-1 durability (better than in-memory).
    return os.getenv("NORTH_BRANCH_DB", "./data/north_branch_registry.sqlite")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            branch_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            parent_branch_id TEXT,
            depth INTEGER NOT NULL,
            created_at REAL NOT NULL
        );
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_branches_session ON branches(session_id);")
    return con


def get_branch(branch_id: str) -> Optional[BranchInfo]:
    con = _connect()
    try:
        cur = con.execute(
            "SELECT branch_id, session_id, parent_branch_id, depth, created_at FROM branches WHERE branch_id = ?",
            (branch_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return BranchInfo(branch_id=row[0], session_id=row[1], parent_branch_id=row[2], depth=int(row[3]), created_at=float(row[4]))
    finally:
        con.close()


def create_branch(session_id: Optional[str], parent_branch_id: Optional[str]) -> BranchInfo:
    # If session_id is not provided, generate one (browser should send one, but backend is defensive).
    sid = session_id.strip() if session_id else str(uuid.uuid4())
    pid = parent_branch_id.strip() if parent_branch_id else None
    parent = get_branch(pid) if pid else None
    depth = (parent.depth + 1) if parent else 0
    bid = str(uuid.uuid4())
    created = time.time()

    con = _connect()
    try:
        con.execute(
            "INSERT INTO branches(branch_id, session_id, parent_branch_id, depth, created_at) VALUES (?,?,?,?,?)",
            (bid, sid, pid, depth, created),
        )
        con.commit()
    finally:
        con.close()

    return BranchInfo(branch_id=bid, session_id=sid, parent_branch_id=pid, depth=depth, created_at=created)
