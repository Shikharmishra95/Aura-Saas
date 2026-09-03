import uuid
from datetime import datetime, time
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.appointment import Appointment, AppointmentStatusHistory, Patient, Doctor
from app.engines.scheduling import SchedulingEngine
from app.core.logging import engine_logger


class AppointmentEngine:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.scheduling = SchedulingEngine(db_session)

    async def book_appointment(
        self,
        hospital_id: str,
        patient_id: str,
        doctor_id: str,
        appointment_datetime: datetime,
        reason: str = "Consultation",
        source: str = "VOICE"
    ) -> dict:
        """Books an appointment, returning a structured result dict with code and data.

        Returns:
            dict with keys: code (str), message (str), and optionally appointment_id, nearest_slot
            Codes: BOOKING_SUCCESS, SLOT_FULL, SAME_DAY_NOT_ALLOWED, DATE_TOO_FAR,
                   DOCTOR_NOT_FOUND, PATIENT_NOT_FOUND, DUPLICATE_BOOKING, ERROR
        """
        engine_logger.info(f"Attempting booking for patient {patient_id} with doctor {doctor_id} at {appointment_datetime}")

        try:
            # IST timezone helper
            from datetime import timezone, timedelta as td_type
            ist_now = datetime.now(timezone.utc) + td_type(hours=5, minutes=30)
            ist_today = ist_now.date()
            appt_date = appointment_datetime.date()

            # 1. Verify Patient Exists
            patient_stmt = select(Patient).where(Patient.id == patient_id)
            patient = (await self.db.execute(patient_stmt)).scalar_one_or_none()
            if not patient:
                engine_logger.error(f"Patient {patient_id} not found.")
                return {"code": "PATIENT_NOT_FOUND", "message": f"Patient {patient_id} not found."}

            # 2. Verify Doctor Exists and is active
            doctor_stmt = select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active == True)
            doctor = (await self.db.execute(doctor_stmt)).scalar_one_or_none()
            if not doctor:
                engine_logger.error(f"Doctor {doctor_id} not found or inactive.")
                return {"code": "DOCTOR_NOT_FOUND", "message": f"Doctor {doctor_id} not found or inactive."}

            # 3. Prevent past-date or same-day bookings
            if appt_date < ist_today:
                engine_logger.info(f"Rejecting past-date booking: {appt_date}")
                return {"code": "SAME_DAY_NOT_ALLOWED", "message": "Past date booking not allowed."}
            if appt_date == ist_today and source == "VOICE":
                engine_logger.info(f"Rejecting same-day booking for VOICE: {appt_date}")
                return {"code": "SAME_DAY_NOT_ALLOWED", "message": "Same-day booking via call is not allowed."}

            # 4. Prevent bookings more than 2 days ahead
            days_ahead = (appt_date - ist_today).days
            if days_ahead > 2:
                engine_logger.info(f"Rejecting booking too far ahead: {days_ahead} days")
                return {
                    "code": "DATE_TOO_FAR",
                    "message": f"Booking more than 2 days ahead is not allowed. Requested {days_ahead} days ahead."
                }

            # 5. Prevent duplicate bookings for same patient/doctor on same day
            start_datetime = datetime.combine(appt_date, time.min)
            end_datetime = datetime.combine(appt_date, time.max)
            existing_stmt = select(Appointment).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.doctor_id == doctor_id,
                    Appointment.appointment_datetime >= start_datetime,
                    Appointment.appointment_datetime <= end_datetime,
                    Appointment.status.in_(["SCHEDULED", "PENDING_PAYMENT"])
                )
            )
            existing_appt = (await self.db.execute(existing_stmt)).scalars().first()
            if existing_appt:
                engine_logger.info(f"Duplicate booking detected for patient {patient_id} with doctor {doctor_id} on {appt_date}")
                return {
                    "code": "DUPLICATE_BOOKING",
                    "message": f"Patient already has an active appointment with this doctor on {appt_date}."
                }

            # 6. Verify Slot Availability
            target_time = appointment_datetime.time()
            available_slots = await self.scheduling.get_available_slots(doctor_id, appt_date)
            slot_is_free = any(slot.start_time == target_time for slot in available_slots)

            if not slot_is_free:
                # Find up to 3 nearest available slots around the requested time
                # Prefer later slots first, then earlier slots if needed
                # Never suggest slots outside doctor working hours or booked slots (already filtered in available_slots)
                later = [s for s in available_slots if s.start_time >= target_time]
                earlier = [s for s in available_slots if s.start_time < target_time]
                
                # Sort later ascending (closest first)
                later.sort(key=lambda s: s.start_time)
                # Sort earlier descending (closest first)
                earlier.sort(key=lambda s: s.start_time, reverse=True)
                
                suggested_slots_objs = []
                # Prefer later slots first, up to 3
                suggested_slots_objs.extend(later[:3])
                
                # If we need more to make it up to 3, add from earlier
                needed = 3 - len(suggested_slots_objs)
                if needed > 0 and earlier:
                    suggested_slots_objs.extend(earlier[:needed])
                
                # Sort the selected slots chronologically so they look/sound natural
                suggested_slots_objs.sort(key=lambda s: s.start_time)
                
                # Format them nicely
                formatted_slots = [s.start_time.strftime("%I:%M %p").lstrip('0') for s in suggested_slots_objs]
                
                if not formatted_slots:
                    nearest_slot_str = "कोई slot उपलब्ध नहीं"
                elif len(formatted_slots) == 1:
                    nearest_slot_str = formatted_slots[0]
                elif len(formatted_slots) == 2:
                    nearest_slot_str = f"{formatted_slots[0]} या {formatted_slots[1]}"
                else:
                    nearest_slot_str = f"{', '.join(formatted_slots[:-1])} या {formatted_slots[-1]}"

                engine_logger.info(
                    f"Slot {target_time} not available for doctor {doctor_id} on {appt_date}. Suggested: {nearest_slot_str}"
                )
                return {
                    "code": "SLOT_FULL",
                    "message": f"The slot {target_time.strftime('%I:%M %p')} on {appt_date} is not available.",
                    "nearest_slot": nearest_slot_str
                }

            # 6b. Direct Atomic Conflict Check to prevent double-booking race conditions
            conflict_stmt = select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime == appointment_datetime,
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "PENDING_PAYMENT", "RESCHEDULED", "IN_CONSULTATION"])
            )
            conflict_appt = (await self.db.execute(conflict_stmt)).scalars().first()
            if conflict_appt:
                engine_logger.info(f"Race condition prevented: Slot {appointment_datetime} already taken for doctor {doctor_id}")
                return {
                    "code": "SLOT_FULL",
                    "message": f"The slot at {appointment_datetime.strftime('%I:%M %p')} was just reserved by another patient.",
                    "nearest_slot": nearest_slot_str if 'nearest_slot_str' in locals() else "कृपया अन्य स्लॉट चुनें"
                }

            # 7. Create Appointment Record
            appointment_id = str(uuid.uuid4())
            appointment = Appointment(
                id=appointment_id,
                hospital_id=hospital_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_datetime=appointment_datetime,
                duration_minutes=30,
                status="PENDING_PAYMENT",
                reason=reason,
                source=source
            )
            self.db.add(appointment)

            # 8. Create Status History Record
            status_history = AppointmentStatusHistory(
                id=str(uuid.uuid4()),
                appointment_id=appointment_id,
                previous_status=None,
                new_status="PENDING_PAYMENT",
                change_reason="Initial booking via Voice Receptionist"
            )
            self.db.add(status_history)

            # 9. Flush changes (caller must commit)
            await self.db.flush()
            await self.db.refresh(appointment)
            engine_logger.info(f"Appointment {appointment_id} flushed successfully. Awaiting commit.")

            return {
                "code": "BOOKING_SUCCESS",
                "appointment_id": appointment_id,
                "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                "appointment_datetime": appointment_datetime.isoformat(),
                "message": "Appointment booked successfully."
            }

        except Exception as e:
            engine_logger.error(f"Unexpected error in book_appointment: {str(e)}", exc_info=True)
            return {"code": "ERROR", "message": str(e)}

    async def cancel_appointment(self, appointment_id: str, reason: str = "Cancelled by patient via Voice") -> dict:
        """Cancels an existing appointment, updating status history."""
        engine_logger.info(f"Cancelling appointment: {appointment_id}")

        try:
            # 1. Fetch Appointment
            stmt = select(Appointment).where(Appointment.id == appointment_id)
            appointment = (await self.db.execute(stmt)).scalar_one_or_none()
            if not appointment:
                return {"code": "NOT_FOUND", "message": f"Appointment {appointment_id} not found."}

            if appointment.status == "CANCELLED":
                return {"code": "ALREADY_CANCELLED", "message": "Appointment is already cancelled."}

            # 2. Record Status Change
            status_history = AppointmentStatusHistory(
                id=str(uuid.uuid4()),
                appointment_id=appointment_id,
                previous_status=appointment.status,
                new_status="CANCELLED",
                change_reason=reason
            )
            self.db.add(status_history)

            # 3. Update Status
            appointment.status = "CANCELLED"
            await self.db.flush()
            await self.db.refresh(appointment)

            # 4. Send WhatsApp Notification
            try:
                from app.services.whatsapp import WhatsAppNotificationService
                from app.database.models.appointment import Patient, Doctor, Hospital
                # Fetch related data for template
                pat_stmt = select(Patient).where(Patient.id == appointment.patient_id)
                patient = (await self.db.execute(pat_stmt)).scalar_one_or_none()
                doc_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
                doctor = (await self.db.execute(doc_stmt)).scalar_one_or_none()
                hosp_stmt = select(Hospital).where(Hospital.id == appointment.hospital_id)
                hospital = (await self.db.execute(hosp_stmt)).scalar_one_or_none()
                
                if patient and doctor and hospital:
                    wa_service = WhatsAppNotificationService()
                    details = {
                        "patient_phone": patient.phone,
                        "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
                        "doctor_name": doctor.name,
                        "hospital_name": hospital.name,
                        "hospital_id": hospital.id,
                        "reason": reason,
                        "payment_status": appointment.payment_status
                    }
                    await wa_service.send_cancellation_refund_notification(details)
            except Exception as wa_err:
                engine_logger.error(f"Failed to send cancel WA msg for {appointment_id}: {wa_err}")

            engine_logger.info(f"Appointment {appointment_id} marked as CANCELLED.")
            return {"code": "CANCELLED", "appointment_id": appointment_id}

        except Exception as e:
            engine_logger.error(f"Error cancelling appointment {appointment_id}: {str(e)}", exc_info=True)
            return {"code": "ERROR", "message": str(e)}

    async def reschedule_appointment(self, appointment_id: str, new_datetime: datetime) -> dict:
        """Reschedules an existing appointment to a new available datetime slot."""
        engine_logger.info(f"Rescheduling appointment {appointment_id} to {new_datetime}")

        try:
            # 1. Fetch Appointment
            stmt = select(Appointment).where(Appointment.id == appointment_id)
            appointment = (await self.db.execute(stmt)).scalar_one_or_none()
            if not appointment:
                return {"code": "NOT_FOUND", "message": f"Appointment {appointment_id} not found."}

            # 2. Verify Availability for the new slot
            search_date = new_datetime.date()
            target_time = new_datetime.time()

            available_slots = await self.scheduling.get_available_slots(appointment.doctor_id, search_date)
            slot_is_free = any(slot.start_time == target_time for slot in available_slots)

            if not slot_is_free:
                nearest_slot = None
                if available_slots:
                    from datetime import datetime as dt_type
                    target_dt = dt_type.combine(search_date, target_time)
                    nearest = min(
                        available_slots,
                        key=lambda s: abs(
                            (dt_type.combine(search_date, s.start_time) - target_dt).total_seconds()
                        )
                    )
                    nearest_slot = nearest.start_time.strftime("%I:%M %p")
                return {
                    "code": "SLOT_FULL",
                    "message": f"The new requested time slot {target_time} on {search_date} is not available.",
                    "nearest_slot": nearest_slot or "कोई slot उपलब्ध नहीं"
                }

            # 3. Record Status Change
            status_history = AppointmentStatusHistory(
                id=str(uuid.uuid4()),
                appointment_id=appointment_id,
                previous_status=appointment.status,
                new_status="RESCHEDULED",
                change_reason="Rescheduled via Voice Receptionist"
            )
            self.db.add(status_history)

            # 4. Update Datetime and status
            appointment.appointment_datetime = new_datetime
            appointment.status = "RESCHEDULED"
            await self.db.flush()
            await self.db.refresh(appointment)

            engine_logger.info(f"Appointment {appointment_id} rescheduled to {new_datetime}.")
            return {
                "code": "RESCHEDULED",
                "appointment_id": appointment_id,
                "new_datetime": new_datetime.isoformat()
            }

        except Exception as e:
            engine_logger.error(f"Error rescheduling appointment {appointment_id}: {str(e)}", exc_info=True)
            return {"code": "ERROR", "message": str(e)}
