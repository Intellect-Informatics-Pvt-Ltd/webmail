"""PSense Mail — SignaturesFacade service."""
from __future__ import annotations

from app.domain.errors import NotFoundError
from app.domain.models import SignatureDoc
from app.domain.requests import SignatureCreateRequest, SignatureUpdateRequest


class SignaturesFacade:
    async def list_signatures(self, user_id: str) -> list[SignatureDoc]:
        return await SignatureDoc.find(SignatureDoc.user_id == user_id).sort([("created_at", -1)]).to_list()

    async def create_signature(self, user_id: str, payload: SignatureCreateRequest) -> SignatureDoc:
        sig = SignatureDoc(user_id=user_id, name=payload.name, body_html=payload.body_html, is_default=payload.is_default)
        if payload.is_default:
            await self._clear_defaults(user_id)
        await sig.insert()
        return sig

    async def update_signature(self, user_id: str, sig_id: str, payload: SignatureUpdateRequest) -> SignatureDoc:
        sig = await SignatureDoc.find_one(SignatureDoc.id == sig_id, SignatureDoc.user_id == user_id)
        if not sig:
            raise NotFoundError("Signature", sig_id)
        for key, val in payload.model_dump(exclude_none=True).items():
            setattr(sig, key, val)
        if payload.is_default:
            await self._clear_defaults(user_id, exclude_id=sig_id)
        await sig.save()
        return sig

    async def set_default(self, user_id: str, sig_id: str) -> SignatureDoc:
        sig = await SignatureDoc.find_one(SignatureDoc.id == sig_id, SignatureDoc.user_id == user_id)
        if not sig:
            raise NotFoundError("Signature", sig_id)
        await self._clear_defaults(user_id, exclude_id=sig_id)
        sig.is_default = True
        await sig.save()
        return sig

    async def delete_signature(self, user_id: str, sig_id: str) -> None:
        sig = await SignatureDoc.find_one(SignatureDoc.id == sig_id, SignatureDoc.user_id == user_id)
        if not sig:
            raise NotFoundError("Signature", sig_id)
        await sig.delete()

    async def _clear_defaults(self, user_id: str, exclude_id: str | None = None) -> None:
        query = SignatureDoc.find(SignatureDoc.user_id == user_id, SignatureDoc.is_default == True)  # noqa: E712
        docs = await query.to_list()
        for d in docs:
            if d.id != exclude_id:
                d.is_default = False
                await d.save()
