import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func

from app.core.config import settings
from app.engines.copilot_tools import CopilotTools
from app.engines.tool_registry import tool_registry
from app.engines.rag_engine import rag_engine
from app.engines.intent_router import intent_router, RouteType, RouterDecision
from app.engines.conversation_memory import conversation_memory, ConversationMessage, SessionContextState
from app.engines.entity_extractor import entity_extractor, ExtractedEntities
from app.engines.groq_client import GroqClient

logger = logging.getLogger("aura.copilot.engine")

class CopilotEngine:
    """
    Enterprise-Grade Context-Augmented Orchestrator for AURA AI Copilot.
    Features:
      - 5-Way Intelligent Intent Router (Knowledge, Live Data, Action, Mixed, Unknown).
      - Dynamic Zero-Trust Tool Registry with BM25/Cosine Semantic Pruning.
      - Role-Scoped Multi-Tenant RAG Knowledge Engine.
      - Redis/In-Memory Multi-Tenant Session Isolation (`conv:{h_id}:{u_id}:{s_id}`).
      - Human-in-the-Loop Confirmation Workflows for High-Risk Actions.
      - Two-Tier Execution: Multi-Turn Gemini Tool Calling + High-Precision Deterministic Fallback.
    """

    @staticmethod
    def get_tool_declarations(role: str) -> List[Dict[str, Any]]:
        """Returns all authorized tool declarations based on user role using tool_registry."""
        return tool_registry.prune_tools_for_user(query="", user_role=role, top_k=50)

    @staticmethod
    async def get_hospital_directory_summary(hospital_id: Optional[str], db: AsyncSession) -> str:
        """Builds a rich context string of all active doctors, timings, fees, and departments."""
        if not hospital_id:
            return "Hospital Directory: General Platform Mode."

        from app.database.models.appointment import Doctor, Department, DoctorSchedule
        from sqlalchemy import select

        stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
            Doctor.hospital_id == hospital_id,
            Doctor.is_active == True
        )
        doc_rows = (await db.execute(stmt)).all()
        if not doc_rows:
            return "No active doctors currently listed for this hospital."

        day_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
        lines = ["ACTIVE HOSPITAL DOCTORS & SCHEDULE DIRECTORY:"]

        for doctor, department in doc_rows:
            sched_stmt = select(DoctorSchedule).where(
                DoctorSchedule.doctor_id == doctor.id
            ).order_by(DoctorSchedule.day_of_week.asc())
            schedules = (await db.execute(sched_stmt)).scalars().all()
            
            timing_strs = []
            for s in schedules:
                day_name = day_map.get(s.day_of_week, f"Day {s.day_of_week}")
                st = s.start_time.strftime("%I:%M %p") if s.start_time else "N/A"
                et = s.end_time.strftime("%I:%M %p") if s.end_time else "N/A"
                timing_strs.append(f"{day_name} ({st} - {et})")

            timings_text = ", ".join(timing_strs) if timing_strs else "Standard OPD Hours"
            fee = doctor.opd_fees or 500
            lines.append(f"- Dr. {doctor.first_name} {doctor.last_name} | Department: {department.name} | OPD Fee: ₹{fee} | Schedule/Timings: {timings_text}")

        return "\n".join(lines)

    @classmethod
    async def _resolve_target_hospital(cls, text: str, db: Optional[AsyncSession]) -> Optional[Dict[str, Any]]:
        """
        Fuzzy resolves target hospital entity from user query text.
        Handles variations, slugs, IDs, and typos like 'rao hospita' -> 'Rao Hospital', 'balaji' -> 'Balaji Hospital', 'apollo' -> 'apolo'.
        """
        if not text or not db:
            return None
        try:
            from app.database.models.appointment import Hospital
            from sqlalchemy import select
            stmt = select(Hospital).where(Hospital.is_active == True)
            hospitals = (await db.execute(stmt)).scalars().all()
            if not hospitals:
                return None

            t_lower = text.lower()
            clean_t = re.sub(r'[^\w\s]', ' ', t_lower)
            tokens = set(clean_t.split())

            for h in hospitals:
                h_name = (h.name or "").strip()
                h_slug = (h.slug or "").strip()
                h_id = h.id.strip()

                # Direct matches on ID or slug
                if h_id.lower() in t_lower or (h_slug and h_slug.lower() in t_lower):
                    return {"id": h.id, "name": h_name, "slug": h_slug}

                # Core words in hospital name (ignore generic words like hospital/clinic)
                h_words = [w for w in re.sub(r'[^\w\s]', ' ', h_name.lower()).split() if w not in ["hospital", "clinic", "healthcare", "hms", "medical", "center", "centre"]]
                for hw in h_words:
                    if len(hw) >= 3 and hw in tokens:
                        return {"id": h.id, "name": h_name, "slug": h_slug}
                    if len(hw) >= 3 and hw in t_lower:
                        return {"id": h.id, "name": h_name, "slug": h_slug}
                    # Fuzzy match for common typos (e.g. apolo vs apollo)
                    if hw == "apolo" and ("apollo" in t_lower or "apolo" in t_lower):
                        return {"id": h.id, "name": h_name, "slug": h_slug}
        except Exception as e:
            logger.debug(f"Error resolving target hospital: {e}")
        return None

    @classmethod
    def _format_markdown_fallback(cls, tool_name: str, result: Dict[str, Any]) -> str:
        """Converts raw tool output to clean Markdown tables and lists."""
        if not result:
            return "No records found matching your query."
            
        if "error" in result:
            return f"⚠️ {result['error']}"

        if tool_name == "search_platform_hospital":
            hospitals = result.get("hospitals", [])
            if not hospitals:
                return f"🔍 **Platform Hospital Lookup:**\n\nNo tenant hospitals found matching your query."
            lines = [f"### 🏥 Platform Hospital Lookup ({len(hospitals)} found)\n"]
            for h in hospitals:
                lines.append(f"#### **{h.get('name', 'Hospital')}**")
                lines.append(f"* **Contact Phone:** 📱 **{h.get('phone', 'N/A')}**")
                lines.append(f"* **Email:** ✉️ {h.get('email', 'N/A')}")
                lines.append(f"* **Location:** 📍 {h.get('city', 'N/A')} — {h.get('address', 'N/A')}")
                lines.append(f"* **Subscription Plan:** 💳 **{h.get('subscription_plan', 'STARTER')}** (Status: `{h.get('plan_status', 'ACTIVE')}`)")
                lines.append(f"* **Expires:** ⏳ {h.get('plan_expires_at', 'N/A')}")
                lines.append(f"* **Active Doctors:** 🩺 **{h.get('active_doctors', 0)} doctors**")
                lines.append(f"* **AI Telephony:** {'✅ Enabled' if h.get('ai_voice_enabled') else '❌ Disabled'}")
                lines.append(f"* **Public Portal:** `/portal/{h.get('slug', '')}`\n")
            return "\n".join(lines)

        if tool_name == "get_missed_and_cancelled_list":
            records = result.get("records", [])
            if not records:
                return f"No missed or cancelled appointments found for {result.get('date', 'the selected date')}."
            lines = [f"### 📋 Missed & Cancelled Appointments ({result.get('date', 'Today')})", f"**Total:** {len(records)}\n"]
            for r in records:
                lines.append(f"* **{r.get('patient_name', 'Patient')}** ({r.get('phone', 'N/A')})")
                lines.append(f"  * **Doctor:** {r.get('doctor', 'N/A')} | **Time:** {r.get('time', 'N/A')}")
                lines.append(f"  * **Status:** {r.get('status', 'N/A')} | **Reason/Problem:** {r.get('problem_reason', 'General')}\n")
            return "\n".join(lines)

        elif tool_name == "search_clinical_emr_records":
            records = result.get("records", [])
            if not records:
                return result.get("message", "No clinical or prescription records found.")
            lines = [f"### 🩺 Clinical & Prescription Records Found ({len(records)})\n"]
            for r in records:
                lines.append(f"* **Patient:** {r.get('patient_name')} ({r.get('mobile')}) | **Visit Date:** {r.get('visit_date')}")
                lines.append(f"  * **Doctor:** {r.get('doctor_name')} ({r.get('department')})")
                lines.append(f"  * **Chief Complaint:** {r.get('chief_complaint')}")
                lines.append(f"  * **Prescription:** {r.get('prescription')}\n")
            return "\n".join(lines)

        elif tool_name == "get_comprehensive_doctor_analytics":
            matrix = result.get("doctor_matrix", [])
            if not matrix:
                return "No doctor analytics data available."
            lines = ["### 📊 Comprehensive Doctor Performance Matrix\n", "| Doctor | Department | Working Days | Booked | Completed | Missed/Cancelled | Revenue |", "|---|---|---|---|---|---|---|"]
            for d in matrix:
                lines.append(f"| {d.get('doctor_name')} | {d.get('department')} | {d.get('weekly_working_days')} days/wk | {d.get('total_appointments')} | {d.get('completed')} | {d.get('cancelled_or_missed')} | {d.get('total_revenue_generated')} |")
            return "\n".join(lines)

        elif tool_name == "get_all_doctors_performance":
            ranking = result.get("ranking") or result.get("performance_roster", [])
            period = result.get("period", "All Time")
            tot_b = result.get("total_hospital_bookings", 0)
            tot_rev = result.get("total_hospital_revenue_collected_formatted") or result.get("total_hospital_revenue_formatted", "₹0")
            if not ranking:
                return f"No doctor booking performance records found for {period}."
            lines = [
                f"### 📊 Doctor-Wise Booking & Performance Report ({period})\n",
                f"* **Total Hospital Bookings:** **{tot_b}**",
                f"* **Total Revenue Generated:** **{tot_rev}**\n",
                "| Doctor | Department | Total Booked | Completed | Cancelled | Revenue Collected |",
                "|---|---|---|---|---|---|"
            ]
            for d in ranking:
                lines.append(f"| **{d.get('doctor_name')}** | {d.get('department')} | {d.get('total_bookings')} | {d.get('completed')} | {d.get('cancelled')} | {d.get('revenue_collected_formatted')} |")
            return "\n".join(lines)

        elif tool_name == "get_doctor_metrics":
            d_name = result.get("doctor_name", "Doctor")
            dept = result.get("department", "OPD")
            period = result.get("period", "All Time")
            fee_str = f"₹{result.get('opd_fee', 0):,}"
            tot_b = result.get("total_appointments") if result.get("total_appointments") is not None else result.get("total_bookings", 0)
            comp = result.get("completed_consultations") if result.get("completed_consultations") is not None else result.get("completed", 0)
            canc = result.get("cancelled_appointments") if result.get("cancelled_appointments") is not None else result.get("cancelled", 0)
            miss = result.get("missed_appointments") if result.get("missed_appointments") is not None else result.get("missed", 0)
            canc_miss = canc + miss if (canc or miss) else 0
            rev_fmt = result.get("total_revenue_collected_formatted") or result.get("revenue_collected_formatted", "₹0")
            dues_fmt = result.get("pending_dues_formatted", "₹0")
            lines = [
                f"### 🩺 Performance & Revenue: {d_name} ({period})\n",
                f"* **Department:** {dept}",
                f"* **OPD Consultation Fee:** {fee_str}",
                f"* **Total Appointments Booked:** **{tot_b}**",
                f"* **Completed Consultations:** **{comp}**",
                f"* **Cancelled / Missed:** **{canc_miss}** ({canc} cancelled, {miss} missed)",
                f"* **Total Revenue Collected:** **{rev_fmt}**",
                f"* **Pending Dues:** **{dues_fmt}**"
            ]
            return "\n".join(lines)

        elif tool_name == "get_revenue_and_dues":
            return (
                f"### 💰 Financial & OPD Revenue Summary ({result.get('period', 'Today')})\n\n"
                f"* **Total Appointments Booked:** {result.get('total_appointments', 0)}\n"
                f"* **Total Revenue Collected (Paid):** **{result.get('total_collected_formatted', '₹0')}** ({result.get('paid_transactions', 0)} transactions)\n"
                f"* **Pending Collection / Dues:** **{result.get('pending_dues_formatted', '₹0')}** ({result.get('pending_collection_count', 0)} pending)"
            )

        elif tool_name == "get_queue_statistics":
            breakdown = result.get("doctor_breakdown", [])
            doc_lines = "\n".join([f"  * **{b.get('doctor')}** ({b.get('department')}): {b.get('booked_count')} bookings" for b in breakdown])
            return (
                f"### 👥 Live OPD Queue Summary ({result.get('date', 'Today')})\n\n"
                f"* **Total Booked:** {result.get('total_appointments', 0)}\n"
                f"* **Completed Visits:** {result.get('completed', 0)}\n"
                f"* **Currently Waiting:** {result.get('waiting', 0)}\n"
                f"* **Missed / Cancelled:** {result.get('missed_or_cancelled', 0)}\n\n"
                f"**Per-Doctor Breakdown:**\n{doc_lines if doc_lines else '  * No doctor bookings for today.'}"
            )

        elif tool_name == "get_appointment_status_summary":
            period = result.get("period", "Today")
            doc_name = result.get("doctor_name")
            total = result.get("total_appointments", 0)
            completed = result.get("completed", 0)
            cancelled = result.get("cancelled", 0)
            missed = result.get("missed", 0)
            confirmed = result.get("confirmed_or_scheduled", 0)
            records = result.get("records", [])
            breakdown = result.get("doctor_breakdown", [])

            header = f"### 📊 Appointment Status Summary — {doc_name} ({period})" if doc_name else f"### 📊 Appointment Status Summary ({period})"
            lines = [header, ""]

            lines.append(f"* **Total Appointments:** **{total}**")
            lines.append(f"* **Completed Visits:** **{completed}**")
            lines.append(f"* **Confirmed / Scheduled (In Queue):** **{confirmed}**")
            lines.append(f"* **Cancelled Bookings:** **{cancelled}**")
            lines.append(f"* **Missed / No-Show:** **{missed}**")
            lines.append("")

            if records:
                lines.append(f"**Detailed Records ({len(records)}):**")
                for r in records:
                    lines.append(f"* **{r.get('patient_name')}** ({r.get('phone')}) — **{r.get('status')}**")
                    lines.append(f"  * Doctor: {r.get('doctor')} | Time: {r.get('datetime')}")
                    if r.get("reason"):
                        lines.append(f"  * Reason: {r.get('reason')}")
                lines.append("")
            elif cancelled == 0 and missed == 0 and total > 0:
                lines.append(f"✅ *All {total} scheduled appointments are active with 0 cancellations or no-shows.*")
            elif total == 0:
                lines.append(f"ℹ️ *No appointment records found for this period.*")

            if breakdown and len(breakdown) > 1:
                lines.append("\n**Doctor-Wise Status Breakdown:**")
                lines.append("| Doctor | Total | Completed | Cancelled | Missed |")
                lines.append("|---|---|---|---|---|")
                for db_item in breakdown:
                    lines.append(f"| {db_item.get('doctor_name')} | {db_item.get('total')} | {db_item.get('completed')} | {db_item.get('cancelled')} | {db_item.get('missed')} |")

            return "\n".join(lines)

        elif tool_name == "get_platform_control_tower_overview":
            fleet = result.get("hospitals_fleet", [])
            total_hosp = result.get("total_active_hospitals", len(fleet))
            total_rev = result.get("total_platform_saas_revenue_formatted", "₹0")
            total_calls = result.get("total_platform_voice_calls", 0)
            lines = [
                f"### 🌐 Platform Control Tower Overview\n",
                f"* **Total Active Hospitals:** {total_hosp}",
                f"* **Total Platform SaaS Revenue:** **{total_rev}**",
                f"* **Total AI Voice Calls Processed:** **{total_calls}**",
                f"* **Top Revenue Hospital:** **{result.get('top_revenue_hospital', 'N/A')}** ({result.get('top_revenue_amount', '₹0')})\n",
                "| Hospital | Plan | SaaS Revenue | Doctors | Bookings | Days Left | Status |",
                "|---|---|---|---|---|---|---|"
            ]
            for h in fleet:
                lines.append(f"| {h.get('hospital_name')} | {h.get('subscription_plan')} | {h.get('saas_revenue_formatted', '₹0')} | {h.get('active_doctors')} | {h.get('total_appointments')} | {h.get('days_remaining')} | {h.get('status')} |")
            return "\n".join(lines)

        elif tool_name == "book_walkin_appointment":
            if result.get("success"):
                return f"✅ **Appointment Confirmed!**\n\n* **Doctor:** {result.get('doctor_name')} ({result.get('department')})\n* **Date & Time:** {result.get('date')} at {result.get('time')}\n* **OPD Fee:** ₹{result.get('opd_fee')}\n* **Booking ID:** `{result.get('appointment_id')}`"
            return f"❌ {result.get('error', 'Booking failed.')}"

        elif tool_name == "get_available_doctors_for_day":
            docs = result.get("available_doctors", [])
            on_leave = result.get("on_leave_doctors", [])
            off_duty = result.get("off_duty_doctors", [])
            day_label = f"{result.get('day_name', 'Today')} ({result.get('date')})"

            lines = [f"### 🩺 Doctors Availability & Duty Roster ({day_label})\n"]
            lines.append(f"* **Total Available & On-Duty:** **{len(docs)}**")
            lines.append(f"* **On Approved Leave:** **{len(on_leave)}**")
            lines.append(f"* **Off-Duty (Weekly Off):** **{len(off_duty)}**\n")

            if docs:
                lines.append("**On-Duty Doctors:**")
                for d in docs:
                    lines.append(f"* **{d.get('doctor_name')}** ({d.get('department')}) — Timings: {d.get('timings')} | OPD Fee: ₹{d.get('opd_fee')}")
            else:
                lines.append("* No doctors scheduled on-duty for this date.")

            if on_leave:
                lines.append("\n**Doctors on Leave:**")
                for l in on_leave:
                    lines.append(f"* 🌴 {l}")
            else:
                lines.append("\n* ✅ **No doctors currently on leave.**")

            if off_duty:
                lines.append("\n**Off-Duty Doctors:**")
                for o in off_duty:
                    lines.append(f"* 🚫 {o}")

            return "\n".join(lines)

        elif tool_name == "get_single_doctor_slots":
            slots = result.get("available_slots", [])
            s_str = ", ".join(slots) if slots else "No open slots available."
            return f"### ⏰ Open Slots for {result.get('doctor_name')} ({result.get('department')})\n* **Date:** {result.get('date')}\n* **OPD Fee:** ₹{result.get('opd_fee')}\n* **Available Slots:** {s_str}"

        elif tool_name == "search_patient_appointment_status":
            patients = result.get("patients", [])
            if not patients:
                return f"No appointment records found matching '{result.get('query', '')}'."
            lines = [f"### 🔍 Patient Appointments Found ({len(patients)})\n", "| Patient Name | Mobile | Doctor | Dept | Date & Time | Status | Payment |", "|---|---|---|---|---|---|---|"]
            for p in patients:
                lines.append(f"| {p.get('patient_name', 'N/A')} | {p.get('mobile', 'N/A')} | {p.get('doctor_name', 'N/A')} | {p.get('department', 'N/A')} | {p.get('appointment_time', 'N/A')} | {p.get('status', 'N/A')} | {p.get('payment_status', 'N/A')} |")
            return "\n".join(lines)

        elif tool_name == "get_doctor_live_queue":
            queue = result.get("waiting_queue") or result.get("patients") or []
            doc = result.get("doctor_name", "Doctor")
            w_count = result.get("waiting_count", len(queue))
            lines = [
                f"### 🚪 Live Waiting Room Queue for {doc} ({result.get('date', 'Today')})\n",
                f"* **Currently Waiting Patients:** **{w_count}**\n",
                "| Token # | Patient Name | Time Slot | Status | Chief Complaint | Payment |",
                "|---|---|---|---|---|---|"
            ]
            if not queue:
                lines.append("| - | *No patients currently waiting in queue* | - | - | - | - |")
            else:
                for q in queue:
                    t_num = q.get("token") or q.get("token_number") or "-"
                    p_name = q.get("patient_name") or "Patient"
                    t_slot = q.get("time_slot") or q.get("time") or "N/A"
                    st = q.get("status") or "WAITING"
                    cc = q.get("chief_complaint") or "General Consultation"
                    pay = q.get("payment_status") or q.get("payment") or "PENDING"
                    lines.append(f"| #{t_num} | {p_name} | {t_slot} | {st} | {cc} | {pay} |")
            return "\n".join(lines)

        elif tool_name in ["check_doctor_availability", "get_doctor_schedule"]:
            doc_name = result.get("doctor_name", "Doctor")
            dept = result.get("department", "OPD")
            status = result.get("status", "ON_DUTY")
            timings = result.get("timings") or result.get("schedule_timings") or "Standard OPD Hours"
            fee = result.get("opd_fee") or result.get("opd_fees", 500)
            target_d = result.get("date", "Tomorrow")

            if result.get("is_on_leave") or status == "ON_LEAVE":
                return (
                    f"### 🩺 Doctor Schedule & Availability ({target_d})\n\n"
                    f"🔴 **{doc_name}** ({dept}) is **ON LEAVE** on {target_d}.\n\n"
                    f"* **Reason:** {result.get('leave_reason', 'Approved Leave')}\n"
                    f"* **Period:** {result.get('leave_period', target_d)}"
                )
            elif result.get("is_off_duty") or status == "WEEKLY_OFF":
                return (
                    f"### 🩺 Doctor Schedule & Availability ({target_d})\n\n"
                    f"🟡 **{doc_name}** ({dept}) has **WEEKLY OFF** on {target_d}.\n\n"
                    f"* **Note:** {result.get('note', 'Doctor has no scheduled OPD shifts on this day.')}"
                )
            else:
                return (
                    f"### 🩺 Doctor Schedule & Availability ({target_d})\n\n"
                    f"🟢 **{doc_name}** ({dept}) is **ON DUTY & AVAILABLE** on {target_d}.\n\n"
                    f"* **Shift / OPD Timings:** **{timings}**\n"
                    f"* **Consultation Fee:** ₹{fee}\n"
                    f"* **Status:** {status}"
                )

        elif tool_name == "check_doctor_leave_status":
            doc_name = result.get("doctor_name", "Doctor")
            dept = result.get("department", "OPD")
            status = result.get("status", "ACTIVE")
            timings = result.get("timings", "Standard OPD Hours")
            fee = result.get("opd_fees", 500)

            if status == "ON_LEAVE" or result.get("is_on_leave"):
                return (
                    f"🔴 **Haan, {doc_name} aaj Chutti (Leave) par hain.**\n\n"
                    f"* **Department:** {dept}\n"
                    f"* **Leave Reason:** {result.get('leave_reason', 'Approved Leave')}\n"
                    f"* **Leave Period:** {result.get('leave_period', 'Today')}\n"
                    f"* **Note:** Aap {dept} department ke anya doctors ke saath appointment book kar sakte hain."
                )
            elif status == "WEEKLY_OFF" or result.get("is_off_duty"):
                return (
                    f"🟡 **{doc_name} ki aaj chutti nahi hai, lekin aaj unka Weekly Off hai.**\n\n"
                    f"* **Department:** {dept}\n"
                    f"* **OPD Fee:** ₹{fee}\n"
                    f"* **Note:** {result.get('note', 'Doctor has no scheduled shift today.')}"
                )
            else:
                return (
                    f"🟢 **Nahi, {doc_name} aaj chutti par nahi hain.**\n\n"
                    f"* **Status:** On Duty & Available\n"
                    f"* **Department:** {dept}\n"
                    f"* **OPD Timings:** **{timings}**\n"
                    f"* **Consultation Fee:** ₹{fee}"
                )

        elif tool_name == "get_daily_cash_register":
            return (
                f"### 💵 Daily Front Desk Cash Register ({result.get('date', 'Today')})\n\n"
                f"* **Total Appointments:** {result.get('total_appointments', 0)}\n"
                f"* **Cash Collected:** **{result.get('cash_collected', '₹0')}**\n"
                f"* **Online / UPI Collected:** **{result.get('online_collected', '₹0')}**\n"
                f"* **Total Revenue Collected:** **{result.get('total_collected', '₹0')}** ({result.get('paid_transactions', 0)} paid)\n"
                f"* **Pending Dues:** **{result.get('pending_dues', '₹0')}** ({result.get('pending_transactions', 0)} pending)"
            )

        elif tool_name == "get_doctor_daily_earnings":
            return (
                f"### 💼 Doctor Daily OPD Earnings ({result.get('date', 'Today')})\n\n"
                f"* **Doctor:** {result.get('doctor_name')}\n"
                f"* **Total Booked Patients:** {result.get('total_booked', 0)}\n"
                f"* **Completed Consultations:** {result.get('completed_consultations', 0)}\n"
                f"* **Consultation Fee:** ₹{result.get('opd_fee', 0)}\n"
                f"* **Total Earnings Today:** **{result.get('total_earned', '₹0')}**"
            )

        elif tool_name == "get_platform_error_telemetry":
            errors = result.get("errors", [])
            if not errors:
                return "✅ **No errors or exceptions reported in the platform telemetry.** All services operating normally."
            lines = [f"### ⚠️ Platform Error Telemetry Stream ({len(errors)} events)\n", "| Service | Severity | Error Code | Message | Time |", "|---|---|---|---|---|"]
            for e in errors:
                lines.append(f"| {e.get('service')} | {e.get('severity')} | {e.get('error_code')} | {e.get('error_message')} | {e.get('occurred_at')} |")
            return "\n".join(lines)

        elif tool_name == "get_platform_audit_trail":
            audits = result.get("audits", [])
            if not audits:
                return "No audit log entries recorded."
            lines = [f"### 🛡️ Platform Security & Audit Trail ({len(audits)} events)\n", "| Actor | Role | Action | Resource | Status | Time |", "|---|---|---|---|---|---|"]
            for a in audits:
                lines.append(f"| {a.get('actor')} | {a.get('role')} | {a.get('action')} | {a.get('resource')} | {a.get('status')} | {a.get('timestamp')} |")
            return "\n".join(lines)

        elif tool_name == "mark_appointment_payment_paid":
            if result.get("success"):
                return f"✅ **Payment Received!**\n\n* **Patient:** {result.get('patient_name')}\n* **Doctor:** {result.get('doctor_name')}\n* **Amount Paid:** {result.get('amount_paid')}\n* **Payment Method:** {result.get('payment_method')}\n* **Status:** PAID"
            return f"❌ {result.get('error', 'Payment recording failed.')}"

        elif tool_name == "update_patient_queue_status":
            if result.get("success"):
                return f"✅ **Queue Status Updated!**\n\n* **Patient:** {result.get('patient_name')} (Token #{result.get('token_number')})\n* **Doctor:** {result.get('doctor_name')}\n* **Status:** `{result.get('old_status')}` ➔ **`{result.get('new_status')}`**"
            return f"❌ {result.get('error', 'Queue update failed.')}"

        elif tool_name == "get_patient_profile_history":
            visits = result.get("visit_history", [])
            lines = [
                f"### 👤 Patient Medical Profile: {result.get('patient_name')}\n",
                f"* **Mobile:** {result.get('phone')} | **Gender:** {result.get('gender')} | **Blood Group:** {result.get('blood_group')}",
                f"* **Emergency Contact:** {result.get('emergency_contact')}\n",
                f"**Visit History ({len(visits)} visits):**\n",
                "| Date | Doctor | Department | Status | Payment |",
                "|---|---|---|---|---|"
            ]
            for v in visits:
                lines.append(f"| {v.get('date')} | {v.get('doctor')} | {v.get('department')} | {v.get('status')} | {v.get('payment_status')} |")
            return "\n".join(lines)

        elif tool_name == "apply_doctor_leave":
            if result.get("success"):
                return f"✅ **Leave Application Submitted!**\n\n* **Doctor:** {result.get('doctor_name')}\n* **Period:** {result.get('period')}\n* **Reason:** {result.get('reason')}\n* **Status:** ⏳ PENDING (Awaiting Hospital Admin Approval)"
            return f"❌ {result.get('error', 'Leave application failed.')}"

        elif tool_name == "get_patient_prescription_receipt":
            return (
                f"### 💊 Patient Prescription & Receipt\n\n"
                f"* **Patient:** {result.get('patient_name')}\n"
                f"* **Doctor:** {result.get('doctor_name')} ({result.get('department')})\n"
                f"* **Visit Date:** {result.get('visit_date')}\n"
                f"* **Diagnosis:** {result.get('diagnosis')}\n"
                f"* **Prescription:** {result.get('prescription')}\n"
                f"* **Follow-up Date:** {result.get('follow_up_date')}\n"
                f"* **Amount Paid:** {result.get('amount_paid')} ({result.get('payment_status')})"
            )

        elif tool_name == "record_patient_intake_vitals":
            if result.get("success"):
                v = result.get("vitals", {})
                return f"✅ **Patient Intake & Vitals Recorded!**\n\n* **Patient:** {result.get('patient_name')}\n* **Chief Complaint:** {result.get('chief_complaint')}\n* **BP:** {v.get('bp')} | **Pulse:** {v.get('pulse')} | **Temp:** {v.get('temp')} | **SpO2:** {v.get('spo2')} | **Weight:** {v.get('weight')}"
            return f"❌ {result.get('error', 'Intake recording failed.')}"

        elif tool_name == "search_doctors":
            docs = result.get("doctors", [])
            total = result.get("total_count", len(docs))
            dept = result.get("department")
            hdr = f"Found {total} doctor(s)" + (f" in **{dept}**" if dept else "")
            if not docs:
                return f"🔍 No active doctors found" + (f" for department '{dept}'." if dept else ".")
            lines = [f"### 🩺 {hdr}\n", "| Doctor Name | Department | Specializations | Consultation Fee | Schedule |", "|---|---|---|---|---|"]
            for d in docs:
                timings = d.get("schedule_timings") or d.get("available_days")
                if isinstance(timings, list):
                    timings = ", ".join([str(x) for x in timings])
                elif not timings:
                    timings = "Standard OPD"
                specs = d.get("specializations", [])
                spec_str = ", ".join([str(s) for s in specs]) if isinstance(specs, list) else str(specs or "")
                lines.append(f"| **{d.get('name') or d.get('doctor_name')}** | {d.get('department')} | {spec_str} | ₹{d.get('opd_fee', 500)} | {timings} |")
            return "\n".join(lines)

        elif tool_name == "get_doctor_details":
            if "error" in result:
                return f"⚠️ {result['error']}"
            schedules = result.get("schedules", []) or result.get("shifts", [])
            shifts_list = []
            for s in schedules:
                if isinstance(s, dict):
                    if "start_time" in s:
                        shifts_list.append(f"  * **{s.get('day')}:** {s.get('start_time')} - {s.get('end_time')}")
                    else:
                        shifts_list.append(f"  * **{s.get('day')}:** {s.get('timings')}")
                elif isinstance(s, str):
                    shifts_list.append(f"  * {s}")
            shifts = "\n".join(shifts_list) if shifts_list else "  * Standard OPD Timings"
            specs = result.get("specializations", [])
            spec_str = ", ".join([str(x) for x in specs]) if isinstance(specs, list) else str(specs or "General")
            return (
                f"### 🩺 Doctor Profile: {result.get('doctor_name') or result.get('name')}\n\n"
                f"* **Department:** {result.get('department')} ({spec_str})\n"
                f"* **Consultation Fee:** ₹{result.get('opd_fee', 500)}\n"
                f"* **License / Registration:** {result.get('license_number') or 'Active'}\n\n"
                f"**Weekly OPD Schedule:**\n{shifts}"
            )

        elif tool_name == "check_doctor_availability":
            doc = result.get("doctor_name", "Doctor")
            dt = result.get("date", "Today")
            if not result.get("is_available"):
                return f"🔴 **{doc} is not available on {dt}.**\n\n* **Reason:** {result.get('message', 'Off-duty or on leave')}\n* **Next Available Date:** {result.get('next_available_date', 'Please check upcoming schedule')}"
            slots = result.get("slots", [])
            s_preview = ", ".join(slots[:6]) + ("..." if len(slots) > 6 else "") if slots else "Slots open"
            return (
                f"🟢 **{doc} is Available on {dt}!**\n\n"
                f"* **Working Hours:** {result.get('start_time', '09:00')} - {result.get('end_time', '17:00')}\n"
                f"* **Available Slots ({result.get('available_slot_count', len(slots))} total):** {s_preview}\n"
                f"* **Consultation Fee:** ₹{result.get('opd_fee', 500)}"
            )

        elif tool_name == "get_available_slots":
            slots = result.get("available_slots", [])
            doc = result.get("doctor_name", "Doctor")
            dt = result.get("date", "Today")
            if not slots:
                return f"⏰ **No open slots available for {doc} on {dt}.**"
            s_list = "\n".join([f"- `{s}`" for s in slots])
            return (
                f"### ⏰ Open Time Slots for {doc}\n"
                f"* **Date:** {dt}\n"
                f"* **Total Available Slots:** **{len(slots)}**\n"
                f"* **OPD Fee:** ₹{result.get('opd_fee', 500)}\n\n"
                f"**Available Times:**\n{s_list}"
            )

        elif tool_name == "book_appointment":
            if result.get("success"):
                return (
                    f"✅ **Appointment Confirmed Successfully!**\n\n"
                    f"* **Appointment ID:** `{result.get('appointment_id')}`\n"
                    f"* **Doctor:** {result.get('doctor_name')} ({result.get('department')})\n"
                    f"* **Patient:** {result.get('patient_name')} ({result.get('patient_phone')})\n"
                    f"* **Date & Time:** **{result.get('date')}** at **{result.get('time_slot')}**\n"
                    f"* **Token Number:** **#{result.get('token_number')}**\n"
                    f"* **OPD Fee:** ₹{result.get('opd_fee')}\n"
                    f"* **Status:** `{result.get('status', 'CONFIRMED')}`"
                )
            return f"❌ **Booking Failed:** {result.get('error', 'Unknown error occurred.')}"

        elif tool_name == "get_my_appointments":
            appts = result.get("appointments", [])
            if not appts:
                return "📋 No appointment records found for your account."
            lines = [f"### 📋 Your Appointments ({len(appts)})\n", "| ID | Doctor | Department | Date & Time | Status | Payment |", "|---|---|---|---|---|---|"]
            for a in appts:
                lines.append(f"| `{a.get('appointment_id')}` | **{a.get('doctor_name')}** | {a.get('department')} | {a.get('date')} {a.get('time_slot')} | `{a.get('status')}` | {a.get('payment_status')} |")
            return "\n".join(lines)

        elif tool_name == "cancel_appointment":
            if result.get("requires_confirmation"):
                return (
                    f"⚠️ **Confirmation Required to Cancel Appointment**\n\n"
                    f"* **Appointment ID:** `{result.get('appointment_id')}`\n"
                    f"* **Doctor:** {result.get('doctor_name')}\n"
                    f"* **Date & Time:** {result.get('date')} at {result.get('time_slot')}\n\n"
                    f"{result.get('prompt', 'To confirm cancellation, please reply with:')}\n"
                    f"`{result.get('confirm_command')}`"
                )
            if result.get("success"):
                return f"✅ **Appointment `{result.get('appointment_id')}` has been successfully cancelled.**\n\n* **Doctor:** {result.get('doctor_name')}\n* **Date & Time:** {result.get('date')} {result.get('time_slot')}"
            return f"❌ **Cancellation Failed:** {result.get('error')}"

        elif tool_name == "reschedule_appointment":
            if result.get("success"):
                return (
                    f"✅ **Appointment Rescheduled Successfully!**\n\n"
                    f"* **Appointment ID:** `{result.get('appointment_id')}`\n"
                    f"* **Doctor:** {result.get('doctor_name')}\n"
                    f"* **Previous Slot:** {result.get('old_date')} {result.get('old_time_slot')}\n"
                    f"* **New Slot:** **{result.get('new_date')}** at **{result.get('new_time_slot')}**\n"
                    f"* **Status:** `{result.get('status')}`"
                )
            return f"❌ **Rescheduling Failed:** {result.get('error')}"

        elif tool_name == "get_patient_details":
            if "error" in result:
                return f"⚠️ {result['error']}"
            p = result.get("patient", {})
            history = result.get("recent_history", [])
            lines = [
                f"### 👤 Patient Details: {p.get('name')}\n",
                f"* **Patient ID:** `{p.get('patient_id')}` | **UHID:** `{p.get('uhid')}`",
                f"* **Phone:** {p.get('phone')} | **Gender:** {p.get('gender')} | **Blood Group:** {p.get('blood_group', 'N/A')}",
                f"* **Emergency Contact:** {p.get('emergency_contact', 'N/A')}\n"
            ]
            if history:
                lines.append(f"**Recent Appointments ({len(history)}):**\n")
                lines.append("| Date | Doctor | Department | Status |")
                lines.append("|---|---|---|---|")
                for h in history:
                    lines.append(f"| {h.get('date')} {h.get('time')} | {h.get('doctor')} | {h.get('department')} | {h.get('status')} |")
            return "\n".join(lines)

        elif tool_name == "get_hospital_information":
            if "error" in result:
                return f"⚠️ {result['error']}"
            depts = ", ".join(result.get("departments", []))
            return (
                f"### 🏥 {result.get('hospital_name')}\n\n"
                f"* **Address:** {result.get('address')}\n"
                f"* **Contact Phone:** {result.get('phone')}\n"
                f"* **Email:** {result.get('email')}\n"
                f"* **OPD Working Hours:** {result.get('working_hours', {}).get('opd', '09:00 AM - 08:00 PM')}\n"
                f"* **Emergency Services:** 🚨 {result.get('emergency_services', '24/7 Available')}\n"
                f"* **Active Doctors:** {result.get('total_doctors', 0)}\n"
                f"* **Departments:** {depts}\n"
                f"* **Facilities:** {', '.join(result.get('facilities', []))}"
            )

        elif tool_name == "get_hospital_subscription_info":
            if "error" in result:
                return f"⚠️ {result['error']}"
            return (
                f"### 🛡️ Hospital Subscription & SaaS License Status\n\n"
                f"* **Hospital:** {result.get('hospital_name')}\n"
                f"* **Subscription Plan:** **{result.get('subscription_plan')}**\n"
                f"* **Plan Status:** `{result.get('plan_status')}`\n"
                f"* **Expiration Date:** **{result.get('expires_at')}**\n"
                f"* **Days Remaining:** **{result.get('days_remaining')} days**\n"
                f"* **Active Doctors:** {result.get('active_doctors')} / {result.get('max_doctor_quota')} quota\n"
                f"* **AI Voice Copilot:** {'✅ Enabled' if result.get('ai_voice_enabled') else '❌ Disabled'}"
            )

        elif tool_name == "get_my_prescriptions":
            rx_list = result.get("prescriptions", [])
            if not rx_list:
                return "📋 No prescription records found for your account."
            lines = [f"### 💊 Your Prescription & Consultation Records ({len(rx_list)})\n"]
            for r in rx_list:
                lines.append(f"* **Visit Date:** {r.get('visit_date')} | **Doctor:** {r.get('doctor_name')} ({r.get('department')})")
                lines.append(f"  * **Diagnosis/Notes:** {r.get('clinical_notes')}")
                lines.append(f"  * **Prescription:** `{r.get('prescription')}`")
                lines.append(f"  * **Follow-up:** {r.get('follow_up_date')}\n")
            return "\n".join(lines)

        elif tool_name == "get_my_live_token_position":
            if not result.get("has_active_appointment"):
                return f"ℹ️ {result.get('message', 'No active appointment for today.')}"
            return (
                f"### 🚪 Live Token & Queue Position (Today)\n\n"
                f"* **Patient:** {result.get('patient_name')}\n"
                f"* **Doctor:** {result.get('doctor_name')} ({result.get('department')})\n"
                f"* **Scheduled Time:** {result.get('appointment_time')}\n"
                f"* **Status:** `{result.get('status')}`\n"
                f"* **Patients Ahead in Queue:** **{result.get('patients_ahead', 0)} patient(s)**\n"
                f"* **Estimated Wait Time:** **~{result.get('estimated_wait_minutes', 0)} minutes**"
            )

        elif tool_name == "get_insurance_tpa_panels":
            panels = result.get("insurance_panels", [])
            if not panels:
                return "ℹ️ No insurance or TPA network panels currently listed."
            lines = [f"### 🛡️ Accepted Cashless Insurance & TPA Panels ({len(panels)})\n", "| Provider Name | Plan Name | Network Status |", "|---|---|---|"]
            for p in panels:
                lines.append(f"| **{p.get('provider_name')}** | {p.get('plan_name')} | `{p.get('network_status')}` |")
            return "\n".join(lines)

        elif tool_name == "save_consultation_notes":
            if result.get("success"):
                return (
                    f"✅ **Consultation Notes & Prescription Saved!**\n\n"
                    f"* **Appointment ID:** `{result.get('appointment_id')}`\n"
                    f"* **Patient:** {result.get('patient_name')} | **Doctor:** {result.get('doctor_name')}\n"
                    f"* **Clinical Notes:** {result.get('clinical_notes')}\n"
                    f"* **Prescription:** {result.get('prescription')}\n"
                    f"* **Follow-up Date:** {result.get('follow_up_date')}\n"
                    f"* **Consultation Status:** COMPLETED"
                )
            return f"❌ {result.get('error', 'Failed to save consultation notes.')}"

        elif tool_name == "generate_appointment_payment_link":
            if result.get("success"):
                if result.get("already_paid"):
                    return f"✅ **Appointment #{result.get('appointment_id')} is already PAID.** (OPD Fee: ₹{result.get('amount')})"
                return (
                    f"### 💳 Online Payment Link Generated\n\n"
                    f"* **Appointment:** `{result.get('appointment_id')}` ({result.get('doctor_name')})\n"
                    f"* **Patient:** {result.get('patient_name')} | **Amount:** **₹{result.get('amount')}**\n"
                    f"* **Payment Checkout Link:** [{result.get('payment_link_url')}]({result.get('payment_link_url')})\n\n"
                    f"> 📲 *Patient can pay instantly via UPI, QR, Debit/Credit Card, or NetBanking.*"
                )
            return f"❌ {result.get('error', 'Payment link generation failed.')}"

        elif tool_name == "get_all_opd_queues":
            queues = result.get("department_queues", [])
            lines = [
                f"### 🏥 Hospital Multi-Department OPD Queues ({result.get('date')})\n\n"
                f"* **Total Appointments Booked:** **{result.get('total_appointments', 0)}**\n"
                f"* **Currently Waiting:** **{result.get('total_waiting', 0)}** | **In Consultation:** **{result.get('total_in_consultation', 0)}** | **Completed:** **{result.get('total_completed', 0)}**\n",
                "| Department | Waiting | In Consultation | Completed | Total Booked |",
                "|---|---|---|---|---|"
            ]
            for q in queues:
                lines.append(f"| **{q.get('department_name')}** | {q.get('waiting_count')} | {q.get('in_consultation_count')} | {q.get('completed_count')} | {q.get('total_booked')} |")
            return "\n".join(lines)

        elif tool_name == "approve_or_reject_doctor_leave":
            if result.get("status") == "CONFIRMATION_REQUIRED":
                return (
                    f"⚠️ **Confirmation Required: {result.get('requested_action')} Leave Application**\n\n"
                    f"* **Doctor:** {result.get('doctor_name')} ({result.get('department')})\n"
                    f"* **Leave Period:** {result.get('period')}\n\n"
                    f"To confirm this action, please reply with:\n"
                    f"`CONFIRM {result.get('confirmation_token')}`"
                )
            if result.get("success"):
                return f"✅ **{result.get('message')}**"
            return f"❌ {result.get('error', 'Leave approval/rejection failed.')}"

        elif tool_name == "update_doctor_schedule":
            if result.get("status") == "CONFIRMATION_REQUIRED":
                return (
                    f"⚠️ **Confirmation Required: Update Doctor OPD Timetable**\n\n"
                    f"* **Doctor:** {result.get('doctor_name')}\n"
                    f"* **Day:** {result.get('day')}\n"
                    f"* **New Timings:** {result.get('new_timings')} (Slot: {result.get('slot_duration')})\n\n"
                    f"To confirm this timetable update, please reply with:\n"
                    f"`CONFIRM {result.get('confirmation_token')}`"
                )
            if result.get("success"):
                return f"✅ **{result.get('message')}**"
            return f"❌ {result.get('error', 'Schedule update failed.')}"

        elif tool_name == "get_expiring_subscriptions_report":
            exp_list = result.get("expiring_hospitals", [])
            if not exp_list:
                return f"✅ **All tenant hospital subscriptions are healthy.** None expiring within the next {result.get('threshold_days', 30)} days."
            lines = [
                f"### ⏳ Tenant Subscriptions Expiring Soon (Next {result.get('threshold_days', 30)} Days)\n",
                f"Found **{len(exp_list)} hospital(s)** requiring renewal:\n",
                "| Hospital Name | Plan | Days Left | Expiry Date | Phone | Status |",
                "|---|---|---|---|---|---|"
            ]
            for h in exp_list:
                lines.append(f"| **{h.get('hospital_name')}** | `{h.get('plan')}` | **{h.get('days_remaining')} days** | {h.get('expires_at')} | {h.get('contact_phone')} | {h.get('status')} |")
            return "\n".join(lines)

        elif tool_name == "extend_hospital_subscription":
            if result.get("status") == "CONFIRMATION_REQUIRED":
                return (
                    f"⚠️ **Confirmation Required: Extend SaaS Subscription**\n\n"
                    f"* **Hospital:** {result.get('hospital_name')} (Plan: `{result.get('plan')}`)\n"
                    f"* **Extension:** +{result.get('duration_days')} days\n"
                    f"* **Current Expiry:** {result.get('current_expiry')} ➔ **New Expiry:** `{result.get('new_expiry')}`\n\n"
                    f"To confirm subscription extension, please reply with:\n"
                    f"`CONFIRM {result.get('confirmation_token')}`"
                )
            if result.get("success"):
                return f"✅ **{result.get('message')}**"
            return f"❌ {result.get('error', 'Subscription extension failed.')}"

        elif tool_name == "get_comprehensive_doctor_analytics":
            matrix = result.get("doctor_matrix", [])
            lines = [
                f"### 🏥 Doctor Weekly Rosters & Performance ({result.get('period', 'Weekly')})\n",
                f"* **Total Active Doctors:** **{result.get('total_active_doctors', len(matrix))}**\n",
                "| Doctor Name | Department | Working Days | OPD Fee | Bookings | Completed | Revenue |",
                "|---|---|---|---|---|---|---|"
            ]
            for d in matrix:
                lines.append(f"| **{d.get('doctor_name')}** | {d.get('department')} | **{d.get('weekly_working_days')} days/wk** | ₹{d.get('opd_fee')} | {d.get('total_appointments')} | {d.get('completed')} | **{d.get('total_revenue_generated')}** |")
            return "\n".join(lines)

        elif tool_name == "get_hospital_department_directory":
            depts = result.get("departments", [])
            lines = [
                f"### 🏢 Hospital Medical Departments ({len(depts)})\n",
                "| Department Name | Active Doctors |",
                "|---|---|"
            ]
            for d in depts:
                lines.append(f"| **{d.get('department')}** | **{d.get('active_doctors')} doctors** |")
            return "\n".join(lines)

        elif tool_name == "apply_leave_for_doctor":
            if result.get("success"):
                return (
                    f"✅ **Doctor Leave Successfully Approved and Recorded!**\n\n"
                    f"* **Doctor:** {result.get('doctor_name')}\n"
                    f"* **Leave Period:** {result.get('start_date')} to {result.get('end_date')}\n"
                    f"* **Reason:** {result.get('reason')}\n"
                    f"* **Status:** `{result.get('status')}`"
                )
            return f"❌ {result.get('error', 'Leave submission failed.')}"

        elif tool_name == "run_analytics_query":
            label = result.get("result_label", "Analytics Report")
            rows = result.get("rows", [])
            summary = result.get("summary")
            count = result.get("count", len(rows) if rows else 0)

            if "error" in result:
                return f"❌ {result['error']}"

            # Special case: repeat ratio post-processed summary
            if summary and isinstance(summary, dict):
                total = summary.get("total_patients", 0)
                new_p = summary.get("new_patients", 0)
                repeat_p = summary.get("repeat_patients", 0)
                rate = summary.get("repeat_rate_pct", 0)
                return (
                    f"### 📊 {label}\n\n"
                    f"* **Total Patients:** {total}\n"
                    f"* **New Patients:** {new_p}\n"
                    f"* **Repeat Patients:** {repeat_p}\n"
                    f"* **Repeat Rate:** **{rate}%**"
                )

            if not rows:
                return f"### 📊 {label}\n\nNo records found for the selected period."

            # Auto-build markdown table from rows
            headers = list(rows[0].keys())
            # Format header display names
            display_headers = [h.replace("_", " ").title() for h in headers]
            lines = [
                f"### 📊 {label} ({count} record{'s' if count != 1 else ''})\n",
                "| " + " | ".join(display_headers) + " |",
                "|" + "---|" * len(headers)
            ]
            for row in rows:
                values = []
                for h in headers:
                    v = row.get(h, "—")
                    # Format currency fields
                    if any(kw in h for kw in ["revenue", "amount", "dues", "fee", "spent", "paid", "monthly_revenue"]):
                        try:
                            values.append(f"₹{int(float(v)):,}" if v is not None else "—")
                        except (ValueError, TypeError):
                            values.append(str(v) if v is not None else "—")
                    # Format percentage
                    elif "pct" in h or "rate" in h:
                        values.append(f"{v}%" if v is not None else "—")
                    else:
                        values.append(str(v) if v is not None else "—")
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)

        elif tool_name == "list_analytics_templates":
            templates = result.get("templates", [])
            if not templates:
                return "No analytics templates are available for your role."
            lines = [
                f"### 📊 Available Analytics Reports ({len(templates)})\n",
                "| Report Name | Template ID |",
                "|---|---|"
            ]
            for t in templates:
                lines.append(f"| {t.get('description')} | `{t.get('template_id')}` |")
            lines.append("\n> 💡 Ask me any of these — I'll run the report for you automatically.")
            return "\n".join(lines)

        # Generic dict formatting
        return "\n".join([f"* **{k.replace('_', ' ').title()}:** {v}" for k, v in result.items()])


    _query_cache: Dict[str, Any] = {}
    CACHE_TTL_SECONDS: float = 30.0

    @classmethod
    async def chat(
        cls,
        user_message: str,
        hospital_id: str,
        user_id: str,
        role: str,
        hospital_name: str,
        active_tab: str,
        selected_date: str,
        chat_history: List[Dict[str, str]],
        db: AsyncSession,
        session_id: Optional[str] = None,
        actor_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes an authenticated, 5-Way Routed, Zero-Trust Copilot turn with Actor Identity.
        """
        import time
        # 0. Multi-Turn Entity Extraction & Typo-Normalized Query
        normalized_msg = entity_extractor.normalize_text(user_message)
        extracted: ExtractedEntities = entity_extractor.extract_entities(normalized_msg)
        context_state: SessionContextState = conversation_memory.get_context_state(hospital_id, user_id, session_id)

        # Logged-in Patient Identity Binding (Permanent Account Phone Lock)
        role_upper = (role or "").upper().replace(" ", "_")
        if role_upper == "PATIENT" and actor_profile:
            acc_phone = actor_profile.get("patient_phone")
            acc_name = actor_profile.get("patient_name")
            if acc_phone:
                context_state.patient_phone = acc_phone
            if not context_state.patient_name and acc_name:
                context_state.patient_name = acc_name

        if extracted.doctor_name:
            context_state.current_doctor_name = extracted.doctor_name
        if extracted.date_str:
            context_state.selected_date = extracted.date_str
        if extracted.time_str:
            context_state.selected_time = extracted.time_str
        if extracted.department:
            context_state.department = extracted.department
        if extracted.patient_name:
            context_state.patient_name = extracted.patient_name
        if extracted.patient_phone:
            # If not a logged-in patient with a locked phone, allow phone update
            if not (role_upper == "PATIENT" and actor_profile and actor_profile.get("patient_phone")):
                context_state.patient_phone = extracted.patient_phone
        if extracted.appointment_id:
            context_state.last_appointment_id = extracted.appointment_id

        # Fast In-Memory Cache Check for Read Queries (Shielding Free-Tier 15 RPM limits)
        cache_key = f"{hospital_id}:{role}:{normalized_msg.lower().strip()}"
        now_ts = time.time()
        if not re.search(r'\b(confirm|cancel|book|reschedule|update|extend|toggle)\b', normalized_msg, re.I):
            if cache_key in cls._query_cache:
                cached_time, cached_res = cls._query_cache[cache_key]
                if now_ts - cached_time < cls.CACHE_TTL_SECONDS:
                    return cached_res

        import httpx

        # 1. Direct Action Confirmation Command Check (e.g. "CONFIRM act_xxx" or single-word "confirm")
        conf_match = re.search(r'\bCONFIRM\s+(act_[a-f0-9]+)\b', user_message, flags=re.IGNORECASE)
        token_id = None
        if conf_match:
            token_id = conf_match.group(1)
        elif user_message.strip().lower() in ["confirm", "yes confirm", "haan confirm", "approve", "yes", "haan", "confirm leave", "confirm please", "submit leave"]:
            token_id = conversation_memory.get_latest_pending_token(hospital_id, user_id)

        if token_id:
            consumed = conversation_memory.validate_and_consume_token(token_id, hospital_id, user_id)
            if not consumed:
                return {"reply": "⚠️ Confirmation token has expired or is invalid. Please trigger the request again.", "route": "ACTION"}
            # Execute confirmed action
            tresult = await tool_registry.execute_tool(
                tool_name=consumed.action_name,
                args=consumed.action_args,
                context={"hospital_id": hospital_id, "user_id": user_id, "role": role},
                db=db
            )
            return {
                "reply": f"✅ **Action Confirmed and Executed!**\n\n" + cls._format_markdown_fallback(consumed.action_name, tresult),
                "tool_used": consumed.action_name,
                "tool_result": tresult,
                "route": "ACTION"
            }

        # 2. Check offline deterministic match first (guarantees sub-20ms response, slot-filling continuity, and zero-hallucination)
        offline_res = await cls._match_offline_intent(
            user_message, role, hospital_id, user_id, db,
            context_state=context_state, actor_profile=actor_profile
        )
        if offline_res:
            offline_res["route"] = "LIVE_DATA"
            if not offline_res.get("suggestions"):
                offline_res["suggestions"] = cls._build_contextual_suggestions(
                    role=role,
                    tool_used=offline_res.get("tool_used"),
                    query=user_message,
                    reply=offline_res.get("reply", ""),
                    is_expired=bool(actor_profile and actor_profile.get("is_subscription_expired"))
                )
            return offline_res

        # 3. 5-Way Intent Routing
        decision: RouterDecision = await intent_router.route_query(
            query=user_message,
            role=role,
            hospital_id=hospital_id
        )

        # 4. Handle UNKNOWN Route:
        # When rigid regexes don't match (typos like 'what the reaosn of patinets', conversational 'okay', 'what', follow-ups):
        # DO NOT abort with robotic error! Hand it over to the ReAct LLM Engine (Groq / Gemini) with role-authorized tools.
        # The LLM will use its intelligence, read conversation history, execute tools if required, or answer naturally.
        if decision.route == RouteType.UNKNOWN:
            candidate_tools = decision.pruned_tools or tool_registry.prune_tools_for_user(query=user_message, user_role=role, top_k=30)
            decision = RouterDecision(
                route=RouteType.LIVE_DATA,
                confidence=0.60,
                knowledge_results=[],
                pruned_tools=candidate_tools
            )

        # 4. Handle Pure KNOWLEDGE Route (Groq synthesizes natural conversational answers, offline falls back to raw RAG text)
        if decision.route == RouteType.KNOWLEDGE and decision.knowledge_results:
            if not GroqClient.is_configured():
                top_hit = decision.knowledge_results[0]
                reply = f"### 📖 {top_hit['title']}\n\n{top_hit['content']}\n\n> 📚 *Source: {top_hit.get('source', 'Hospital Knowledge Base')}*"
                return {
                    "reply": reply,
                    "route": decision.route.value,
                    "citations": [k["title"] for k in decision.knowledge_results]
                }
            # When Groq is online, fall through so Groq synthesizes a conversational, ChatGPT-like answer using rag_context_block!

        # 5. Compile Live Dynamic System Prompt & Pruned Tool Spec
        today_obj = datetime.now()
        today_str = today_obj.strftime("%Y-%m-%d (%A)")
        filter_date = selected_date or today_obj.strftime("%Y-%m-%d")
        kal_date = (today_obj + timedelta(days=1)).strftime("%Y-%m-%d (%A)")
        parso_date = (today_obj + timedelta(days=2)).strftime("%Y-%m-%d (%A)")

        hospital_directory = await cls.get_hospital_directory_summary(hospital_id, db)
        
        # Knowledge Context Block (for MIXED and Context Enrichment)
        rag_context_block = ""
        if decision.knowledge_results:
            rag_snippets = "\n".join([f"- [{k['title']}]: {k['content']}" for k in decision.knowledge_results])
            rag_context_block = f"\nHOSPITAL KNOWLEDGE BASE / POLICY SNIPPETS:\n{rag_snippets}\n"

        # Actor Identity Injection Block
        actor_context_block = ""
        if actor_profile:
            if actor_profile.get("doctor_name"):
                actor_context_block = f"""
LOGGED-IN ACTOR IDENTITY (CRITICAL GROUNDING):
- Logged-in Doctor: {actor_profile.get('doctor_name')}
- Doctor ID: {actor_profile.get('doctor_id')}
- Department: {actor_profile.get('department')}
- Regular Schedule / Timings: {actor_profile.get('timings')}
- OPD Fee: ₹{actor_profile.get('opd_fees')}
- DIRECTIVE: When this user asks 'my queue', 'how many patients are waiting in my queue?', 'my shift timings tomorrow?', 'my earnings today?', 'apply for leave next Monday', ALWAYS execute tools for THIS DOCTOR ('{actor_profile.get('doctor_name')}', ID: '{actor_profile.get('doctor_id')}').
"""
            elif actor_profile.get("patient_name"):
                actor_context_block = f"""
LOGGED-IN ACTOR IDENTITY (CRITICAL GROUNDING):
- Logged-in Patient: {actor_profile.get('patient_name')}
- Patient ID: {actor_profile.get('patient_id')}
- Phone: {actor_profile.get('patient_phone')}
- DIRECTIVE: All first-person queries ('my appointment', 'my prescription') refer to THIS PATIENT.
"""

        working_context_block = f"""
ACTIVE CONVERSATION WORKING CONTEXT & EXTRACTED ENTITIES:
- Discussed Doctor: {context_state.current_doctor_name or (actor_profile.get('doctor_name') if actor_profile else 'None')} (ID: {context_state.current_doctor_id or (actor_profile.get('doctor_id') if actor_profile else 'None')})
- Target Date: {context_state.selected_date or filter_date}
- Target Time / Slot: {context_state.selected_time or 'None'}
- Clinical Department: {context_state.department or (actor_profile.get('department') if actor_profile else 'None')}
- Patient Name: {context_state.patient_name or 'None'}
- Patient Phone: {context_state.patient_phone or 'None'}
- Target Appointment ID: {context_state.last_appointment_id or 'None'}
- Last Tool Used: {context_state.last_tool_used or 'None'}
"""

        # Fetch compressed conversation summary for long-context continuity
        session_summary = conversation_memory.get_session_summary(hospital_id, user_id, session_id)
        summary_block = f"\nCONVERSATION HISTORY SUMMARY (Earlier turns, compressed):\n{session_summary}\n" if session_summary else ""

        # Hospital Admin Real-Time Grounding Snapshot
        admin_live_block = ""
        role_upper = (role or "").upper().replace(" ", "_")
        if role_upper in ["ADMIN", "HOSPITAL_ADMIN"] and hospital_id:
            try:
                from app.engines.hospital_directory_intel import HospitalDirectoryIntel
                roster = await HospitalDirectoryIntel.get_hospital_roster(hospital_id, db)
                from app.tools.admin_tools import AdminTools
                live_q = await AdminTools.get_all_opd_queues(hospital_id, filter_date, db)
                doc_lines = []
                for d in roster:
                    doc_b = next((q for q in live_q.get("doctors_breakdown", []) if d["id"] == q.get("doctor_id") or d["first_name"].lower() in q.get("doctor_name", "").lower()), {})
                    b_cnt = doc_b.get("booked_count", 0)
                    c_cnt = doc_b.get("completed_count", 0)
                    w_cnt = doc_b.get("waiting_count", 0)
                    doc_lines.append(f"- {d['full_name']} ({d['department']}): Fee ₹{d['opd_fee']}, Today: {b_cnt} booked ({c_cnt} completed, {w_cnt} waiting). Schedule: {d['working_days_names']}")
                
                admin_live_block = f"""
LIVE HOSPITAL ADMIN METRICS & DOCTOR STATUS TODAY ({filter_date}):
{chr(10).join(doc_lines)}
- Total OPD Bookings Today: {live_q.get('total_booked', 0)}
- DIRECTIVE FOR ADMIN QUERIES:
  * When asked 'which doctor is free today who have 0 appointment' or similar, directly identify doctors with 0 bookings today from the list above!
  * Never invent fake doctor names or start booking unless explicitly requested.
"""
            except Exception as snap_e:
                logger.debug(f"Admin live block snapshot error: {snap_e}")

        # Super Admin Real-Time Grounding Snapshot & Fleet Context
        super_admin_live_block = ""
        if role_upper in ["SUPER_ADMIN", "SUPERADMIN"] and db:
            try:
                from app.tools.control_tower_tools import ControlTowerTools
                fleet_overview = await ControlTowerTools.get_platform_control_tower_overview(db=db)
                fleet = fleet_overview.get("hospitals_fleet", [])
                fleet_lines = []
                for h in fleet:
                    fleet_lines.append(
                        f"- Hospital: '{h.get('hospital_name')}' | ID: '{h.get('hospital_id')}' | Plan: {h.get('subscription_plan')} | Status: {h.get('status')} | Doctors: {h.get('active_doctors')} | Total Appointments: {h.get('total_appointments')}"
                    )
                super_admin_live_block = f"""
PLATFORM OWNER (SUPER ADMIN) CONTROL TOWER & FLEET DIRECTIVES:
- Authenticated Mode: SUPER_ADMIN (Platform Owner / Control Tower).
- ROLE BOUNDARY: You are the Platform Owner assistant, NOT a hospital receptionist. NEVER book patient OPD appointments or ask for patient details. If a user asks to book an appointment, clearly inform them that patient bookings are handled via individual hospital reception portals.
- REGISTERED TENANT HOSPITALS ON AURA PLATFORM:
{chr(10).join(fleet_lines)}
- CRITICAL TOOL & QUERY DIRECTIVES:
  * When asked about revenue, metrics, or details for a specific hospital (e.g. 'rao hospita', 'balaji', 'apollo'), map it to its registered Hospital ID above (e.g. 'Rao Hospital' -> 'HOSP-RAOH-4893') and pass that hospital_id to 'get_revenue_and_dues(hospital_id=...)' or 'get_comprehensive_doctor_analytics(hospital_id=...)'.
  * When using 'search_platform_hospital', pass ONLY the core hospital name keyword (e.g. 'rao'), NOT full query strings.
"""
            except Exception as sa_e:
                logger.debug(f"Super admin live block snapshot error: {sa_e}")

        # Expired Hospital Subscription Mode Directive
        expired_consulting_block = ""
        is_expired_hospital = bool(actor_profile and actor_profile.get("is_subscription_expired"))
        if is_expired_hospital:
            expired_consulting_block = f"""
EXPIRED HOSPITAL SUBSCRIPTION MODE DIRECTIVE:
- The authenticated hospital ({hospital_name}) has an EXPIRED subscription (Plan: '{actor_profile.get('subscription_plan', 'STARTER')}', Expired: '{actor_profile.get('plan_expires_at')}').
- STRICT SECURITY DIRECTIVE: DO NOT execute tools or disclose internal live hospital data (OPD queues, doctor rosters, patient EMR, or revenue).
- ROLE & PERSONA: You are the official AURA SaaS Product & Sales Consultant (ChatGPT-style consultation).
- Your mission is to assist the hospital admin in understanding AURA subscription plans (Starter ₹1,500/mo, Pro AI ₹2,999/mo, Enterprise 360 ₹29,999/yr), comparing tiers, explaining 24/7 AI Voice phone calling capabilities, and actively recommending the best plan for their hospital size and doctor count based on the retrieved knowledge base.
- Guide them politely to click the 'Renew Now via Razorpay' button directly on their workspace screen for instant reactivation.
"""

        hosp_display = 'AURA Platform Control Tower' if role_upper in ['SUPER_ADMIN', 'SUPERADMIN'] else hospital_name
        system_instruction = f"""You are AURA AI Copilot, the official enterprise intelligent healthcare assistant for {hosp_display}.
Current Authenticated Context:
- User Role: {role}
- Hospital: {hospital_name} (ID: {hospital_id or 'Platform'})
- Dashboard Tab: {active_tab}
- Today's Date: {today_str} (Use this for 'aaj' / 'today')
- Tomorrow ('kal'): {kal_date}
- Day After Tomorrow ('parso'): {parso_date}
- Dashboard Selected Date: {filter_date}
{actor_context_block}
{working_context_block}
{summary_block}
{rag_context_block}
{hospital_directory}
{admin_live_block}
{super_admin_live_block}
{expired_consulting_block}

STRICT ANTI-HALLUCINATION & GROUNDING DIRECTIVES:
1. ZERO HALLUCINATION: NEVER invent, guess, or fabricate appointment IDs (apt_...), doctor IDs, patient medical records, slot timings, prices (₹), queue numbers, or financial metrics.
2. SOURCE OF TRUTH: Every factual detail in your response MUST be directly derived from verified database tool output or the official hospital directory/knowledge snippets above.
3. MISSING ENTITIES: If a doctor, patient, appointment, slot, or record is not found in tool outputs, explicitly inform the user that no record was found. Never guess.
4. ACTION ACCURACY: Do not claim an appointment or change was booked/modified unless the tool returned success=True with a verified database ID.
5. MULTI-STEP REASONING: You can execute a sequence of tools across turns (e.g. search doctor -> get slots -> book appointment) to completely satisfy multi-step user questions.
6. FORMATTING: Use clean, structured Markdown with bullet points or tables. Highlight key IDs and amounts clearly. Never return raw JSON.
7. LANGUAGE: Mirror user language (English, Hindi, or polite Hinglish).
"""

        # Pruned Tools passed to LLM (Disabled when hospital subscription is expired to ensure pure consultation)
        tools_spec = [] if is_expired_hospital else decision.pruned_tools

        contents = []
        for msg in chat_history[-10:]:
            contents.append({"role": "user" if msg["role"] == "user" else "model", "parts": [{"text": str(msg["content"])}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        # TIER 1A: Groq Ultra-High-Speed Cloud Inference Engine (qwen/qwen3.8-27b)
        if GroqClient.is_configured():
            groq_res = await cls._execute_groq_react_loop(
                system_instruction=system_instruction,
                chat_history=chat_history,
                user_message=user_message,
                tools_spec=tools_spec,
                context_state=context_state,
                actor_profile=actor_profile,
                hospital_id=hospital_id,
                user_id=user_id,
                role=role,
                decision=decision,
                db=db
            )
            if groq_res:
                return groq_res

        gemini_api_key = settings.GEMINI_API_KEY
        models_to_try = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
            "gemini-1.5-pro"
        ]
        headers = {
            "Content-Type": "application/json"
        }
        if gemini_api_key:
            headers["x-goog-api-key"] = gemini_api_key
            if gemini_api_key.startswith("AQ.") or gemini_api_key.startswith("ya29."):
                headers["Authorization"] = f"Bearer {gemini_api_key}"

        # TIER 1B: Multi-Step Agentic Tool Calling Loop via Google Gemini API
        # ReAct Loop: Reason → Act → Observe → Reason (up to MAX_HOPS per message)
        MAX_HOPS = 4  # Safety cap: prevents infinite loops
        # HIGH_RISK tools that require HITL confirmation — never chain automatically
        CHAIN_BLOCKED_TOOLS = {
            "apply_leave_for_doctor", "approve_or_reject_doctor_leave",
            "cancel_appointment", "reschedule_appointment",
            "extend_hospital_subscription", "update_doctor_schedule",
            "mark_appointment_payment_paid"
        }
        if gemini_api_key:
            try:
                async with httpx.AsyncClient(timeout=12.0) as client:
                    for model_name in models_to_try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_api_key}"
                        current_contents = list(contents)
                        max_iterations = MAX_HOPS
                        executed_tool_name = None
                        executed_tool_result = None
                        executed_tool_chain: List[str] = []  # Track all tools executed in this turn
                        loop_success = False

                        for iteration in range(max_iterations):
                            iter_payload = {
                                "system_instruction": {"parts": [{"text": system_instruction}]},
                                "contents": current_contents,
                                "generationConfig": {"temperature": 0.2}
                            }
                            if tools_spec:
                                iter_payload["tools"] = [{"functionDeclarations": tools_spec}]

                            try:
                                resp = await client.post(url, json=iter_payload, headers=headers)
                                if resp.status_code == 200:
                                    data = resp.json()
                                    cand = data.get("candidates", [{}])[0]
                                    part = cand.get("content", {}).get("parts", [{}])[0]
                                    
                                    # If Gemini invokes a tool
                                    if "functionCall" in part:
                                        fcall = part["functionCall"]
                                        tname = fcall.get("name")
                                        targs = fcall.get("args", {})
                                        call_id = fcall.get("id")

                                        # SAFETY: Block HIGH-RISK tools from being auto-chained in hop 2+
                                        if iteration > 0 and tname in CHAIN_BLOCKED_TOOLS:
                                            logger.info(f"ReAct chain blocked HIGH-RISK tool '{tname}' at hop {iteration+1}. Requires explicit user request.")
                                            break

                                        # Auto-resolve missing fields from context state
                                        if "doctor_id" in targs and not targs["doctor_id"] and context_state.current_doctor_id:
                                            targs["doctor_id"] = context_state.current_doctor_id
                                        if "doctor_name" in targs and not targs["doctor_name"] and context_state.current_doctor_name:
                                            targs["doctor_name"] = context_state.current_doctor_name
                                        if "date_str" in targs and not targs["date_str"] and context_state.selected_date:
                                            targs["date_str"] = context_state.selected_date

                                        # Build enriched context (includes doctor_id + patient_id for analytics)
                                        enriched_context = {
                                            "hospital_id": hospital_id,
                                            "user_id": user_id,
                                            "role": role
                                        }
                                        if actor_profile:
                                            if actor_profile.get("doctor_id"):
                                                enriched_context["doctor_id"] = actor_profile["doctor_id"]
                                            if actor_profile.get("patient_id"):
                                                enriched_context["patient_id"] = actor_profile["patient_id"]

                                        # Execute through Dynamic Registry
                                        tresult = await tool_registry.execute_tool(
                                            tool_name=tname,
                                            args=targs,
                                            context=enriched_context,
                                            db=db
                                        )
                                        executed_tool_name = tname
                                        executed_tool_result = tresult
                                        executed_tool_chain.append(tname)
                                        logger.info(f"ReAct hop {iteration+1}/{MAX_HOPS}: executed '{tname}' → {len(str(tresult))} chars result")

                                        # Update context state with returned entities
                                        context_state.last_tool_used = tname
                                        context_state.last_tool_result = tresult
                                        if isinstance(tresult, dict):
                                            if tresult.get("doctor_id"):
                                                context_state.current_doctor_id = tresult["doctor_id"]
                                            if tresult.get("doctor_name") or tresult.get("name"):
                                                context_state.current_doctor_name = tresult.get("doctor_name") or tresult.get("name")
                                            if tresult.get("appointment_id") or tresult.get("id"):
                                                context_state.last_appointment_id = tresult.get("appointment_id") or tresult.get("id")
                                            if tresult.get("doctors") and len(tresult["doctors"]) == 1:
                                                first_doc = tresult["doctors"][0]
                                                context_state.current_doctor_id = first_doc.get("doctor_id") or first_doc.get("id")
                                                context_state.current_doctor_name = first_doc.get("doctor_name") or first_doc.get("name")

                                        # Append to contents for next step
                                        f_resp_part = {
                                            "name": tname,
                                            "response": {"result": tresult}
                                        }
                                        if call_id:
                                            f_resp_part["id"] = call_id

                                        current_contents.append(cand.get("content"))
                                        current_contents.append({
                                            "role": "user",
                                            "parts": [{"functionResponse": f_resp_part}]
                                        })
                                        continue

                                    txt = part.get("text", "")
                                    if txt and txt.strip():
                                        loop_success = True
                                        return {
                                            "reply": txt.strip(),
                                            "tool_used": executed_tool_name,
                                            "tool_result": executed_tool_result,
                                            "route": decision.route.value
                                        }
                            except Exception as e:
                                logger.warning(f"Iteration {iteration} on model {model_name} failed: {e}")
                                break

                        if loop_success:
                            break
                        elif executed_tool_name and executed_tool_result:
                            return {
                                "reply": cls._format_markdown_fallback(executed_tool_name, executed_tool_result),
                                "tool_used": executed_tool_name,
                                "tool_result": executed_tool_result,
                                "route": decision.route.value
                            }
            except Exception as outer_e:
                logger.warning(f"Tier 1 LLM failure: {outer_e}")

        # TIER 2: Deterministic Semantic Fallback (100% Uptime even with 429 quota exhaustion)
        offline_res = await cls._match_offline_intent(
            user_message, role, hospital_id, user_id, db,
            context_state=context_state, actor_profile=actor_profile
        )
        if offline_res:
            offline_res["route"] = decision.route.value
            if not offline_res.get("suggestions"):
                offline_res["suggestions"] = cls._build_contextual_suggestions(
                    role=role,
                    tool_used=offline_res.get("tool_used"),
                    query=user_message,
                    reply=offline_res.get("reply", ""),
                    is_expired=bool(actor_profile and actor_profile.get("is_subscription_expired"))
                )
            return offline_res

        # Contextual, Enterprise-Grade Smart Fallback with Actionable Suggestions
        role_upper = (role or "STAFF").upper()
        if is_expired_hospital and role_upper not in ["SUPER_ADMIN", "SUPERADMIN"]:
            fallback_reply = (
                f"Your hospital workspace is currently suspended due to an expired subscription plan. "
                f"As your AURA SaaS Consultant, I can help you compare plans or guide you through instant Razorpay renewal:"
            )
            fallback_suggestions = [
                "Compare Starter, Pro AI, and Enterprise subscription plans",
                "Which AURA subscription plan is best for our hospital?",
                "What features are included in the Pro AI Voice plan?",
                "How can I renew our hospital subscription plan via Razorpay?"
            ]
        elif role_upper in ["SUPER_ADMIN", "SUPERADMIN"]:
            fallback_reply = (
                f"I couldn't locate specific platform metrics matching *\"{user_message}\"*. "
                f"As **Platform SuperAdmin**, you have direct access to global multi-tenant telemetry. "
                f"Try one of these real-time overviews:"
            )
            fallback_suggestions = [
                "Platform monthly revenue overview",
                "How many hospitals are active on AURA platform?",
                "Which subscriptions are expiring in next 30 days?",
                "Total AI voice calls processed today"
            ]
        elif role_upper in ["ADMIN", "HOSPITAL_ADMIN"]:
            fallback_reply = (
                f"I checked hospital live records, but couldn't find a direct record matching *\"{user_message}\"*. "
                f"As **Hospital Administrator**, you can instantly query live OPD, staff schedules, and financial collections:"
            )
            fallback_suggestions = [
                "How many appointments were cancelled today?",
                "What is our total OPD revenue for this month?",
                "Show doctor-wise booking performance",
                "Which doctors are on duty today?"
            ]
        elif role_upper == "DOCTOR":
            fallback_reply = (
                f"I couldn't find that specific clinical entry for *\"{user_message}\"*. "
                f"Here are quick actions for your consultation shift:"
            )
            fallback_suggestions = [
                "How many patients are waiting in my queue?",
                "What are my shift timings for tomorrow?",
                "Today's total consulted patients",
                "What are my OPD earnings today?"
            ]
        elif role_upper == "PATIENT":
            fallback_reply = (
                f"I couldn't find that in our patient service directory for *\"{user_message}\"*. "
                f"I can assist you with appointment booking, doctor schedules, and hospital consultation fees:"
            )
            fallback_suggestions = [
                "I want to book an appointment",
                "Which doctors are available today?",
                "What are the doctor consultation fees?",
                "Check my live token position"
            ]
        else:
            fallback_reply = (
                f"I couldn't find a direct match for *\"{user_message}\"*. "
                f"Here are front desk actions you can execute right now:"
            )
            fallback_suggestions = [
                "Show live OPD queue summary",
                "Check daily cash register",
                "Which doctors are available today?",
                "How many appointments were cancelled today?"
            ]

        bullets = "\n".join([f"* **{sug}**" for sug in fallback_suggestions])
        full_reply = f"{fallback_reply}\n\n{bullets}"
        return {
            "reply": full_reply,
            "route": decision.route.value,
            "suggestions": fallback_suggestions
        }

    @classmethod
    def _build_contextual_suggestions(
        cls,
        role: str,
        tool_used: Optional[str],
        query: str,
        reply: str,
        is_expired: bool = False
    ) -> List[str]:
        """Generates 3-4 smart, highly relevant next-step query pills strictly related to the answered topic."""
        role_up = (role or "STAFF").upper()
        q = (query or "").lower()
        t = (tool_used or "").lower()
        r = (reply or "").lower()

        # 0. Expired hospital or Subscription / Plan consultation intent (All roles except SuperAdmin)
        is_sub_query = any(w in q for w in ["plan", "subscri", "starter", "pro", "enterprise", "renew", "upgrade", "pricing", "cost", "price", "paywall", "razorpay", "voice call", "trial"])
        is_sub_reply = any(w in r for w in ["starter plan", "pro ai plan", "enterprise 360", "renew now", "razorpay", "subscription plan", "workspace is locked", "workspace is suspended", "subscription is suspended"])

        if (is_expired or is_sub_query or is_sub_reply) and role_up not in ["SUPER_ADMIN", "SUPERADMIN"]:
            if "voice" in q or "call" in q:
                return [
                    "Compare Starter, Pro AI, and Enterprise subscription plans",
                    "Which AURA subscription plan is best for our hospital?",
                    "How can I renew our hospital subscription plan via Razorpay?",
                    "What are the doctor limits for Pro AI vs Starter?"
                ]
            if "starter" in q:
                return [
                    "Compare Starter vs Pro AI plan features",
                    "How does 24/7 AI Voice Phone Receptionist work?",
                    "Which AURA subscription plan is best for our hospital?",
                    "How can I renew our hospital subscription plan via Razorpay?"
                ]
            if "pro" in q:
                return [
                    "What features are included in the Pro AI Voice plan?",
                    "Compare Pro AI and Enterprise 360 plans",
                    "How can I renew our hospital subscription plan via Razorpay?",
                    "Which AURA subscription plan is best for our hospital?"
                ]
            if "enterprise" in q:
                return [
                    "Compare Pro AI and Enterprise 360 plans",
                    "What features are included in the Pro AI Voice plan?",
                    "How can I renew our hospital subscription plan via Razorpay?",
                    "Which AURA subscription plan is best for our hospital?"
                ]
            return [
                "Compare Starter, Pro AI, and Enterprise subscription plans",
                "Which AURA subscription plan is best for our hospital?",
                "What features are included in the Pro AI Voice plan?",
                "How can I renew our hospital subscription plan via Razorpay?"
            ]

        if role_up in ["SUPER_ADMIN", "SUPERADMIN"]:
            if "voice" in q or "call" in q or "telemetry" in t:
                return [
                    "Show platform error telemetry",
                    "Which subscriptions are expiring in next 30 days?",
                    "Platform monthly revenue overview",
                    "Show all active hospital tenants"
                ]
            if "expir" in q or "renew" in q:
                return [
                    "Show all active hospital tenants",
                    "Platform monthly revenue overview",
                    "Total AI voice calls processed today"
                ]
            if "revenue" in q or "saas" in q or "money" in q:
                return [
                    "Which hospital generates maximum revenue?",
                    "Which subscriptions are expiring in next 30 days?",
                    "Total AI voice calls processed today"
                ]
            if "error" in q or "incident" in q or "telemetry" in q:
                return [
                    "Total AI voice calls processed today",
                    "Security audit trail",
                    "Platform monthly revenue overview"
                ]
            return [
                "Platform monthly revenue overview",
                "Which subscriptions are expiring in next 30 days?",
                "Total AI voice calls processed today",
                "Show all active hospital tenants"
            ]

        if role_up in ["ADMIN", "HOSPITAL_ADMIN"]:
            if any(w in q for w in ["cancel", "miss", "status", "appointment", "booking", "patient"]):
                return [
                    "Which doctors are on duty today and available?",
                    "What is our total OPD revenue for this month?",
                    "Show pending patient dues & unpaid bills",
                    "Show doctor-wise booking performance"
                ]
            if any(w in q for w in ["revenue", "due", "finance", "collection", "fee", "earning", "cash"]):
                return [
                    "Show pending patient dues & unpaid bills",
                    "Which department generated highest revenue?",
                    "How many appointments were cancelled today?",
                    "Which doctors are on duty today?"
                ]
            if any(w in q for w in ["doctor", "duty", "availab", "roster", "leave", "shift"]):
                return [
                    "How many appointments were cancelled today?",
                    "Show doctor-wise booking performance",
                    "What is our total OPD revenue for this month?",
                    "What is our current subscription plan validity?"
                ]
            return [
                "How many appointments were cancelled today?",
                "What is our total OPD revenue for this month?",
                "Which doctors are on duty today and available?",
                "Show pending patient dues & unpaid bills"
            ]

        if role_up == "DOCTOR":
            if any(w in q for w in ["queue", "token", "patient", "waiting"]):
                return [
                    "What is the next patient's chief complaint?",
                    "Today's total consulted patients",
                    "What are my shift timings for tomorrow?"
                ]
            return [
                "How many patients are waiting in my queue?",
                "What are my shift timings for tomorrow?",
                "Today's total consulted patients",
                "What are my OPD earnings today?"
            ]

        if role_up == "PATIENT":
            if any(w in q for w in ["book", "slot", "appointment", "schedule"]):
                return [
                    "Which doctors are available today?",
                    "What are the doctor consultation fees?",
                    "Check my current appointment token status"
                ]
            return [
                "I want to book an appointment",
                "Which doctors are available today?",
                "What are the doctor consultation fees?",
                "Check my live token position"
            ]

        return [
            "Which doctors are available today?",
            "How many appointments were cancelled today?",
            "What is our total OPD revenue for this month?"
        ]

    @classmethod
    async def _execute_groq_react_loop(
        cls,
        system_instruction: str,
        chat_history: List[Dict[str, Any]],
        user_message: str,
        tools_spec: Optional[List[Dict[str, Any]]],
        context_state: SessionContextState,
        actor_profile: Optional[Dict[str, Any]],
        hospital_id: Optional[str],
        user_id: Optional[str],
        role: str,
        decision: Any,
        db: AsyncSession,
        max_hops: int = 4
    ) -> Optional[Dict[str, Any]]:
        """
        Tier-1A Agentic ReAct Loop via Groq Cloud High-Speed Inference Engine (qwen/qwen3.8-27b).
        Executes database tools natively and returns grounded answers in <100ms with zero 429 quota exhaustion.
        """
        if not GroqClient.is_configured():
            return None

        import httpx
        api_key = settings.GROQ_API_KEY.strip()
        model_name = GroqClient.get_model()

        CHAIN_BLOCKED_TOOLS = {
            "apply_leave_for_doctor", "approve_or_reject_doctor_leave",
            "cancel_appointment", "reschedule_appointment",
            "extend_hospital_subscription", "update_doctor_schedule",
            "mark_appointment_payment_paid"
        }

        # Build initial messages (OpenAI format)
        groq_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_instruction}]
        for msg in chat_history[-10:]:
            r = "assistant" if msg.get("role") in ["model", "assistant"] else "user"
            c = msg.get("content", "")
            if c:
                groq_messages.append({"role": r, "content": str(c)})
        groq_messages.append({"role": "user", "content": user_message})

        def _norm_schema(o: Any) -> Any:
            if isinstance(o, dict):
                return {k: v.lower() if k == "type" and isinstance(v, str) else _norm_schema(v) for k, v in o.items()}
            if isinstance(o, list):
                return [_norm_schema(x) for x in o]
            return o

        # Format tools for OpenAI function calling
        groq_tools = None
        if tools_spec:
            groq_tools = []
            for t in tools_spec:
                groq_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": _norm_schema(t.get("parameters", {"type": "object", "properties": {}}))
                    }
                })

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AURA-Hospital-Copilot/1.0"
        }

        executed_tool_name = None
        executed_tool_result = None

        models_to_try = [model_name]
        if "qwen3.6-27b" not in model_name:
            models_to_try.append("qwen/qwen3.6-27b")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                for active_model in models_to_try:
                    current_groq_messages = list(groq_messages)
                    model_failed = False
                    for iteration in range(max_hops):
                        payload: Dict[str, Any] = {
                            "model": active_model,
                            "messages": current_groq_messages,
                            "temperature": 0.2,
                            "max_tokens": 1024
                        }
                        if groq_tools:
                            payload["tools"] = groq_tools
                            payload["tool_choice"] = "auto"

                        resp = await client.post(GroqClient.API_URL, json=payload, headers=headers)
                        if resp.status_code != 200:
                            logger.warning(f"Groq API ({active_model}) returned HTTP {resp.status_code}: {resp.text[:200]}")
                            model_failed = True
                            break

                        data = resp.json()
                        choices = data.get("choices", [])
                        if not choices:
                            break
                        choice = choices[0]
                        msg_obj = choice.get("message", {})
                        tool_calls = msg_obj.get("tool_calls")

                        if tool_calls:
                            # Append assistant message with tool calls
                            current_groq_messages.append(msg_obj)

                            for tc in tool_calls:
                                f_info = tc.get("function", {})
                                tname = f_info.get("name")
                                fargs_raw = f_info.get("arguments", "{}")
                                try:
                                    targs = json.loads(fargs_raw) if isinstance(fargs_raw, str) else (fargs_raw or {})
                                except Exception:
                                    targs = {}

                                call_id = tc.get("id") or f"call_{iteration}"

                                # Safety: block high-risk chained tools
                                if iteration > 0 and tname in CHAIN_BLOCKED_TOOLS:
                                    logger.info(f"Groq ReAct chain blocked HIGH-RISK tool '{tname}' at hop {iteration+1}.")
                                    break

                                # Auto-resolve missing fields
                                if "doctor_id" in targs and not targs["doctor_id"] and context_state.current_doctor_id:
                                    targs["doctor_id"] = context_state.current_doctor_id
                                if "doctor_name" in targs and not targs["doctor_name"] and context_state.current_doctor_name:
                                    targs["doctor_name"] = context_state.current_doctor_name
                                if "date_str" in targs and not targs["date_str"] and context_state.selected_date:
                                    targs["date_str"] = context_state.selected_date

                                enriched_context = {
                                    "hospital_id": hospital_id,
                                    "user_id": user_id,
                                    "role": role
                                }
                                if actor_profile:
                                    if actor_profile.get("doctor_id"):
                                        enriched_context["doctor_id"] = actor_profile["doctor_id"]
                                    if actor_profile.get("patient_id"):
                                        enriched_context["patient_id"] = actor_profile["patient_id"]

                                # Execute tool
                                tresult = await tool_registry.execute_tool(
                                    tool_name=tname,
                                    args=targs,
                                    context=enriched_context,
                                    db=db
                                )
                                executed_tool_name = tname
                                executed_tool_result = tresult
                                logger.info(f"Groq ReAct hop {iteration+1}/{max_hops}: executed '{tname}' -> {len(str(tresult))} chars")

                                # Update context state
                                context_state.last_tool_used = tname
                                context_state.last_tool_result = tresult
                                if isinstance(tresult, dict):
                                    if tresult.get("doctor_id"):
                                        context_state.current_doctor_id = tresult["doctor_id"]
                                    if tresult.get("doctor_name") or tresult.get("name"):
                                        context_state.current_doctor_name = tresult.get("doctor_name") or tresult.get("name")
                                    if tresult.get("appointment_id") or tresult.get("id"):
                                        context_state.last_appointment_id = tresult.get("appointment_id") or tresult.get("id")

                                # Append tool response message
                                current_groq_messages.append({
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "name": tname,
                                    "content": json.dumps(tresult, default=str)
                                })
                            continue

                        # Text reply received
                        txt = msg_obj.get("content", "")
                        if txt and txt.strip():
                            return {
                                "reply": txt.strip(),
                                "tool_used": executed_tool_name,
                                "tool_result": executed_tool_result,
                                "route": decision.route.value
                            }
                        break

                    if not model_failed:
                        break

            if executed_tool_name and executed_tool_result:
                return {
                    "reply": cls._format_markdown_fallback(executed_tool_name, executed_tool_result),
                    "tool_used": executed_tool_name,
                    "tool_result": executed_tool_result,
                    "route": decision.route.value
                }
        except Exception as groq_err:
            logger.warning(f"Groq ReAct loop error: {groq_err}")

        return None

    @classmethod
    async def _match_offline_intent(
        cls,
        user_message: str,
        role: str,
        hospital_id: Optional[str],
        user_id: Optional[str],
        db: AsyncSession,
        context_state: Optional[SessionContextState] = None,
        actor_profile: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Tier-2 Deterministic Semantic Matcher: Executes database tools directly when LLM is offline or 429 rate-limited."""
        norm_msg = entity_extractor.normalize_text(user_message)
        msg_lower = norm_msg.lower().strip()
        role_upper = (role or "").upper().replace(" ", "_")

        # Expired Hospital Bypass: Let Groq LLM & RAG handle natural language subscription consultation
        if actor_profile and actor_profile.get("is_subscription_expired"):
            return None
        
        # 1. Date extraction
        target_date = (context_state.selected_date if context_state and context_state.selected_date else None) or datetime.now().strftime("%Y-%m-%d")
        if "kal" in msg_lower or "tomorrow" in msg_lower:
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "parso" in msg_lower:
            target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # Check specific date like "3 sep" or "2026-09-03"
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})|(\d{1,2})\s*(sep|september|oct|october|aug|august|nov|dec|jan|feb|mar|apr|may|jun|jul)', msg_lower)
        if date_match:
            try:
                if date_match.group(1):
                    target_date = date_match.group(1)
                else:
                    d_num = int(date_match.group(2))
                    m_str = date_match.group(3)[:3]
                    m_num = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}.get(m_str, datetime.now().month)
                    target_date = f"{datetime.now().year:04d}-{m_num:02d}-{d_num:02d}"
            except Exception:
                pass

        # 1A. Grounded Hospital Directory & Entity Intelligence
        # Handles fees (highest, lowest, all fees, doctor fee), departments, doctor schedules
        if not (context_state and getattr(context_state, "booking_in_progress", False)):
            try:
                from app.engines.hospital_directory_intel import HospitalDirectoryIntel
                intel_res = await HospitalDirectoryIntel.analyze_and_answer(
                    user_message=user_message,
                    hospital_id=hospital_id,
                    db=db
                )
                if intel_res:
                    return intel_res
            except Exception as intel_e:
                logger.warning(f"HospitalDirectoryIntel evaluation error: {intel_e}")

        # Check if user has an active pending confirmation token
        pending_tok = conversation_memory.get_latest_pending_token(hospital_id, user_id)
        has_pending_token = bool(pending_tok)

        # 1B. Conversational Multi-Turn Appointment Booking Flow
        booking_kw = [
            r"\bwant\s+to?\s*book\b", r"\bbook\s+for\b", r"\bbook\s+an?\s+appointment\b",
            r"\bappointment\s+book\b", r"\bbook\s+appointment\b", r"\bslot\s+book\b",
            r"\bbook\s+slot\b", r"\bbooking\s+karo\b", r"\bparcha\s+banao\b",
            r"\bnayi\s+booking\b", r"\bbook\s+kar\s+do\b", r"\bbook\s+kr\s+do\b",
            r"\bappointment\s+schedule\b", r"\bschedule\s+appointment\b", r"\bek\s+appointment\b",
            r"\bdoctor\s+ke\s+sa?th\b", r"\bappointment\s+chahi?e\b"
        ]
        has_explicit_booking_kw = any(re.search(pat, msg_lower) for pat in booking_kw)

        is_analytics_query = any(w in msg_lower for w in [
            "performance", "report", "stats", "statistics", "matrix", "analysis", "analytics",
            "history", "trend", "breakdown", "load", "total", "summary", "count", "kitne",
            "kitna", "how many", "all time", "revenue", "kamai", "earning", "earnings", "collection",
            "dues", "booked", "completed", "cancelled", "missed", "status", "ranking", "fleet"
        ])
        has_booking_entities = bool(re.search(r'\b([6-9]\d{9})\b', norm_msg) and any(w in msg_lower for w in ["patient", "dr", "doctor", "pm", "am", "appointment", "slot"]))
        
        # Modification trigger: user correcting or modifying details (time, name, doctor, date) while confirmation is pending
        is_modification_request = has_pending_token and (
            any(w in msg_lower for w in ["change", "badal", "nahi", "not", "time", "slot", "naam", "name", "doctor", "dr", "date", "tarikh", "baje"]) or
            bool(entity_extractor._parse_time(norm_msg)) or
            bool(re.search(r'\b(0?[1-9]|1[0-2])[:;.\s]([0-5]\d)\b', norm_msg))
        )

        is_booking_trigger = (has_explicit_booking_kw or has_booking_entities or is_modification_request) and not is_analytics_query
        is_in_booking_flow = bool(context_state and getattr(context_state, "booking_in_progress", False)) and not is_analytics_query

        # STRICT ROLE FIREWALL: ADMIN, HOSPITAL_ADMIN, SUPER_ADMIN, and DOCTOR never run conversational patient booking flow
        is_admin_or_doc = role_upper in ["ADMIN", "HOSPITAL_ADMIN", "SUPER_ADMIN", "SUPERADMIN", "DOCTOR"]
        if is_admin_or_doc or is_analytics_query:
            is_booking_trigger = False
            is_in_booking_flow = False
            if context_state and getattr(context_state, "booking_in_progress", False):
                context_state.booking_in_progress = False

        # SUPER ADMIN ROLE BOUNDARY: Platform Owner does not perform patient OPD bookings
        if role_upper in ["SUPER_ADMIN", "SUPERADMIN"] and (has_explicit_booking_kw or any(w in msg_lower for w in ["book", "paointment", "appointment", "parcha", "booking", "nayi booking"])) and not is_analytics_query:
            suggestions = [
                "Show all active hospital tenants",
                "Rao Hospital total revenue all time",
                "Which hospital generates maximum revenue?",
                "Platform monthly revenue overview"
            ]
            return {
                "reply": (
                    "🛡️ **Platform Owner (Super Admin) Notice:**\n\n"
                    "Aap **Platform Control Tower** (Super Admin) portal me hain. Patient OPD appointment bookings individual hospital (jaise Rao Hospital ya Balaji Hospital) ke receptionist portal ya patient portal se perform hoti hain.\n\n"
                    "Platform Owner ke roop me aap:\n"
                    "* Kisi bhi hospital ka **total revenue & booking count** dekh sakte hain (e.g. *'Rao Hospital total revenue all time'*)\n"
                    "* **Active doctors & rosters** inspect kar sakte hain\n"
                    "* **Subscription plans & renewals** manage kar sakte hain\n"
                    "* **AI Telemetry & platform error logs** monitor kar sakte hain\n\n"
                    "Agar aap kisi specific hospital ke stats dekhna chahte hain, to kripya hospital ka naam batayein."
                ),
                "tool_used": "super_admin_role_boundary",
                "tool_result": {"status": "ROLE_RESTRICTED", "role": "SUPER_ADMIN"},
                "suggestions": suggestions
            }

        if is_booking_trigger or is_in_booking_flow:
            if any(w in msg_lower for w in ["cancel", "nahi chahiye", "rehne do", "stop", "abort"]):
                if context_state:
                    context_state.booking_in_progress = False
                return {"reply": "❌ Appointment booking has been cancelled.", "tool_used": "book_appointment", "tool_result": {"cancelled": True}}

            # Extract time slot if provided (supports 3:45, 3;45, 3.45, 3;20, 10:00 AM, 5 baje)
            parsed_time = entity_extractor._parse_time(norm_msg)
            if parsed_time and context_state:
                context_state.selected_time = parsed_time
            if target_date and context_state:
                context_state.selected_date = target_date

            # Fetch active doctors in hospital
            active_docs = []
            if db and hospital_id:
                from app.database.models.appointment import Doctor, Department
                d_stmt = select(Doctor, Department).join(Department, Doctor.department_id == Department.id).where(
                    Doctor.hospital_id == hospital_id,
                    Doctor.is_active == True
                )
                active_docs = (await db.execute(d_stmt)).all()

            # Check if user mentioned a doctor's name or department
            matched_doc = None
            matched_dept = None
            has_doc_intent = any(w in msg_lower for w in ["dr", "doctor", "change", "badal", "dusre", "dusra", "switch"])
            already_has_doc = bool(context_state and context_state.current_doctor_name)
            can_switch_doc = not already_has_doc or has_doc_intent

            if can_switch_doc:
                for d, dept in active_docs:
                    full_n = f"{d.first_name} {d.last_name}".lower()
                    fname = d.first_name.lower()
                    lname = d.last_name.lower()
                    
                    full_match = full_n in msg_lower
                    fname_match = bool(re.search(rf"\b{re.escape(fname)}\b", msg_lower))
                    lname_match = bool(re.search(rf"\b(?:dr\.?|doctor)\s+{re.escape(lname)}\b", msg_lower))
                    dept_match = bool(re.search(rf"\b{re.escape(dept.name.lower())}\b", msg_lower))

                    if full_match or fname_match or lname_match or dept_match:
                        matched_doc = d
                        matched_dept = dept
                        break

            if matched_doc and context_state:
                context_state.current_doctor_name = f"Dr. {matched_doc.first_name} {matched_doc.last_name}"
                context_state.current_doctor_id = matched_doc.id
                context_state.department = matched_dept.name

            # Auto-fill patient details and STRICTLY LOCK PHONE if role is PATIENT
            if role_upper == "PATIENT" and actor_profile and context_state:
                acc_phone = actor_profile.get("patient_phone")
                acc_name = actor_profile.get("patient_name")
                if acc_phone:
                    context_state.patient_phone = acc_phone
                if not context_state.patient_name and acc_name:
                    context_state.patient_name = acc_name

            # Check for phone number (Only allowed for guests/staff, NOT allowed to change logged-in patient's account phone)
            phone_match = re.search(r'\b([6-9]\d{9})\b', norm_msg)
            if phone_match and context_state:
                if not (role_upper == "PATIENT" and actor_profile and actor_profile.get("patient_phone")):
                    context_state.patient_phone = phone_match.group(1)

            # Check for patient name modification or direct entry
            pat_mod_match = re.search(r'\b(?:naam|name|patient)\s*(?:change\s*karke|badal\s*ke|change\s*to|is|hai|karo|kar\s*do|to)?\s*[:\-]?\s*([a-zA-Z\s]{2,30})', norm_msg, re.IGNORECASE)
            if pat_mod_match and context_state:
                cand_raw = pat_mod_match.group(1).strip()
                p_extracted = entity_extractor._parse_patient_name(f"patient {cand_raw}")
                if p_extracted:
                    context_state.patient_name = p_extracted
                elif cand_raw and not any(w.lower() in ["change", "badal", "karo", "kar", "do", "hai", "is", "for", "to", "doctor", "appointment", "time", "date", "slot"] for w in cand_raw.split()):
                    if len(cand_raw) >= 2:
                        context_state.patient_name = cand_raw.title()
            elif is_in_booking_flow and context_state and not context_state.patient_name:
                candidate = norm_msg
                if phone_match:
                    candidate = candidate.replace(phone_match.group(1), "")
                candidate = re.sub(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|baje)\b', '', candidate, flags=re.IGNORECASE)
                candidate = re.sub(r'\b(?:book|booking|appointment|karo|kar|do|chahiye|please|plz|for|mera|meri|naam|hai|patient|slot|confirm|haan|yes)\b', '', candidate, flags=re.IGNORECASE)
                candidate = re.sub(r'[^a-zA-Z\s]', ' ', candidate).strip()
                candidate = re.sub(r'\s+', ' ', candidate)
                if 2 <= len(candidate) <= 35:
                    words = candidate.split()
                    if not any(w.lower() in ["cancel", "stop", "no", "nahi", "exit", "help"] for w in words):
                        p_cand = entity_extractor._parse_patient_name(f"patient {candidate}")
                        if p_cand:
                            context_state.patient_name = p_cand
                        elif len(candidate) >= 2:
                            context_state.patient_name = candidate.title()

            cur_doc = context_state.current_doctor_name if context_state else None
            cur_time = (context_state.selected_time if context_state else None) or "10:00 AM"
            cur_date = (context_state.selected_date if context_state else None) or target_date
            cur_pname = context_state.patient_name if context_state else None
            cur_phone = context_state.patient_phone if context_state else None

            # CASE 1: Doctor name is NOT known yet -> Ask user for doctor
            if not cur_doc:
                if context_state:
                    context_state.booking_in_progress = True
                    context_state.dialog_state = "AWAITING_DOCTOR"
                doc_lines = []
                for d, dept in active_docs:
                    fee = d.opd_fees or 500
                    doc_lines.append(f"* **Dr. {d.first_name} {d.last_name}** ({dept.name}) — Fee: ₹{fee}")
                doc_list_text = "\n".join(doc_lines) if doc_lines else "* Contact reception for active doctor schedules."

                time_note = f" for **{cur_date}** at **{cur_time}**" if parsed_time else f" for **{cur_date}**"
                reply = (
                    f"### 🗓️ New Appointment Booking\n\n"
                    f"I can help you schedule an appointment{time_note}! 🏥\n\n"
                    f"**Which doctor would you like to consult?**\n\n"
                    f"{doc_list_text}\n\n"
                    f"> 💬 *Reply with the Doctor's name or Specialization.*"
                )
                return {"reply": reply, "tool_used": "book_appointment", "tool_result": {"status": "AWAITING_DOCTOR"}}

            # CASE 2: Doctor is known, but Patient Name or Phone is missing (Only for guests where details are genuinely unknown)
            if not cur_pname or not cur_phone:
                if context_state:
                    context_state.booking_in_progress = True
                    context_state.dialog_state = "AWAITING_PATIENT_DETAILS"
                fee_val = 500
                for d, dept in active_docs:
                    if d.id == (context_state.current_doctor_id if context_state else None) or (d.first_name.lower() in cur_doc.lower()):
                        fee_val = d.opd_fees or 500
                        break

                if cur_pname and not cur_phone:
                    reply = (
                        f"### 🗓️ Booking with {cur_doc}\n\n"
                        f"* **Patient Name:** **{cur_pname}**\n"
                        f"* **Department:** {getattr(context_state, 'department', 'OPD')}\n"
                        f"* **Date & Time:** **{cur_date}** at **{cur_time}**\n"
                        f"* **Consultation Fee:** ₹{fee_val}\n\n"
                        f"Please provide the **10-digit Mobile Number** for **{cur_pname}** to proceed.\n\n"
                        f"> *Example: '9876543210'*"
                    )
                elif cur_phone and not cur_pname:
                    reply = (
                        f"### 🗓️ Booking with {cur_doc}\n\n"
                        f"* **Mobile:** **{cur_phone}**\n"
                        f"* **Department:** {getattr(context_state, 'department', 'OPD')}\n"
                        f"* **Date & Time:** **{cur_date}** at **{cur_time}**\n"
                        f"* **Consultation Fee:** ₹{fee_val}\n\n"
                        f"Please provide the **Patient's Full Name** to proceed.\n\n"
                        f"> *Example: 'Rahul Sharma'*"
                    )
                else:
                    reply = (
                        f"### 🗓️ Booking with {cur_doc}\n\n"
                        f"* **Department:** {getattr(context_state, 'department', 'OPD')}\n"
                        f"* **Date & Time:** **{cur_date}** at **{cur_time}**\n"
                        f"* **Consultation Fee:** ₹{fee_val}\n\n"
                        f"Please provide the **Patient's Full Name** and **10-digit Mobile Number** to proceed.\n\n"
                        f"> *Example: 'Patient Rahul Sharma, 9876543210'*"
                    )
                return {"reply": reply, "tool_used": "book_appointment", "tool_result": {"status": "AWAITING_PATIENT_DETAILS"}}

            # CASE 3: All details are available -> Stage or Update confirmation
            fee_val = 500
            for d, dept in active_docs:
                if d.id == (context_state.current_doctor_id if context_state else None) or (d.first_name.lower() in cur_doc.lower()):
                    fee_val = d.opd_fees or 500
                    break

            conf_tok = conversation_memory.create_confirmation_token(
                hospital_id=hospital_id or "GLOBAL",
                user_id=user_id or "ANONYMOUS",
                action_name="book_appointment",
                action_args={
                    "doctor_name_or_dept": cur_doc,
                    "date_str": cur_date,
                    "time_slot": cur_time,
                    "patient_name": cur_pname,
                    "phone": cur_phone,
                    "reason": "OPD Consultation"
                },
                summary=f"Book appointment for {cur_pname} with {cur_doc} on {cur_date} at {cur_time}"
            )
            if context_state:
                context_state.booking_in_progress = False

            card_title = "📋 Updated Appointment Booking Details" if is_modification_request else "📋 Confirm Appointment Booking Details"
            phone_note = f"\n> 🔒 *Note: Mobile number ({cur_phone}) is permanently linked to your patient account.*" if (role_upper == "PATIENT" and actor_profile and actor_profile.get("patient_phone")) else ""

            reply = (
                f"### {card_title}\n\n"
                f"Please verify the details below before generating the token:\n\n"
                f"* **Doctor:** **{cur_doc}** ({getattr(context_state, 'department', 'OPD')})\n"
                f"* **Date & Time:** **{cur_date}** at **{cur_time}**\n"
                f"* **Patient:** **{cur_pname}** (📱 {cur_phone})\n"
                f"* **OPD Fee:** ₹{fee_val}\n\n"
                f"> 💬 Reply **\"confirm\"** or **\"haan\"** to confirm and issue the OPD Token.{phone_note}"
            )
            return {"reply": reply, "tool_used": "book_appointment", "tool_result": {"status": "CONFIRMATION_REQUIRED", "confirmation_token": conf_tok.token}}

        # 1C. Doctor-wise Booking Performance & Analytics Matcher
        if any(w in msg_lower for w in [
            "booking performance", "doctor-wise", "doctor wise", "performance report",
            "booking stats", "doctor performance", "doctor ranking", "doctors performance",
            "doctor wise booking", "doctor wise performance"
        ]):
            t_range = "all"
            if any(w in msg_lower for w in ["today", "aaj"]):
                t_range = "today"
            elif any(w in msg_lower for w in ["yesterday", "kal"]):
                t_range = "yesterday"
            elif any(w in msg_lower for w in ["month", "mahine", "is mahine"]):
                t_range = "this_month"
            elif any(w in msg_lower for w in ["week", "hafte"]):
                t_range = "this_week"
            res = await CopilotTools.get_all_doctors_performance(hospital_id=hospital_id or "", time_range=t_range, db=db)
            return {
                "reply": cls._format_markdown_fallback("get_all_doctors_performance", res),
                "tool_used": "get_all_doctors_performance",
                "tool_result": res,
                "suggestions": [
                    "What is our total OPD revenue for this month?",
                    "Which doctors are on duty today?",
                    "Show live OPD queue summary"
                ]
            }

        # 1C-2. Specific Doctor Metrics & Performance Matcher (Bookings, Revenue, Completed, Cancelled)
        doc_metric_match = re.search(r'\b(?:dr\.?|doctor)\s+([a-zA-Z]+)', msg_lower)
        target_doc_cand = doc_metric_match.group(1) if doc_metric_match else None
        if not target_doc_cand:
            for d_token in ["vivek", "nitin", "shiva", "dewedi", "pransh", "agni", "mishra"]:
                if d_token in msg_lower:
                    target_doc_cand = d_token
                    break

        if target_doc_cand and any(w in msg_lower for w in ["performance", "metrics", "stats", "load", "booking count", "total bookings", "kitne booking", "kitne appointment", "total appointment", "revenue", "kamai", "collection", "earning", "earnings"]):
            t_range = "all"
            if any(w in msg_lower for w in ["today", "aaj"]):
                t_range = "today"
            elif any(w in msg_lower for w in ["yesterday", "kal"]):
                t_range = "yesterday"
            elif any(w in msg_lower for w in ["month", "mahine", "is mahine"]):
                t_range = "this_month"
            elif any(w in msg_lower for w in ["week", "hafte"]):
                t_range = "this_week"

            res = await CopilotTools.get_doctor_metrics(
                hospital_id=hospital_id or "",
                doctor_name=target_doc_cand,
                metric="all",
                time_range=t_range,
                db=db
            )
            if not res.get("error"):
                return {
                    "reply": cls._format_markdown_fallback("get_doctor_metrics", res),
                    "tool_used": "get_doctor_metrics",
                    "tool_result": res,
                    "suggestions": [
                        "Show doctor-wise booking performance",
                        f"Check Dr. {target_doc_cand.title()} shift timings",
                        "What is our total OPD revenue for this month?"
                    ]
                }

        # 1D. All Doctor Shift Timings and OPD Fees Matcher
        if any(w in msg_lower for w in ["shift timings and opd fees", "all doctor shift timings", "doctor shift timings", "timings and opd fees", "shift timings and fees", "show all doctor"]):
            res = await CopilotTools.get_comprehensive_doctor_analytics(hospital_id=hospital_id or "", time_range="all", db=db)
            return {"reply": cls._format_markdown_fallback("get_comprehensive_doctor_analytics", res), "tool_used": "get_comprehensive_doctor_analytics", "tool_result": res}

        # 1E. Hospital Admin Subscription & License Validity Matcher (Tenant Admin checking their own expiry)
        if hospital_id and role_upper not in ["SUPER_ADMIN", "SUPERADMIN"] and any(w in msg_lower for w in [
            "subscription validity", "subscription expiry", "plan validity", "license validity", 
            "plan status", "days remaining", "kab expire", "expiry date", "plan kab khatam", "when does plan expire"
        ]):
            res = await CopilotTools.get_hospital_subscription_info(hospital_id=hospital_id, db=db)
            return {"reply": cls._format_markdown_fallback("get_hospital_subscription_info", res), "tool_used": "get_hospital_subscription_info", "tool_result": res}

        # 2. SuperAdmin Platform Control Tower & Subscriptions
        if role_upper in ["SUPER_ADMIN", "SUPERADMIN"]:
            # Platform Monthly Revenue / SaaS Collections / MRR Overview
            if any(w in msg_lower for w in [
                "platform monthly revenue", "monthly revenue overview", "platform revenue",
                "saas revenue", "platform collections", "subscription revenue", "mrr",
                "total platform revenue", "revenue overview"
            ]) or ("platform" in msg_lower and "revenue" in msg_lower) or ("revenue" in msg_lower and any(w in msg_lower for w in ["monthly", "subscription", "saas", "collection", "collections"])):
                res = await CopilotTools.get_platform_control_tower_overview(db=db)
                total_saas_rev = res.get("total_platform_saas_revenue_formatted", "₹0")
                total_hosp = res.get("total_active_hospitals", 0)
                fleet = res.get("hospitals_fleet", [])
                total_calls = res.get("total_platform_voice_calls", 0)

                rev_lines = [
                    f"### 🌐 Platform SaaS Revenue Overview\n",
                    f"* **Total Platform SaaS Revenue:** **{total_saas_rev}** (Razorpay Live Collections)",
                    f"* **Active Onboarded Hospitals:** **{total_hosp}**",
                    f"* **Total AI Voice Calls Processed:** **{total_calls}**\n",
                    "**Tenant Hospital SaaS Breakdown:**",
                    "| Hospital | Plan | SaaS Revenue | Doctors | Bookings | Days Left | Status |",
                    "|---|---|---|---|---|---|---|"
                ]
                for h in fleet:
                    rev_lines.append(f"| {h.get('hospital_name')} | {h.get('subscription_plan')} | {h.get('saas_revenue_formatted', '₹0')} | {h.get('active_doctors')} | {h.get('total_appointments')} | {h.get('days_remaining', 'N/A')} | {h.get('status')} |")

                reply = "\n".join(rev_lines)
                suggestions = [
                    "Which subscriptions are expiring in next 30 days?",
                    "Total AI voice calls processed today",
                    "Which hospital generates maximum revenue?",
                    "Show all active hospital tenants"
                ]
                return {
                    "reply": reply,
                    "tool_used": "get_platform_control_tower_overview",
                    "tool_result": res,
                    "suggestions": suggestions
                }

            if re.search(r'\b(active hospitals?|hospitals? (are )?active|how many hospitals?|hospital count|number of hospitals?|kitne hospitals?)\b', msg_lower):
                res = await CopilotTools.get_platform_control_tower_overview(db=db)
                fleet = res.get("hospitals_fleet", [])
                total = res.get("total_active_hospitals", len(fleet))
                h_list = "\n".join([f"{i}. **{h.get('hospital_name')}** (Plan: {h.get('subscription_plan')}, Doctors: {h.get('active_doctors')})" for i, h in enumerate(fleet, 1)])
                reply = f"There are currently **{total} active hospitals** on the AURA platform:\n\n{h_list}"
                suggestions = [
                    "Which hospital generates maximum revenue?",
                    "Which subscriptions are expiring in next 30 days?",
                    "Total AI voice calls processed today"
                ]
                return {"reply": reply, "tool_used": "get_platform_control_tower_overview", "tool_result": res, "suggestions": suggestions}

            if any(w in msg_lower for w in ["expiring", "subscription expiring", "renew", "renewal", "30 days", "expire"]):
                res = await CopilotTools.get_platform_control_tower_overview(db=db)
                exp_list = res.get("expiring_hospitals", [])
                if exp_list:
                    exp_items = "\n".join([
                        f"* **{h.get('hospital_name')}** (Plan: `{h.get('plan')}`) — **{h.get('days_left')} days left** (Expires on `{h.get('expires_at')}`)"
                        for h in exp_list
                    ])
                    reply = f"### ⏳ Subscriptions Expiring Soon (Next 30 Days)\n\nFound **{len(exp_list)} hospital(s)** requiring renewal:\n\n{exp_items}"
                else:
                    reply = "### ⏳ Subscriptions Expiring Status\n\n* **Expiring in Next 30 Days:** **0 hospitals**\n* All current hospitals have active subscriptions valid beyond 30 days."
                suggestions = [
                    "Show all active hospital tenants",
                    "Platform monthly revenue overview",
                    "Total AI voice calls processed today"
                ]
                return {"reply": reply, "tool_used": "get_platform_control_tower_overview", "tool_result": res, "suggestions": suggestions}

            if any(w in msg_lower for w in ["maximum revenue", "maxmimum revenue", "max revenue", "highest revenue", "top revenue", "jyada kamai", "sabse jyada", "generate maximum", "generates maximum"]):
                res = await CopilotTools.get_platform_control_tower_overview(db=db)
                top_hosp = res.get("top_revenue_hospital", "N/A")
                top_amt = res.get("top_revenue_amount", "₹0")
                total_rev = res.get("total_platform_saas_revenue_formatted", "₹0")
                fleet = res.get("hospitals_fleet", [])
                rev_breakdown = "\n".join([
                    f"* **{h.get('hospital_name')}** ({h.get('subscription_plan')}): **{h.get('saas_revenue_formatted')}** ({h.get('total_appointments')} bookings, {h.get('active_doctors')} doctors)"
                    for h in sorted(fleet, key=lambda x: x.get('saas_revenue', 0), reverse=True)
                ])
                reply = f"### 🏆 Top Revenue Generating Hospital\n\n**{top_hosp}** generates the highest platform revenue with **{top_amt}** in SaaS subscriptions.\n\n**Platform Revenue Breakdown (Total: {total_rev}):**\n{rev_breakdown}"
                suggestions = [
                    "Platform monthly revenue overview",
                    "Which subscriptions are expiring in next 30 days?",
                    "Total AI voice calls processed today"
                ]
                return {"reply": reply, "tool_used": "get_platform_control_tower_overview", "tool_result": res, "suggestions": suggestions}

            if any(w in msg_lower for w in ["voice call", "voice calls", "call logs", "calls processed", "ai calls", "calls today"]):
                res = await CopilotTools.get_platform_control_tower_overview(db=db)
                total_calls = res.get("total_platform_voice_calls", 0)
                today_calls = res.get("total_platform_voice_calls_today", 0)
                fleet = res.get("hospitals_fleet", [])

                is_today = any(w in msg_lower for w in ["today", "aaj", "current day"])
                if is_today:
                    call_breakdown = "\n".join([f"* **{h.get('hospital_name')}**: **{h.get('voice_calls_today', 0)} calls today** (All-time: {h.get('voice_calls_count', 0)})" for h in fleet])
                    reply = (
                        f"### 🎙️ Platform AI Voice Telemetry (Today)\n\n"
                        f"* **AI Voice Calls Processed Today:** **{today_calls} calls**\n"
                        f"* **Platform Lifetime Total:** **{total_calls} calls**\n\n"
                        f"**Hospital Breakdown (Today):**\n{call_breakdown}"
                    )
                else:
                    call_breakdown = "\n".join([f"* **{h.get('hospital_name')}**: **{h.get('voice_calls_count', 0)} calls** (Today: {h.get('voice_calls_today', 0)})" for h in fleet])
                    reply = (
                        f"### 🎙️ Platform AI Voice Telemetry\n\n"
                        f"* **Total AI Voice Calls Processed:** **{total_calls} calls**\n"
                        f"* **Today's Activity:** **{today_calls} calls**\n\n"
                        f"**Hospital Breakdown:**\n{call_breakdown}"
                    )

                suggestions = [
                    "Show platform error telemetry",
                    "Which subscriptions are expiring in next 30 days?",
                    "Platform monthly revenue overview",
                    "Show all active hospital tenants"
                ]
                return {
                    "reply": reply,
                    "tool_used": "get_platform_control_tower_overview",
                    "tool_result": res,
                    "suggestions": suggestions
                }

            if any(w in msg_lower for w in ["error log", "error logs", "platform errors", "system errors", "error telemetry"]):
                res = await CopilotTools.get_platform_error_telemetry(db=db)
                suggestions = [
                    "Total AI voice calls processed today",
                    "Security audit trail",
                    "Platform monthly revenue overview"
                ]
                return {"reply": cls._format_markdown_fallback("get_platform_error_telemetry", res), "tool_used": "get_platform_error_telemetry", "tool_result": res, "suggestions": suggestions}

            if any(w in msg_lower for w in ["audit trail", "audit log", "security trail", "who changed"]):
                res = await CopilotTools.get_platform_audit_trail(db=db)
                suggestions = [
                    "Show platform error telemetry",
                    "Platform monthly revenue overview",
                    "Show all active hospital tenants"
                ]
                return {"reply": cls._format_markdown_fallback("get_platform_audit_trail", res), "tool_used": "get_platform_audit_trail", "tool_result": res, "suggestions": suggestions}

            # SuperAdmin Tenant Hospital Lookup (Contact details, phone, plan, status)
            if (any(w in msg_lower for w in ["hospital", "clinic", "tenant"]) and any(w in msg_lower for w in ["number", "phone", "contact", "detail", "details", "info", "address", "kaun", "search", "find", "batao", "do", "kaha", "view"])) or ("balaji" in msg_lower) or ("hosp-" in msg_lower):
                from app.tools.control_tower_tools import ControlTowerTools
                res = await ControlTowerTools.search_platform_hospital(query=user_message, db=db)
                return {"reply": cls._format_markdown_fallback("search_platform_hospital", res), "tool_used": "search_platform_hospital", "tool_result": res}

        # 3. Doctor Personal Queries (Using Actor Profile)
        if role_upper == "DOCTOR":
            doc_id = actor_profile.get("doctor_id") if actor_profile else None
            doc_name = actor_profile.get("doctor_name") if actor_profile else None

            # 3A. Doctor Consulted Patients
            if any(w in msg_lower for w in [
                "consulted patient", "consulted patients", "total consulted", "consulted count",
                "completed consultation", "completed consultations", "completed visit", "completed visits",
                "kitne consult hue", "kitne mareez dekhe"
            ]):
                res = await CopilotTools.get_doctor_daily_earnings(hospital_id=hospital_id or "", user_id=user_id, doctor_name=doc_name, date_str=target_date, db=db)
                reply = (
                    f"### 🩺 Consulted Patients Summary ({target_date})\n\n"
                    f"* **Doctor:** {doc_name or 'Dr. CP Tiwari'}\n"
                    f"* **Total Completed / Consulted Patients:** **{res.get('completed_consultations', 0)}**\n"
                    f"* **Total Booked Patients Today:** **{res.get('total_booked', 0)}**\n"
                    f"* **Consultation Fee:** ₹{res.get('opd_fee', 500)}\n"
                    f"* **Total Earnings Today:** **{res.get('total_earned', '₹0')}**"
                )
                return {"reply": reply, "tool_used": "get_doctor_daily_earnings", "tool_result": res}

            # 3B. Next Patient's Chief Complaint & Intake
            if any(w in msg_lower for w in [
                "next patient", "chief complaint", "next patient's chief complaint",
                "agla patient", "next token", "symptoms of next patient", "intake complaint"
            ]):
                res = await CopilotTools.get_doctor_live_queue(hospital_id=hospital_id or "", doctor_name=doc_name, date_str=target_date, db=db)
                patients = res.get("patients") or res.get("waiting_queue") or []
                waiting_p = [p for p in patients if p.get("status") in ["WAITING", "SCHEDULED", "CONFIRMED"]]
                if waiting_p:
                    next_p = waiting_p[0]
                    reply = (
                        f"### 🚪 Next Patient in Queue\n\n"
                        f"* **Token Number:** #{next_p.get('token_number') or next_p.get('token', 1)}\n"
                        f"* **Patient Name:** **{next_p.get('patient_name')}** ({next_p.get('mobile', 'N/A')})\n"
                        f"* **Time Slot:** {next_p.get('time') or next_p.get('time_slot', 'N/A')}\n"
                        f"* **Chief Complaint / Symptoms:** 🩺 **{next_p.get('chief_complaint', 'General Consultation')}**\n"
                        f"* **Status:** `{next_p.get('status', 'WAITING')}`"
                    )
                else:
                    reply = f"ℹ️ There are currently **0 waiting patients** in your queue for {target_date}."
                return {"reply": reply, "tool_used": "get_doctor_live_queue", "tool_result": res}

            # 3C. Doctor Live Queue
            if any(w in msg_lower for w in [
                "my queue", "waiting in my queue", "patients are waiting in my queue",
                "patient in my queue", "patients in my queue", "how many patients",
                "mere patient", "mere appointment", "waiting room queue", "show my live queue", "show my queue"
            ]):
                res = await CopilotTools.get_doctor_live_queue(hospital_id=hospital_id or "", doctor_name=doc_name, date_str=target_date, db=db)
                return {"reply": cls._format_markdown_fallback("get_doctor_live_queue", res), "tool_used": "get_doctor_live_queue", "tool_result": res}

            # 3D. Doctor Shifts, Timings, Working Hours
            if any(w in msg_lower for w in [
                "shift timing", "shift timings", "my timing", "my timings", "my shift", "my shifts",
                "my schedule", "my working hours", "my opd timing", "tomorrow shift", "kal ki timing",
                "schedule for tomorrow", "timings for tomorrow", "shift for tomorrow", "duty timing"
            ]):
                from app.tools.doctor_tools import DoctorTools
                res = await DoctorTools.check_doctor_availability(hospital_id=hospital_id or "", doctor_id=doc_id, doctor_name=doc_name, date_str=target_date, db=db)
                return {"reply": cls._format_markdown_fallback("check_doctor_availability", res), "tool_used": "check_doctor_availability", "tool_result": res}

            # 3E. Doctor Daily / Lifetime OPD Earnings & Appointments
            if any(w in msg_lower for w in [
                "my earning", "my earnings", "meri kamai", "today earnings", "my collection", "my revenue", "opd earnings today",
                "total earning", "total earnings", "earning of all time", "earnings of all time", "total apointment", "total appointment", "apointment and total earning", "appointment and total earning"
            ]):
                t_range = "all" if any(w in msg_lower for w in ["all time", "lifetime", "total", "overall", "all"]) else ("month" if "month" in msg_lower else "today")
                res = await CopilotTools.get_doctor_daily_earnings(hospital_id=hospital_id or "", user_id=user_id, doctor_name=doc_name, date_str=target_date, time_range=t_range, db=db)
                reply = (
                    f"### 💼 Doctor Earnings & Consultations Summary ({res.get('period', target_date)})\n\n"
                    f"* **Doctor:** {res.get('doctor_name', doc_name or 'Doctor')}\n"
                    f"* **Total Completed / Consulted Patients:** **{res.get('completed_consultations', 0)}**\n"
                    f"* **Total Booked Appointments:** **{res.get('total_booked', 0)}**\n"
                    f"* **Consultation Fee:** ₹{res.get('opd_fee', 500)}\n"
                    f"* **Total Earnings ({res.get('period', target_date)}):** **{res.get('total_earned', '₹0')}**"
                )
                return {"reply": reply, "tool_used": "get_doctor_daily_earnings", "tool_result": res}

            # 3F. Doctor Apply Leave (Generate Action Token)
            if any(w in msg_lower for w in ["apply leave", "apply for leave", "chutti chahiye", "take leave", "request leave", "apply chutti"]):
                tok_rec = conversation_memory.create_confirmation_token(
                    hospital_id=hospital_id or "",
                    user_id=user_id or "",
                    action_name="apply_leave_for_doctor",
                    action_args={
                        "hospital_id": hospital_id or "",
                        "doctor_name": doc_name or "",
                        "start_date_str": target_date,
                        "end_date_str": target_date,
                        "reason": "Personal Leave"
                    },
                    summary=f"Leave application for {doc_name or 'Doctor'} on {target_date}"
                )
                token_id = tok_rec.token
                reply = (
                    f"### 📋 Leave Application Request for {doc_name or 'Doctor'}\n\n"
                    f"* **Doctor:** {doc_name or 'Current Doctor'}\n"
                    f"* **Date:** {target_date}\n"
                    f"* **Reason:** Personal Leave\n"
                    f"* **Status:** Pending Approval\n\n"
                    f"To confirm and submit this leave request, please reply:\n"
                    f"👉 `CONFIRM {token_id}` *(or simply reply **'confirm'**)*"
                )
                return {"reply": reply, "tool_used": "apply_leave_for_doctor", "tool_result": {"status": "PENDING_CONFIRMATION", "token": token_id}}

            # 3G. Leave History & Status Check
            if any(w in msg_lower for w in ["my leave history", "past leaves", "leaves list", "approved leave status", "leave status", "check my leave", "my leave status"]):
                res = await CopilotTools.get_doctor_leave_history(hospital_id=hospital_id or "", doctor_name=doc_name, user_id=user_id, db=db)
                return {"reply": cls._format_markdown_fallback("get_doctor_leave_history", res), "tool_used": "get_doctor_leave_history", "tool_result": res}

        # 4. Comprehensive Doctor Weekly Schedules, Working Days & Department Matrix
        if any(w in msg_lower for w in [
            "which department", "which departments", "departments exist", "department doctors", "department doctor",
            "schedule of this week", "weekly schedule", "working days", "total working days", "working day",
            "doctor schedule", "doctor schedules", "doctor working days", "working days if all doctor", "working days of all doctor"
        ]):
            res = await CopilotTools.get_comprehensive_doctor_analytics(hospital_id=hospital_id or "", time_range="week", db=db)
            return {"reply": cls._format_markdown_fallback("get_comprehensive_doctor_analytics", res), "tool_used": "get_comprehensive_doctor_analytics", "tool_result": res}

        # Partial or general Department / Specialization lookup (e.g. "in our hospital which type of", "types of doctor")
        if any(w in msg_lower for w in [
            "which type", "which types", "types of", "types of doctor", "type of doctor", "types of doctors", "type of doctors",
            "specialization", "specializations", "speciality", "specialities", "hospital departments"
        ]):
            res = await CopilotTools.get_hospital_department_directory(hospital_id=hospital_id or "", db=db)
            return {"reply": cls._format_markdown_fallback("get_hospital_department_directory", res), "tool_used": "get_hospital_department_directory", "tool_result": res}

        # 5. Comparative & Analytical Leaderboards (Busiest Doctor, Highest Appointments, Most Bookings)
        if any(w in msg_lower for w in [
            "more appointment", "more appointments", "most appointment", "most appointments",
            "busiest doctor", "busy doctor", "highest appointment", "highest appointments",
            "max appointment", "maximum appointment", "sabse jyada patient", "sabse jyada appointment",
            "kiske jyada", "kiske sabse jyada", "kiska crowd", "bhid kiske", "top doctor",
            "which doctor has more", "which doctor have more", "who has more appointment", "who has more appointments"
        ]):
            from app.tools.admin_tools import AdminTools
            res = await AdminTools.get_all_opd_queues(hospital_id=hospital_id or "", date_str=target_date, db=db)
            doctors = res.get("doctors_breakdown", [])
            total_b = res.get("total_booked", 0)
            if doctors:
                sorted_docs = sorted(doctors, key=lambda d: d.get("booked_count", 0), reverse=True)
                top_doc = sorted_docs[0]
                if top_doc.get("booked_count", 0) > 0:
                    leader_msg = f"🏆 **{top_doc.get('doctor_name')}** ({top_doc.get('department')}) currently has the highest number of appointments today with **{top_doc.get('booked_count')} booked patients**."
                else:
                    leader_msg = f"ℹ️ All doctors currently have **0 active bookings** for today ({target_date})."
                
                doc_lines = "\n".join([f"* **{d.get('doctor_name')}** ({d.get('department')}): **{d.get('booked_count')} booked** (Completed: {d.get('completed_count')}, Waiting: {d.get('waiting_count')})" for d in sorted_docs])
                reply = f"### 📊 Doctor Appointment Leaderboard ({target_date})\n\n{leader_msg}\n\n**Doctor Breakdown:**\n{doc_lines}\n\n* **Total OPD Bookings:** {total_b}"
                return {"reply": reply, "tool_used": "get_all_opd_queues", "tool_result": res}
            else:
                reply = f"### 📊 Doctor Appointment Leaderboard ({target_date})\n\nNo doctors or appointments found for {target_date}."
                return {"reply": reply, "tool_used": "get_all_opd_queues", "tool_result": res}

        # 6. General On-Duty & Available Doctors Roster
        is_general_roster_query = any(w in msg_lower for w in [
            "which doctor", "which doctors", "who is on duty", "who is available",
            "doctors on duty", "doctors are on duty", "doctors are tomorrow", "doctors are today", "doctors tomorrow", "doctors today",
            "kon kon doctor", "kaun doctor", "aaj kaun hai", "kal kaun hai", "doctor list today", "doctor list tomorrow", "available tomorrow", "available today"
        ])
        if is_general_roster_query:
            res = await CopilotTools.get_available_doctors_for_day(hospital_id=hospital_id or "", date_str=target_date, db=db)
            return {"reply": cls._format_markdown_fallback("get_available_doctors_for_day", res), "tool_used": "get_available_doctors_for_day", "tool_result": res}

        # 7. Total Appointments (All-Time & Date Scoped)
        if any(w in msg_lower for w in [
            "total appointment", "total appointments", "all time appointment", "all time appointments",
            "appointments of all time", "total bookings", "how many appointments of all time", "kitne total appointment",
            "appointment booked all time", "appointments booked all time", "total appointment booked", "total appointments booked"
        ]):
            t_range = "all" if any(w in msg_lower for w in ["all time", "lifetime", "total all", "overall", "all"]) else ("today" if any(w in msg_lower for w in ["today", "aaj"]) else "all")
            res = await CopilotTools.get_appointment_status_summary(
                hospital_id=hospital_id or "",
                doctor_name=None,
                status=None,
                time_range=t_range,
                date_str=target_date if any(w in msg_lower for w in ["today", "aaj"]) else None,
                db=db
            )
            return {
                "reply": cls._format_markdown_fallback("get_appointment_status_summary", res),
                "tool_used": "get_appointment_status_summary",
                "tool_result": res,
                "suggestions": [
                    "Show doctor-wise booking performance",
                    "What is our total OPD revenue for this month?",
                    "Which doctors are on duty today?"
                ]
            }

        # 7B. Universal Appointment Status Metrics (Cancelled, Missed, Completed, Scheduled)
        is_status_query = (
            any(w in msg_lower for w in ["cancelled", "canceled", "cancled", "canceld", "missed", "no-show", "no show", "noshow", "complete", "completed", "consulted"]) and
            any(w in msg_lower for w in ["appointment", "appointments", "booking", "bookings", "visit", "visits", "patient", "patients", "how many", "total", "count", "kitne", "batao", "list"])
        ) or any(w in msg_lower for w in [
            "missed bookings", "cancelled bookings", "complete bookings", "completed bookings",
            "missed appointments", "cancelled appointments", "completed appointments", "cancelled today",
            "missed today", "completed today"
        ])
        
        if is_status_query:
            # 1. Doctor fuzzy extraction
            doc_candidate = None
            doc_match = re.search(r'\b(dr\.?|de|doctor)\s+([a-zA-Z]+)', msg_lower)
            if doc_match:
                doc_candidate = doc_match.group(2)
            else:
                for d_token in ["vivek", "nitin", "shiva", "dewedi", "pransh", "agni", "mishra"]:
                    if d_token in msg_lower:
                        doc_candidate = d_token
                        break
            
            # 2. Time range
            t_range = "today"
            if any(w in msg_lower for w in ["yesterday", "kal", "beeta"]):
                t_range = "yesterday"
            elif any(w in msg_lower for w in ["month", "mahine", "is mahine"]):
                t_range = "this_month"
            elif any(w in msg_lower for w in ["week", "hafte"]):
                t_range = "this_week"
            elif any(w in msg_lower for w in ["all time", "lifetime", "total all", "overall"]):
                t_range = "all"

            # 3. Status filter
            st_filter = None
            has_cancel = any(w in msg_lower for w in ["cancel", "canceled", "cancelled", "cancled"])
            has_miss = any(w in msg_lower for w in ["miss", "missed", "no-show", "no show"])
            has_comp = any(w in msg_lower for w in ["complete", "completed", "consulted"])

            # If user explicitly asked for one status only
            if has_cancel and not (has_miss or has_comp):
                st_filter = "CANCELLED"
            elif has_miss and not (has_cancel or has_comp):
                st_filter = "MISSED"
            elif has_comp and not (has_cancel or has_miss):
                st_filter = "COMPLETED"

            res = await CopilotTools.get_appointment_status_summary(
                hospital_id=hospital_id or "",
                doctor_name=doc_candidate,
                status=st_filter,
                time_range=t_range,
                date_str=target_date if any(w in msg_lower for w in ["today", "aaj"]) else None,
                db=db
            )

            suggestions = [
                "What is our total OPD revenue for this month?",
                "Which doctors are on duty today?",
                "Show live OPD queue summary"
            ]
            if doc_candidate:
                doc_clean = res.get("doctor_name") or f"Dr. {doc_candidate.title()}"
                suggestions.insert(0, f"Check {doc_clean} shift timings")

            return {
                "reply": cls._format_markdown_fallback("get_appointment_status_summary", res),
                "tool_used": "get_appointment_status_summary",
                "tool_result": res,
                "suggestions": suggestions[:3]
            }

        # 8. Revenue, Payments & Dues (All-Time, Monthly, Daily)
        if any(w in msg_lower for w in ["revenue", "paisa", "rupaye", "money", "collected", "collection", "dues", "kamai", "paid", "unpaid", "pending collection"]):
            t_range = "all" if any(w in msg_lower for w in ["all time", "lifetime", "total", "overall", "all"]) else ("month" if any(w in msg_lower for w in ["month", "mahine", "is mahine"]) else "today")

            # Resolve target hospital if specified or if in SuperAdmin context
            resolved_hosp = None
            effective_hospital_id = hospital_id or ""
            effective_hospital_name = (actor_profile.get("hospital_name") if actor_profile else None) or "Hospital"
            if db:
                resolved_hosp = await cls._resolve_target_hospital(user_message, db)
                if resolved_hosp:
                    effective_hospital_id = resolved_hosp["id"]
                    effective_hospital_name = resolved_hosp["name"]

            # Check if user is asking for a specific doctor's revenue
            doc_candidate = None
            doc_match = re.search(r'\b(?:dr\.?|doctor)\s+([a-zA-Z]+)', msg_lower)
            if doc_match:
                doc_candidate = doc_match.group(1)
            else:
                for d_token in ["vivek", "nitin", "shiva", "dewedi", "pransh", "agni", "mishra"]:
                    if d_token in msg_lower:
                        doc_candidate = d_token
                        break

            if doc_candidate:
                res = await CopilotTools.get_doctor_metrics(
                    hospital_id=effective_hospital_id,
                    doctor_name=doc_candidate,
                    metric="revenue",
                    time_range=t_range,
                    db=db
                )
                if not res.get("error"):
                    return {
                        "reply": cls._format_markdown_fallback("get_doctor_metrics", res),
                        "tool_used": "get_doctor_metrics",
                        "tool_result": res,
                        "suggestions": [
                            "Show doctor-wise booking performance",
                            f"Check Dr. {doc_candidate.title()} shift timings",
                            "What is our total OPD revenue for this month?"
                        ]
                    }

            res = await CopilotTools.get_revenue_and_dues(hospital_id=effective_hospital_id, time_range=t_range, role=role, db=db)
            prefix = f"{effective_hospital_name} — " if (resolved_hosp or (effective_hospital_name and effective_hospital_name not in ['Hospital', 'Platform', 'AURA Hospital'])) else ""
            reply = (
                f"### 💰 {prefix}Financial & OPD Revenue Summary ({res.get('period', 'Today')})\n\n"
                f"* **Total Appointments Booked:** {res.get('total_appointments', 0)}\n"
                f"* **Total Revenue Collected (Paid):** **{res.get('total_collected_formatted', '₹0')}** ({res.get('paid_transactions', 0)} transactions)\n"
                f"* **Pending Collection / Dues:** **{res.get('pending_dues_formatted', '₹0')}** ({res.get('pending_collection_count', 0)} pending)"
            )
            return {"reply": reply, "tool_used": "get_revenue_and_dues", "tool_result": res}

        # 8. Doctor Leave / On-Duty / Sitting Status (Specific Named Doctor)
        if any(w in msg_lower for w in ["leave", "chutti", "off duty", "off-duty", "baith", "aayenge", "duty par", "available", "on duty", "on-duty", "weekly off"]):
            clean_name = re.sub(r'\b(is|dr|doctor|on|leave|today|aaj|kal|parso|chutti|hai|kya|pe|par|status|check|please|tell|me|of|the|for|batao|dikhao|off|duty|baith|baithe|baithte|rhe|rahe|ya|aur|hain?|aayenge|duty|any|all|which|who|if|approved|list|koi|sare|sab|available|doctors|are)\b', '', msg_lower, flags=re.IGNORECASE)
            clean_name = re.sub(r'[^\w\s]', ' ', clean_name).strip()
            generic_words = {"any", "all", "which", "who", "if", "approved", "list", "koi", "sare", "sab", "available", "leave", "off", "duty", "doctor", "dr", "ya", "rhe", "aur", "doctors", "are"}
            
            target_doc_name = clean_name if (clean_name and clean_name not in generic_words and len(clean_name) >= 2) else (context_state.current_doctor_name if context_state else None)
            
            if target_doc_name:
                res = await CopilotTools.check_doctor_leave_status(hospital_id=hospital_id or "", doctor_name=target_doc_name, date_str=target_date, db=db)
                return {"reply": cls._format_markdown_fallback("check_doctor_leave_status", res), "tool_used": "check_doctor_leave_status", "tool_result": res}
            else:
                res = await CopilotTools.get_available_doctors_for_day(hospital_id=hospital_id or "", date_str=target_date, db=db)
                return {"reply": cls._format_markdown_fallback("get_available_doctors_for_day", res), "tool_used": "get_available_doctors_for_day", "tool_result": res}

        # 7. Queue Statistics
        if any(w in msg_lower for w in ["queue", "waiting", "kitne patient", "kitne log", "live queue", "opd summary"]):
            res = await CopilotTools.get_queue_statistics(hospital_id=hospital_id or "", date_str=target_date, db=db)
            return {"reply": cls._format_markdown_fallback("get_queue_statistics", res), "tool_used": "get_queue_statistics", "tool_result": res}

        # 8. Cash Register
        if any(w in msg_lower for w in ["cash register", "cash collection", "kitna cash", "daily cash"]):
            res = await CopilotTools.get_daily_cash_register(hospital_id=hospital_id or "", date_str=target_date, db=db)
            return {"reply": cls._format_markdown_fallback("get_daily_cash_register", res), "tool_used": "get_daily_cash_register", "tool_result": res}

        # 9. Hospital Information (Address, Phone, Timings, Emergency, Insurance)
        if any(w in msg_lower for w in ["hospital address", "hospital location", "hospital phone", "hospital contact", "hospital timing", "opd timing", "emergency service", "hospital info", "hospital details", "kahan hai", "address kya hai", "phone number"]):
            from app.tools import get_hospital_information
            res = await get_hospital_information(hospital_id=hospital_id, db=db)
            return {"reply": cls._format_markdown_fallback("get_hospital_information", res), "tool_used": "get_hospital_information", "tool_result": res}

        if any(w in msg_lower for w in ["insurance", "tpa", "cashless", "mediclaim", "insurance panel", "cashless panel"]):
            from app.tools.patient_portal_tools import PatientPortalTools
            res = await PatientPortalTools.get_insurance_tpa_panels(hospital_id=hospital_id, db=db)
            return {"reply": cls._format_markdown_fallback("get_insurance_tpa_panels", res), "tool_used": "get_insurance_tpa_panels", "tool_result": res}

        # 10. Appointment Lookup by ID or Patient's Own Appointments
        apt_match = re.search(r'\b(apt_[a-zA-Z0-9_\-]+)\b', norm_msg, re.IGNORECASE)
        target_apt_id = apt_match.group(1) if apt_match else None
        
        if target_apt_id:
            from app.database.models.appointment import Appointment
            
            stmt = select(Appointment).where(Appointment.id == target_apt_id)
            if hospital_id:
                stmt = stmt.where(Appointment.hospital_id == hospital_id)
            apt_obj = (await db.execute(stmt)).scalars().first()
            if apt_obj:
                reply = f"### 📅 Appointment Details\n\n* **ID:** `{apt_obj.id}`\n* **Patient ID:** `{apt_obj.patient_id}`\n* **Date:** {apt_obj.appointment_datetime.strftime('%Y-%m-%d')}\n* **Time:** {apt_obj.appointment_datetime.strftime('%I:%M %p')}\n* **Status:** `{apt_obj.status}`\n* **Payment:** `{apt_obj.payment_status}`"
                return {"reply": reply, "tool_used": "get_my_appointments", "tool_result": {"appointment_id": apt_obj.id, "status": apt_obj.status}}
            else:
                return {
                    "reply": f"ℹ️ Appointment `{target_apt_id}` was not found in the records. Please verify your booking ID.",
                    "tool_used": "get_my_appointments",
                    "tool_result": {"found": False, "appointment_id": target_apt_id}
                }

        if any(w in msg_lower for w in ["my appointment", "my bookings", "meri appointment", "mera appointment", "booked appointment", "appointment status"]):
            from app.tools import get_my_appointments
            res = await get_my_appointments(patient_id=user_id if role_upper == "PATIENT" else None, hospital_id=hospital_id, db=db)
            return {"reply": cls._format_markdown_fallback("get_my_appointments", res), "tool_used": "get_my_appointments", "tool_result": res}

        # 11. Doctor Search by Speciality or Department (with strict word boundaries)
        dept_keywords = {
            r"\bcardio\b": "Cardiology",
            r"\bcardiology\b": "Cardiology",
            r"\bheart\b": "Cardiology",
            r"\bortho\b": "Orthopedics",
            r"\borthopedics\b": "Orthopedics",
            r"\bbone\b": "Orthopedics",
            r"\bgynae\b": "Gynecology",
            r"\bgynecology\b": "Gynecology",
            r"\bderma\b": "Dermatology",
            r"\bdermatology\b": "Dermatology",
            r"\bskin\b": "Dermatology",
            r"\bneuro\b": "Neurology",
            r"\bneurology\b": "Neurology",
            r"\bpedia\b": "Pediatrics",
            r"\bpediatrics\b": "Pediatrics",
            r"\bchild\b": "Pediatrics",
            r"\bent\b": "ENT",
            r"\bgeneral medicine\b": "General Medicine",
            r"\bdental\b": "Dentistry",
            r"\bdentist\b": "Dentistry"
        }
        matched_dept = None
        for pat, d_name in dept_keywords.items():
            if re.search(pat, msg_lower):
                matched_dept = d_name
                break

        if matched_dept or any(w in msg_lower for w in ["list of doctors", "doctor list", "show doctors", "all doctors", "find doctor", "search doctor", "doctor chahiye", "specialist"]):
            from app.tools import search_doctors
            res = await search_doctors(department=matched_dept, hospital_id=hospital_id, db=db)
            return {"reply": cls._format_markdown_fallback("search_doctors", res), "tool_used": "search_doctors", "tool_result": res}

        # 12. Prescriptions & Medications
        if any(w in msg_lower for w in ["prescription", "prescriptions", "dawai", "medicine", "rx", "parcha"]):
            from app.tools import get_my_prescriptions
            res = await get_my_prescriptions(hospital_id=hospital_id, patient_id=user_id if role_upper == "PATIENT" else None, db=db)
            return {"reply": cls._format_markdown_fallback("get_my_prescriptions", res), "tool_used": "get_my_prescriptions", "tool_result": res}

        # 13. Live Token & Wait Time
        if any(w in msg_lower for w in ["my token", "token position", "waiting time", "kitna time", "mera number", "kab number"]):
            from app.tools import get_my_live_token_position
            target_apt = context_state.last_appointment_id if context_state else None
            res = await get_my_live_token_position(hospital_id=hospital_id, patient_id=user_id if role_upper == "PATIENT" else None, appointment_id=target_apt, db=db)
            return {"reply": cls._format_markdown_fallback("get_my_live_token_position", res), "tool_used": "get_my_live_token_position", "tool_result": res}

        # 14. Available Slots
        if any(w in msg_lower for w in ["open slots", "available slots", "slots", "slot", "timings for doctor", "slot khali"]):
            from app.tools import get_available_slots
            extracted_doc = entity_extractor.extract_entities(norm_msg).doctor_name
            doc_id = context_state.current_doctor_id if context_state else None
            doc_name = extracted_doc or (context_state.current_doctor_name if context_state else None)
            if doc_id or doc_name:
                res = await get_available_slots(hospital_id=hospital_id, doctor_id=doc_id, doctor_name=doc_name, date_str=target_date, db=db)
                return {"reply": cls._format_markdown_fallback("get_available_slots", res), "tool_used": "get_available_slots", "tool_result": res}

        # 15. Medical General Knowledge & Educational Guidance (Offline Rate-Limit Shield)
        med_topics = {
            "cardiology": "Cardiology is the medical branch dedicated to diagnosing and treating heart and cardiovascular disorders.",
            "cardio": "Cardiology specializes in cardiovascular health, heart rhythm, and blood pressure management.",
            "dermatology": "Dermatology is the medical branch focused on skin, hair, and nail health, infections, and allergies.",
            "orthopedics": "Orthopedics specializes in the musculoskeletal system, including bone fractures, joint arthritis, and spine care.",
            "pediatrics": "Pediatrics manages the physical, behavioral, and medical care of infants, children, and adolescents.",
            "neurology": "Neurology focuses on the brain, spinal cord, and nervous system disorders.",
            "fever": "Common fever symptoms include elevated temperature, body ache, and chills. Please stay hydrated and consult a doctor if temperature exceeds 100°F.",
            "ecg": "An Electrocardiogram (ECG) records heart electrical activity to detect arrhythmias, blockages, or past heart attacks."
        }
        for m_term, m_desc in med_topics.items():
            if re.search(rf'\b{m_term}\b', msg_lower):
                return {
                    "reply": f"### 🩺 Medical Knowledge Overview\n\n{m_desc}\n\n> ⚠️ *Disclaimer: For personalized clinical advice and prescriptions, please consult our on-duty hospital specialist doctors.*",
                    "route": "KNOWLEDGE"
                }

        return None


copilot_engine = CopilotEngine()
