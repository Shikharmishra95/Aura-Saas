"""
AURA HMS AI Tools Suite
Modular, role-governed, multi-tenant HMS operational tools for the AURA AI Agent.
"""

from app.tools.doctor_tools import DoctorTools
from app.tools.appointment_tools import AppointmentTools
from app.tools.patient_tools import PatientTools
from app.tools.hospital_tools import HospitalTools
from app.tools.clinical_tools import ClinicalTools
from app.tools.payment_tools import PaymentTools
from app.tools.admin_tools import AdminTools
from app.tools.control_tower_tools import ControlTowerTools

search_doctors = DoctorTools.search_doctors
get_doctor_details = DoctorTools.get_doctor_details
check_doctor_availability = DoctorTools.check_doctor_availability
get_available_slots = DoctorTools.get_available_slots

book_appointment = AppointmentTools.book_appointment
get_my_appointments = AppointmentTools.get_my_appointments
cancel_appointment = AppointmentTools.cancel_appointment
reschedule_appointment = AppointmentTools.reschedule_appointment

get_patient_details = PatientTools.get_patient_details
get_hospital_information = HospitalTools.get_hospital_information

get_my_prescriptions = ClinicalTools.get_my_prescriptions
get_my_live_token_position = ClinicalTools.get_my_live_token_position
get_insurance_tpa_panels = ClinicalTools.get_insurance_tpa_panels
save_consultation_notes = ClinicalTools.save_consultation_notes

generate_appointment_payment_link = PaymentTools.generate_appointment_payment_link

get_all_opd_queues = AdminTools.get_all_opd_queues
approve_or_reject_doctor_leave = AdminTools.approve_or_reject_doctor_leave
update_doctor_schedule = AdminTools.update_doctor_schedule

get_expiring_subscriptions_report = ControlTowerTools.get_expiring_subscriptions_report
extend_hospital_subscription = ControlTowerTools.extend_hospital_subscription
toggle_hospital_ai_voice_service = ControlTowerTools.toggle_hospital_ai_voice_service

__all__ = [
    "DoctorTools",
    "AppointmentTools",
    "PatientTools",
    "HospitalTools",
    "ClinicalTools",
    "PaymentTools",
    "AdminTools",
    "ControlTowerTools",
    "search_doctors",
    "get_doctor_details",
    "check_doctor_availability",
    "get_available_slots",
    "book_appointment",
    "get_my_appointments",
    "cancel_appointment",
    "reschedule_appointment",
    "get_patient_details",
    "get_hospital_information",
    "get_my_prescriptions",
    "get_my_live_token_position",
    "get_insurance_tpa_panels",
    "save_consultation_notes",
    "generate_appointment_payment_link",
    "get_all_opd_queues",
    "approve_or_reject_doctor_leave",
    "update_doctor_schedule",
    "get_expiring_subscriptions_report",
    "extend_hospital_subscription",
    "toggle_hospital_ai_voice_service"
]

