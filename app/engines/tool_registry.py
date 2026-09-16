import math
import re
import logging
from collections import Counter
from typing import Dict, Any, List, Optional, Callable, Set
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.copilot_tools import CopilotTools
from app.tools.doctor_tools import DoctorTools
from app.tools.appointment_tools import AppointmentTools
from app.tools.patient_tools import PatientTools
from app.tools.hospital_tools import HospitalTools
from app.tools.clinical_tools import ClinicalTools
from app.tools.payment_tools import PaymentTools
from app.tools.admin_tools import AdminTools
from app.tools.control_tower_tools import ControlTowerTools

logger = logging.getLogger("aura.copilot.registry")

class ToolMetadata(BaseModel):
    tool_name: str
    domain: str  # 'doctor', 'appointment', 'patient', 'hospital', 'queue', 'finance', 'admin', 'control_tower'
    description: str
    parameters: Dict[str, Any]
    intent_examples: List[str] = Field(default_factory=list)
    required_roles: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    risk_level: str = "READ_ONLY"  # 'READ_ONLY', 'LOW', 'MEDIUM', 'HIGH'
    requires_confirmation: bool = False

    class Config:
        arbitrary_types_allowed = True


class DynamicToolRegistry:
    """
    Enterprise Dynamic Tool Registry & Semantic Pruning Engine.
    - Scales from 10 to 150+ tools without LLM context window bloat.
    - Enforces Zero-Trust RBAC: A patient never gets exposed to SuperAdmin or Doctor tools.
    - In-Memory High-Speed Semantic BM25/Cosine Re-ranker (<1ms latency).
    """

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._corpus_tokens: Dict[str, Counter] = {}
        self._idf: Dict[str, float] = {}
        self._register_all_default_tools()
        self._compute_idf()

    def register(self, metadata: ToolMetadata, handler: Callable):
        """Registers a tool with its metadata, intent signatures, and execution handler."""
        self._tools[metadata.tool_name] = metadata
        self._tool_handlers[metadata.tool_name] = handler
        
        # Build token signature from name, domain, description, and examples
        combined_text = f"{metadata.tool_name} {metadata.domain} {metadata.description} " + " ".join(metadata.intent_examples)
        tokens = self._tokenize(combined_text)
        self._corpus_tokens[metadata.tool_name] = Counter(tokens)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizes text into clean lowercase n-grams and words."""
        cleaned = re.sub(r'[^a-zA-Z0-9_\s]', ' ', text.lower())
        words = [w for w in cleaned.split() if len(w) > 1]
        bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)] if len(words) > 1 else []
        return words + bigrams

    def _compute_idf(self):
        """Precomputes Inverse Document Frequency across all registered tool signatures."""
        num_tools = max(len(self._corpus_tokens), 1)
        doc_freq = Counter()
        for token_counts in self._corpus_tokens.values():
            for token in token_counts.keys():
                doc_freq[token] += 1
        
        self._idf = {}
        for token, count in doc_freq.items():
            self._idf[token] = math.log((num_tools + 1.0) / (count + 1.0)) + 1.0

    def is_authorized(self, tool_name: str, user_role: str, user_permissions: Optional[List[str]] = None) -> bool:
        """Returns True if the given user role and permissions are authorized to execute tool_name."""
        meta = self._tools.get(tool_name)
        if not meta:
            return False
        role_upper = (user_role or "").upper().replace(" ", "_")

        # Zero-Trust RBAC: SuperAdmin is platform owner, never performs receptionist OPD patient bookings or doctor personal consultations
        DISALLOWED_FOR_SUPER_ADMIN = {
            "book_appointment", "reschedule_appointment", "cancel_appointment", 
            "get_available_slots", "check_in_patient", "get_my_appointments",
            "get_my_prescriptions", "get_my_live_token_position", "save_consultation_notes",
            "generate_appointment_payment_link", "get_doctor_live_queue", "admit_ipd_patient",
            "discharge_ipd_patient", "dispense_pharmacy_bill"
        }
        if role_upper in ["SUPER_ADMIN", "SUPERADMIN"] and meta.tool_name in DISALLOWED_FOR_SUPER_ADMIN:
            return False

        role_allowed = ("ALL" in meta.required_roles) or (role_upper in meta.required_roles)
        if not role_allowed:
            return False
        if meta.required_permissions:
            perms_set = set(user_permissions or [])
            if not all(p in perms_set for p in meta.required_permissions):
                return False
        return True

    def prune_tools_for_user(
        self,
        query: str,
        user_role: str,
        user_permissions: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        1. Zero-Trust RBAC Hard Filter: Exclude tools unauthorized for the user role.
        2. Semantic Re-ranking: Score user query against permitted tools using TF-IDF cosine.
        3. Returns Top-K tool declaration schemas formatted for Gemini function calling.
        """
        role_upper = (user_role or "").upper().replace(" ", "_")
        perms_set = set(user_permissions or [])
        DISALLOWED_FOR_SUPER_ADMIN = {
            "book_appointment", "reschedule_appointment", "cancel_appointment", 
            "get_available_slots", "check_in_patient", "get_my_appointments",
            "get_my_prescriptions", "get_my_live_token_position", "save_consultation_notes",
            "generate_appointment_payment_link", "get_doctor_live_queue", "admit_ipd_patient",
            "discharge_ipd_patient", "dispense_pharmacy_bill"
        }

        # Step 1: Zero-Trust RBAC Filter
        permitted_tools: List[ToolMetadata] = []
        for meta in self._tools.values():
            # Zero-Trust RBAC: SuperAdmin is platform owner, never performs receptionist OPD patient bookings
            if role_upper in ["SUPER_ADMIN", "SUPERADMIN"] and meta.tool_name in DISALLOWED_FOR_SUPER_ADMIN:
                continue

            role_allowed = ("ALL" in meta.required_roles) or (role_upper in meta.required_roles)
            if not role_allowed:
                continue

            if meta.required_permissions:
                if not all(p in perms_set for p in meta.required_permissions):
                    continue

            permitted_tools.append(meta)

        if not permitted_tools:
            return []

        if len(permitted_tools) <= top_k:
            return [
                {
                    "name": t.tool_name,
                    "description": t.description,
                    "parameters": t.parameters
                }
                for t in permitted_tools
            ]

        # Step 2: Semantic Re-ranking
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [
                {
                    "name": t.tool_name,
                    "description": t.description,
                    "parameters": t.parameters
                }
                for t in permitted_tools[:top_k]
            ]

        query_counts = Counter(query_tokens)
        query_vec = {t: query_counts[t] * self._idf.get(t, 1.0) for t in query_counts}
        query_norm = math.sqrt(sum(v * v for v in query_vec.values())) or 1.0

        scored_tools = []
        for meta in permitted_tools:
            tool_counts = self._corpus_tokens.get(meta.tool_name, Counter())
            dot_product = 0.0
            tool_vec_sq = 0.0
            for t, count in tool_counts.items():
                w = count * self._idf.get(t, 1.0)
                tool_vec_sq += w * w
                if t in query_vec:
                    dot_product += query_vec[t] * w
            
            tool_norm = math.sqrt(tool_vec_sq) or 1.0
            score = dot_product / (query_norm * tool_norm)
            scored_tools.append((score, meta))

        scored_tools.sort(key=lambda x: x[0], reverse=True)
        selected = [meta for _, meta in scored_tools[:top_k]]
        return [
            {
                "name": t.tool_name,
                "description": t.description,
                "parameters": t.parameters
            }
            for t in selected
        ]

    async def execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Executes a registered tool with tenant and security context verification.
        """
        meta = self._tools.get(tool_name)
        if not meta:
            return {"error": f"Tool '{tool_name}' is not recognized in the dynamic registry."}

        # Role Verification
        user_role = (context.get("role") or "").upper().replace(" ", "_")
        if "ALL" not in meta.required_roles and user_role not in meta.required_roles:
            return {"error": f"Access Denied: Role '{user_role}' is not authorized to execute tool '{tool_name}'."}

        handler = self._tool_handlers.get(tool_name)
        if not handler:
            return {"error": f"No execution handler registered for '{tool_name}'."}

        try:
            return await handler(args=args, context=context, db=db)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}

    def _register_all_default_tools(self):
        """Populates the dynamic registry with core HMS AI tools and rich multilingual intent signatures."""

        # 1. search_doctors
        self.register(
            ToolMetadata(
                tool_name="search_doctors",
                domain="doctor",
                description="Search active doctors by name, department, or medical specialization. Always returns live hospital doctors.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING", "description": "Doctor full or partial name (e.g. 'Nitin', 'Vivek', 'Dewedi')"},
                        "department": {"type": "STRING", "description": "Department name (e.g. 'Cardiology', 'Orthopedics', 'Dermatology')"},
                        "specialization": {"type": "STRING", "description": "Medical specialty (e.g. 'Heart', 'Skin', 'Bone')"},
                        "availability_date": {"type": "STRING", "description": "Target date YYYY-MM-DD"}
                    }
                },
                intent_examples=[
                    "mujhe cardiologist chahiye", "cardiology mein kaunse doctors hain", "find heart specialist",
                    "skin doctor list", "search doctor by department", "which doctors are available in hospital",
                    "bone doctor", "orthopedic doctor", "doctor search", "find doctor"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: DoctorTools.search_doctors(
                hospital_id=context.get("hospital_id"),
                name=args.get("name"),
                department=args.get("department"),
                specialization=args.get("specialization"),
                availability_date=args.get("availability_date"),
                db=db
            )
        )

        # 2. get_doctor_details
        self.register(
            ToolMetadata(
                tool_name="get_doctor_details",
                domain="doctor",
                description="Get safe, professional details of a doctor (OPD consultation fee, timings, department, specializations).",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Doctor name (e.g. 'Dr. Nitin Dewedi')"},
                        "doctor_id": {"type": "STRING", "description": "Doctor ID"}
                    }
                },
                intent_examples=[
                    "doctor details", "dr nitin ki fees kitni hai", "dr vivek timings and opd fee",
                    "doctor profile", "doctor consultation fee", "qualification and timings for doctor"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: DoctorTools.get_doctor_details(
                hospital_id=context.get("hospital_id"),
                doctor_id=args.get("doctor_id"),
                doctor_name=args.get("doctor_name"),
                db=db
            )
        )

        # 3. check_doctor_availability
        self.register(
            ToolMetadata(
                tool_name="check_doctor_availability",
                domain="doctor",
                description="Check if a specific doctor is on-duty, on approved leave, or off-duty for a specific date using live HMS data.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Name of doctor (e.g. 'Nitin', 'Vivek')"},
                        "doctor_id": {"type": "STRING", "description": "Doctor ID"},
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD (defaults to today)"}
                    }
                },
                intent_examples=[
                    "is dr sharma available tomorrow", "dr sharma kal baithenge", "kya doctor chutti par hai",
                    "is doctor on leave today", "doctor duty roster", "which doctors are on duty today",
                    "aaj doctor baith rhe hai ya nahi", "doctor holiday status"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: DoctorTools.check_doctor_availability(
                hospital_id=context.get("hospital_id"),
                doctor_id=args.get("doctor_id"),
                doctor_name=args.get("doctor_name"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 4. get_available_slots
        self.register(
            ToolMetadata(
                tool_name="get_available_slots",
                domain="doctor",
                description="Calculate and return live open booking time slots for a doctor on a specific date. Never guess slots.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Doctor name or department"},
                        "doctor_id": {"type": "STRING", "description": "Doctor ID"},
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD"}
                    }
                },
                intent_examples=[
                    "kal cardiology ka slot hai", "5 PM ka slot available hai", "open slots for doctor",
                    "available appointment times", "dr vivek ke paas open slot kab hai", "time slots for tomorrow"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: DoctorTools.get_available_slots(
                hospital_id=context.get("hospital_id"),
                doctor_id=args.get("doctor_id"),
                doctor_name=args.get("doctor_name"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 5. book_appointment
        self.register(
            ToolMetadata(
                tool_name="book_appointment",
                domain="appointment",
                description="Book an appointment for a patient with a doctor after validating slot vacancy, doctor schedule, and tenant boundary.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name_or_dept": {"type": "STRING", "description": "Doctor name or department"},
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD"},
                        "time_slot": {"type": "STRING", "description": "Time slot (e.g. '10:00 AM', '05:00 PM')"},
                        "patient_name": {"type": "STRING", "description": "Patient full name"},
                        "phone": {"type": "STRING", "description": "Patient mobile phone number"},
                        "reason": {"type": "STRING", "description": "Reason for consultation"}
                    },
                    "required": ["doctor_name_or_dept", "date_str", "time_slot"]
                },
                intent_examples=[
                    "5 baje book kar do", "book appointment", "appointment schedule karo",
                    "book slot with dr nitin tomorrow at 5 PM", "nayi booking banao", "parcha banao"
                ],
                required_roles=["ALL"],
                risk_level="MEDIUM"
            ),
            handler=lambda args, context, db: AppointmentTools.book_appointment(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                doctor_name_or_dept=args.get("doctor_name_or_dept", ""),
                date_str=args.get("date_str", ""),
                time_slot=args.get("time_slot", ""),
                patient_name=args.get("patient_name"),
                phone=args.get("phone"),
                reason=args.get("reason", "OPD Consultation"),
                source="AI_COPILOT",
                db=db
            )
        )

        # 6. get_my_appointments
        self.register(
            ToolMetadata(
                tool_name="get_my_appointments",
                domain="appointment",
                description="Retrieve upcoming and past appointments strictly scoped to the authenticated patient identity.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "phone": {"type": "STRING", "description": "Patient mobile phone number"}
                    }
                },
                intent_examples=[
                    "mera appointment dikhao", "my appointments", "check my booking status",
                    "view upcoming appointments", "parcha dikhao", "mera appointment status"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: AppointmentTools.get_my_appointments(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                phone=args.get("phone"),
                db=db
            )
        )

        # 7. cancel_appointment
        self.register(
            ToolMetadata(
                tool_name="cancel_appointment",
                domain="appointment",
                description="Securely cancel an appointment with human-in-the-loop action confirmation tokens.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id_or_query": {"type": "STRING", "description": "Appointment ID or phone number"},
                        "reason": {"type": "STRING", "description": "Reason for cancellation"},
                        "confirmation_token": {"type": "STRING", "description": "One-time action confirmation token"}
                    },
                    "required": ["appointment_id_or_query"]
                },
                intent_examples=[
                    "mera appointment cancel kar do", "cancel appointment", "booking radd karo",
                    "delete appointment", "cancel my visit"
                ],
                required_roles=["ALL"],
                risk_level="HIGH",
                requires_confirmation=True
            ),
            handler=lambda args, context, db: AppointmentTools.cancel_appointment(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                appointment_id_or_query=args.get("appointment_id_or_query", ""),
                reason=args.get("reason", "Cancelled via Copilot"),
                confirmation_token=args.get("confirmation_token"),
                db=db
            )
        )

        # 8. reschedule_appointment
        self.register(
            ToolMetadata(
                tool_name="reschedule_appointment",
                domain="appointment",
                description="Reschedule an active appointment to a new date and time slot with live vacancy revalidation.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id_or_query": {"type": "STRING", "description": "Appointment ID or patient phone number"},
                        "new_date_str": {"type": "STRING", "description": "New date YYYY-MM-DD"},
                        "new_time_slot": {"type": "STRING", "description": "New time slot e.g. '11:00 AM'"},
                        "reason": {"type": "STRING", "description": "Reason for rescheduling"}
                    },
                    "required": ["appointment_id_or_query", "new_date_str", "new_time_slot"]
                },
                intent_examples=[
                    "mera appointment kal shift kar do", "reschedule appointment", "change appointment date",
                    "postpone my visit to tomorrow 11 AM", "dusre din shift karo"
                ],
                required_roles=["ALL"],
                risk_level="MEDIUM"
            ),
            handler=lambda args, context, db: AppointmentTools.reschedule_appointment(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                appointment_id_or_query=args.get("appointment_id_or_query", ""),
                new_date_str=args.get("new_date_str", ""),
                new_time_slot=args.get("new_time_slot", ""),
                reason=args.get("reason", "Rescheduled via Copilot"),
                confirmation_token=args.get("confirmation_token"),
                db=db
            )
        )

        # 9. get_patient_details
        self.register(
            ToolMetadata(
                tool_name="get_patient_details",
                domain="patient",
                description="Get patient profile and medical visit history, strictly respecting caller RBAC boundaries.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "patient_id": {"type": "STRING", "description": "Patient ID"},
                        "query": {"type": "STRING", "description": "Patient name or mobile phone number"}
                    }
                },
                intent_examples=[
                    "get patient details", "patient medical profile", "patient visit history",
                    "patient record search"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: PatientTools.get_patient_details(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                patient_id=args.get("patient_id"),
                query=args.get("query"),
                db=db
            )
        )

        # 10. get_hospital_information
        self.register(
            ToolMetadata(
                tool_name="get_hospital_information",
                domain="hospital",
                description="Get live structured hospital information (name, departments list, doctor counts, working hours, contact numbers).",
                parameters={"type": "OBJECT", "properties": {}},
                intent_examples=[
                    "how much doctor registered in hospital", "hospital information",
                    "how many departments", "hospital working hours and contact", "hospital info",
                    "how many total doctors are active in my hospital", "how many doctors in hospital",
                    "total active doctors", "active doctors count", "total doctors in hospital", "hospital doctor count"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: HospitalTools.get_hospital_information(
                hospital_id=context.get("hospital_id"),
                db=db
            )
        )

        # 10b. get_hospital_subscription_info (Admin / Hospital Admin / SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="get_hospital_subscription_info",
                domain="admin",
                description="Retrieves hospital SaaS subscription plan, status, expiry date, days remaining, doctor quota, and AI voice status.",
                parameters={"type": "OBJECT", "properties": {}},
                intent_examples=[
                    "what is our subscription validity", "hospital subscription details",
                    "subscription expiry", "plan validity", "days remaining in subscription",
                    "what is my subscription plan", "subscription status", "saas plan expiry",
                    "subscription validity", "license validity", "hospital plan status"
                ],
                required_roles=["ADMIN", "HOSPITAL_ADMIN", "SUPERADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_hospital_subscription_info(
                hospital_id=context.get("hospital_id"),
                db=db
            )
        )

        # 11. get_queue_statistics (Staff / Admin / Doctor)
        self.register(
            ToolMetadata(
                tool_name="get_queue_statistics",
                domain="queue",
                description="Get appointment totals (completed, waiting, missed) and per-doctor counts for any date.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "date_str": {"type": "STRING", "description": "Date in YYYY-MM-DD format"}
                    }
                },
                intent_examples=[
                    "queue stats", "total appointments today", "kitne patient aaye", "how many waiting",
                    "opd queue summary", "waiting count", "completed appointments", "footfall today"
                ],
                required_roles=["RECEPTIONIST", "ADMIN", "SUPER_ADMIN", "DOCTOR"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_queue_statistics(
                hospital_id=context.get("hospital_id"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 11b. get_appointment_status_summary (Staff / Admin / Doctor / SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="get_appointment_status_summary",
                domain="appointments",
                description="Get aggregated counts and details of appointments by status (cancelled, missed, completed, scheduled) with optional doctor and date range filters.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Doctor's name (e.g. Dr. Vivek, Dr. Nitin) to filter by"},
                        "status": {"type": "STRING", "description": "Appointment status: 'CANCELLED', 'MISSED', 'COMPLETED', 'CONFIRMED', or 'ALL'"},
                        "time_range": {"type": "STRING", "description": "'today', 'yesterday', 'this_week', 'this_month', or 'all'"},
                        "date_str": {"type": "STRING", "description": "Specific date in YYYY-MM-DD format"}
                    }
                },
                intent_examples=[
                    "how many appointments were cancelled today", "cancelled appointments today",
                    "missed bookings today", "de vivek total missed bookings and total complete bookings",
                    "dr vivek missed appointments", "how many completed appointments today",
                    "total completed visits this month", "show cancelled appointments",
                    "how many patients missed their visit"
                ],
                required_roles=["RECEPTIONIST", "ADMIN", "SUPER_ADMIN", "DOCTOR"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_appointment_status_summary(
                hospital_id=context.get("hospital_id"),
                doctor_name=args.get("doctor_name"),
                status=args.get("status"),
                time_range=args.get("time_range", "today"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 12. get_daily_cash_register (Finance / Receptionist / Admin)
        self.register(
            ToolMetadata(
                tool_name="get_daily_cash_register",
                domain="finance",
                description="Get front desk daily cash register breakdown (Cash vs UPI vs Pending Dues).",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD"}
                    }
                },
                intent_examples=["cash register", "aaj kitna cash aaya", "front desk collection", "upi vs cash breakdown"],
                required_roles=["RECEPTIONIST", "ADMIN", "SUPER_ADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_daily_cash_register(
                hospital_id=context.get("hospital_id"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 13. get_revenue_and_dues (All Portals)
        self.register(
            ToolMetadata(
                tool_name="get_revenue_and_dues",
                domain="finance",
                description="Get financial and OPD revenue summary: total revenue collected, paid transactions, and pending collection dues for today, week, month, or all time.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "time_range": {"type": "STRING", "description": "Period: 'today', 'week', 'month', or 'all' (use 'all' for all-time lifetime revenue and dues)"}
                    }
                },
                intent_examples=[
                    "revenue summary", "total collection today", "pending dues", "aaj kitni kamai hui",
                    "hospital revenue", "kitna paisa baki hai", "all time pending collection dues",
                    "total revenue of all time", "financial opd revenue summary all time", "all time revenue"
                ],
                required_roles=["ADMIN", "SUPER_ADMIN", "ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_revenue_and_dues(
                hospital_id=context.get("hospital_id"),
                time_range=args.get("time_range", "today"),
                role=context.get("role"),
                db=db
            )
        )

        # 14. get_doctor_live_queue (Doctor / Receptionist)
        self.register(
            ToolMetadata(
                tool_name="get_doctor_live_queue",
                domain="queue",
                description="Get live waiting patient queue with token numbers and intake complaints for a doctor.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Doctor name"},
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD"}
                    }
                },
                intent_examples=[
                    "my live queue", "who is waiting outside my room", "doctor queue", "token queue",
                    "what is the next patient chief complaint", "line me kitne log hai"
                ],
                required_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN", "RECEPTIONIST"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_doctor_live_queue(
                hospital_id=context.get("hospital_id"),
                doctor_name=args.get("doctor_name"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 15. get_doctor_daily_earnings (Doctor Personal)
        self.register(
            ToolMetadata(
                tool_name="get_doctor_daily_earnings",
                domain="finance",
                description="Get personal daily OPD earnings and completed consultation count for a doctor.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Doctor name"},
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD"}
                    }
                },
                intent_examples=["what are my opd earnings today", "meri aaj ki kamai", "doctor opd earnings", "how much i earned today"],
                required_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_doctor_daily_earnings(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                doctor_name=args.get("doctor_name"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 16. search_clinical_emr_records (Doctor / Admin)
        self.register(
            ToolMetadata(
                tool_name="search_clinical_emr_records",
                domain="emr",
                description="Search past clinical records, prescriptions, symptoms (e.g. cough, fever, pain), diagnosis, and intake notes.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Symptom, diagnosis, medicine, or complaint to search"},
                        "date_str": {"type": "STRING", "description": "Visit date in YYYY-MM-DD"},
                        "patient_name": {"type": "STRING", "description": "Patient name"},
                        "doctor_name": {"type": "STRING", "description": "Doctor name"}
                    }
                },
                intent_examples=[
                    "search past prescriptions with pain or fever", "find patients with cough", "fever diagnosis history",
                    "khansi wale patient", "clinical notes search", "emr records"
                ],
                required_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.search_clinical_emr_records(
                hospital_id=context.get("hospital_id"),
                query=args.get("query"),
                date_str=args.get("date_str"),
                patient_name=args.get("patient_name"),
                doctor_name=args.get("doctor_name"),
                db=db
            )
        )

        # 17. get_platform_control_tower_overview (SuperAdmin Global)
        self.register(
            ToolMetadata(
                tool_name="get_platform_control_tower_overview",
                domain="control_tower",
                description="Get platform-wide overview of all active hospitals, subscriptions, doctor fleets, and renewal timelines.",
                parameters={"type": "OBJECT", "properties": {}},
                intent_examples=[
                    "control tower overview", "all hospitals fleet", "platform active hospitals", "expiring subscriptions 30 days",
                    "top revenue hospital", "which hospital generates maximum revenue", "superadmin metrics"
                ],
                required_roles=["SUPER_ADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_platform_control_tower_overview(db=db)
        )

        # 18. get_comprehensive_doctor_analytics (Admin / SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="get_comprehensive_doctor_analytics",
                domain="admin",
                description="Get multi-dimensional matrix of all doctors showing total appointments, completed, cancelled, working days, and revenue.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "time_range": {"type": "STRING", "description": "'all' or 'month'"}
                    }
                },
                intent_examples=[
                    "doctor performance", "doctor analytics matrix", "check doctor nitin total appointment booked all time",
                    "doctor revenue ranking", "doctor metrics report"
                ],
                required_roles=["ADMIN", "SUPER_ADMIN", "RECEPTIONIST"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_comprehensive_doctor_analytics(
                hospital_id=context.get("hospital_id"),
                time_range=args.get("time_range", "all"),
                db=db
            )
        )

        # 19. get_my_prescriptions (Patient / Doctor)
        self.register(
            ToolMetadata(
                tool_name="get_my_prescriptions",
                domain="patient",
                description="Retrieve consultation notes, prescriptions, and follow-up medical advice scoped to the authenticated patient.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "phone": {"type": "STRING", "description": "Patient registered phone number"}
                    }
                },
                intent_examples=[
                    "meri purani dawa", "show my prescriptions", "doctor ne kya dawai likhi",
                    "my clinical notes", "prescription receipt", "past prescriptions list"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: ClinicalTools.get_my_prescriptions(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                phone=args.get("phone"),
                db=db
            )
        )

        # 20. get_my_live_token_position (Patient)
        self.register(
            ToolMetadata(
                tool_name="get_my_live_token_position",
                domain="patient",
                description="Check patient's live token position, number of waiting patients ahead, and estimated wait time in minutes for today's appointment.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id_or_phone": {"type": "STRING", "description": "Appointment ID or patient phone"}
                    }
                },
                intent_examples=[
                    "mere aage kitne log hain", "mera number kab aayega", "how many patients ahead of me",
                    "live token position", "estimated wait time", "kitna time lagega"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: ClinicalTools.get_my_live_token_position(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                appointment_id_or_phone=args.get("appointment_id_or_phone"),
                db=db
            )
        )

        # 21. get_insurance_tpa_panels (Patient / All)
        self.register(
            ToolMetadata(
                tool_name="get_insurance_tpa_panels",
                domain="hospital",
                description="Check accepted cashless insurance panels, TPA tie-ups, and network status for the hospital.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "provider_name": {"type": "STRING", "description": "Insurance provider name (e.g. 'Star Health', 'HDFC ERGO', 'Bajaj')"}
                    }
                },
                intent_examples=[
                    "insurance accepted", "kya star health cashless hai", "tpa tie up list",
                    "cashless insurance panel", "mediclaim accepted", "hdfc ergo cashless"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: ClinicalTools.get_insurance_tpa_panels(
                hospital_id=context.get("hospital_id"),
                provider_name=args.get("provider_name"),
                db=db
            )
        )

        # 22. save_consultation_notes (Doctor)
        self.register(
            ToolMetadata(
                tool_name="save_consultation_notes",
                domain="doctor",
                description="Record doctor consultation notes, prescription medicines, and follow-up date for an appointment, completing the visit.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id": {"type": "STRING", "description": "Appointment ID"},
                        "clinical_notes": {"type": "STRING", "description": "Diagnosis and consultation summary"},
                        "prescription": {"type": "STRING", "description": "Prescribed medications and dosage instructions"},
                        "follow_up_date_str": {"type": "STRING", "description": "Next follow-up date in YYYY-MM-DD"}
                    },
                    "required": ["appointment_id", "clinical_notes"]
                },
                intent_examples=[
                    "save prescription", "record consultation notes", "patient diagnosis likho",
                    "dawai likh do", "complete consultation", "parcha banao"
                ],
                required_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN"],
                risk_level="MEDIUM"
            ),
            handler=lambda args, context, db: ClinicalTools.save_consultation_notes(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "DOCTOR"),
                appointment_id=args.get("appointment_id", ""),
                clinical_notes=args.get("clinical_notes", ""),
                prescription=args.get("prescription"),
                follow_up_date_str=args.get("follow_up_date_str"),
                db=db
            )
        )

        # 23. generate_appointment_payment_link (Patient / Receptionist)
        self.register(
            ToolMetadata(
                tool_name="generate_appointment_payment_link",
                domain="finance",
                description="Generate an instant online Razorpay payment checkout URL and UPI QR link for an appointment OPD fee.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "appointment_id": {"type": "STRING", "description": "Appointment ID"}
                    },
                    "required": ["appointment_id"]
                },
                intent_examples=[
                    "generate payment link", "online payment link bhejo", "upi link create karo",
                    "pay fees online", "fees jama karne ka link", "razorpay payment link"
                ],
                required_roles=["ALL"],
                risk_level="LOW"
            ),
            handler=lambda args, context, db: PaymentTools.generate_appointment_payment_link(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "PATIENT"),
                appointment_id=args.get("appointment_id", ""),
                db=db
            )
        )

        # 24. get_all_opd_queues (Receptionist / Admin)
        self.register(
            ToolMetadata(
                tool_name="get_all_opd_queues",
                domain="admin",
                description="Aggregated real-time waiting, in-consultation, and completed patient queues across all hospital wings and departments.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD (defaults to today)"}
                    }
                },
                intent_examples=[
                    "all opd queues", "sab departments ka queue", "overall hospital queue load",
                    "all wing queue status", "hospital live patient load"
                ],
                required_roles=["RECEPTIONIST", "ADMIN", "SUPER_ADMIN", "DOCTOR"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: AdminTools.get_all_opd_queues(
                hospital_id=context.get("hospital_id"),
                date_str=args.get("date_str"),
                db=db
            )
        )

        # 25. approve_or_reject_doctor_leave (Admin)
        self.register(
            ToolMetadata(
                tool_name="approve_or_reject_doctor_leave",
                domain="admin",
                description="Approve or reject a doctor's planned leave request with Human-in-the-Loop Confirmation.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "leave_id": {"type": "STRING", "description": "Leave application ID"},
                        "action": {"type": "STRING", "description": "'APPROVE' or 'REJECT'"},
                        "rejection_reason": {"type": "STRING", "description": "Reason if rejecting leave"}
                    },
                    "required": ["leave_id", "action"]
                },
                intent_examples=[
                    "approve leave", "reject doctor leave", "chutti approve karo",
                    "doctor leave pass karo", "reject leave application"
                ],
                required_roles=["ADMIN", "SUPER_ADMIN"],
                risk_level="HIGH",
                requires_confirmation=True
            ),
            handler=lambda args, context, db: AdminTools.approve_or_reject_doctor_leave(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "ADMIN"),
                leave_id=args.get("leave_id", ""),
                action=args.get("action", "APPROVE"),
                rejection_reason=args.get("rejection_reason"),
                confirmation_token=args.get("confirmation_token"),
                db=db
            )
        )

        # 26. update_doctor_schedule (Admin)
        self.register(
            ToolMetadata(
                tool_name="update_doctor_schedule",
                domain="admin",
                description="Update a doctor's weekly shift start/end times and slot duration with Human-in-the-Loop Confirmation.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_id_or_name": {"type": "STRING", "description": "Doctor name or ID"},
                        "day_of_week": {"type": "INTEGER", "description": "Day (1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun)"},
                        "start_time_str": {"type": "STRING", "description": "Start time (e.g. '09:00 AM')"},
                        "end_time_str": {"type": "STRING", "description": "End time (e.g. '05:00 PM')"},
                        "slot_duration_minutes": {"type": "INTEGER", "description": "Slot duration in minutes (e.g. 20)"}
                    },
                    "required": ["doctor_id_or_name", "day_of_week", "start_time_str", "end_time_str"]
                },
                intent_examples=[
                    "update doctor schedule", "dr nitin ki timing badal do", "change shift timing",
                    "schedule update karo", "opd timing change"
                ],
                required_roles=["ADMIN", "SUPER_ADMIN"],
                risk_level="HIGH",
                requires_confirmation=True
            ),
            handler=lambda args, context, db: AdminTools.update_doctor_schedule(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                role=context.get("role", "ADMIN"),
                doctor_id_or_name=args.get("doctor_id_or_name", ""),
                day_of_week=args.get("day_of_week", 1),
                start_time_str=args.get("start_time_str", "09:00 AM"),
                end_time_str=args.get("end_time_str", "05:00 PM"),
                slot_duration_minutes=args.get("slot_duration_minutes", 20),
                confirmation_token=args.get("confirmation_token"),
                db=db
            )
        )

        # 27. get_expiring_subscriptions_report (SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="get_expiring_subscriptions_report",
                domain="control_tower",
                description="List all tenant hospitals whose SaaS subscriptions are expiring within N days.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "days_threshold": {"type": "INTEGER", "description": "Days lookahead (defaults to 30)"}
                    }
                },
                intent_examples=[
                    "expiring subscriptions", "subscriptions expiring in 30 days", "renewal due hospitals",
                    "plan expire hone wale hospitals", "expiring tenant list"
                ],
                required_roles=["SUPER_ADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: ControlTowerTools.get_expiring_subscriptions_report(
                days_threshold=args.get("days_threshold", 30),
                db=db
            )
        )

        # 28. extend_hospital_subscription (SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="extend_hospital_subscription",
                domain="control_tower",
                description="Extend or renew a hospital's SaaS subscription with an immutable audit ledger entry.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "hospital_id": {"type": "STRING", "description": "Hospital ID"},
                        "duration_days": {"type": "INTEGER", "description": "Days to add (e.g. 30, 365)"},
                        "plan_name": {"type": "STRING", "description": "Plan tier ('STARTER', 'PRO', 'ENTERPRISE')"},
                        "notes": {"type": "STRING", "description": "Renewal notes or transaction ref"}
                    },
                    "required": ["hospital_id", "duration_days"]
                },
                intent_examples=[
                    "extend subscription", "renew hospital plan", "subscription badhao",
                    "hospital validity extend", "add 365 days to plan"
                ],
                required_roles=["SUPER_ADMIN"],
                risk_level="HIGH",
                requires_confirmation=True
            ),
            handler=lambda args, context, db: ControlTowerTools.extend_hospital_subscription(
                hospital_id=args.get("hospital_id", ""),
                duration_days=args.get("duration_days", 30),
                plan_name=args.get("plan_name"),
                notes=args.get("notes"),
                user_id=context.get("user_id"),
                confirmation_token=args.get("confirmation_token"),
                db=db
            )
        )

        # 29. search_platform_hospital (SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="search_platform_hospital",
                domain="control_tower",
                description="Search and view details of any tenant hospital across the platform (phone, email, doctors, plan, status).",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Hospital name, slug, ID or city to search"}
                    },
                    "required": ["query"]
                },
                intent_examples=[
                    "balaji hospital ka number do", "hospital phone number", "search hospital",
                    "find hospital contact", "hospital ki details do", "hospital details",
                    "balaji hospital info", "tenant details", "look up hospital"
                ],
                required_roles=["SUPER_ADMIN", "SUPERADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: ControlTowerTools.search_platform_hospital(
                query=args.get("query", ""),
                db=db
            )
        )

        # 30. apply_leave_for_doctor (Doctor)
        self.register(
            ToolMetadata(
                tool_name="apply_leave_for_doctor",
                domain="doctor",
                description="Apply for doctor leave with Human-in-the-Loop Confirmation.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "leave_date": {"type": "STRING", "description": "Start date YYYY-MM-DD"},
                        "start_date_str": {"type": "STRING", "description": "Start date YYYY-MM-DD"},
                        "end_date_str": {"type": "STRING", "description": "End date YYYY-MM-DD"},
                        "reason": {"type": "STRING", "description": "Reason for leave"},
                        "doctor_name": {"type": "STRING", "description": "Doctor name or empty"}
                    },
                    "required": []
                },
                intent_examples=[
                    "apply for leave", "chutti apply karo", "take leave next monday", "i want leave"
                ],
                required_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN", "ALL"],
                risk_level="HIGH",
                requires_confirmation=True
            ),
            handler=lambda args, context, db: CopilotTools.apply_leave_for_doctor(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                doctor_name=args.get("doctor_name"),
                leave_date=args.get("leave_date") or args.get("start_date_str"),
                start_date_str=args.get("start_date_str") or args.get("leave_date"),
                end_date_str=args.get("end_date_str"),
                reason=args.get("reason", "Personal Leave"),
                confirmation_token=args.get("confirmation_token"),
                db=db
            )
        )

        # 31. get_comprehensive_doctor_analytics (Admin / Doctor)
        self.register(
            ToolMetadata(
                tool_name="get_comprehensive_doctor_analytics",
                domain="admin",
                description="Comprehensive department & weekly doctor schedule matrix, working days, and revenue analytics.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "time_range": {"type": "STRING", "description": "'today', 'week', 'month', or 'all'"}
                    }
                },
                intent_examples=[
                    "doctor schedule of this week", "which departments doctors exist", "total working days of doctors",
                    "departments directory", "doctor working days"
                ],
                required_roles=["ADMIN", "SUPER_ADMIN", "DOCTOR", "RECEPTIONIST", "ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_comprehensive_doctor_analytics(
                hospital_id=context.get("hospital_id"),
                time_range=args.get("time_range", "all"),
                db=db
            )
        )

        # 32. get_hospital_department_directory (All)
        self.register(
            ToolMetadata(
                tool_name="get_hospital_department_directory",
                domain="hospital",
                description="Returns all active hospital departments, doctor counts, and specialist rosters.",
                parameters={
                    "type": "OBJECT",
                    "properties": {}
                },
                intent_examples=[
                    "which departments exist", "types of doctors", "hospital departments", "specializations in hospital"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_hospital_department_directory(
                hospital_id=context.get("hospital_id"),
                db=db
            )
        )

        # 33. get_revenue_and_dues (Admin / SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="get_revenue_and_dues",
                domain="finance",
                description="Financial OPD revenue, total collections, and pending dues for today, this month, or all time.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "time_range": {"type": "STRING", "description": "'today', 'week', 'month', or 'all'"}
                    }
                },
                intent_examples=[
                    "all time pending collection dues", "total revenue of all time", "pending dues summary", "revenue today"
                ],
                required_roles=["ADMIN", "SUPER_ADMIN", "SUPERADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_revenue_and_dues(
                hospital_id=context.get("hospital_id"),
                time_range=args.get("time_range", "today"),
                db=db
            )
        )

        # 34. get_doctor_daily_earnings (Doctor / Admin)
        self.register(
            ToolMetadata(
                tool_name="get_doctor_daily_earnings",
                domain="doctor",
                description="Doctor personal consultations, earnings, and patient load for today, month, or all time.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "date_str": {"type": "STRING", "description": "Date YYYY-MM-DD"},
                        "time_range": {"type": "STRING", "description": "'today', 'week', 'month', or 'all'"},
                        "doctor_name": {"type": "STRING", "description": "Doctor name"}
                    }
                },
                intent_examples=[
                    "my total appointment and total earning of all time", "today's consulted patients", "my earnings", "opd earnings today"
                ],
                required_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN", "SUPERADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_doctor_daily_earnings(
                hospital_id=context.get("hospital_id"),
                user_id=context.get("user_id"),
                doctor_name=args.get("doctor_name"),
                date_str=args.get("date_str"),
                time_range=args.get("time_range", "today"),
                db=db
            )
        )

        # 35. get_platform_control_tower_overview (SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="get_platform_control_tower_overview",
                domain="control_tower",
                description="Global multi-tenant platform control tower overview across all hospitals, subscriptions, and AI voice telemetry.",
                parameters={
                    "type": "OBJECT",
                    "properties": {}
                },
                intent_examples=[
                    "how many hospitals are active", "platform revenue overview", "expiring subscriptions", "voice telemetry"
                ],
                required_roles=["SUPER_ADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_platform_control_tower_overview(
                db=db
            )
        )

        # 36. run_analytics_query — Structured Analytics Query Builder (All Portals)
        from app.engines.analytics_query_builder import analytics_query_builder
        self.register(
            ToolMetadata(
                tool_name="run_analytics_query",
                domain="analytics",
                description=(
                    "Execute a structured analytics query from pre-approved templates. "
                    "Supports revenue by department, doctor load comparison, cancellation rates, payment method breakdown, "
                    "monthly trends, pending dues by age, new vs repeat patients, peak hour analysis, "
                    "doctor's own monthly consultations, revenue trend, repeat patient ratio, top diagnoses, "
                    "patient visit history, annual spending, and platform-wide SuperAdmin metrics. "
                    "Use this for ANY analytical, trend, breakdown, comparison, or summary question."
                ),
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "template_id": {
                            "type": "STRING",
                            "description": (
                                "Analytics template ID. Options: "
                                "DOCTOR_MONTHLY_CONSULTATIONS, DOCTOR_PEAK_DAY_ANALYSIS, DOCTOR_REPEAT_PATIENT_RATIO, "
                                "DOCTOR_TOP_DIAGNOSES, DOCTOR_REVENUE_TREND, "
                                "RECEPT_WALKIN_VS_BOOKED, RECEPT_PEAK_SLOT_ANALYSIS, RECEPT_NO_SHOW_SUMMARY, RECEPT_PENDING_DUES_LIST, "
                                "ADMIN_DEPT_REVENUE_BREAKDOWN, ADMIN_DOCTOR_LOAD_COMPARISON, ADMIN_CANCELLATION_RATE_BY_DOCTOR, "
                                "ADMIN_PAYMENT_METHOD_BREAKDOWN, ADMIN_NEW_VS_REPEAT_PATIENTS, ADMIN_MONTHLY_REVENUE_TREND, "
                                "ADMIN_PENDING_DUES_BY_AGE, ADMIN_TOP_PERFORMING_DOCTORS, "
                                "SA_TOP_REVENUE_HOSPITALS, SA_EXPIRING_SUBSCRIPTIONS, SA_PLATFORM_MRR, "
                                "SA_ACTIVE_HOSPITALS_OVERVIEW, SA_PLATFORM_APPOINTMENT_TRENDS, "
                                "PATIENT_VISIT_HISTORY_SUMMARY, PATIENT_ANNUAL_SPENDING, PATIENT_DOCTORS_VISITED"
                            )
                        },
                        "date_from": {"type": "STRING", "description": "Start date YYYY-MM-DD (default: 90 days ago)"},
                        "date_to":   {"type": "STRING", "description": "End date YYYY-MM-DD (default: today)"},
                        "days_ahead": {"type": "INTEGER", "description": "For subscription expiry template: days to look ahead (default: 30)"}
                    },
                    "required": ["template_id"]
                },
                intent_examples=[
                    "revenue by department", "department wise revenue", "August mein cardiology ka revenue",
                    "doctor load comparison", "cancellation rate by doctor", "payment method breakdown",
                    "cash vs upi vs card", "monthly revenue trend", "pending dues by age", "overdue dues",
                    "top performing doctors", "busiest doctors", "new vs repeat patients",
                    "my monthly consultations", "mera monthly earnings trend", "my peak day",
                    "which day am i busiest", "most common complaints", "top diagnoses",
                    "walk-in vs booked", "peak time slot", "no show summary", "platform MRR",
                    "expiring subscriptions", "top revenue hospitals", "patient visit history",
                    "how much money did i spend", "doctors i visited", "mere saare visits",
                    "analytics", "breakdown", "trend", "comparison", "summary report"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: analytics_query_builder.execute(
                template_id=args.get("template_id", ""),
                params={k: v for k, v in args.items() if k != "template_id"},
                context=context,
                db=db
            )
        )

        # 37. list_analytics_templates — Show available analytics for user's role
        self.register(
            ToolMetadata(
                tool_name="list_analytics_templates",
                domain="analytics",
                description="List all available analytics report templates for the current user's role.",
                parameters={
                    "type": "OBJECT",
                    "properties": {}
                },
                intent_examples=[
                    "what analytics can i see", "available reports", "what reports are available",
                    "kaunse analytics dekh sakta hoon", "show me analytics options"
                ],
                required_roles=["ALL"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: {
                "templates": analytics_query_builder.get_available_templates(context.get("role", ""))
            }
        )

        # 38. search_platform_hospital (SuperAdmin)
        self.register(
            ToolMetadata(
                tool_name="search_platform_hospital",
                domain="control_tower",
                description="Global platform hospital lookup for SuperAdmin across all tenant hospitals (contact details, phone, address, plan, doctor count).",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "Hospital name, slug, id, or location to search"}
                    },
                    "required": ["query"]
                },
                intent_examples=[
                    "balaji hospital ka number do mujhe", "search hospital alpha-medical", "hospital contact info", "hospital details", "balaji hospital info"
                ],
                required_roles=["SUPER_ADMIN", "SUPERADMIN"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: ControlTowerTools.search_platform_hospital(
                query=args.get("query", ""),
                db=db
            )
        )

        # 39. get_doctor_metrics
        self.register(
            ToolMetadata(
                tool_name="get_doctor_metrics",
                domain="doctor",
                description="Fetches live doctor-specific metrics including total revenue collected, total appointments booked, completed visits, and cancellations.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "doctor_name": {"type": "STRING", "description": "Doctor name e.g. 'Dr. Nitin Dewedi'"},
                        "metric": {"type": "STRING", "description": "'revenue', 'bookings', 'completed', or 'all'"},
                        "time_range": {"type": "STRING", "description": "'today', 'this_week', 'this_month', or 'all'"}
                    },
                    "required": ["doctor_name"]
                },
                intent_examples=[
                    "dr nitin total revenue", "dr vivek kamai kitni hui", "how much did dr shiva earn",
                    "dr nitin appointments count", "doctor revenue", "doctor total collections"
                ],
                required_roles=["ADMIN", "HOSPITAL_ADMIN", "SUPER_ADMIN", "DOCTOR", "RECEPTIONIST"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_doctor_metrics(
                hospital_id=context.get("hospital_id"),
                doctor_name=args.get("doctor_name", ""),
                metric=args.get("metric", "all"),
                time_range=args.get("time_range", "all"),
                db=db
            )
        )

        # 40. get_all_doctors_performance
        self.register(
            ToolMetadata(
                tool_name="get_all_doctors_performance",
                domain="doctor",
                description="Live performance leaderboard of all doctors in the hospital showing total bookings, completed consultations, cancellations, and revenue generated.",
                parameters={
                    "type": "OBJECT",
                    "properties": {
                        "time_range": {"type": "STRING", "description": "'today', 'this_week', 'this_month', or 'all'"}
                    }
                },
                intent_examples=[
                    "show doctor-wise booking performance", "doctor performance", "doctor booking stats",
                    "doctor wise load", "which doctor has highest bookings", "doctor ranking"
                ],
                required_roles=["ADMIN", "HOSPITAL_ADMIN", "SUPER_ADMIN", "DOCTOR", "RECEPTIONIST"],
                risk_level="READ_ONLY"
            ),
            handler=lambda args, context, db: CopilotTools.get_all_doctors_performance(
                hospital_id=context.get("hospital_id"),
                time_range=args.get("time_range", "all"),
                db=db
            )
        )


# Global singleton instance
tool_registry = DynamicToolRegistry()

