import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ExtractedEntities(BaseModel):
    doctor_name: Optional[str] = None
    doctor_id: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_id: Optional[str] = None
    department: Optional[str] = None
    date_str: Optional[str] = None
    time_str: Optional[str] = None
    appointment_id: Optional[str] = None
    action_token: Optional[str] = None
    hospital_id: Optional[str] = None
    specialization: Optional[str] = None
    time_range: Optional[str] = None
    raw_entities: Dict[str, Any] = Field(default_factory=dict)


class EntityExtractor:
    """
    Healthcare Domain Entity Extraction Engine for AURA AI Copilot.
    Extracts structured domain entities from natural language queries (English, Hindi, Hinglish).
    """

    DEPARTMENT_MAP = {
        "cardio": "Cardiology",
        "cardiology": "Cardiology",
        "heart": "Cardiology",
        "dental": "Dental",
        "dentist": "Dental",
        "teeth": "Dental",
        "derma": "Dermatology",
        "dermatology": "Dermatology",
        "skin": "Dermatology",
        "diabetology": "Diabetology",
        "diabetes": "Diabetology",
        "sugar": "Diabetology",
        "ent": "ENT",
        "ear": "ENT",
        "nose": "ENT",
        "throat": "ENT",
        "ophthalmology": "Ophthalmology",
        "eye": "Ophthalmology",
        "vision": "Ophthalmology",
        "gastro": "Gastroenterology",
        "gastroenterology": "Gastroenterology",
        "stomach": "Gastroenterology",
        "liver": "Gastroenterology",
        "gynae": "Gynecology",
        "gynecology": "Gynecology",
        "gynaecology": "Gynecology",
        "women": "Gynecology",
        "general medicine": "General Medicine",
        "general physician": "General Medicine",
        "physician": "General Medicine",
        "internal medicine": "General Medicine",
        "neuro": "Neurology",
        "neurology": "Neurology",
        "brain": "Neurology",
        "nerve": "Neurology",
        "onco": "Oncology",
        "oncology": "Oncology",
        "cancer": "Oncology",
        "ortho": "Orthopedics",
        "orthopedics": "Orthopedics",
        "bone": "Orthopedics",
        "joint": "Orthopedics",
        "pedia": "Pediatrics",
        "pediatrics": "Pediatrics",
        "child": "Pediatrics",
        "kid": "Pediatrics",
        "psychiatry": "Psychiatry",
        "mental": "Psychiatry",
        "pulmo": "Pulmonology",
        "pulmonology": "Pulmonology",
        "chest": "Pulmonology",
        "lung": "Pulmonology",
        "respiratory": "Pulmonology",
        "uro": "Urology",
        "urology": "Urology",
        "kidney": "Urology"
    }

    DAY_NAME_MAP = {
        "monday": 0, "somwar": 0, "mon": 0,
        "tuesday": 1, "mangalwar": 1, "tue": 1,
        "wednesday": 2, "budhwar": 2, "wed": 2,
        "thursday": 3, "guruwar": 3, "brihaspatiwar": 3, "thu": 3,
        "friday": 4, "shukrawar": 4, "jumma": 4, "fri": 4,
        "saturday": 5, "shaniwar": 5, "sat": 5,
        "sunday": 6, "raviwar": 6, "itwar": 6, "sun": 6
    }

    COMMON_TYPOS = {
        "apoointment": "appointment",
        "apoointments": "appointments",
        "appoinment": "appointment",
        "appoinments": "appointments",
        "apointment": "appointment",
        "apointments": "appointments",
        "appointmnt": "appointment",
        "appointmnts": "appointments",
        "apointmnt": "appointment",
        "aptment": "appointment",
        "docter": "doctor",
        "docters": "doctors",
        "doctro": "doctor",
        "doktor": "doctor",
        "dactor": "doctor",
        "shcedule": "schedule",
        "shcedules": "schedules",
        "sheudle": "schedule",
        "sheudles": "schedules",
        "shedule": "schedule",
        "shedules": "schedules",
        "scheduel": "schedule",
        "schedul": "schedule",
        "scheule": "schedule",
        "timin": "timing",
        "timins": "timings",
        "earnin": "earning",
        "earnins": "earnings",
        "earngs": "earnings",
        "erning": "earning",
        "ernings": "earnings",
        "typew": "types",
        "tyep": "types",
        "typs": "types",
        "iun": "in",
        "inn": "in",
        "there": "their",
        "cancle": "cancel",
        "cancled": "cancelled",
        "canceld": "cancelled",
        "cancelation": "cancellation",
        "departmnt": "department",
        "departmnts": "departments",
        "dipartment": "department",
        "depatment": "department",
        "patinet": "patient",
        "patinets": "patients",
        "patiet": "patient",
        "patiets": "patients",
        "patien": "patient",
        "leav": "leave",
        "leve": "leave",
        "leavs": "leaves",
        "sltos": "slots",
        "solts": "slots",
        "solt": "slot",
        "chuti": "chutti",
        "chhutti": "chutti",
        "perscription": "prescription",
        "precryption": "prescription",
        "insuranse": "insurance",
        "insurence": "insurance",
        "cashles": "cashless",
        "revenew": "revenue",
        "revenu": "revenue",
        "revnue": "revenue",
        "colletion": "collection",
        "colection": "collection",
        "confrm": "confirm",
        "confrim": "confirm",
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Corrects common healthcare typos and normalizes slang terms."""
        if not text:
            return ""
        # Clean common apostrophe words e.g. appointment's -> appointments, doctor's -> doctors
        cleaned_text = re.sub(r"(\w+)'s\b", r"\1s", text, flags=re.IGNORECASE)
        cleaned_text = re.sub(r"today's\b", "today", cleaned_text, flags=re.IGNORECASE)
        words = cleaned_text.split()
        normalized_words = []
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w.lower())
            if clean_w in cls.COMMON_TYPOS:
                corrected = cls.COMMON_TYPOS[clean_w]
                # Preserve punctuation if attached
                if w.endswith(('.', '?', '!', ',')):
                    corrected += w[-1]
                normalized_words.append(corrected)
            else:
                normalized_words.append(w)
        return " ".join(normalized_words)

    @classmethod
    def extract_entities(cls, text: str, reference_date: Optional[date] = None) -> ExtractedEntities:
        """
        Parses text and extracts all domain entities with typo normalization.
        """
        ref_date = reference_date or date.today()
        q_raw = cls.normalize_text(text.strip())
        q_lower = q_raw.lower()

        entities = ExtractedEntities()
        raw: Dict[str, Any] = {}

        # 1. Appointment ID
        apt_match = re.search(r'\b(apt_[a-f0-9]+)\b', q_raw, re.IGNORECASE)
        if apt_match:
            entities.appointment_id = apt_match.group(1).lower()
            raw["appointment_id"] = entities.appointment_id

        # 2. Action Confirmation Token
        act_match = re.search(r'\b(act_[a-f0-9]+)\b', q_raw, re.IGNORECASE)
        if act_match:
            entities.action_token = act_match.group(1).lower()
            raw["action_token"] = entities.action_token

        # 3. Indian Phone Number (10 digits starting with 6-9)
        phone_match = re.search(r'(?:\+91[\-\s]?)?([6-9]\d{9})\b', q_raw)
        if phone_match:
            entities.patient_phone = phone_match.group(1)
            raw["patient_phone"] = entities.patient_phone

        # 4. Date Parsing
        parsed_date = cls._parse_date(q_lower, ref_date)
        if parsed_date:
            entities.date_str = parsed_date.isoformat()
            raw["date_str"] = entities.date_str

        # 5. Time Parsing
        parsed_time = cls._parse_time(q_raw)
        if parsed_time:
            entities.time_str = parsed_time
            raw["time_str"] = entities.time_str

        # 6. Department / Specialization
        parsed_dept = cls._parse_department(q_lower)
        if parsed_dept:
            entities.department = parsed_dept
            entities.specialization = parsed_dept
            raw["department"] = parsed_dept

        # 7. Doctor Name Parsing
        parsed_doctor = cls._parse_doctor_name(q_raw)
        if parsed_doctor:
            entities.doctor_name = parsed_doctor
            raw["doctor_name"] = parsed_doctor

        # 8. Patient Name Parsing (e.g. "for Rahul", "patient name Ramesh", "mera naam Sita")
        parsed_patient = cls._parse_patient_name(q_raw)
        if parsed_patient:
            entities.patient_name = parsed_patient
            raw["patient_name"] = parsed_patient

        # 9. Time Range (e.g., "today", "this month", "last 7 days")
        if any(w in q_lower for w in ["today", "aaj", "daily"]):
            entities.time_range = "today"
        elif any(w in q_lower for w in ["this week", "is hafte", "past 7 days", "last 7 days"]):
            entities.time_range = "week"
        elif any(w in q_lower for w in ["this month", "is mahine", "past 30 days", "last 30 days"]):
            entities.time_range = "month"

        entities.raw_entities = raw
        return entities

    @classmethod
    def _parse_date(cls, text_lower: str, ref_date: date) -> Optional[date]:
        """Resolves relative and explicit dates."""
        # Explicit ISO format: YYYY-MM-DD
        iso_match = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', text_lower)
        if iso_match:
            try:
                y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                return date(y, m, d)
            except ValueError:
                pass

        # Explicit DD/MM/YYYY or DD-MM-YYYY
        dmy_match = re.search(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b', text_lower)
        if dmy_match:
            try:
                d, m, y = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
                return date(y, m, d)
            except ValueError:
                pass

        # Relative keywords: Today / Aaj
        if re.search(r'\b(today|aaj|current date)\b', text_lower):
            return ref_date

        # Relative keywords: Tomorrow / Kal
        if re.search(r'\b(tomorrow|kal|agle din|next day)\b', text_lower):
            return ref_date + timedelta(days=1)

        # Relative keywords: Day after tomorrow / Parso
        if re.search(r'\b(day after tomorrow|parso|tarso)\b', text_lower):
            return ref_date + timedelta(days=2)

        # Day of week (e.g. "on Friday", "this Saturday", "next Monday", "somwar ko")
        for day_name, target_weekday in cls.DAY_NAME_MAP.items():
            pattern = rf'\b(?:this|next|on|aane wale)?\s*{day_name}\b'
            if re.search(pattern, text_lower):
                current_weekday = ref_date.weekday()
                days_ahead = target_weekday - current_weekday
                if "next" in text_lower and days_ahead <= 0:
                    days_ahead += 7
                elif days_ahead <= 0:
                    days_ahead += 7
                return ref_date + timedelta(days=days_ahead)

        return None

    @classmethod
    def _parse_time(cls, text: str) -> Optional[str]:
        """Resolves slot times (e.g., 10:00 AM, 2:30 PM, 14:00, 10am)."""
        # Matches "10:00 AM", "10:30am", "02:00 PM"
        t_match1 = re.search(r'\b(0?[1-9]|1[0-2]):([0-5]\d)\s*(am|pm)\b', text, re.IGNORECASE)
        if t_match1:
            hour = int(t_match1.group(1))
            minute = t_match1.group(2)
            meridiem = t_match1.group(3).upper()
            return f"{hour:02d}:{minute} {meridiem}"

        # Matches "10 AM", "2 PM", "11pm"
        t_match2 = re.search(r'\b(0?[1-9]|1[0-2])\s*(am|pm)\b', text, re.IGNORECASE)
        if t_match2:
            hour = int(t_match2.group(1))
            meridiem = t_match2.group(2).upper()
            return f"{hour:02d}:00 {meridiem}"

        # Matches 24hr "14:00", "09:30"
        t_match3 = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', text)
        if t_match3:
            h = int(t_match3.group(1))
            m = int(t_match3.group(2))
            meridiem = "PM" if h >= 12 else "AM"
            h_12 = h % 12 or 12
            return f"{h_12:02d}:{m:02d} {meridiem}"

        return None

    @classmethod
    def _parse_department(cls, text_lower: str) -> Optional[str]:
        """Matches clinical specialty / department keywords."""
        for kw, dept in cls.DEPARTMENT_MAP.items():
            if re.search(rf'\b{kw}\b', text_lower):
                return dept
        return None

    @classmethod
    def _parse_doctor_name(cls, text: str) -> Optional[str]:
        """Extracts doctor name with honorifics."""
        doc_match = re.search(r'\b(?:dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)', text, re.IGNORECASE)
        if doc_match:
            candidate = doc_match.group(1).strip()
            stop_words = {
                "available", "slots", "slot", "appointment", "timing", "timings", "fee", "fees",
                "on", "today", "tomorrow", "yesterday", "hai", "hain", "ko", "ke", "ka", "ki",
                "se", "par", "pe", "chutti", "in", "at", "for", "is", "are", "was", "were",
                "free", "busy", "who", "which", "that", "having", "have", "has", "had", "any",
                "all", "some", "good", "best", "near", "can", "will", "do", "does", "list",
                "name", "names", "details", "check", "tell", "show", "give", "kripya", "please"
            }
            words = candidate.split()
            clean_words = [w for w in words if w.lower() not in stop_words]
            if clean_words:
                clean_name = " ".join(clean_words).strip()
                if len(clean_name) >= 3 and clean_name.lower() not in stop_words:
                    return f"Dr. {clean_name.title()}" if not clean_name.lower().startswith("dr") else clean_name.title()
        return None

    @classmethod
    def _parse_patient_name(cls, text: str) -> Optional[str]:
        """Extracts patient name from booking phrases."""
        patterns = [
            r'\b(?:for|patient|patient name|naam|name)\s+(?:is\s+)?([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b',
            r'\b(?:mera naam|patient ka naam)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b'
        ]
        stop_words = {"doctor", "appointment", "booking", "dr", "slot", "hospital", "cardiology", "today", "tomorrow", "phone", "mobile", "contact", "number", "with", "on", "at", "date"}
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                cand = match.group(1).strip()
                words = cand.split()
                clean_words = []
                for w in words:
                    if w.lower() in stop_words:
                        break
                    clean_words.append(w)
                if clean_words:
                    clean_name = " ".join(clean_words)
                    if len(clean_name) > 1:
                        return clean_name.title()
        return None


entity_extractor = EntityExtractor()
