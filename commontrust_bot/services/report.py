"""Report service: create reports, trigger AI review, resolve with admin decision."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from commontrust_bot.pocketbase_client import pb_client
from commontrust_bot.services.ai_review import analyze_report
from commontrust_bot.services.reputation import reputation_service

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, pb=None, reputation=None):
        self.pb = pb or pb_client
        self.reputation = reputation or reputation_service

    async def create_report(
        self,
        *,
        reporter_telegram_id: int,
        reported_telegram_id: int,
        description: str,
        photo_data: list[tuple[str, bytes, str]] | None = None,
        forwarded_messages: list[dict] | None = None,
        deal_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a report record with optional file uploads. Returns the PB record."""
        reporter = await self.reputation.get_or_create_member(reporter_telegram_id)
        reported = await self.reputation.get_or_create_member(reported_telegram_id)

        data: dict[str, Any] = {
            "reporter_id": reporter["id"],
            "reported_id": reported["id"],
            "description": description,
            "status": "pending_ai",
            "forwarded_messages": forwarded_messages or [],
        }
        if deal_id:
            data["deal_id"] = deal_id

        files: list[tuple[str, str, bytes, str]] = []
        for filename, content, mime in (photo_data or []):
            files.append(("evidence_photos", filename, content, mime))

        if files:
            record = await self.pb.create_record_with_files("reports", data, files)
        else:
            record = await self.pb.create_record("reports", data)

        return record

    async def trigger_ai_review(self, report_id: str) -> dict[str, Any]:
        """Run AI analysis and update the report. Returns the updated record."""
        report = await self.pb.get_record("reports", report_id)

        reporter = await self.pb.get_record("members", report["reporter_id"])
        reported = await self.pb.get_record("members", report["reported_id"])

        reporter_stats = await self.reputation.get_member_stats(reporter["id"])
        reported_stats = await self.reputation.get_member_stats(reported["id"])
        reporter_rep = reporter_stats.get("reputation", {})
        reported_rep = reported_stats.get("reputation", {})

        prior_reports = await self.get_reports_against(reported["id"])

        deal_description = None
        if report.get("deal_id"):
            try:
                deal = await self.pb.deal_get(report["deal_id"])
                deal_description = (deal or {}).get("description")
            except Exception:
                pass

        forwarded = report.get("forwarded_messages") or []
        photo_count = len(report.get("evidence_photos") or [])

        result = await analyze_report(
            description=report.get("description", ""),
            reporter_name=reporter.get("display_name") or reporter.get("username") or "Unknown",
            reporter_deals=reporter_rep.get("verified_deals", 0),
            reporter_rating=reporter_rep.get("avg_rating", 0.0),
            reported_name=reported.get("display_name") or reported.get("username") or "Unknown",
            reported_deals=reported_rep.get("verified_deals", 0),
            reported_rating=reported_rep.get("avg_rating", 0.0),
            prior_reports=len(prior_reports),
            deal_description=deal_description,
            forwarded_messages=forwarded,
            photo_count=photo_count,
        )

        update_data: dict[str, Any] = {
            "ai_severity": result.severity,
            "ai_summary": result.summary,
            "ai_recommendation": result.recommendation,
            "ai_reasoning": result.reasoning,
            "ai_model_used": result.model_used,
            "status": "pending_admin",
        }
        return await self.pb.update_record("reports", report_id, update_data)

    async def resolve_report(
        self,
        report_id: str,
        admin_telegram_id: int,
        decision: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Apply admin decision and return updated report."""
        report = await self.pb.get_record("reports", report_id)

        update_data: dict[str, Any] = {
            "admin_decision": decision,
            "admin_id": admin_telegram_id,
            "resolved_at": datetime.now().isoformat(),
        }
        if note:
            update_data["admin_note"] = note

        if decision == "confirm_scammer":
            update_data["status"] = "approved"
            reported_id = report["reported_id"]
            await self.pb.member_set_scammer(reported_id)
            await self.pb.sanction_create(
                member_id=reported_id,
                group_id=None,
                sanction_type="ban",
                reason=f"Confirmed scammer (Report #{report_id[:8]})",
            )
        elif decision == "warn":
            update_data["status"] = "approved"
            reported_id = report["reported_id"]
            await self.pb.sanction_create(
                member_id=reported_id,
                group_id=None,
                sanction_type="warning",
                reason=f"Warning from scam report (Report #{report_id[:8]})",
            )
        elif decision == "dismiss":
            update_data["status"] = "dismissed"

        return await self.pb.update_record("reports", report_id, update_data)

    async def get_reports_against(self, member_id: str) -> list[dict[str, Any]]:
        """Get all reports filed against a member."""
        result = await self.pb.list_records(
            "reports", filter=f'reported_id="{member_id}"', sort="-created_at"
        )
        return result.get("items", [])

    async def get_report(self, report_id: str) -> dict[str, Any]:
        return await self.pb.get_record("reports", report_id)


report_service = ReportService()
