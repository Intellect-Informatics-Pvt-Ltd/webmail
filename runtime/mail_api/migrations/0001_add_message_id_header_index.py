"""Migration 0001 — Add message_id_header sparse unique index.

Ensures that RFC 2822 Message-ID lookup and dedup uses an index scan.
"""
DESCRIPTION = "Add sparse unique index on messages.message_id_header"


async def up() -> None:
    from app.domain.models import MessageDoc
    coll = MessageDoc.get_motor_collection()
    await coll.create_index(
        [("message_id_header", 1)],
        unique=True,
        sparse=True,
        name="idx_message_id_header_unique_sparse",
    )


async def down() -> None:
    from app.domain.models import MessageDoc
    coll = MessageDoc.get_motor_collection()
    await coll.drop_index("idx_message_id_header_unique_sparse")
