"""PSense Mail — Focused Inbox ML scorer.

Computes a focus score (0.0–1.0) for incoming messages based on
sender engagement signals. Messages with score ≥ 0.5 are classified
as "focused"; others go to "other".

Signals and weights:
  - Previously replied to sender:     0.4
  - Sender is in contacts:            0.3
  - Previously opened sender's msgs:  0.2
  - Direct recipient (not CC/BCC):    0.1
"""
from __future__ import annotations

import logging

from app.domain.models import ContactDoc, MessageDoc

logger = logging.getLogger(__name__)


class FocusedInboxScorer:
    """Computes is_focused for a new message based on engagement signals."""

    async def score(self, message: MessageDoc, user_id: str) -> float:
        """Return a focus score between 0.0 and 1.0."""
        sender_email = message.sender.email.lower() if message.sender else ""
        if not sender_email:
            return 0.5

        score = 0.0

        # Signal 1: user has replied to this sender before (weight 0.4)
        replied = await MessageDoc.find(
            MessageDoc.user_id == user_id,
            MessageDoc.sender.email == user_id,  # messages FROM this user
            {"recipients.email": sender_email},
        ).limit(1).count()
        # Simplified: check if user sent any message TO sender_email
        sent_to_sender = await MessageDoc.get_motor_collection().count_documents(
            {
                "user_id": user_id,
                "sender.email": {"$ne": sender_email},
                "recipients.email": sender_email,
                "is_draft": False,
            },
            limit=1,
        )
        if sent_to_sender > 0:
            score += 0.4

        # Signal 2: sender is in contacts (weight 0.3)
        contact_count = await ContactDoc.find(
            ContactDoc.user_id == user_id,
            ContactDoc.email == sender_email,
            ContactDoc.deleted_at == None,  # noqa: E711
        ).limit(1).count()
        if contact_count > 0:
            score += 0.3

        # Signal 3: user has opened (read) messages from this sender (weight 0.2)
        read_count = await MessageDoc.get_motor_collection().count_documents(
            {
                "user_id": user_id,
                "sender.email": sender_email,
                "is_read": True,
            },
            limit=1,
        )
        if read_count > 0:
            score += 0.2

        # Signal 4: addressed directly (not CC/BCC) (weight 0.1)
        # Check if the user's email is in the 'to' recipients
        from app.domain.models import AccountDoc
        account = await AccountDoc.find_one(
            AccountDoc.owner_user_id == user_id,
            AccountDoc.is_primary == True,  # noqa: E712
        )
        if account:
            user_email = account.address.lower()
            direct = any(
                r.email.lower() == user_email
                for r in (message.recipients or [])
            )
            if direct:
                score += 0.1

        return min(score, 1.0)
