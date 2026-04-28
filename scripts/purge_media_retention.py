from __future__ import annotations

import argparse
import asyncio

from app.integrations.storage_media import get_storage_media_provider
from app.media.services.media_services_media_privacy_service import (
    purge_expired_media_assets,
)
from app.shared.database import async_session_maker


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run media retention purge against expired recording assets."
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help="Override MEDIA_RETENTION_DAYS for this run.",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=200,
        help="Maximum recordings to scan in one run (default: 200).",
    )
    return parser


async def _run(retention_days: int | None, batch_limit: int) -> int:
    provider = get_storage_media_provider()
    async with async_session_maker() as db:
        result = await purge_expired_media_assets(
            db,
            storage_provider=provider,
            retention_days=retention_days,
            batch_limit=batch_limit,
        )

    print(
        "media_retention_purge"
        f" scanned={result.scanned_count}"
        f" purged={result.purged_count}"
        f" skipped={result.skipped_count}"
        f" failed={result.failed_count}"
    )
    if result.purged_recording_ids:
        ids = ",".join(
            str(recording_id) for recording_id in result.purged_recording_ids
        )
        print(f"purged_recording_ids={ids}")
    return 0 if result.failed_count == 0 else 1


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args.retention_days, args.batch_limit))


if __name__ == "__main__":
    raise SystemExit(main())
