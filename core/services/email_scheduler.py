"""
Email Scheduler - Manages campaign scheduling and day-of-week restrictions.
Handles:
- Scheduling campaigns for specific dates/times
- Skipping Saturday/Sunday (configurable)
- Time window restrictions (send only between X and Y time)
- Multiple email account rotation
"""
import os
import sys
from datetime import datetime, time
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (
    get_connection, get_due_campaigns, get_email_accounts,
    get_next_available_account, update_account_usage, reset_daily_counts,
    get_campaign_email_sends, update_campaign_status, get_email_send_stats
)
from core.services.email_sending_service import EmailSendingService
from utils.logger import get_logger

logger = get_logger("scheduler")


class EmailScheduler:
    """Manages scheduled email campaigns with day/time restrictions."""

    # Day mapping: 0=Monday, 6=Sunday
    DAYS_OF_WEEK = {
        "0": "Monday",
        "1": "Tuesday",
        "2": "Wednesday",
        "3": "Thursday",
        "4": "Friday",
        "5": "Saturday",
        "6": "Sunday",
    }

    def __init__(self):
        self.email_service = EmailSendingService()

    def is_work_day(self, date: datetime = None) -> bool:
        """Check if today is a work day (not in excluded days)."""
        if date is None:
            date = datetime.now()

        # Get all scheduled campaigns to check excluded days
        # Default: exclude Saturday (5) and Sunday (6)
        excluded_days = [5, 6]  # Saturday, Sunday

        return date.weekday() not in excluded_days

    def is_within_send_window(self, campaign: Dict, check_time: datetime = None) -> bool:
        """Check if current time is within the campaign's send window."""
        if check_time is None:
            check_time = datetime.now()

        start_time_str = campaign.get("send_time_start", "09:00")
        end_time_str = campaign.get("send_time_end", "17:00")

        try:
            start_time = datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.strptime(end_time_str, "%H:%M").time()
            current_time = check_time.time()

            return start_time <= current_time <= end_time
        except Exception as e:
            logger.error("Error parsing send window times: %s", e)
            return True  # If error, allow sending

    def get_campaign_send_days(self, campaign: Dict) -> List[int]:
        """Get list of days (0-6) when campaign can send."""
        send_days_str = campaign.get("send_days", "0,1,2,3,4")
        try:
            return [int(d.strip()) for d in send_days_str.split(",")]
        except Exception:
            return [0, 1, 2, 3, 4]  # Default: Mon-Fri

    def can_send_today(self, campaign: Dict, check_date: datetime = None) -> bool:
        """Check if campaign can send today based on day-of-week restrictions."""
        if check_date is None:
            check_date = datetime.now()

        allowed_days = self.get_campaign_send_days(campaign)
        current_day = check_date.weekday()

        return current_day in allowed_days

    def process_scheduled_campaigns(self) -> Dict:
        """Process all campaigns that are due and should send."""
        logger.info("Checking for due campaigns...")

        due_campaigns = get_due_campaigns()
        if not due_campaigns:
            logger.info("No campaigns due")
            return {"processed": 0, "message": "No campaigns due"}

        results = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }

        for campaign in due_campaigns:
            campaign_id = campaign["id"]
            campaign_name = campaign["name"]

            logger.info("Processing campaign: %s (ID: %d)", campaign_name, campaign_id)

            # Check day-of-week restriction
            if not self.can_send_today(campaign):
                day_name = self.DAYS_OF_WEEK.get(str(datetime.now().weekday()), "Unknown")
                logger.info("Skipping campaign %s - not allowed on %s", campaign_name, day_name)
                results["skipped"] += 1
                results["details"].append({
                    "campaign_id": campaign_id,
                    "status": "skipped",
                    "reason": f"Not allowed on {day_name}"
                })
                continue

            # Check time window
            if not self.is_within_send_window(campaign):
                logger.info("Skipping campaign %s - outside send window", campaign_name)
                results["skipped"] += 1
                results["details"].append({
                    "campaign_id": campaign_id,
                    "status": "skipped",
                    "reason": "Outside send window"
                })
                continue

            # Check if we have email accounts available
            if campaign.get("use_account_rotation"):
                account = get_next_available_account()
                if not account:
                    logger.warning("No available email accounts for campaign %s", campaign_name)
                    results["errors"] += 1
                    results["details"].append({
                        "campaign_id": campaign_id,
                        "status": "error",
                        "reason": "No available email accounts"
                    })
                    continue

            # Process the campaign
            try:
                result = self.send_campaign_with_rotation(campaign)
                results["processed"] += 1
                results["details"].append({
                    "campaign_id": campaign_id,
                    "status": "processed",
                    "result": result
                })
            except Exception as e:
                logger.error("Error processing campaign %s: %s", campaign_name, e)
                results["errors"] += 1
                results["details"].append({
                    "campaign_id": campaign_id,
                    "status": "error",
                    "reason": str(e)
                })

        return results

    def send_campaign_with_rotation(self, campaign: Dict) -> Dict:
        """Send a campaign using email account rotation."""
        campaign_id = campaign["id"]
        use_rotation = campaign.get("use_account_rotation", False)
        emails_per_day = campaign.get("emails_per_day", 20)

        logger.info("Sending campaign %s with rotation=%s, limit=%d/day",
                    campaign["name"], use_rotation, emails_per_day)

        if not use_rotation:
            # Use first available account for non-rotation scheduled sends
            account = get_next_available_account()
            if not account:
                return {"success": False, "message": "No available email accounts for non-rotation send"}
            return self.email_service.send_campaign(
                campaign_id=campaign_id,
                smtp_preset=account["smtp_preset"],
                username=account["username"],
                password=account["password"],
            )

        # Check how many emails already sent today
        today_sends = get_campaign_email_sends(campaign_id, status="sent")
        today_count = len([s for s in today_sends
                          if s.get("sent_at", "").startswith(datetime.now().strftime("%Y-%m-%d"))])

        if today_count >= emails_per_day:
            logger.info("Daily limit reached for campaign %s: %d/%d",
                        campaign["name"], today_count, emails_per_day)
            return {"success": False, "message": "Daily limit reached"}

        remaining_today = emails_per_day - today_count
        logger.info("Can send %d more emails today for campaign %s",
                    remaining_today, campaign["name"])

        # Get available accounts
        accounts = get_email_accounts(active_only=True)
        if not accounts:
            return {"success": False, "message": "No active email accounts"}

        # Calculate emails per account
        emails_per_account = max(1, remaining_today // len(accounts))
        logger.info("Will send ~%d emails per account", emails_per_account)

        total_sent = 0
        total_failed = 0

        for account in accounts:
            if total_sent >= remaining_today:
                break

            # Check account daily limit
            account_today_limit = min(emails_per_account, account["daily_limit"] - account["daily_sent_today"])
            if account_today_limit <= 0:
                logger.info("Account %s reached daily limit", account["email"])
                continue

            # Send using this account
            try:
                result = self.email_service.send_campaign(
                    campaign_id=campaign_id,
                    smtp_preset=account["smtp_preset"],
                    username=account["username"],
                    password=account["password"],
                    max_send=account_today_limit,
                )

                sent = result.get("sent", 0)
                failed = result.get("failed", 0)

                total_sent += sent
                total_failed += failed

                # Update account usage
                for _ in range(sent):
                    update_account_usage(account["id"])

                logger.info("Account %s: sent=%d, failed=%d",
                            account["email"], sent, failed)

            except Exception as e:
                logger.error("Error sending with account %s: %s", account["email"], e)

        return {
            "success": True,
            "message": f"Sent {total_sent} emails using {len(accounts)} accounts",
            "stats": {"sent": total_sent, "failed": total_failed}
        }

    def reset_daily_counts_if_needed(self) -> bool:
        """Reset daily counts if it's a new day."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Get the last reset date
            cursor.execute("SELECT MAX(last_used_date) FROM email_accounts")
            last_reset = cursor.fetchone()[0]

            today = datetime.now().strftime("%Y-%m-%d")

            if last_reset != today:
                from core.database import reset_daily_counts
                reset_daily_counts()
                logger.info("Reset daily counts for new day: %s", today)
                return True
            return False
        except Exception as e:
            logger.error("Error checking reset: %s", e)
            return False
        finally:
            conn.close()

    def schedule_campaign(self, campaign_id: int, scheduled_at: str,
                          send_days: str = None, send_time_start: str = None,
                          send_time_end: str = None, emails_per_day: int = None,
                          use_account_rotation: bool = False) -> bool:
        """Schedule a campaign for later sending."""
        from core.database import update_campaign_schedule

        logger.info("Scheduling campaign %d for %s", campaign_id, scheduled_at)

        result = update_campaign_schedule(
            campaign_id=campaign_id,
            scheduled_at=scheduled_at,
            send_days=send_days,
            send_time_start=send_time_start,
            send_time_end=send_time_end,
            emails_per_day=emails_per_day,
            use_account_rotation=use_account_rotation,
        )

        if result:
            update_campaign_status(campaign_id, "scheduled")
            logger.info("Campaign %d scheduled successfully", campaign_id)
        else:
            logger.error("Failed to schedule campaign %d", campaign_id)

        return result


def run_scheduler():
    """Main entry point for running the scheduler (can be called from cron)."""
    logger.info("=" * 60)
    logger.info("EMAIL SCHEDULER STARTED")
    logger.info("=" * 60)

    scheduler = EmailScheduler()

    # Reset daily counts if needed
    scheduler.reset_daily_counts_if_needed()

    # Process due campaigns
    results = scheduler.process_scheduled_campaigns()

    logger.info("=" * 60)
    logger.info("SCHEDULER COMPLETED")
    logger.info("Processed: %d, Skipped: %d, Errors: %d",
                results["processed"], results["skipped"], results["errors"])
    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    run_scheduler()
