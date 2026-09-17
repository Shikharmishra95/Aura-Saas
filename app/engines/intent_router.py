import re
import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.engines.rag_engine import rag_engine, RAGSearchResult
from app.engines.tool_registry import tool_registry
from app.engines.entity_extractor import entity_extractor

logger = logging.getLogger("aura.copilot.router")

class RouteType(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    LIVE_DATA = "LIVE_DATA"
    ACTION = "ACTION"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"

class RouterDecision(BaseModel):
    route: RouteType
    confidence: float
    knowledge_results: List[Dict[str, Any]] = []
    pruned_tools: List[Dict[str, Any]] = []
    is_mutation: bool = False
    requires_confirmation: bool = False
    suggested_reply: Optional[str] = None


class CopilotIntentRouter:
    """
    Enterprise 5-Way Intent Router for AURA AI Copilot:
      1. KNOWLEDGE: Policies, SOPs, FAQ, Timings, Insurance, Guidelines.
      2. LIVE_DATA: Real-time DB state (Roster, Leaves, Live Queue, Cash Register, EMR Search).
      3. ACTION: State changes (Bookings, Rescheduling, Cancellations, Payments, Vitals, Leaves).
      4. MIXED: Combines Knowledge/Policy + Live DB Tool.
      5. UNKNOWN: Out-of-domain or low-confidence requests.
    """

    ACTION_PATTERNS = [
        r'\b(book|booking|schedule|appoint|banao|parcha banao|slot book)\b',
        r'\b(cancel|radd|cancel karo|delete booking)\b',
        r'\b(reschedule|postpone|change time|shift karo)\b',
        r'\b(mark paid|record payment|paisa jama|collect fee)\b',
        r'\b(record intake|save vitals|bp pulse|record consultation|write rx|prescription likho)\b',
        r'\b(apply leave|apply for leave|chutti chahiye|take leave|request leave|approve leave|reject leave|chutti apply)\b',
        r'\b(next patient|call patient|mark completed|status change)\b'
    ]

    LIVE_DATA_PATTERNS = [
        r'\b(consulted patients?|total consulted|completed visits?|completed patients?|consulted count|kitne consult hue|patients? consulted)\b',
        r'\b(chief complaint|next patient|next patient\'s chief complaint|intake summary|symptoms of next patient|agla patient)\b',
        r'\b(approved leave status|leave status|my leave history|check my leave|leave request status|past leaves)\b',
        r'\b(shift timings?|my timings?|my shifts?|my schedule|my working hours|my opd timing|doctor schedule|duty timings?|working hours?)\b',
        r'\b(working days?|weekly schedule|schedule of this week|total working days|working days of all doctor|doctor working days)\b',
        r'\b(departments?|specialty|specialties|specialization|doctors? exist|doctor directory|doctor roster|types? of doctors?|which types?|total doctors?|active doctors?|doctor count|kitne doctor)\b',
        r'\b(which doctors? are|doctors? on duty|doctors? are on duty|doctors? are tomorrow|doctors? tomorrow|kon kon doctor|doctor list today|available tomorrow|who is available|kon doctor)\b',
        r'\b(total appointments?|all time appointments?|appointments? of all time|total opd|total bookings?|all time|lifetime)\b',
        r'\b(on leave|chutti par|chutti|holiday|off duty|available|baith rhe|duty roster)\b',
        r'\b(live queue|waiting|kitne patient|queue count|waiting outside|line me|my queue|waiting in my queue|patients are waiting in my queue)\b',
        r'\b(revenue|collection|kamai|cash register|pending dues|total collected|daily earnings|my earnings?|all time pending|pending collection)\b',
        r'\b(doctor performance|doctor analytics|total appointments|completed count|missed list)\b',
        r'\b(control tower|platform revenue|active hospitals|expiring subscriptions|voice calls processed|telemetry|audit)\b',
        r'\b(patient profile|visit history|search appointment|check status|find patient|cough|fever|khansi|diagnosis|prescription)\b',
        r'\b(open slots|time slots|timings for doctor|slot khali|slots available)\b',
        r'\b(department|quota|subscription|plan validity|validity|plan status|license validity)\b',
        # Analytics Query Builder patterns
        r'\b(analytics?|breakdown|trend|comparison|report|summary report|analysis)\b',
        r'\b(revenue by|by department|dept.?wise|department.?wise|monthly revenue|annual revenue|yearly revenue)\b',
        r'\b(cancellation rate|no.?show|no show|missed appointments?|cancelled appointments?)\b',
        r'\b(doctor load|busiest doctor|top doctor|top performing|best doctor|worst doctor)\b',
        r'\b(payment method|cash vs|upi vs|online vs|card vs|payment split|payment breakdown)\b',
        r'\b(peak hour|peak time|peak slot|busiest time|busiest hour|busiest slot)\b',
        r'\b(new patient|repeat patient|new vs repeat|returning patient|patient frequency)\b',
        r'\b(pending dues by|overdue|dues aging|old dues|60 days due)\b',
        r'\b(my monthly|monthly consultation|mera monthly|monthly stats|my stats)\b',
        r'\b(my peak day|busiest day|which day busy|kaun sa din)\b',
        r'\b(top diagnos|common complaints?|chief complaint analysis|most common)\b',
        r'\b(platform mrr|monthly recurring|mrr|arr|platform stats)\b',
        r'\b(walk.?in vs|walkin vs booked|walkin ratio)\b',
        r'\b(how much.*spent|total.*spent|kitna paisa|mera kharch|my spending|annual spending)\b',
        r'\b(doctors? i visited|doctors? consulted|mere doctors?|visit history|mere saare visits)\b',
    ]

    KNOWLEDGE_PATTERNS = [
        r'\b(policy|rules|refund|cancellation charge|tpa|insurance|cashless|tie up|tieup|claim)\b',
        r'\b(visiting hours|visiting time|pass|attendant pass|icu timing|ward timing|visiting rule)\b',
        r'\b(opd timing|general timing|hospital hours|sunday opd|emergency 24x7|casualty timing)\b',
        r'\b(sop|guidelines|triaging|triage protocol|superadmin tier|pricing tier|starter tier|growth tier|enterprise tier)\b',
        r'\b(subscription|subscriptions|saas plans?|pricing|price list|starter plan|pro plan|enterprise plan|pro ai|plans comparison|which plan|best plan|kaunsa plan|konsa plan|renew|renewal|upgrade plan|plan lena chahiye)\b'
    ]

    # Strong Healthcare Domain Anchor Tokens
    HEALTHCARE_DOMAIN_PATTERNS = [
        r'\b(hospital|doctor|dr|patient|opd|token|appointment|slot|nurse|bed|icu|casualty|medicine|rx|prescription|fee|charge|bill|revenue|queue|leave|duty|roster|symptom|fever|cough|pain|khansi|bukhar|dawai|parcha|department|departments|working days|subscription|plan|plans|pricing|upgrade|renew)\b'
    ]

    @classmethod
    async def route_query(
        cls,
        query: str,
        role: str,
        hospital_id: Optional[str],
        permissions: Optional[List[str]] = None
    ) -> RouterDecision:
        """
        Fast multi-stage classification returning the optimal execution route,
        pre-fetched RAG chunks, and pruned candidate tools.
        """
        from app.engines.entity_extractor import entity_extractor
        norm_query = entity_extractor.normalize_text(query)
        q_lower = norm_query.lower().strip()
        role_upper = (role or "").upper().replace(" ", "_")

        # 1. Check for Action / Mutation triggers
        is_action = any(re.search(pat, q_lower) for pat in cls.ACTION_PATTERNS)
        
        # 2. Check for Live Data triggers
        is_live_data = any(re.search(pat, q_lower) for pat in cls.LIVE_DATA_PATTERNS)

        # 3. Check for Knowledge / Policy triggers
        is_knowledge = any(re.search(pat, q_lower) for pat in cls.KNOWLEDGE_PATTERNS)

        # 4. Check for general Healthcare domain relevance
        is_healthcare = any(re.search(pat, q_lower) for pat in cls.HEALTHCARE_DOMAIN_PATTERNS)

        # 5. Pre-fetch RAG Knowledge Chunks
        rag_hits = await rag_engine.search(
            query=query,
            hospital_id=hospital_id,
            role=role_upper,
            top_k=2,
            min_score=0.20
        )
        has_strong_rag = len(rag_hits) > 0 and rag_hits[0].score >= 0.22

        # 6. Pre-prune Permitted Tools
        pruned_tools = tool_registry.prune_tools_for_user(
            query=query,
            user_role=role_upper,
            user_permissions=permissions,
            top_k=6
        )

        # Check for High-Risk Confirmation
        requires_conf = False
        if any(w in q_lower for w in ["cancel", "radd", "delete", "reject leave"]):
            requires_conf = True

        # If zero domain match and zero RAG match -> UNKNOWN
        if not (is_action or is_live_data or is_knowledge or is_healthcare or has_strong_rag):
            fallback_msg = cls._generate_safe_fallback(role_upper)
            return RouterDecision(
                route=RouteType.UNKNOWN,
                confidence=0.15,
                knowledge_results=[],
                pruned_tools=[],
                suggested_reply=fallback_msg
            )

        # A. MIXED ROUTE: Knowledge match + Live Data or Action match
        if (is_knowledge or has_strong_rag) and (is_live_data or is_action):
            return RouterDecision(
                route=RouteType.MIXED,
                confidence=0.92,
                knowledge_results=[r.dict() for r in rag_hits],
                pruned_tools=pruned_tools,
                is_mutation=is_action,
                requires_confirmation=requires_conf
            )

        # B. ACTION ROUTE
        if is_action:
            return RouterDecision(
                route=RouteType.ACTION,
                confidence=0.95,
                knowledge_results=[],
                pruned_tools=pruned_tools,
                is_mutation=True,
                requires_confirmation=requires_conf
            )

        # C. KNOWLEDGE ROUTE
        if is_knowledge or has_strong_rag:
            return RouterDecision(
                route=RouteType.KNOWLEDGE,
                confidence=0.90 if has_strong_rag else 0.75,
                knowledge_results=[r.dict() for r in rag_hits],
                pruned_tools=[]
            )

        # D. LIVE DATA ROUTE
        if is_live_data or (is_healthcare and pruned_tools):
            return RouterDecision(
                route=RouteType.LIVE_DATA,
                confidence=0.88,
                knowledge_results=[],
                pruned_tools=pruned_tools
            )

        # E. UNKNOWN / SAFE FALLBACK
        fallback_msg = cls._generate_safe_fallback(role_upper)
        return RouterDecision(
            route=RouteType.UNKNOWN,
            confidence=0.40,
            knowledge_results=[],
            pruned_tools=[],
            suggested_reply=fallback_msg
        )

    @staticmethod
    def _generate_safe_fallback(role: str) -> str:
        """Returns safe, helpful role-based fallback with quick suggested actions."""
        if role == "SUPER_ADMIN":
            return (
                "I couldn't find a direct match for your request in the platform telemetry or knowledge base. "
                "Here are some things you can ask me:\n\n"
                "* **'Show active hospitals overview'**\n"
                "* **'Which hospital generates maximum revenue?'**\n"
                "* **'List subscriptions expiring in next 30 days'**\n"
                "* **'Show AI Voice Agent call telemetry'**"
            )
        elif role in ["ADMIN", "HOSPITAL_ADMIN"]:
            return (
                "I couldn't find a direct record for your query. Here are quick actions you can try:\n\n"
                "* **'What is our total revenue and dues today?'**\n"
                "* **'Show doctor availability and duty roster'**\n"
                "* **'Get live OPD queue statistics'**\n"
                "* **'What is our refund and cancellation policy?'**"
            )
        elif role == "DOCTOR":
            return (
                "I couldn't locate that specific record. As a doctor, you can ask:\n\n"
                "* **'Show my live waiting queue'**\n"
                "* **'Search past prescriptions with cough or fever'**\n"
                "* **'What are my OPD earnings today?'**\n"
                "* **'Apply for leave next Monday'**"
            )
        elif role == "RECEPTIONIST":
            return (
                "I couldn't find that query. You can ask me to:\n\n"
                "* **'Is Dr. Dewedi on leave today?'**\n"
                "* **'Check daily cash register'**\n"
                "* **'Book a walk-in appointment'**\n"
                "* **'What are the visiting hours and attendant rules?'**"
            )
        else:
            return (
                "Namaste! Aap mujhse yeh baatein pooch sakte hain:\n\n"
                "* **'Kya doctor aaj chutti par hain?'**\n"
                "* **'Dr. Vivek ke paas open slot kab hai?'**\n"
                "* **'Hospital ke OPD timings aur visiting hours kya hain?'**\n"
                "* **'Mera appointment status check karo'**"
            )


# Global singleton instance
intent_router = CopilotIntentRouter()
