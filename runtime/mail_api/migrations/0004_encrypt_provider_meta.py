"""Migration 0004 — Encrypt existing plaintext provider_meta.

Re-saves all AccountDoc records so the Beanie before_event hook
encrypts provider_meta into provider_meta_enc.
"""
DESCRIPTION = "Encrypt existing plaintext provider_meta on AccountDoc"


async def up() -> None:
    from app.domain.models import AccountDoc

    docs = await AccountDoc.find_all().to_list()
    count = 0
    for doc in docs:
        if doc.provider_meta and not doc.provider_meta_enc:
            await doc.save()  # triggers encrypt_provider_meta hook
            count += 1
    if count:
        print(f"    accounts: encrypted provider_meta on {count} docs")
