"""PSense Mail — PreferencesFacade service."""
from __future__ import annotations

from typing import Any

from app.domain.models import PreferencesDoc, NotificationPrefs, OutOfOfficePrefs


class PreferencesFacade:
    async def get_preferences(self, user_id: str) -> PreferencesDoc:
        prefs = await PreferencesDoc.find_one(PreferencesDoc.id == user_id)
        if not prefs:
            prefs = PreferencesDoc(id=user_id)
            await prefs.insert()
        return prefs

    async def update_preferences(self, user_id: str, patch: dict[str, Any]) -> PreferencesDoc:
        prefs = await self.get_preferences(user_id)

        for key, val in patch.items():
            if val is None:
                continue
            if key == "notifications" and isinstance(val, dict):
                prefs.notifications = NotificationPrefs(**val)
            elif key == "out_of_office" and isinstance(val, dict):
                prefs.out_of_office = OutOfOfficePrefs(**val)
            elif hasattr(prefs, key):
                setattr(prefs, key, val)

        await prefs.save()
        return prefs
