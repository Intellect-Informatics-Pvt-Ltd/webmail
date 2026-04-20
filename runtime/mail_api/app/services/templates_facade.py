"""PSense Mail — TemplatesFacade service."""
from __future__ import annotations

from app.domain.errors import NotFoundError
from app.domain.models import TemplateDoc
from app.domain.requests import TemplateCreateRequest, TemplateUpdateRequest


class TemplatesFacade:
    async def list_templates(self, user_id: str) -> list[TemplateDoc]:
        return await TemplateDoc.find(TemplateDoc.user_id == user_id).sort([("created_at", -1)]).to_list()

    async def create_template(self, user_id: str, payload: TemplateCreateRequest, tenant_id: str = "default", account_id: str = "") -> TemplateDoc:
        tpl = TemplateDoc(user_id=user_id, tenant_id=tenant_id, account_id=account_id or user_id, name=payload.name, subject=payload.subject, body_html=payload.body_html)
        await tpl.insert()
        return tpl

    async def update_template(self, user_id: str, template_id: str, payload: TemplateUpdateRequest) -> TemplateDoc:
        tpl = await TemplateDoc.find_one(TemplateDoc.id == template_id, TemplateDoc.user_id == user_id)
        if not tpl:
            raise NotFoundError("Template", template_id)
        for key, val in payload.model_dump(exclude_none=True).items():
            setattr(tpl, key, val)
        await tpl.save()
        return tpl

    async def delete_template(self, user_id: str, template_id: str) -> None:
        tpl = await TemplateDoc.find_one(TemplateDoc.id == template_id, TemplateDoc.user_id == user_id)
        if not tpl:
            raise NotFoundError("Template", template_id)
        await tpl.delete()
