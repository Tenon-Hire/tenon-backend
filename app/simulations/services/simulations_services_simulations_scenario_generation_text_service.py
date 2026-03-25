from __future__ import annotations

import hashlib


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def seed_from_inputs(role: str, tech_stack: str, template_key: str) -> int:
    seed_source = "||".join(
        (
            normalize_text(role).lower(),
            normalize_text(tech_stack).lower(),
            normalize_text(template_key).lower(),
        )
    )
    digest = hashlib.sha256(seed_source.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


__all__ = ["normalize_text", "seed_from_inputs"]
