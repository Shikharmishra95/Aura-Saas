"""
AURA Hospital Directory & Entity Intelligence Engine
===================================================
Provides zero-shot, grounded natural language answers for:
- Doctor fee comparisons (highest fees, lowest fees, fee rankings, specific doctor fees)
- Department-wise doctor lookups (Cardiology, Dermatology, Orthopedics, etc.)
- Doctor profiles and weekly schedules/timings
- Hospital department overview and staff rosters

Operates 100% deterministically from MySQL database records with full multilingual
support (Hinglish, Hindi, and English) to ensure 100% uptime even when external LLMs
hit 429 rate limits or are offline.
"""

import re
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.appointment import Doctor, Department, DoctorSchedule

logger = logging.getLogger("aura.directory.intel")

DAY_MAP = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday"
}

DEPT_ALIASES = {
    "cardiology": ["cardio", "cardiology", "heart", "dil", "cardiac"],
    "dermatology": ["derma", "dermatology", "skin", "chamdi", "twacha"],
    "orthopedics": ["ortho", "orthopedics", "bone", "haddi", "joint", "joints", "fracture"],
    "gynecology": ["gynae", "gynec", "gynecology", "mahila", "woman"],
    "pediatrics": ["pedia", "pediatrics", "child", "bachha", "bachon", "kid"],
    "neurology": ["neuro", "neurology", "brain", "dimag"],
    "ent": ["ent", "ear", "nose", "throat", "kaan", "gala"],
    "ophthalmology": ["eye", "aankh", "ophthalmology"],
    "dentistry": ["dental", "dentist", "daant", "dentistry"],
    "general medicine": ["general medicine", "physician", "general", "fever", "bukhar"]
}


class HospitalDirectoryIntel:
    """
    Intelligent entity and directory analyzer for hospital staff, fees, and departments.
    """

    @classmethod
    async def get_hospital_roster(cls, hospital_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetches active doctors, departments, fees, and working days for a hospital."""
        stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(Doctor.hospital_id == hospital_id, Doctor.is_active == True)
            .order_by(Doctor.first_name.asc())
        )
        rows = (await db.execute(stmt)).all()
        if not rows:
            return []

        doc_ids = [d.id for d, _ in rows]
        sched_stmt = select(DoctorSchedule).where(DoctorSchedule.doctor_id.in_(doc_ids))
        sched_rows = (await db.execute(sched_stmt)).scalars().all()

        # Group schedules by doctor
        sched_by_doc: Dict[str, List[DoctorSchedule]] = {}
        for s in sched_rows:
            sched_by_doc.setdefault(s.doctor_id, []).append(s)

        roster = []
        for doc, dept in rows:
            doc_scheds = sched_by_doc.get(doc.id, [])
            days_set = sorted(list({s.day_of_week for s in doc_scheds}))
            day_names = [DAY_MAP.get(d, f"Day {d}") for d in days_set]
            
            timing_str = "10:00 AM - 05:00 PM"
            if doc_scheds:
                st = doc_scheds[0].start_time.strftime("%I:%M %p") if hasattr(doc_scheds[0].start_time, "strftime") else str(doc_scheds[0].start_time)
                et = doc_scheds[0].end_time.strftime("%I:%M %p") if hasattr(doc_scheds[0].end_time, "strftime") else str(doc_scheds[0].end_time)
                timing_str = f"{st} - {et}"

            roster.append({
                "id": doc.id,
                "first_name": doc.first_name.strip(),
                "last_name": doc.last_name.strip(),
                "full_name": f"Dr. {doc.first_name.strip()} {doc.last_name.strip()}".strip(),
                "department": dept.name,
                "department_id": dept.id,
                "opd_fee": doc.opd_fees or 500,
                "phone": doc.phone or "N/A",
                "email": doc.email or "N/A",
                "working_days_count": len(days_set) or 6,
                "working_days_names": ", ".join(day_names) if day_names else "Mon - Sat",
                "timing": timing_str
            })

        return roster

    @classmethod
    async def analyze_and_answer(
        cls,
        user_message: str,
        hospital_id: Optional[str],
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes user message for entity/directory/fee/schedule queries.
        Returns a structured markdown reply if recognized, or None to let other tools handle it.
        """
        if not hospital_id or not db:
            return None

        clean_text = user_message.strip().lower()
        norm_text = re.sub(r'[^\w\s]', ' ', clean_text)
        norm_text = re.sub(r'\s+', ' ', norm_text)

        # Guard: If user wants to book an appointment, let the booking flow handle it!
        booking_kw = [
            "want book", "want to book", "book for", "book appointment", "appointment book",
            "slot book", "book slot", "booking karo", "parcha banao", "nayi booking",
            "book kar do", "book kr do", "appointment schedule", "schedule appointment", "ek appointment"
        ]
        is_analytics = any(w in norm_text for w in ["performance", "report", "stats", "matrix", "analysis", "analytics"])
        if any(w in norm_text for w in booking_kw) and not is_analytics:
            return None

        fee_kw = ["fee", "fees", "charge", "charges", "rupaye", "rupee", "paisa", "paise", "cost", "rate", "daam", "mehnga", "mehngi", "sasta", "sasti", "expensive", "cheap"]
        doc_kw = ["doctor", "dctor", "doctors", "dr", "drs", "specialist", "physician", "practitioner"]
        dept_kw = ["department", "departments", "dept", "speciality", "specialization", "branch"]
        schedule_kw = ["timing", "timings", "schedule", "kab baith", "kab aate", "working day", "working days", "hours", "shift"]

        has_fee = any(w in norm_text for w in fee_kw)
        has_doc = any(w in norm_text for w in doc_kw)
        has_dept = any(w in norm_text for w in dept_kw)
        has_schedule = any(w in norm_text for w in schedule_kw)

        matched_dept_alias = None
        for canonical_dept, aliases in DEPT_ALIASES.items():
            if any(re.search(rf'\b{re.escape(a)}\b', norm_text) for a in aliases):
                matched_dept_alias = canonical_dept
                break

        if not (has_fee or has_doc or has_dept or has_schedule or matched_dept_alias):
            return None

        roster = await cls.get_hospital_roster(hospital_id=hospital_id, db=db)
        if not roster:
            return None

        mentioned_doctor = None
        for d in roster:
            fn = d["first_name"].lower()
            ln = d["last_name"].lower()
            full = f"{fn} {ln}".lower()
            if (len(fn) >= 3 and re.search(rf'\b{re.escape(fn)}\b', norm_text)) or \
               (len(ln) >= 3 and re.search(rf'\b{re.escape(ln)}\b', norm_text)) or \
               (full in norm_text):
                mentioned_doctor = d
                break

        # =========================================================================
        # 0. FREE DOCTOR / ZERO APPOINTMENTS QUERY
        # =========================================================================
        if any(w in norm_text for w in ["free", "0 appointment", "zero appointment", "0 appointments", "zero appointments", "khali doctor", "no appointment", "no appointments"]):
            from app.tools.admin_tools import AdminTools
            live_q = await AdminTools.get_all_opd_queues(hospital_id=hospital_id, date_str=None, db=db)
            breakdown = live_q.get("doctors_breakdown", [])
            free_docs = [d for d in breakdown if d.get("booked_count", 0) == 0]
            if free_docs:
                doc_lines = "\n".join([f"* **{d.get('doctor_name')}** ({d.get('department')}) — **0 booked appointments** today" for d in free_docs])
                reply = (
                    f"### 🩺 Doctors with 0 Bookings Today (Free)\n\n"
                    f"Aapke hospital me aaj following doctor(s) free hain jinka **0 appointment** hai:\n\n"
                    f"{doc_lines}\n\n"
                    f"> 💡 *Total OPD bookings today: {live_q.get('total_booked', 0)} across all doctors.*"
                )
            else:
                reply = f"ℹ️ Hospital ke sabhi active doctors ke paas aaj kam se kam 1 booked appointment hai (Total: {live_q.get('total_booked', 0)})."
            return {
                "reply": reply,
                "tool_used": "get_all_opd_queues",
                "tool_result": live_q
            }

        # =========================================================================
        # 1. FEE QUESTIONS (HIGHEST, LOWEST, SPECIFIC DOCTOR, ALL FEES)
        # =========================================================================
        if has_fee:
            is_highest = any(w in norm_text for w in [
                "sabse jyada", "sabse jada", "sabse badi", "sabse adhik", "sabse unchi", "sabse high",
                "highest", "maximum", "max", "top", "costliest", "most expensive", "mehnga", "mehngi",
                "sabse mehenga", "kiska jyada", "kiske jyada", "maxmimum", "jyada fees"
            ])
            is_lowest = any(w in norm_text for w in [
                "sabse kam", "sabse sasta", "sabse sasti", "lowest", "minimum", "min", "cheapest",
                "least", "affordable", "sasta", "sasti", "kiska kam", "kiske kam", "kam fees"
            ])

            if is_highest:
                sorted_by_fee = sorted(roster, key=lambda x: x["opd_fee"], reverse=True)
                top_doc = sorted_by_fee[0]
                rows_md = "\n".join([
                    f"| **{d['full_name']}** | {d['department']} | ₹{d['opd_fee']:,} | {d['working_days_count']} days/wk |"
                    for d in sorted_by_fee
                ])
                reply = (
                    f"### 💰 Highest Consultation Fee Doctor\n\n"
                    f"Aapke hospital me **{top_doc['full_name']}** ({top_doc['department']}) ki OPD consultation fees sabse jyada hai:\n\n"
                    f"* 🩺 **Doctor:** **{top_doc['full_name']}**\n"
                    f"* 🏥 **Department:** {top_doc['department']}\n"
                    f"* 💵 **OPD Fee:** **₹{top_doc['opd_fee']:,} per consultation**\n"
                    f"* ⏰ **Working Days:** {top_doc['working_days_names']} ({top_doc['timing']})\n\n"
                    f"#### 📊 Complete Doctor Fee Ranking (High to Low):\n"
                    f"| Doctor | Department | Consultation Fee | Working Days |\n"
                    f"|---|---|---|---|\n"
                    f"{rows_md}"
                )
                return {
                    "reply": reply,
                    "tool_used": "get_comprehensive_doctor_analytics",
                    "tool_result": {"highest_fee_doctor": top_doc, "ranking": sorted_by_fee}
                }

            if is_lowest:
                sorted_by_fee = sorted(roster, key=lambda x: x["opd_fee"])
                lowest_doc = sorted_by_fee[0]
                rows_md = "\n".join([
                    f"| **{d['full_name']}** | {d['department']} | ₹{d['opd_fee']:,} | {d['working_days_count']} days/wk |"
                    for d in sorted_by_fee
                ])
                reply = (
                    f"### 💰 Most Affordable / Lowest Fee Doctor\n\n"
                    f"Aapke hospital me **{lowest_doc['full_name']}** ({lowest_doc['department']}) ki OPD consultation fees sabse kam hai:\n\n"
                    f"* 🩺 **Doctor:** **{lowest_doc['full_name']}**\n"
                    f"* 🏥 **Department:** {lowest_doc['department']}\n"
                    f"* 💵 **OPD Fee:** **₹{lowest_doc['opd_fee']:,} per consultation**\n"
                    f"* ⏰ **Working Days:** {lowest_doc['working_days_names']} ({lowest_doc['timing']})\n\n"
                    f"#### 📊 Complete Doctor Fee Ranking (Low to High):\n"
                    f"| Doctor | Department | Consultation Fee | Working Days |\n"
                    f"|---|---|---|---|\n"
                    f"{rows_md}"
                )
                return {
                    "reply": reply,
                    "tool_used": "get_comprehensive_doctor_analytics",
                    "tool_result": {"lowest_fee_doctor": lowest_doc, "ranking": sorted_by_fee}
                }

            if mentioned_doctor:
                reply = (
                    f"### 🩺 {mentioned_doctor['full_name']} Consultation Fee\n\n"
                    f"* **Doctor:** **{mentioned_doctor['full_name']}**\n"
                    f"* **Department:** {mentioned_doctor['department']}\n"
                    f"* **OPD Fee:** **₹{mentioned_doctor['opd_fee']:,} per visit**\n"
                    f"* **Timings:** {mentioned_doctor['timing']}\n"
                    f"* **Working Days:** {mentioned_doctor['working_days_names']}"
                )
                return {
                    "reply": reply,
                    "tool_used": "get_comprehensive_doctor_analytics",
                    "tool_result": {"doctor": mentioned_doctor}
                }

            sorted_by_fee = sorted(roster, key=lambda x: x["opd_fee"], reverse=True)
            rows_md = "\n".join([
                f"| **{d['full_name']}** | {d['department']} | ₹{d['opd_fee']:,} | {d['working_days_count']} days/wk |"
                for d in sorted_by_fee
            ])
            reply = (
                f"### 💵 Hospital OPD Doctor Fee Structure\n\n"
                f"Aapke hospital ke sabhi active doctors ki OPD consultation fees:\n\n"
                f"| Doctor | Department | Consultation Fee | Working Days |\n"
                f"|---|---|---|---|\n"
                f"{rows_md}\n\n"
                f"> 💡 *Fees vary between **₹{sorted_by_fee[-1]['opd_fee']}** and **₹{sorted_by_fee[0]['opd_fee']}** depending on specialization.*"
            )
            return {
                "reply": reply,
                "tool_used": "get_comprehensive_doctor_analytics",
                "tool_result": {"fee_structure": sorted_by_fee}
            }

        # =========================================================================
        # 2. DEPARTMENT-WISE DOCTOR LOOKUP
        # =========================================================================
        if matched_dept_alias:
            dept_docs = [
                d for d in roster
                if matched_dept_alias in d["department"].lower() or any(a in d["department"].lower() for a in DEPT_ALIASES.get(matched_dept_alias, []))
            ]
            dept_title = dept_docs[0]["department"] if dept_docs else matched_dept_alias.capitalize()
            if dept_docs:
                doc_lines = "\n".join([
                    f"* **{d['full_name']}** — OPD Fee: **₹{d['opd_fee']}** | Days: {d['working_days_names']} ({d['timing']})"
                    for d in dept_docs
                ])
                reply = (
                    f"### 🩺 Doctors in {dept_title} Department\n\n"
                    f"Aapke hospital ke **{dept_title}** department me currently **{len(dept_docs)} specialist doctor(s)** available hain:\n\n"
                    f"{doc_lines}\n\n"
                    f"> 💬 *Aap kisi bhi doctor ke sath appointment book karne ke liye 'Book appointment with Dr. [Name]' bol sakte hain.*"
                )
            else:
                reply = (
                    f"### 🩺 {dept_title} Department Status\n\n"
                    f"Currently hospital me **{dept_title}** department ke liye koi active doctor assigned nahi hai.\n"
                    f"Available departments dekhne ke liye *'Show hospital departments'* poochein."
                )
            return {
                "reply": reply,
                "tool_used": "get_hospital_department_directory",
                "tool_result": {"department": dept_title, "doctors": dept_docs}
            }

        # =========================================================================
        # 3. SPECIFIC DOCTOR TIMING / SCHEDULE / DETAILS
        # =========================================================================
        if mentioned_doctor and has_schedule:
            reply = (
                f"### ⏰ Schedule & OPD Hours for {mentioned_doctor['full_name']}\n\n"
                f"* **Doctor:** **{mentioned_doctor['full_name']}**\n"
                f"* **Department:** {mentioned_doctor['department']}\n"
                f"* **OPD Fee:** ₹{mentioned_doctor['opd_fee']:,}\n"
                f"* **Working Days:** **{mentioned_doctor['working_days_names']}** ({mentioned_doctor['working_days_count']} days/week)\n"
                f"* **Shift Hours:** **{mentioned_doctor['timing']}**"
            )
            return {
                "reply": reply,
                "tool_used": "check_doctor_availability",
                "tool_result": {"doctor": mentioned_doctor}
            }

        if mentioned_doctor:
            reply = (
                f"### 🩺 Doctor Profile: {mentioned_doctor['full_name']}\n\n"
                f"* **Department:** {mentioned_doctor['department']}\n"
                f"* **OPD Consultation Fee:** ₹{mentioned_doctor['opd_fee']:,}\n"
                f"* **Working Schedule:** {mentioned_doctor['working_days_names']} ({mentioned_doctor['timing']})\n"
                f"* **Contact:** {mentioned_doctor['phone']}"
            )
            return {
                "reply": reply,
                "tool_used": "get_comprehensive_doctor_analytics",
                "tool_result": {"doctor": mentioned_doctor}
            }

        # =========================================================================
        # 4. HOSPITAL DEPARTMENTS OVERVIEW
        # =========================================================================
        if has_dept and any(w in norm_text for w in ["list", "kaun", "which", "all", "kitne", "exist", "batao", "dikhao", "kya"]):
            depts_map: Dict[str, List[str]] = {}
            for d in roster:
                depts_map.setdefault(d["department"], []).append(d["full_name"])

            dept_lines = "\n".join([
                f"* **{dept}** ({len(docs)} doctors): {', '.join(docs)}"
                for dept, docs in sorted(depts_map.items())
            ])
            reply = (
                f"### 🏥 Hospital Departments Directory\n\n"
                f"Aapke hospital me currently **{len(depts_map)} active departments** hain:\n\n"
                f"{dept_lines}"
            )
            return {
                "reply": reply,
                "tool_used": "get_hospital_department_directory",
                "tool_result": {"departments": depts_map}
            }

        # =========================================================================
        # 5. GENERAL ALL DOCTORS ROSTER
        # =========================================================================
        if has_doc and any(w in norm_text for w in ["list", "sabhi", "all", "sare", "sab", "kaun", "kon", "dikhao", "batao", "show", "kitne"]):
            rows_md = "\n".join([
                f"| **{d['full_name']}** | {d['department']} | ₹{d['opd_fee']:,} | {d['working_days_count']} days/wk |"
                for d in roster
            ])
            reply = (
                f"### 👥 Active Doctors Directory\n\n"
                f"Aapke hospital me currently **{len(roster)} active doctors** registered hain:\n\n"
                f"| Doctor | Department | OPD Fee | Working Days |\n"
                f"|---|---|---|---|\n"
                f"{rows_md}"
            )
            return {
                "reply": reply,
                "tool_used": "get_comprehensive_doctor_analytics",
                "tool_result": {"doctors": roster}
            }

        return None
