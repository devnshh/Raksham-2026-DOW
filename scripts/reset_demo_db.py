"""
Reset the demo database to a clean, freshly seeded state.

Run this right before every demo: seeded mule fan-in ages out after 24 hours, and a
previous run's payments, appeals and holds change later checks.

    python scripts/reset_demo_db.py            # uses SATARK_DB_PATH or api/satark.db
    python scripts/reset_demo_db.py --db x.db
"""

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.config import DB_PATH  # noqa: E402
from api.db.seed import seed_data  # noqa: E402
from scripts.seed_demo import seed_demo_data  # noqa: E402


def reset(db_path: str) -> None:
    for suffix in ("", "-wal", "-shm"):
        Path(db_path + suffix).unlink(missing_ok=True)
    seed_data(db_path)
    seed_demo_data(db_path)
    print(f"[RESET] Fresh demo database ready at {db_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DB_PATH)
    reset(ap.parse_args().db)
