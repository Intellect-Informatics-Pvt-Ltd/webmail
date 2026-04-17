"""PSense Mail — Demo data seeder.

Ports the mock data from webmail_ui/src/data/ into MongoDB documents.
Called during startup when database.memory.seed_on_start = true,
or via POST /api/v1/admin/seed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.domain.enums import FolderKind, Importance
from app.domain.models import (
    CategoryDoc,
    DraftDoc,
    FavoritesDoc,
    FolderDoc,
    MailAttachmentMeta,
    MailRecipient,
    MessageDoc,
    PreferencesDoc,
    RuleAction,
    RuleCondition,
    RuleDoc,
    SignatureDoc,
    TemplateDoc,
    ThreadDoc,
    UserDoc,
)

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

_now = datetime.now(timezone.utc)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def _ago(delta: timedelta) -> datetime:
    return _now - delta


def _future(delta: timedelta) -> datetime:
    return _now + delta


ME = MailRecipient(email="avery@psense.ai", name="Avery Chen")


def _person(name: str, email: str) -> MailRecipient:
    return MailRecipient(name=name, email=email)


# ── Seeder ───────────────────────────────────────────────────────────────────


async def seed_demo_data(user_id: str) -> dict[str, int]:
    """Seed demo data for a user. Returns counts of created documents."""

    # Check if already seeded
    existing = await MessageDoc.find(MessageDoc.user_id == user_id).count()
    if existing > 0:
        logger.info("User %s already has %d messages — skipping seed", user_id, existing)
        return {"messages": existing, "skipped": True}

    # ── User ─────────────────────────────────────────────────────────────
    user = UserDoc(id=user_id, email="avery@psense.ai", display_name="Avery Chen")
    await user.insert()

    # ── System Folders ───────────────────────────────────────────────────
    system_folders = [
        ("inbox", "Inbox", FolderKind.INBOX),
        ("focused", "Focused", FolderKind.FOCUSED),
        ("other", "Other", FolderKind.OTHER),
        ("drafts", "Drafts", FolderKind.DRAFTS),
        ("sent", "Sent", FolderKind.SENT),
        ("archive", "Archive", FolderKind.ARCHIVE),
        ("snoozed", "Snoozed", FolderKind.SNOOZED),
        ("flagged", "Flagged", FolderKind.FLAGGED),
        ("deleted", "Deleted", FolderKind.DELETED),
        ("junk", "Junk", FolderKind.JUNK),
    ]
    for fid, fname, fkind in system_folders:
        await FolderDoc(id=fid, user_id=user_id, name=fname, kind=fkind, system=True).insert()

    # ── Custom Folders ───────────────────────────────────────────────────
    custom_folders = [
        ("f-clients", "Clients"),
        ("f-finance", "Finance & Billing"),
        ("f-hiring", "Hiring 2026"),
        ("f-projects", "Projects"),
        ("f-receipts", "Receipts"),
    ]
    for fid, fname in custom_folders:
        await FolderDoc(id=fid, user_id=user_id, name=fname, kind=FolderKind.CUSTOM).insert()

    # ── Favorites ────────────────────────────────────────────────────────
    await FavoritesDoc(id=user_id, folder_ids=["inbox", "flagged", "f-clients"]).insert()

    # ── Categories ───────────────────────────────────────────────────────
    categories = [
        ("sales", "Sales", "violet"),
        ("customer", "Customer", "sky"),
        ("internal", "Internal", "emerald"),
        ("newsletter", "Newsletter", "amber"),
        ("vendor", "Vendor", "rose"),
        ("follow-up", "Follow-up", "fuchsia"),
    ]
    for cid, cname, ccolor in categories:
        await CategoryDoc(id=cid, user_id=user_id, name=cname, color=ccolor).insert()

    # ── Messages ─────────────────────────────────────────────────────────
    messages = [
        MessageDoc(
            id="m1", user_id=user_id, thread_id="t1", folder_id="inbox",
            subject="Q1 board deck — final review tonight",
            preview="Avery, can you take one more pass at slides 12–18 before we lock the deck for tomorrow?",
            body_html="<div><p>Hi Avery,</p><p>Can you take one more pass at slides 12–18?</p></div>",
            sender=_person("Priya Raman", "priya@psense.ai"), recipients=[ME],
            cc=[_person("Maya Sullivan", "maya@psense.ai")],
            received_at=_ago(timedelta(minutes=35)),
            is_flagged=True, is_pinned=True, has_attachments=True,
            importance=Importance.HIGH, categories=["internal"],
            is_focused=True, has_mentions=True, trust_verified=True,
            attachments=[
                MailAttachmentMeta(id="a1", name="PSense-Q1-Board-Deck-v9.pptx", size=4_812_000, mime="pptx"),
                MailAttachmentMeta(id="a2", name="Renewal-Cohorts.xlsx", size=312_000, mime="xlsx"),
            ],
        ),
        MessageDoc(
            id="m2", user_id=user_id, thread_id="t2", folder_id="inbox",
            subject="Re: Pricing approval for Northwind expansion",
            preview="Approved. Please proceed with the proposal at the discussed terms.",
            body_html="<div><p>Approved. Please proceed at the discussed terms.</p></div>",
            sender=_person("Daniel Okafor", "daniel@psense.ai"), recipients=[ME],
            received_at=_ago(2 * HOUR),
            importance=Importance.HIGH, categories=["sales", "internal"],
            is_focused=True, trust_verified=True,
        ),
        MessageDoc(
            id="m3", user_id=user_id, thread_id="t3", folder_id="inbox",
            subject="Northwind — security review questionnaire",
            preview="Hi Avery, attached is our standard vendor security questionnaire.",
            body_html="<div><p>Attached is our standard vendor security questionnaire.</p></div>",
            sender=_person("Helena Voss", "helena.voss@northwind.com"), recipients=[ME],
            cc=[_person("Daniel Okafor", "daniel@psense.ai")],
            received_at=_ago(4 * HOUR), has_attachments=True,
            categories=["customer", "sales"], is_focused=True,
            attachments=[MailAttachmentMeta(id="a3", name="Northwind-Vendor-Security-2026.pdf", size=1_240_000, mime="pdf")],
        ),
        MessageDoc(
            id="m4", user_id=user_id, thread_id="t4", folder_id="inbox",
            subject="Coffee Thursday?",
            preview="Hey — in town this week. Any chance for a quick coffee Thursday afternoon?",
            body_html="<div><p>Hey — in town this week. Coffee Thursday?</p></div>",
            sender=_person("Jules Marchetti", "jules@marchetti.studio"), recipients=[ME],
            received_at=_ago(6 * HOUR), is_read=True,
        ),
        MessageDoc(
            id="m5", user_id=user_id, thread_id="t5", folder_id="inbox",
            subject="Your weekly digest — 14 highlights",
            preview="The biggest stories in B2B SaaS this week.",
            body_html="<div><h3>Top stories</h3></div>",
            sender=_person("SaaS Weekly", "digest@saasweekly.io"), recipients=[ME],
            received_at=_ago(8 * HOUR), is_read=True,
            importance=Importance.LOW, categories=["newsletter"],
        ),
        MessageDoc(
            id="m6", user_id=user_id, thread_id="t6", folder_id="inbox",
            subject="Action required: 2026 enrollment closes Friday",
            preview="Reminder: open enrollment for benefits closes this Friday at 6pm PT.",
            body_html="<div><p>Open enrollment closes Friday.</p></div>",
            sender=_person("People Ops", "peopleops@psense.ai"), recipients=[ME],
            received_at=_ago(28 * HOUR), is_flagged=True,
            importance=Importance.HIGH, categories=["internal"],
            is_focused=True, trust_verified=True,
        ),
        MessageDoc(
            id="m7", user_id=user_id, thread_id="t7", folder_id="inbox",
            subject="Invoice INV-2026-0481 paid",
            preview="Your payment of $2,400.00 to Linear has been processed.",
            body_html="<div><p>Payment processed.</p></div>",
            sender=_person("Linear Billing", "billing@linear.app"), recipients=[ME],
            received_at=_ago(30 * HOUR), is_read=True, has_attachments=True,
            importance=Importance.LOW, categories=["vendor"],
            attachments=[MailAttachmentMeta(id="a4", name="INV-2026-0481.pdf", size=84_000, mime="pdf")],
        ),
        MessageDoc(
            id="m8", user_id=user_id, thread_id="t8", folder_id="inbox",
            subject="Re: Onboarding — week 2 sync",
            preview="Loved the demo session yesterday. A few questions our team raised.",
            body_html="<div><p>Loved the demo session.</p></div>",
            sender=_person("Marcus Webb", "marcus@globalretail.io"), recipients=[ME],
            cc=[_person("Riya Patel", "riya@globalretail.io")],
            received_at=_ago(32 * HOUR), categories=["customer"],
            is_focused=True, has_mentions=True,
        ),
        # Sent
        MessageDoc(
            id="ms1", user_id=user_id, thread_id="ts1", folder_id="sent",
            subject="Follow-up: Q2 roadmap themes",
            preview="Hi all — circling back on the three themes we discussed Monday.",
            body_html="<div><p>Circling back on themes.</p></div>",
            sender=ME, recipients=[_person("Priya Raman", "priya@psense.ai")],
            received_at=_ago(7 * HOUR), is_read=True, categories=["internal"],
        ),
        # Archive
        MessageDoc(
            id="ma1", user_id=user_id, thread_id="ta1", folder_id="archive",
            subject="Lease renewal options — 555 Howard",
            preview="Three options summarized for your review.",
            body_html="<div><p>Three options.</p></div>",
            sender=_person("Sasha Lin", "sasha@cushwake.com"), recipients=[ME],
            received_at=_ago(20 * DAY), is_read=True, has_attachments=True, categories=["vendor"],
        ),
        # Snoozed
        MessageDoc(
            id="msn1", user_id=user_id, thread_id="tsn1", folder_id="snoozed",
            subject="Re: Compliance audit — evidence requested",
            preview="Snoozed until Monday.",
            body_html="<div><p>Compliance audit evidence.</p></div>",
            sender=_person("Lena Park", "lena@auditfirm.com"), recipients=[ME],
            received_at=_ago(2 * DAY), is_read=True,
            snoozed_until=_future(3 * DAY), categories=["vendor"],
        ),
        # Deleted
        MessageDoc(
            id="mx1", user_id=user_id, thread_id="tx1", folder_id="deleted",
            subject="Last chance: 30% off Pro",
            preview="Don't miss out.",
            body_html="<div><p>Promo.</p></div>",
            sender=_person("ToolCo", "promo@toolco.com"), recipients=[ME],
            received_at=_ago(6 * DAY), is_read=True, importance=Importance.LOW, categories=["newsletter"],
        ),
        # Junk
        MessageDoc(
            id="mj1", user_id=user_id, thread_id="tj1", folder_id="junk",
            subject="Re: invoice attached",
            preview="Suspicious sender — quarantined.",
            body_html="<div><p>Suspicious.</p></div>",
            sender=_person("Unknown", "noreply@suspicious-domain.xyz"), recipients=[ME],
            received_at=_ago(12 * HOUR), has_attachments=True, importance=Importance.LOW,
        ),
        # Custom folder
        MessageDoc(
            id="mc1", user_id=user_id, thread_id="tc1", folder_id="f-clients",
            subject="Acme renewal — green light",
            preview="Confirmed renewal, $220k ACV, 2-year term.",
            body_html="<div><p>Confirmed renewal.</p></div>",
            sender=_person("Karim Aziz", "karim@acme.io"), recipients=[ME],
            received_at=_ago(36 * HOUR), is_read=True, is_flagged=True,
            importance=Importance.HIGH, categories=["customer", "sales"],
        ),
    ]

    for msg in messages:
        await msg.insert()

    # ── Threads ──────────────────────────────────────────────────────────
    # Build threads from messages
    thread_map: dict[str, list[MessageDoc]] = {}
    for msg in messages:
        thread_map.setdefault(msg.thread_id, []).append(msg)

    for tid, msgs in thread_map.items():
        last = max(msgs, key=lambda m: m.received_at or _now)
        await ThreadDoc(
            id=tid, user_id=user_id, subject=last.subject,
            folder_id=last.folder_id,
            participant_emails=list({m.sender.email for m in msgs}),
            message_ids=[m.id for m in msgs],
            last_message_at=last.received_at,
            unread_count=sum(1 for m in msgs if not m.is_read),
            total_count=len(msgs),
            has_attachments=any(m.has_attachments for m in msgs),
            is_flagged=any(m.is_flagged for m in msgs),
        ).insert()

    # ── Rules ────────────────────────────────────────────────────────────
    rules = [
        RuleDoc(id="r1", user_id=user_id, name="Newsletters → Newsletter folder", enabled=True,
                conditions=[RuleCondition(field="sender", op="contains", value="newsletter")],
                actions=[RuleAction(type="categorize", category_id="newsletter")]),
        RuleDoc(id="r2", user_id=user_id, name="Invoices → Finance & Billing", enabled=True,
                conditions=[RuleCondition(field="subject", op="contains", value="invoice")],
                actions=[RuleAction(type="move", folder_id="f-finance")]),
        RuleDoc(id="r3", user_id=user_id, name="Important from CEO", enabled=True,
                conditions=[RuleCondition(field="sender", op="contains", value="priya@psense.ai")],
                actions=[RuleAction(type="markImportant")]),
    ]
    for rule in rules:
        await rule.insert()

    # ── Templates ────────────────────────────────────────────────────────
    templates = [
        TemplateDoc(id="tpl1", user_id=user_id, name="Intro — discovery call",
                    subject="Quick intro — exploring fit",
                    body_html="<p>Hi {{name}},</p><p>Thanks for the time on our call.</p>"),
        TemplateDoc(id="tpl2", user_id=user_id, name="Follow-up — proposal sent",
                    subject="Following up on the proposal",
                    body_html="<p>Hi {{name}},</p><p>Following up on the proposal sent last week.</p>"),
    ]
    for tpl in templates:
        await tpl.insert()

    # ── Signatures ───────────────────────────────────────────────────────
    sigs = [
        SignatureDoc(id="sig1", user_id=user_id, name="Default", is_default=True,
                     body_html="<p>—<br/><strong>Avery Chen</strong><br/>Head of Operations · PSense.ai</p>"),
        SignatureDoc(id="sig2", user_id=user_id, name="Short",
                     body_html="<p>— Avery</p>"),
    ]
    for sig in sigs:
        await sig.insert()

    # ── Preferences ──────────────────────────────────────────────────────
    await PreferencesDoc(id=user_id).insert()

    counts = {
        "user": 1,
        "folders": len(system_folders) + len(custom_folders),
        "categories": len(categories),
        "messages": len(messages),
        "threads": len(thread_map),
        "rules": len(rules),
        "templates": len(templates),
        "signatures": len(sigs),
    }
    logger.info("Seeded demo data for user %s: %s", user_id, counts)
    return counts
