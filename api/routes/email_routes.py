"""
Email Campaign Routes — full business logic for campaigns, sending, scheduling, accounts.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from api.dependencies import create_job, update_job
from api.middleware.auth import verify_api_key
from core.database import (
    create_email_campaign, get_email_campaign, get_all_email_campaigns,
    update_campaign_status, get_campaign_email_sends, get_email_send_stats,
    get_email_accounts, add_email_account, reset_daily_counts,
    update_campaign_schedule, get_connection,
)
from core.services.email_sending_service import EmailSendingService
from core.services.email_scheduler import EmailScheduler, run_scheduler
from core.services.email_testing_service import EmailTestingService

router = APIRouter(prefix="/email", tags=["Email"])
logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────

class CampaignCreateRequest(BaseModel):
    name: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    cv_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    from_name: Optional[str] = None


class SendRequest(BaseModel):
    """Backward-compatible body for POST /email/send"""
    campaign_id: int
    smtp_preset: str = "gmail"
    username: str
    password: str
    max_send: Optional[int] = None
    only_verified: bool = False


class CampaignSendRequest(BaseModel):
    """New RESTful send request — supports saved accounts."""
    smtp_preset: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_saved_account: bool = False
    account_id: Optional[int] = None
    max_send: Optional[int] = None
    only_verified: bool = False
    from_name: Optional[str] = None


class TestEmailRequest(BaseModel):
    to_email: str
    smtp_preset: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_saved_account: bool = False
    account_id: Optional[int] = None


class ScheduleRequest(BaseModel):
    """Backward-compatible body for POST /email/schedule"""
    campaign_id: int
    scheduled_at: Optional[str] = None
    send_days: Optional[str] = None
    send_time_start: Optional[str] = None
    send_time_end: Optional[str] = None
    emails_per_day: Optional[int] = None
    use_account_rotation: Optional[bool] = None


class CampaignScheduleRequest(BaseModel):
    scheduled_at: Optional[str] = None
    send_days: Optional[str] = None
    send_time_start: Optional[str] = None
    send_time_end: Optional[str] = None
    emails_per_day: Optional[int] = None
    use_account_rotation: Optional[bool] = None


class AccountRequest(BaseModel):
    email: str
    smtp_preset: str = "gmail"
    username: str
    password: str
    daily_limit: int = 50


class AccountUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    daily_limit: Optional[int] = None


class VerifyRequest(BaseModel):
    email: Optional[str] = None
    method: str = "dns"
    max_test: Optional[int] = None


# ── Internal helpers ──────────────────────────────────────

def _resolve_smtp(smtp_preset=None, username=None, password=None,
                  use_saved_account=False, account_id=None):
    """Return (preset, user, pwd) — from request or first saved account."""
    if use_saved_account or not username:
        accounts = get_email_accounts(active_only=True)
        if not accounts:
            raise HTTPException(400, "No active email accounts configured. "
                                "Add one in the Accounts tab first.")
        acc = (next((a for a in accounts if a["id"] == account_id), None)
               if account_id else accounts[0])
        if not acc:
            raise HTTPException(400, "Requested account not found")
        return acc["smtp_preset"], acc["username"], acc["password"]
    if not smtp_preset:
        raise HTTPException(400, "Provide smtp_preset+username+password or enable use_saved_account")
    return smtp_preset, username, password


def _campaign_send_stats(campaign_id: int) -> dict:
    """Per-status send counts for one campaign."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT status, COUNT(*) FROM email_sends
            WHERE campaign_id=? GROUP BY status
        """, (campaign_id,))
        return {row[0]: row[1] for row in cursor.fetchall()}
    finally:
        conn.close()


# ── Campaigns CRUD ────────────────────────────────────────

@router.get("/campaigns", dependencies=[Depends(verify_api_key)])
async def list_campaigns():
    campaigns = get_all_email_campaigns()
    for c in campaigns:
        c["send_stats"] = _campaign_send_stats(c["id"])
    return {"campaigns": campaigns}


@router.post("/campaigns", dependencies=[Depends(verify_api_key)])
async def create_campaign(req: CampaignCreateRequest):
    campaign_id = create_email_campaign(
        name=req.name,
        subject=req.subject,
        body_template=req.body_text,
        body_template_html=req.body_html,
        cv_path=req.cv_path,
        cover_letter_path=req.cover_letter_path,
    )
    if not campaign_id:
        raise HTTPException(500, "Failed to create campaign")
    return {"success": True, "campaign_id": campaign_id,
            "message": f"Campaign '{req.name}' created"}


@router.get("/campaigns/{campaign_id}", dependencies=[Depends(verify_api_key)])
async def get_campaign(campaign_id: int):
    c = get_email_campaign(campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    c["send_stats"] = _campaign_send_stats(campaign_id)
    return c


@router.delete("/campaigns/{campaign_id}", dependencies=[Depends(verify_api_key)])
async def delete_campaign(campaign_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM email_sends WHERE campaign_id=?", (campaign_id,))
        cursor.execute("DELETE FROM email_campaigns WHERE id=?", (campaign_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, "Campaign not found")
        return {"success": True, "message": "Campaign deleted"}
    finally:
        conn.close()


# ── Campaign workflow ─────────────────────────────────────

@router.post("/campaigns/{campaign_id}/prepare", dependencies=[Depends(verify_api_key)])
async def prepare_campaign(campaign_id: int):
    """Build email_sends records from enriched profiles (idempotent)."""
    if not get_email_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    prepared = EmailSendingService.prepare_campaign_emails(campaign_id)
    if prepared > 0:
        update_campaign_status(campaign_id, "prepared")
    return {"success": True, "prepared": prepared,
            "message": f"{prepared} email(s) queued"}


@router.get("/campaigns/{campaign_id}/preview", dependencies=[Depends(verify_api_key)])
async def preview_campaign(campaign_id: int):
    """Return a rendered sample email using the first enriched profile."""
    result = EmailSendingService.preview_email(campaign_id)
    if not result["success"]:
        raise HTTPException(400, result["message"])
    return result


@router.get("/campaigns/{campaign_id}/sends", dependencies=[Depends(verify_api_key)])
async def list_sends(campaign_id: int, status: str = "",
                     limit: int = 50, offset: int = 0):
    """Paginated list of individual email sends for a campaign."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        base = "FROM email_sends WHERE campaign_id=?"
        params: list = [campaign_id]
        if status:
            base += " AND status=?"
            params.append(status)
        cursor.execute(f"SELECT COUNT(*) {base}", params)
        total = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT id, email, first_name, last_name, company, subject, "
            f"status, error_message, sent_at FROM email_sends {base.replace('FROM ', 'FROM ')} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        rows = [dict(r) for r in cursor.fetchall()]
        return {"sends": rows, "total": total}
    finally:
        conn.close()


@router.post("/campaigns/{campaign_id}/send", dependencies=[Depends(verify_api_key)])
async def send_campaign_restful(campaign_id: int, req: CampaignSendRequest):
    """Send a campaign. Auto-prepares if no pending emails exist."""
    if not get_email_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    preset, user, pwd = _resolve_smtp(req.smtp_preset, req.username, req.password,
                                       req.use_saved_account, req.account_id)
    result = EmailSendingService.send_campaign(
        campaign_id=campaign_id,
        smtp_preset=preset, username=user, password=pwd,
        max_send=req.max_send,
        only_verified=req.only_verified,
        from_name=req.from_name,
    )
    return result


@router.post("/campaigns/{campaign_id}/test", dependencies=[Depends(verify_api_key)])
async def test_campaign_email(campaign_id: int, req: TestEmailRequest):
    """Send a single test email to `req.to_email` using the campaign's template."""
    if not get_email_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    preset, user, pwd = _resolve_smtp(req.smtp_preset, req.username, req.password,
                                       req.use_saved_account, req.account_id)
    preview = EmailSendingService.preview_email(campaign_id)
    if not preview.get("success"):
        raise HTTPException(400, preview.get("message", "No profile data for preview"))

    from core.email_sender import EmailSender
    try:
        sender = EmailSender.from_preset(preset, user, pwd)
        ok, msg = sender.send_email(
            to_email=req.to_email,
            subject=f"[TEST] {preview['subject']}",
            body_text=preview["body_text"],
            body_html=preview.get("body_html"),
        )
        return {"success": ok, "message": msg}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/campaigns/{campaign_id}/retry", dependencies=[Depends(verify_api_key)])
async def retry_failed_sends(campaign_id: int, req: CampaignSendRequest):
    """Reset failed sends → pending, then re-send."""
    if not get_email_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    preset, user, pwd = _resolve_smtp(req.smtp_preset, req.username, req.password,
                                       req.use_saved_account, req.account_id)
    result = EmailSendingService.retry_failed(
        campaign_id=campaign_id,
        smtp_preset=preset, username=user, password=pwd,
        max_send=req.max_send,
        from_name=req.from_name,
    )
    return result


@router.post("/campaigns/{campaign_id}/schedule", dependencies=[Depends(verify_api_key)])
async def schedule_campaign_restful(campaign_id: int, req: CampaignScheduleRequest):
    if not get_email_campaign(campaign_id):
        raise HTTPException(404, "Campaign not found")
    scheduler = EmailScheduler()
    ok = scheduler.schedule_campaign(
        campaign_id=campaign_id,
        scheduled_at=req.scheduled_at,
        send_days=req.send_days,
        send_time_start=req.send_time_start,
        send_time_end=req.send_time_end,
        emails_per_day=req.emails_per_day,
        use_account_rotation=req.use_account_rotation or False,
    )
    return {"success": ok, "message": "Campaign scheduled" if ok else "Failed to schedule"}


# ── Backward-compatible flat routes ───────────────────────

@router.post("/send", dependencies=[Depends(verify_api_key)])
async def send_campaign_compat(req: SendRequest):
    """Legacy endpoint — kept for CLI and existing integrations."""
    result = EmailSendingService.send_campaign(
        campaign_id=req.campaign_id,
        smtp_preset=req.smtp_preset,
        username=req.username,
        password=req.password,
        max_send=req.max_send,
        only_verified=req.only_verified,
    )
    return result


@router.post("/schedule", dependencies=[Depends(verify_api_key)])
async def schedule_campaign_compat(req: ScheduleRequest):
    """Legacy schedule endpoint."""
    scheduler = EmailScheduler()
    ok = scheduler.schedule_campaign(
        campaign_id=req.campaign_id,
        scheduled_at=req.scheduled_at,
        send_days=req.send_days,
        send_time_start=req.send_time_start,
        send_time_end=req.send_time_end,
        emails_per_day=req.emails_per_day,
        use_account_rotation=req.use_account_rotation or False,
    )
    return {"success": ok, "message": "Scheduled" if ok else "Failed to schedule"}


@router.post("/scheduler/run", dependencies=[Depends(verify_api_key)])
async def run_scheduler_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scheduler)
    return {"success": True, "message": "Scheduler started"}


# ── Email Verification ────────────────────────────────────

@router.post("/verify", dependencies=[Depends(verify_api_key)])
async def verify_emails(req: VerifyRequest, background_tasks: BackgroundTasks):
    """
    Single email: verify synchronously and return result.
    No email provided: verify all unverified profiles in background job.
    """
    if req.email:
        valid, reason = EmailTestingService.test_single_email(req.email, req.method)
        return {"success": True, "email": req.email, "valid": valid, "reason": reason}

    job_id = create_job("verify_emails")

    def task():
        update_job(job_id, status="running", progress=10)
        try:
            result = EmailTestingService.test_profile_emails(
                max_test=req.max_test, method=req.method, only_unverified=True,
            )
            update_job(job_id, status="completed", progress=100, result=result)
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))

    background_tasks.add_task(task)
    return {"job_id": job_id, "status": "pending",
            "message": "Email verification job started"}


# ── SMTP Accounts ─────────────────────────────────────────

@router.get("/accounts", dependencies=[Depends(verify_api_key)])
async def list_accounts(active_only: bool = False):
    return {"accounts": get_email_accounts(active_only=active_only)}


@router.post("/accounts", dependencies=[Depends(verify_api_key)])
async def add_account(req: AccountRequest):
    account_id = add_email_account(
        req.email, req.smtp_preset, req.username, req.password, req.daily_limit,
    )
    if not account_id:
        raise HTTPException(500, "Failed to add account")
    return {"success": True, "account_id": account_id,
            "message": f"Account '{req.email}' added"}


@router.patch("/accounts/{account_id}", dependencies=[Depends(verify_api_key)])
async def update_account(account_id: int, req: AccountUpdateRequest):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        updates, params = [], []
        if req.is_active is not None:
            updates.append("is_active=?"); params.append(1 if req.is_active else 0)
        if req.daily_limit is not None:
            updates.append("daily_limit=?"); params.append(req.daily_limit)
        if not updates:
            raise HTTPException(400, "Nothing to update")
        params.append(account_id)
        cursor.execute(f"UPDATE email_accounts SET {', '.join(updates)} WHERE id=?", params)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, "Account not found")
        return {"success": True, "message": "Account updated"}
    finally:
        conn.close()


@router.delete("/accounts/{account_id}", dependencies=[Depends(verify_api_key)])
async def delete_account(account_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM email_accounts WHERE id=?", (account_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, "Account not found")
        return {"success": True, "message": "Account deleted"}
    finally:
        conn.close()


@router.post("/accounts/reset", dependencies=[Depends(verify_api_key)])
async def reset_account_daily_counts():
    reset_daily_counts()
    return {"success": True, "message": "Daily counts reset"}
