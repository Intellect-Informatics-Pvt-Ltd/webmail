"""PSense Mail — RulesFacade service.

Mail rules CRUD and evaluation engine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.domain.enums import MessageAction, RuleActionType, RuleConditionField, RuleConditionOp
from app.domain.errors import NotFoundError
from app.domain.models import MessageDoc, RuleDoc, RuleCondition, RuleAction
from app.domain.requests import RuleCreateRequest, RuleUpdateRequest

logger = logging.getLogger(__name__)


class RulesFacade:
    """Mail rules CRUD and evaluation."""

    async def list_rules(self, user_id: str) -> list[RuleDoc]:
        return await RuleDoc.find(RuleDoc.user_id == user_id).sort([("created_at", -1)]).to_list()

    async def create_rule(self, user_id: str, payload: RuleCreateRequest) -> RuleDoc:
        rule = RuleDoc(
            user_id=user_id, name=payload.name, enabled=payload.enabled,
            conditions=payload.conditions, actions=payload.actions,
        )
        await rule.insert()
        logger.info("Created rule %s for user %s", rule.id, user_id)
        return rule

    async def update_rule(self, user_id: str, rule_id: str, payload: RuleUpdateRequest) -> RuleDoc:
        rule = await RuleDoc.find_one(RuleDoc.id == rule_id, RuleDoc.user_id == user_id)
        if not rule:
            raise NotFoundError("Rule", rule_id)

        patch_data = payload.model_dump(exclude_none=True)
        for key, val in patch_data.items():
            setattr(rule, key, val)
        await rule.save()
        return rule

    async def delete_rule(self, user_id: str, rule_id: str) -> None:
        rule = await RuleDoc.find_one(RuleDoc.id == rule_id, RuleDoc.user_id == user_id)
        if not rule:
            raise NotFoundError("Rule", rule_id)
        await rule.delete()

    async def evaluate_rules(self, user_id: str, message: MessageDoc) -> list[str]:
        """Evaluate all enabled rules against a message.

        Returns list of actions applied.
        """
        rules = await RuleDoc.find(RuleDoc.user_id == user_id, RuleDoc.enabled == True).to_list()  # noqa: E712
        applied: list[str] = []

        for rule in rules:
            if self._matches_conditions(rule.conditions, message):
                for action in rule.actions:
                    self._apply_action(action, message)
                    applied.append(f"{rule.name}: {action.type.value}")

        if applied:
            message.updated_at = datetime.now(timezone.utc)
            await message.save()
            logger.info("Applied %d rule actions to message %s", len(applied), message.id)

        return applied

    def _matches_conditions(self, conditions: list[RuleCondition], message: MessageDoc) -> bool:
        """Check if ALL conditions match (AND logic)."""
        for cond in conditions:
            if not self._matches_single(cond, message):
                return False
        return True

    def _matches_single(self, cond: RuleCondition, message: MessageDoc) -> bool:
        """Evaluate a single condition."""
        if cond.field == RuleConditionField.SENDER:
            target = f"{message.sender.name} {message.sender.email}".lower()
            value = str(cond.value).lower()
            if cond.op == RuleConditionOp.CONTAINS:
                return value in target
            elif cond.op == RuleConditionOp.EQUALS:
                return message.sender.email.lower() == value
        elif cond.field == RuleConditionField.SUBJECT:
            target = message.subject.lower()
            value = str(cond.value).lower()
            if cond.op == RuleConditionOp.CONTAINS:
                return value in target
            elif cond.op == RuleConditionOp.EQUALS:
                return target == value
        elif cond.field == RuleConditionField.HAS_ATTACHMENT:
            return message.has_attachments == bool(cond.value)
        elif cond.field == RuleConditionField.OLDER_THAN_DAYS:
            if message.received_at:
                days = (datetime.now(timezone.utc) - message.received_at).days
                return days > int(cond.value)
        return False

    def _apply_action(self, action: RuleAction, message: MessageDoc) -> None:
        """Apply a single rule action to a message (in-place mutation)."""
        if action.type == RuleActionType.MOVE and action.folder_id:
            message.folder_id = action.folder_id
        elif action.type == RuleActionType.CATEGORIZE and action.category_id:
            if action.category_id not in message.categories:
                message.categories.append(action.category_id)
        elif action.type == RuleActionType.MARK_IMPORTANT:
            from app.domain.enums import Importance
            message.importance = Importance.HIGH
        elif action.type == RuleActionType.ARCHIVE:
            message.folder_id = "archive"
        elif action.type == RuleActionType.DELETE:
            message.folder_id = "deleted"
