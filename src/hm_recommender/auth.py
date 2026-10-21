from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections.abc import Sequence
from pathlib import Path
from threading import Lock


USERS_PATH = Path(os.getenv("HM_USERS_PATH", "data/users/users.json"))


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 100_000).hex()


class UserStore:
    """Username+password login mapped to existing dataset customer IDs.

    One login always maps to exactly one customer ID (persisted on disk),
    so recommendations follow the user across devices and restarts.
    """

    def __init__(self, pool: Sequence[str], path: Path = USERS_PATH) -> None:
        self._pool = pool
        self._path = path
        self._lock = Lock()
        self._users: dict[str, dict] = {}
        self._taken: set[str] = set()
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        for login_id, record in data.items():
            if isinstance(record, dict) and record.get("customer_id"):
                self._users[login_id] = record
                self._taken.add(record["customer_id"])

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._users), encoding="utf-8")
        tmp.replace(self._path)

    def _assign(self, login_id: str) -> str:
        digest = hashlib.sha256(f"user-assignment:{login_id}".encode()).hexdigest()
        start = int(digest[:8], 16) % len(self._pool)
        for step in range(len(self._pool)):
            candidate = self._pool[(start + step) % len(self._pool)]
            if candidate not in self._taken:
                return candidate
        raise RuntimeError("customer pool exhausted")

    def pool_size(self) -> int:
        return len(self._pool)

    def user_count(self) -> int:
        return len(self._users)

    def register(self, login_id: str, password: str) -> tuple[str, bool]:
        """Create account (or return existing). Returns (customer_id, created)."""
        login_id = login_id.strip().lower()
        if not login_id or not password or len(password) < 4:
            raise ValueError("login ID and password (min 4 chars) required")
        with self._lock:
            existing = self._users.get(login_id)
            if existing:
                return existing["customer_id"], False
            customer_id = self._assign(login_id)
            salt = secrets.token_hex(16)
            self._users[login_id] = {
                "customer_id": customer_id,
                "salt": salt,
                "password_hash": _hash_password(password, salt),
            }
            self._taken.add(customer_id)
            self._save()
            return customer_id, True

    def login(self, login_id: str, password: str) -> str | None:
        """Return customer_id on success, None on bad credentials."""
        login_id = login_id.strip().lower()
        with self._lock:
            record = self._users.get(login_id)
        if not record:
            return None
        expected = _hash_password(password, record["salt"])
        if not secrets.compare_digest(expected, record["password_hash"]):
            return None
        return record["customer_id"]
