"""PSense Mail — CategoriesFacade service."""
from __future__ import annotations

from app.domain.errors import NotFoundError
from app.domain.models import CategoryDoc
from app.domain.requests import CategoryCreateRequest, CategoryUpdateRequest


class CategoriesFacade:
    async def list_categories(self, user_id: str, tenant_id: str = "default") -> list[CategoryDoc]:
        return await CategoryDoc.find(CategoryDoc.user_id == user_id).to_list()

    async def create_category(self, user_id: str, payload: CategoryCreateRequest, tenant_id: str = "default", account_id: str = "") -> CategoryDoc:
        cat = CategoryDoc(user_id=user_id, tenant_id=tenant_id, account_id=account_id or user_id, name=payload.name, color=payload.color)
        await cat.insert()
        return cat

    async def update_category(self, user_id: str, cat_id: str, payload: CategoryUpdateRequest) -> CategoryDoc:
        cat = await CategoryDoc.find_one(CategoryDoc.id == cat_id, CategoryDoc.user_id == user_id)
        if not cat:
            raise NotFoundError("Category", cat_id)
        for key, val in payload.model_dump(exclude_none=True).items():
            setattr(cat, key, val)
        await cat.save()
        return cat

    async def delete_category(self, user_id: str, cat_id: str) -> None:
        cat = await CategoryDoc.find_one(CategoryDoc.id == cat_id, CategoryDoc.user_id == user_id)
        if not cat:
            raise NotFoundError("Category", cat_id)
        # Remove category from all messages
        from app.domain.models import MessageDoc
        messages = await MessageDoc.find(
            MessageDoc.user_id == user_id, {"categories": cat_id},
        ).to_list()
        for msg in messages:
            msg.categories = [c for c in msg.categories if c != cat_id]
            await msg.save()
        await cat.delete()
