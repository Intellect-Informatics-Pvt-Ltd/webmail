"""PSense Mail — SavedSearchesFacade service."""
from __future__ import annotations

from app.domain.errors import NotFoundError
from app.domain.models import SavedSearchDoc
from app.domain.requests import SavedSearchCreateRequest


class SavedSearchesFacade:
    async def list_saved_searches(self, user_id: str) -> list[SavedSearchDoc]:
        return await SavedSearchDoc.find(SavedSearchDoc.user_id == user_id).sort([("created_at", -1)]).to_list()

    async def create_saved_search(self, user_id: str, payload: SavedSearchCreateRequest) -> SavedSearchDoc:
        ss = SavedSearchDoc(user_id=user_id, name=payload.name, query=payload.query, filters=payload.filters)
        await ss.insert()
        return ss

    async def delete_saved_search(self, user_id: str, search_id: str) -> None:
        ss = await SavedSearchDoc.find_one(SavedSearchDoc.id == search_id, SavedSearchDoc.user_id == user_id)
        if not ss:
            raise NotFoundError("SavedSearch", search_id)
        await ss.delete()
