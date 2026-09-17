import re
import os
import json
import math
import asyncio
import logging
from collections import Counter
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("aura.copilot.rag")

class KnowledgeDocument(BaseModel):
    doc_id: str
    hospital_id: str  # 'GLOBAL' or specific tenant ID like 'HOSP-001'
    title: str
    category: str  # 'faq', 'policy', 'sop', 'doctor_profile', 'pricing', 'emergency'
    allowed_roles: List[str] = Field(default_factory=lambda: ["ALL"])
    department_id: Optional[str] = None
    visibility: str = "PUBLIC"  # 'PUBLIC', 'INTERNAL', 'RESTRICTED'
    content: str
    source: Optional[str] = None


class RAGSearchResult(BaseModel):
    title: str
    category: str
    content: str
    hospital_id: str
    score: float
    source: Optional[str] = None


class RoleScopedRAGEngine:
    """
    Enterprise-Grade Multi-Tenant, Role-Scoped RAG Vector & Knowledge Engine.
    - Zero Cross-Tenant Leakage: Strict filter on `hospital_id` in [user_hospital_id, 'GLOBAL'].
    - Zero Privilege Escalation: Strict filter on `allowed_roles`.
    - High-Speed In-Memory BM25/Cosine Index with Overlapping Chunking.
    """

    EMBEDDINGS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "rag_embeddings_cache.json")
    EMBEDDING_MODEL = "models/text-embedding-004"
    EMBEDDING_DIM = 768

    def __init__(self):
        self._documents: Dict[str, KnowledgeDocument] = {}
        self._chunks: List[Dict[str, Any]] = []
        self._chunk_tokens: List[Counter] = []
        self._idf: Dict[str, float] = {}
        # Dense embedding vectors: list of lists (one per chunk), same index as _chunks
        self._embeddings: List[Optional[List[float]]] = []
        # Load cache from disk if available
        self._embedding_cache: Dict[str, List[float]] = self._load_embedding_cache()
        self._seed_default_knowledge_base()
        self._rebuild_index()
        # Save cache after seeding (captures any newly embedded chunks)
        self._save_embedding_cache()

    def ingest_document(self, doc: KnowledgeDocument, chunk_size: int = 400, overlap: int = 60):
        """Chunks and indexes a knowledge document."""
        self._documents[doc.doc_id] = doc
        
        # Chunk content
        words = doc.content.split()
        if len(words) <= chunk_size:
            chunk_texts = [doc.content]
        else:
            chunk_texts = []
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_texts.append(" ".join(words[start:end]))
                if end == len(words):
                    break
                start += (chunk_size - overlap)

        for idx, chunk_text in enumerate(chunk_texts):
            chunk_meta = {
                "chunk_id": f"{doc.doc_id}_c{idx}",
                "doc_id": doc.doc_id,
                "hospital_id": doc.hospital_id,
                "title": doc.title,
                "category": doc.category,
                "allowed_roles": [r.upper() for r in doc.allowed_roles],
                "department_id": doc.department_id,
                "visibility": doc.visibility,
                "content": chunk_text,
                "source": doc.source or doc.title
            }
            self._chunks.append(chunk_meta)
            tokens = self._tokenize(f"{doc.title} {chunk_text}")
            self._chunk_tokens.append(Counter(tokens))
            # Generate dense embedding (uses cache if available, falls back gracefully)
            embed_text = f"{doc.title}. {chunk_text}"
            embedding = self._embed_text_sync(embed_text)
            self._embeddings.append(embedding)

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r'[^a-zA-Z0-9_\s]', ' ', text.lower())
        words = [w for w in cleaned.split() if len(w) > 1]
        bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)] if len(words) > 1 else []
        return words + bigrams

    def _rebuild_index(self):
        num_chunks = max(len(self._chunks), 1)
        doc_freq = Counter()
        for token_counts in self._chunk_tokens:
            for token in token_counts.keys():
                doc_freq[token] += 1
        
        self._idf = {}
        for token, count in doc_freq.items():
            self._idf[token] = math.log((num_chunks + 1.0) / (count + 1.0)) + 1.0

    def _load_embedding_cache(self) -> Dict[str, List[float]]:
        """Loads pre-computed embeddings from disk cache to avoid re-generating on restart."""
        try:
            if os.path.exists(self.EMBEDDINGS_CACHE_PATH):
                with open(self.EMBEDDINGS_CACHE_PATH, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                logger.info(f"RAG: Loaded {len(cache)} embeddings from disk cache.")
                return cache
        except Exception as e:
            logger.warning(f"RAG: Could not load embedding cache: {e}")
        return {}

    def _save_embedding_cache(self):
        """Persists current embedding cache to disk."""
        try:
            with open(self.EMBEDDINGS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._embedding_cache, f)
            logger.info(f"RAG: Saved {len(self._embedding_cache)} embeddings to disk cache.")
        except Exception as e:
            logger.warning(f"RAG: Could not save embedding cache: {e}")

    def _embed_text_sync(self, text: str) -> Optional[List[float]]:
        """Generates a dense embedding vector for text using Google text-embedding-004.
        Returns None silently if API is unavailable (offline fallback to BM25)."""
        # Cache check
        cache_key = text[:200]  # Key by first 200 chars
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        try:
            from app.core.config import settings
            api_key = getattr(settings, "GEMINI_API_KEY", None)
            if not api_key:
                return None
            # Try new google.genai SDK first (recommended), fall back to deprecated one
            try:
                from google import genai as new_genai
                client = new_genai.Client(api_key=api_key)
                result = client.models.embed_content(
                    model=self.EMBEDDING_MODEL,
                    contents=text
                )
                embedding = result.embeddings[0].values
            except (ImportError, AttributeError):
                # Fallback to deprecated package if new one not installed
                import google.generativeai as genai  # noqa: F401
                genai.configure(api_key=api_key)
                result = genai.embed_content(
                    model=self.EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = result["embedding"]
            self._embedding_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            logger.debug(f"RAG embedding failed (BM25 fallback active): {e}")
            return None

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """Fast cosine similarity between two equal-length vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (norm_a * norm_b)

    async def search(
        self,
        query: str,
        hospital_id: Optional[str],
        role: str,
        department_id: Optional[str] = None,
        top_k: int = 3,
        min_score: float = 0.15
    ) -> List[RAGSearchResult]:
        """
        Executes a role-scoped, tenant-isolated vector search across knowledge chunks.
        """
        role_upper = (role or "").upper().replace(" ", "_")
        target_hospital = hospital_id or "GLOBAL"

        # Generate query embedding (gracefully falls back to BM25 if unavailable)
        query_embedding = self._embed_text_sync(query)

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_counts = Counter(query_tokens)
        query_vec = {t: query_counts[t] * self._idf.get(t, 1.0) for t in query_counts}
        query_norm = math.sqrt(sum(v * v for v in query_vec.values())) or 1.0

        scored_results: List[RAGSearchResult] = []

        for idx, chunk in enumerate(self._chunks):
            # 1. Tenant Filter: Must match user's hospital OR be a GLOBAL platform document
            if chunk["hospital_id"] != "GLOBAL" and chunk["hospital_id"] != target_hospital:
                continue

            # 2. RBAC Filter: User role must be in allowed_roles or 'ALL'
            allowed = chunk["allowed_roles"]
            if "ALL" not in allowed and role_upper not in allowed:
                continue

            # 3. Department Filter (if applicable)
            if chunk.get("department_id") and department_id and chunk["department_id"] != department_id:
                continue

            # 4a. BM25 Score (always available)
            token_counts = self._chunk_tokens[idx]
            dot_product = 0.0
            vec_sq = 0.0
            for t, count in token_counts.items():
                w = count * self._idf.get(t, 1.0)
                vec_sq += w * w
                if t in query_vec:
                    dot_product += query_vec[t] * w

            chunk_norm = math.sqrt(vec_sq) or 1.0
            bm25_score = dot_product / (query_norm * chunk_norm)

            # 4b. Dense Embedding Score (if embeddings are available for this chunk)
            chunk_embedding = self._embeddings[idx] if idx < len(self._embeddings) else None
            if chunk_embedding and query_embedding:
                embed_score = self._cosine_sim(query_embedding, chunk_embedding)
                # Hybrid: 70% embedding + 30% BM25
                score = 0.7 * embed_score + 0.3 * bm25_score
            else:
                # Pure BM25 fallback (no embedding available)
                score = bm25_score

            if score >= min_score:
                scored_results.append(
                    RAGSearchResult(
                        title=chunk["title"],
                        category=chunk["category"],
                        content=chunk["content"],
                        hospital_id=chunk["hospital_id"],
                        score=score,
                        source=chunk["source"]
                    )
                )

        # Sort by relevance descending
        scored_results.sort(key=lambda x: x.score, reverse=True)
        return scored_results[:top_k]

    def _seed_default_knowledge_base(self):
        """Seeds standard hospital FAQs, policies, SOPs, and medical protocols."""

        # 1. Hospital OPD Timings & General FAQs (GLOBAL & Multi-Tenant)
        self.ingest_document(
            KnowledgeDocument(
                doc_id="faq_opd_hours",
                hospital_id="GLOBAL",
                title="Hospital General OPD & Visiting Hours",
                category="faq",
                allowed_roles=["ALL"],
                content=(
                    "Standard OPD consultation hours are Monday to Saturday from 09:00 AM to 08:00 PM. "
                    "Emergency and Trauma care is open 24x7 with round-the-clock casualty medical officers and ICU support. "
                    "Sunday OPD is available for emergency walk-ins and specialized shifts between 10:00 AM and 02:00 PM. "
                    "Patient visiting hours for inpatient wards are 04:00 PM to 07:00 PM daily. Only one attendant pass is permitted per bed."
                )
            )
        )

        # 2. Appointment Booking & Cancellation Policy
        self.ingest_document(
            KnowledgeDocument(
                doc_id="policy_cancellation_refund",
                hospital_id="GLOBAL",
                title="Appointment Cancellation & Refund Policy",
                category="policy",
                allowed_roles=["ALL"],
                content=(
                    "Patients can cancel or reschedule appointments up to 2 hours prior to the scheduled consultation time. "
                    "In case of online advance payments via UPI or Card, 100% refund is initiated automatically to the original payment method within 3-5 business days upon valid cancellation. "
                    "For walk-in appointments, refunds can be collected directly from the billing desk upon showing the cancellation token. "
                    "Missed consultations without prior cancellation are non-refundable but can be rescheduled once within 48 hours with hospital admin approval."
                )
            )
        )

        # 3. Insurance & TPA Cashless Tie-ups
        self.ingest_document(
            KnowledgeDocument(
                doc_id="policy_insurance_tpa",
                hospital_id="GLOBAL",
                title="Insurance & TPA Cashless Hospitalization Guidelines",
                category="policy",
                allowed_roles=["ALL"],
                content=(
                    "AURA partnered hospitals support major TPAs and insurance providers including Star Health, HDFC ERGO, ICICI Lombard, Max Bupa/Niva Bupa, Care Health, and Bajaj Allianz. "
                    "For planned admissions, pre-authorization requests must be submitted at the TPA desk 48 hours in advance along with doctor prescription, government ID proof, and policy card. "
                    "For emergency admissions, cashless pre-authorization is processed within 4 hours of patient admission."
                )
            )
        )

        # 4. Front Desk SOP: Walk-in & Emergency Triaging (INTERNAL STAFF ONLY)
        self.ingest_document(
            KnowledgeDocument(
                doc_id="sop_reception_triage",
                hospital_id="GLOBAL",
                title="Front Desk OPD Registration & Emergency Triaging SOP",
                category="sop",
                allowed_roles=["RECEPTIONIST", "ADMIN", "SUPER_ADMIN", "DOCTOR"],
                visibility="INTERNAL",
                content=(
                    "Standard Operating Procedure for Front Desk Staff: "
                    "1. Walk-in Registration: Always check if the patient already exists in the system by searching their mobile number before creating a new profile. "
                    "2. Collect and record chief complaint and basic vitals (BP, Pulse, Temperature) during initial check-in. "
                    "3. For patients presenting with acute chest pain, breathlessness, severe bleeding, or unconsciousness, bypass regular OPD queue and immediately escort to Casualty/Emergency Room 1. "
                    "4. Cash Collections: Issue digital printed receipts for all cash payments and reconcile with daily register report at the end of each shift."
                )
            )
        )

        # 5. Doctor Clinical Prescription & Tele-Consult Protocol (DOCTOR & ADMIN ONLY)
        self.ingest_document(
            KnowledgeDocument(
                doc_id="sop_clinical_prescription",
                hospital_id="GLOBAL",
                title="Clinical Documentation & Digital Prescription SOP",
                category="sop",
                allowed_roles=["DOCTOR", "ADMIN", "SUPER_ADMIN"],
                visibility="INTERNAL",
                content=(
                    "Clinical Consultation SOP: "
                    "1. Every completed consultation must record differential diagnosis and specific generic medicine names with dosage and duration. "
                    "2. Mark follow-up review dates clearly to enable automated reminder SMS to patients. "
                    "3. Leave Requests: Doctors must submit planned leave requests at least 7 days in advance through the Copilot portal to facilitate automated patient reschedule alerts."
                )
            )
        )

        # 6. AURA SaaS Official Subscription Plans, Pricing & Feature Catalog (ALL ROLES & GLOBAL)
        self.ingest_document(
            KnowledgeDocument(
                doc_id="aura_saas_subscription_catalog",
                hospital_id="GLOBAL",
                title="AURA SaaS Official Subscription Plans, Pricing and Feature Catalog",
                category="pricing",
                allowed_roles=["ALL"],
                visibility="PUBLIC",
                content=(
                    "AURA Intelligent Healthcare SaaS Official Subscription Plans & Pricing:\n"
                    "1. STARTER PLAN (₹1,500 / month after 15-Day Free Trial):\n"
                    "- Capacity: Up to 1 Active Doctor Profile.\n"
                    "- Key Features: Basic OPD schedule, live patient queue, manual appointment booking, automated WhatsApp appointment alerts, patient portal link.\n"
                    "- AI Voice Receptionist: Disabled (Voice calling not available on Starter).\n"
                    "- Ideal For: Solo practitioners, independent consultation chambers, and small clinics.\n\n"
                    "2. PRO AI PLAN (₹2,999 / month):\n"
                    "- Capacity: Up to 5 Active Doctor Profiles.\n"
                    "- Key Features: 24/7 Live Automated AI Voice Receptionist (Twilio phone line pickup), automated phone appointment booking in Hindi & English, WhatsApp confirmations with token numbers, Razorpay online payments & OPD fee collection, automated doctor schedule management.\n"
                    "- AI Voice Receptionist: Fully Enabled with low-latency conversational AI.\n"
                    "- Ideal For: Growing nursing homes, multi-doctor clinics, and hospitals wanting zero missed patient calls.\n\n"
                    "3. ENTERPRISE 360 PLAN (₹29,999 / year - Annual Flat Saver):\n"
                    "- Capacity: Unlimited Doctor Profiles across all departments.\n"
                    "- Key Features: Dedicated priority low-latency Voice LLM, custom hospital white-label branding and logo, multi-branch support, comprehensive financial & doctor matrix analytics, 24/7 dedicated SRE support and 99.9% uptime SLA.\n"
                    "- Billing: Annual (Flat 20%+ discount compared to monthly billing).\n"
                    "- Ideal For: Large multi-specialty hospitals with 6+ doctors, high patient footfall, and high call volumes.\n\n"
                    "Renewal & Activation: Instant reactivation via Razorpay in under 5 seconds. All patient records, histories, and doctor profiles are securely preserved during plan expiry.\n"
                    "Keywords: subscription plans, plan details, pricing list, kitne ka hai, plans comparison, starter pro enterprise, price list, calling plan, recharge, renew subscription, cost, fees."
                )
            )
        )

        # 7. AURA SaaS Plan Selection & Consultation Guidelines (ALL ROLES & GLOBAL)
        self.ingest_document(
            KnowledgeDocument(
                doc_id="aura_saas_plan_consultant_guide",
                hospital_id="GLOBAL",
                title="AURA SaaS Hospital Plan Consultation & Recommendation Guidelines",
                category="consulting",
                allowed_roles=["ALL"],
                visibility="PUBLIC",
                content=(
                    "AURA SaaS Plan Recommendation Logic (ChatGPT-style consultation):\n"
                    "- Recommendation by Doctor Count:\n"
                    "  * 1 Doctor: Recommend Starter Plan (₹1,500/mo). Most affordable entry point.\n"
                    "  * 2 to 5 Doctors: Recommend PRO AI Plan (₹2,999/mo). Perfectly covers up to 5 doctors and includes 24/7 AI Voice phone booking.\n"
                    "  * 6 or more Doctors: Recommend Enterprise 360 (₹29,999/yr). Unlimited doctor profiles and priority voice channels.\n"
                    "- Recommendation by Calling & Automation Need:\n"
                    "  * If user asks for automated phone reception, missed call booking, or voice agent: Always recommend PRO AI or Enterprise, as Starter does not include AI Voice.\n"
                    "  * Explain that a single missed patient appointment costs ₹500 to ₹1,000, so the PRO plan (₹2,999/mo) pays for itself in just 3-4 appointments.\n"
                    "- Recommendation for Expired Hospitals:\n"
                    "  * Be polite, empathetic, and encouraging. Explain that all their data and doctor schedules are safely preserved.\n"
                    "  * If they previously had Starter and now have multiple doctors, suggest upgrading to PRO for AI Voice capabilities.\n"
                    "  * Guide them to click the 'Renew Now via Razorpay' button directly on their workspace screen for 5-second instant reactivation.\n"
                    "Keywords: kaunsa plan lena chahiye, hamare hospital ke liye best plan, kaun sa plan sahi rahega, doctors limit, voice calling, renewal, upgrade, recharge, payment, best plan for hospital, hamare doctors hain."
                )
            )
        )


# Global singleton instance
rag_engine = RoleScopedRAGEngine()
