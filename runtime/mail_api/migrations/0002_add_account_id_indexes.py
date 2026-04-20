"""Migration 0002 — Add account_id compound indexes.

Adds the primary query indexes using account_id on messages, threads,
and folders collections.
"""
DESCRIPTION = "Add account_id compound indexes to messages, threads, folders"


async def up() -> None:
    from app.domain.models import MessageDoc, ThreadDoc, FolderDoc

    msg_coll = MessageDoc.get_motor_collection()
    await msg_coll.create_index(
        [("account_id", 1), ("folder_id", 1), ("received_at", -1)],
        name="idx_account_folder_received",
    )
    await msg_coll.create_index(
        [("account_id", 1), ("updated_at", -1)],
        name="idx_account_updated",
    )

    thread_coll = ThreadDoc.get_motor_collection()
    await thread_coll.create_index(
        [("account_id", 1), ("folder_id", 1), ("last_message_at", -1)],
        name="idx_account_folder_last_message",
    )

    folder_coll = FolderDoc.get_motor_collection()
    await folder_coll.create_index(
        [("account_id", 1), ("kind", 1)],
        name="idx_account_kind",
    )


async def down() -> None:
    from app.domain.models import MessageDoc, ThreadDoc, FolderDoc

    await MessageDoc.get_motor_collection().drop_index("idx_account_folder_received")
    await MessageDoc.get_motor_collection().drop_index("idx_account_updated")
    await ThreadDoc.get_motor_collection().drop_index("idx_account_folder_last_message")
    await FolderDoc.get_motor_collection().drop_index("idx_account_kind")
