import uuid
import asyncio
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.logging import logger
from app.database.models.call_log import User, Role, UserRole
from app.database.models.appointment import Appointment, Patient, Doctor, Department, Hospital, AppointmentStatusHistory

router = APIRouter(tags=["payment"])


class PaymentOrderRequest(BaseModel):
    appointment_id: str
    amount: int


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    appointment_id: str


@router.post("/payment/create-order", tags=["payment"])
async def create_razorpay_order(
    appt: str = Query(..., description="Appointment ID"),
    db: AsyncSession = Depends(get_db)
):
    """Creates a Razorpay Order and returns order_id + key_id to the frontend."""
    import razorpay

    stmt = select(Appointment).where(Appointment.id == appt)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appointment.status == "SCHEDULED":
        return {"already_paid": True}

    doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
    doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()
    amount_inr = doctor.opd_fees if (doctor and doctor.opd_fees is not None) else 500
    amount_paise = amount_inr * 100

    order_id = None
    if settings.RAZORPAY_KEY_SECRET:
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"rcpt_{appointment.id[-8:]}",
                "notes": {
                    "appointment_id": appointment.id,
                    "doctor": appointment.doctor_id
                }
            }
            order = await asyncio.to_thread(client.order.create, data=order_data)
            order_id = order["id"]
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {str(e)}")

    return {
        "order_id": order_id,
        "key_id": settings.RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "amount_inr": amount_inr,
        "appointment_id": appointment.id,
        "currency": "INR"
    }


@router.post("/payment/verify", tags=["payment"])
async def verify_razorpay_payment(
    razorpay_order_id: Optional[str] = Form(None),
    razorpay_payment_id: str = Form(...),
    razorpay_signature: Optional[str] = Form(None),
    appointment_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Verifies Razorpay payment signature, marks appointment SCHEDULED, sends WhatsApp, and triggers AI intake call."""
    if settings.RAZORPAY_KEY_SECRET:
        if razorpay_order_id and razorpay_signature:
            key_secret = settings.RAZORPAY_KEY_SECRET.encode()
            message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
            expected_sig = hmac.new(key_secret, message, hashlib.sha256).hexdigest()
            if expected_sig != razorpay_signature:
                raise HTTPException(status_code=400, detail="Payment signature verification failed.")
        elif getattr(settings, 'ENVIRONMENT', 'development') == 'production':
            raise HTTPException(status_code=400, detail="Missing required payment signature verification parameters.")

    stmt = select(Appointment).where(Appointment.id == appointment_id)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    if appointment.status == "SCHEDULED":
        return {"success": True, "message": "Already confirmed"}

    old_status = appointment.status
    appointment.status = "SCHEDULED"
    appointment.updated_at = datetime.now()

    status_history = AppointmentStatusHistory(
        id=str(uuid.uuid4()),
        appointment_id=appointment.id,
        previous_status=old_status,
        new_status="SCHEDULED",
        change_reason=f"Razorpay payment verified. Payment ID: {razorpay_payment_id}"
    )
    db.add(status_history)
    await db.flush()

    patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
    patient = (await db.execute(patient_stmt)).scalar_one_or_none()
    doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
    doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()

    await db.commit()

    if patient and doctor:
        from app.services.whatsapp import WhatsAppNotificationService
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "appointment_id": appointment.id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": appointment.reason
        }
        asyncio.create_task(wa_service.send_payment_confirmation(wa_details))

        async def start_whatsapp_intake():
            await asyncio.sleep(5)
            try:
                from app.services.whatsapp_intake import get_intake_service
                intake_svc = get_intake_service()
                await intake_svc.start_intake_conversation(
                    appointment_id=appointment.id,
                    patient_name=f"{patient.first_name} {patient.last_name}".strip(),
                    patient_phone=patient.phone,
                    doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}",
                    appointment_datetime=appointment.appointment_datetime.isoformat()
                )
            except Exception as intake_err:
                logger.error(f"WhatsApp intake start failed (non-critical): {str(intake_err)}")

        asyncio.create_task(start_whatsapp_intake())

    return {
        "success": True,
        "message": "Payment verified. Appointment confirmed. WhatsApp intake conversation started.",
        "phone": patient.phone if patient else ""
    }


@router.post("/payment/confirm/{appointment_id}", tags=["payment"])
async def payment_confirmation_webhook(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirms counter / manual cash payment for an appointment.
    Protected: Requires authenticated staff (RECEPTIONIST, ADMIN) or SUPER_ADMIN.
    Enforces tenant isolation: staff cannot confirm payments for other hospitals.
    Updates appointment payment status to PAID and dispatches WhatsApp notification.
    """
    from app.services.whatsapp import WhatsAppNotificationService

    # 1. Enforce RBAC
    role_stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    roles = set((await db.execute(role_stmt)).scalars().all())

    is_super_admin = "SUPER_ADMIN" in roles or current_user.hospital_id == "super_admin"
    is_authorized_staff = bool(roles.intersection({"RECEPTIONIST", "ADMIN"}))

    if not is_super_admin and not is_authorized_staff:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Only Receptionist, Hospital Admin, or SuperAdmin can confirm counter payments."
        )

    # 2. Lookup appointment
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    appointment = (await db.execute(stmt)).scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")

    # 3. Enforce tenant isolation
    if not is_super_admin and appointment.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cannot confirm payment for an appointment belonging to another hospital."
        )

    if appointment.status == "SCHEDULED" and appointment.payment_status == "PAID":
        return {"success": True, "message": "Already confirmed", "phone": "N/A"}

    try:
        old_status = appointment.status
        appointment.payment_status = "PAID"
        if appointment.status == "PENDING_PAYMENT":
            appointment.status = "SCHEDULED"
        appointment.updated_at = datetime.now()

        status_history = AppointmentStatusHistory(
            id=str(uuid.uuid4()),
            appointment_id=appointment.id,
            previous_status=old_status,
            new_status="SCHEDULED" if appointment.status == "SCHEDULED" else old_status,
            changed_by_user_id=current_user.id,
            change_reason=f"Counter payment confirmed by {current_user.username}"
        )
        db.add(status_history)
        await db.flush()

        patient_stmt = select(Patient).where(Patient.id == appointment.patient_id)
        patient = (await db.execute(patient_stmt)).scalar_one_or_none()
        doctor_stmt = select(Doctor).where(Doctor.id == appointment.doctor_id)
        doctor = (await db.execute(doctor_stmt)).scalar_one_or_none()

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to confirm payment for appointment {appointment_id}: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="Internal error during payment confirmation.")

    if patient and doctor:
        wa_service = WhatsAppNotificationService()
        wa_details = {
            "appointment_id": appointment.id,
            "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_phone": patient.phone,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "reason": appointment.reason
        }
        try:
            await wa_service.send_payment_confirmation(wa_details)
        except Exception as wa_err:
            logger.error(f"WhatsApp payment confirmation failed: {str(wa_err)}")

    return {
        "success": True,
        "message": "Payment confirmed and WhatsApp dispatched.",
        "phone": patient.phone if patient else ""
    }


@router.get("/payment/checkout", response_class=HTMLResponse, tags=["payment"])
async def payment_checkout_page(
    appt: str = Query(..., description="Full ID or last 8 characters of the appointment ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Simulated CP Tiwari Hospital payment checkout page.
    Renders details, billing amount, and Razorpay modal integration.
    """
    if len(appt.strip()) == 8:
        stmt = (
            select(Appointment, Patient, Doctor, Department, Hospital)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Hospital, Appointment.hospital_id == Hospital.id)
            .where(Appointment.id.like(f"%{appt.strip()}"))
        )
    else:
        stmt = (
            select(Appointment, Patient, Doctor, Department, Hospital)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Doctor, Appointment.doctor_id == Doctor.id)
            .join(Department, Doctor.department_id == Department.id)
            .join(Hospital, Appointment.hospital_id == Hospital.id)
            .where(Appointment.id == appt.strip())
        )

    res = (await db.execute(stmt)).first()
    if not res:
        return HTMLResponse(
            content="<h3>त्रुटि (Error): अपॉइंटमेंट नहीं मिला। कृपया लिंक दोबारा जांचें।</h3>",
            status_code=404
        )

    appointment, patient, doctor, department, hospital = res
    appt_display_time = appointment.appointment_datetime.strftime("%d %b %Y, %I:%M %p")
    amount = doctor.opd_fees if (doctor and doctor.opd_fees is not None) else 500

    if appointment.status == "SCHEDULED":
        return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>पेमेंट रसीद — {hospital.name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #f0f5fc; color: #0f172a; padding: 40px 20px; text-align: center; }}
        .card {{ background: white; max-width: 480px; margin: 0 auto; padding: 40px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; }}
        .success-icon {{ font-size: 56px; color: #16a34a; margin-bottom: 20px; }}
        h2 {{ font-size: 22px; font-weight: 800; color: #0f3276; margin-bottom: 12px; }}
        p {{ color: #64748b; font-size: 14px; margin-bottom: 24px; line-height: 1.5; }}
        .details {{ text-align: left; background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 24px; border: 1px dashed #cbd5e1; }}
        .detail-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; }}
        .detail-row:last-child {{ margin-bottom: 0; }}
        .label {{ color: #64748b; font-weight: 500; }}
        .val {{ color: #0f172a; font-weight: 700; }}
        .badge {{ background: #dcfce7; color: #16a34a; padding: 4px 10px; border-radius: 8px; font-weight: 700; }}
        .btn {{ display: inline-block; background: #0f3276; color: white; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 10px; }}
        .btn:hover {{ background: #1a4fa0; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="success-icon">🎉</div>
        <h2>पेमेंट पहले ही हो चुका है!</h2>
        <p>इस अपॉइंटमेंट के लिए पेमेंट सफलतापूर्वक प्राप्त हो चुका है और अपॉइंटमेंट कन्फर्म है।</p>
        <div class="details">
            <div class="detail-row"><span class="label">मरीज़:</span><span class="val">{patient.first_name} {patient.last_name}</span></div>
            <div class="detail-row"><span class="label">डॉक्टर:</span><span class="val">Dr. {doctor.first_name} {doctor.last_name}</span></div>
            <div class="detail-row"><span class="label">समय:</span><span class="val">{appt_display_time}</span></div>
            <div class="detail-row"><span class="label">राशि:</span><span class="val">₹{amount} (Paid)</span></div>
            <div class="detail-row"><span class="label">स्थिति:</span><span class="val"><span class="badge">कन्फर्म (Confirmed)</span></span></div>
        </div>
        <a href="/receptionist/schedule" class="btn">डैशबोर्ड पर जाएं</a>
    </div>
</body>
</html>""")

    checkout_html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>सुरक्षित भुगतान द्वार (Checkout) — {hospital.name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a4fa0;
            --primary-dark: #0f3276;
            --primary-light: #dbeafe;
            --bg: #f0f5fc;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --radius: 16px;
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .checkout-box {{
            background: white;
            width: 100%;
            max-width: 480px;
            border-radius: var(--radius);
            box-shadow: 0 10px 30px rgba(15,50,118,0.12);
            border: 1px solid var(--border);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #0f3276 0%, #1a4fa0 100%);
            padding: 24px;
            color: white;
            text-align: center;
        }}
        .header h2 {{ font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }}
        .header p {{ font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 4px; }}
        .body {{
            padding: 28px;
        }}
        .summary-card {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }}
        .summary-title {{
            font-size: 13px;
            font-weight: 700;
            color: var(--primary-dark);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 14px;
            border-bottom: 1.5px solid var(--primary-light);
            padding-bottom: 6px;
        }}
        .summary-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 13.5px;
        }}
        .summary-row:last-child {{ margin-bottom: 0; }}
        .label {{ color: var(--text-muted); font-weight: 500; }}
        .value {{ color: var(--text); font-weight: 700; }}
        
        .amount-card {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            padding: 16px 20px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .amount-label {{ font-size: 14px; font-weight: 600; color: var(--primary-dark); }}
        .amount-val {{ font-size: 24px; font-weight: 800; color: var(--primary-dark); }}

        .pay-btn {{
            width: 100%;
            background: #16a34a;
            color: white;
            border: none;
            padding: 14px 20px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
            box-shadow: 0 4px 12px rgba(22,163,74,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .pay-btn:hover {{ background: #15803d; }}
        .pay-btn:disabled {{ background: #a3a3a3; cursor: not-allowed; box-shadow: none; }}
        
        .footer {{
            text-align: center;
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 20px;
        }}
    </style>
</head>
<body>

    <div class="checkout-box">
        <div class="header">
            <h2>🏥 {hospital.name}</h2>
            <p>सुरक्षित ओपीडी भुगतान पोर्टल (Secure Payment Gateway)</p>
        </div>
        <div class="body">
            <div class="summary-card">
                <div class="summary-title">अपॉइंटमेंट सारांश</div>
                <div class="summary-row">
                    <span class="label">मरीज़ का नाम:</span>
                    <span class="value">{patient.first_name} {patient.last_name}</span>
                </div>
                <div class="summary-row">
                    <span class="label">मोबाइल नंबर:</span>
                    <span class="value">{patient.phone}</span>
                </div>
                <div class="summary-row">
                    <span class="label">डॉक्टर का नाम:</span>
                    <span class="value">Dr. {doctor.first_name} {doctor.last_name} ({department.name})</span>
                </div>
                <div class="summary-row">
                    <span class="label">दिनांक व समय:</span>
                    <span class="value">{appt_display_time}</span>
                </div>
                <div class="summary-row">
                    <span class="label">भुगतान स्थिति:</span>
                    <span class="value" style="color: #d97706;">⏳ Payment Pending</span>
                </div>
            </div>

            <div class="amount-card">
                <span class="amount-label">कुल भुगतान राशि:</span>
                <span class="amount-val">₹{amount}</span>
            </div>

            <button class="pay-btn" id="payBtn" onclick="processPayment()">
                🔒 भुगतान करें (Pay ₹{amount})
            </button>
            
            <div class="footer">
                🛡️ PCI-DSS अनुपालन • 256-Bit SSL सुरक्षित एन्क्रिप्शन
            </div>
        </div>
    </div>

    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script>
        async function processPayment() {{
            const btn = document.getElementById('payBtn');
            btn.disabled = true;
            btn.textContent = '🔄 Order बन रहा है...';

            try {{
                const orderRes = await fetch('/payment/create-order?appt={appointment.id}', {{
                    method: 'POST'
                }});
                const orderData = await orderRes.json();

                if (orderData.already_paid) {{
                    document.body.innerHTML = `<div style="text-align:center;padding:60px;font-family:Inter,sans-serif"><div style="font-size:56px">🎉</div><h2 style="color:#0f3276">पेमेंट पहले हो चुका है!</h2><p style="color:#64748b">आपकी अपॉइंटमेंट पहले से Confirmed है।</p></div>`;
                    return;
                }}

                const options = {{
                    key: orderData.key_id || 'rzp_test_TDfSGFZwtVgpme',
                    amount: orderData.amount,
                    currency: orderData.currency,
                    name: '{hospital.name}',
                    description: 'OPD Appointment Fee',
                    handler: async function(response) {{
                        const formData = new FormData();
                        if (response.razorpay_order_id) {{
                            formData.append('razorpay_order_id', response.razorpay_order_id);
                        }}
                        formData.append('razorpay_payment_id', response.razorpay_payment_id);
                        if (response.razorpay_signature) {{
                            formData.append('razorpay_signature', response.razorpay_signature);
                        }}
                        formData.append('appointment_id', '{appointment.id}');

                        btn.textContent = '✅ पेमेंट सत्यापित हो रहा है...';
                        const verifyRes = await fetch('/payment/verify', {{
                            method: 'POST',
                            body: formData
                        }});
                        if (verifyRes.ok) {{
                            window.location.reload();
                        }} else {{
                            alert('Payment verification failed.');
                            btn.disabled = false;
                            btn.textContent = '🔒 भुगतान करें (Pay ₹{amount})';
                        }}
                    }},
                    prefill: {{
                        name: "{patient.first_name} {patient.last_name}",
                        contact: "{patient.phone}"
                    }},
                    theme: {{
                        color: "#0f3276"
                    }}
                }};
                
                const rzp1 = new Razorpay(options);
                rzp1.on('payment.failed', function (response){{
                    alert("Payment Failed: " + response.error.description);
                    btn.innerHTML = '🔒 भुगतान करें (Pay ₹{amount})';
                    btn.disabled = false;
                }});
                
                rzp1.open();
            }} catch (e) {{
                alert("Error connecting to payment gateway.");
                btn.disabled = false;
                btn.textContent = '🔒 भुगतान करें (Pay ₹{amount})';
            }}
        }}
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=checkout_html)
