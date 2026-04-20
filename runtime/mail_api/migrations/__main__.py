"""PSense Mail — Migration runner CLI.

Discovers numbered scripts in this package, tracks applied state in
a ``MigrationDoc`` collection, and runs pending migrations in order.

Usage:
    python -m migrations up          # apply all pending
    python -m migrations down <n>    # roll back last n
    python -m migrations status      # list applied / pending
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import pkgutil
import sys
import time
from pathlib import Path

logger = logging.getLogger("migrations")


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _discover_scripts() -> list[tuple[str, str]]:
    """Return sorted list of (name, module_path) for migration scripts.

    Scripts must be named ``NNNN_<slug>.py`` (4-digit prefix).
    """
    migrations_dir = Path(__file__).parent
    found: list[tuple[str, str]] = []
    for info in pkgutil.iter_modules([str(migrations_dir)]):
        name = info.name
        if name.startswith("_"):
            continue
        # Expect "0001_xxx" pattern
        if len(name) >= 5 and name[:4].isdigit() and name[4] == "_":
            found.append((name, f"migrations.{name}"))
    return sorted(found)


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

async def _init_db() -> None:
    """Bootstrap Mongo + Beanie so MigrationDoc is available."""
    from config.settings import get_settings
    from app.adapters.db.mongo import init_mongo
    settings = get_settings()
    await init_mongo(settings)


async def _applied_set() -> set[str]:
    from app.domain.models import MigrationDoc
    docs = await MigrationDoc.find_all().to_list()
    return {d.id for d in docs}


async def _run_up() -> None:
    await _init_db()
    from app.domain.models import MigrationDoc
    from datetime import datetime, timezone

    scripts = _discover_scripts()
    applied = await _applied_set()

    pending = [(n, p) for n, p in scripts if n not in applied]
    if not pending:
        print("Nothing to migrate — all scripts already applied.")
        return

    for name, mod_path in pending:
        print(f"  ▶ Applying {name} …", end=" ", flush=True)
        mod = importlib.import_module(mod_path)
        t0 = time.monotonic()
        try:
            await mod.up()  # type: ignore[attr-defined]
            duration_ms = (time.monotonic() - t0) * 1000
            doc = MigrationDoc(
                id=name,
                applied_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                description=getattr(mod, "DESCRIPTION", ""),
                rollback_possible=hasattr(mod, "down"),
            )
            await doc.insert()
            print(f"OK ({duration_ms:.0f} ms)")
        except Exception as exc:
            print(f"FAILED — {exc}")
            logger.exception("Migration %s failed", name)
            sys.exit(1)

    print(f"\n✓ Applied {len(pending)} migration(s).")


async def _run_down(count: int) -> None:
    await _init_db()
    from app.domain.models import MigrationDoc

    applied_docs = await MigrationDoc.find_all().sort(
        [("applied_at", -1)]
    ).limit(count).to_list()

    if not applied_docs:
        print("No applied migrations to roll back.")
        return

    scripts_by_name = {n: p for n, p in _discover_scripts()}
    for doc in applied_docs:
        mod_path = scripts_by_name.get(doc.id)
        if not mod_path:
            print(f"  ⚠ Script for {doc.id} not found — skipping")
            continue
        mod = importlib.import_module(mod_path)
        if not hasattr(mod, "down"):
            print(f"  ⚠ {doc.id} has no down() — skipping")
            continue
        print(f"  ◀ Rolling back {doc.id} …", end=" ", flush=True)
        try:
            await mod.down()  # type: ignore[attr-defined]
            await doc.delete()
            print("OK")
        except Exception as exc:
            print(f"FAILED — {exc}")
            logger.exception("Rollback of %s failed", doc.id)
            sys.exit(1)

    print(f"\n✓ Rolled back {len(applied_docs)} migration(s).")


async def _run_status() -> None:
    await _init_db()
    scripts = _discover_scripts()
    applied = await _applied_set()

    print(f"\n{'Name':<45} {'Status':<10}")
    print("─" * 55)
    for name, _ in scripts:
        status = "applied" if name in applied else "pending"
        print(f"  {name:<43} {status:<10}")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    if cmd == "up":
        asyncio.run(_run_up())
    elif cmd == "down":
        count = int(args[1]) if len(args) > 1 else 1
        asyncio.run(_run_down(count))
    elif cmd == "status":
        asyncio.run(_run_status())
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
