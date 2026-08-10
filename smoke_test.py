import requests
import json
import sys
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def test_health():
    print("Testing /api/v1/health...")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/health")
        print(f"Status: {r.status_code}")
        print(f"Content: {r.json()}")
        return r.status_code == 200 and r.json().get("status") == "healthy"
    except Exception as e:
        print(f"Failed: {e}")
        return False

def test_login():
    print("\nTesting Staff Login...")
    try:
        data = {
            "username": "recep",
            "password": "#@112233"
        }
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", data=data)
        print(f"Status: {r.status_code}")
        res = r.json()
        print(f"Access Token: {res.get('access_token')[:15]}...")
        return res.get("access_token")
    except Exception as e:
        print(f"Failed: {e}")
        return None

def test_receptionist_booking(token):
    print("\nTesting Receptionist Booking...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        appt_time = f"{tomorrow}T14:30:00"
        
        payload = {
            "patient_name": "Smoke Test Receptionist Patient",
            "patient_phone": "9999999999",
            "patient_gender": "Male",
            "patient_dob": "1995-05-15",
            "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
            "appointment_datetime": appt_time,
            "reason": "Routine Checkup",
            "payment_mode": "CASH",
            "hospital_id": "HOSP-BALA-7282"
        }
        
        r = requests.post(f"{BASE_URL}/api/v1/receptionist/book-appointment", json=payload, headers=headers)
        print(f"Status: {r.status_code}")
        res = r.json()
        print(f"Response: {res}")
        return r.status_code == 200 and res.get("success") == True, res.get("appointment_id")
    except Exception as e:
        print(f"Failed: {e}")
        return False, None

def test_patient_portal_auth():
    print("\nTesting Patient Portal Auth...")
    try:
        # 1. Send OTP
        print("Sending OTP to patient...")
        send_payload = {
            "phone": "9999999999",
            "hospital_id": "HOSP-BALA-7282"
        }
        r1 = requests.post(f"{BASE_URL}/api/v1/patient/send-otp", json=send_payload)
        print(f"Send OTP Status: {r1.status_code}")
        
        # 2. Verify OTP
        print("Verifying OTP...")
        verify_payload = {
            "phone": "9999999999",
            "hospital_id": "HOSP-BALA-7282",
            "otp": "1234",
            "name": "Smoke Test Receptionist Patient",
            "age": 30
        }
        r2 = requests.post(f"{BASE_URL}/api/v1/patient/verify-otp", json=verify_payload)
        print(f"Verify OTP Status: {r2.status_code}")
        res2 = r2.json()
        patient_token = res2.get("access_token")
        print(f"Patient Token: {patient_token[:15]}...")
        return patient_token
    except Exception as e:
        print(f"Failed: {e}")
        return None

def test_patient_booking_and_duplicate(patient_token):
    print("\nTesting Patient Booking & Duplicate Prevention...")
    try:
        headers = {"Authorization": f"Bearer {patient_token}"}
        profile_res = requests.get(f"{BASE_URL}/api/v1/patient/profile", headers=headers)
        patient_id = profile_res.json().get("id")
        
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        appt_time = f"{tomorrow}T15:30:00"
        
        booking_payload = {
            "hospital_id": "HOSP-BALA-7282",
            "patient_id": patient_id,
            "doctor_id": "53224cae-13cf-42ac-8e4b-04ead468bef7",
            "appointment_datetime": appt_time,
            "reason": "Routine Dental Checkup",
            "payment_mode": "ONLINE"
        }
        
        # Attempt 1
        print("Sending first patient booking attempt...")
        r1 = requests.post(f"{BASE_URL}/api/v1/patient/appointments", json=booking_payload, headers=headers)
        print(f"Status: {r1.status_code}")
        res1 = r1.json()
        print(f"Response: {res1}")
        
        # Attempt 2 (Duplicate check)
        print("Sending duplicate patient booking attempt...")
        r2 = requests.post(f"{BASE_URL}/api/v1/patient/appointments", json=booking_payload, headers=headers)
        print(f"Status: {r2.status_code}")
        res2 = r2.json()
        print(f"Response: {res2}")
        
        success = (r1.status_code == 200) and (r2.status_code == 200 and res2.get("idempotent") == True)
        return success, res1.get("appointment_id")
    except Exception as e:
        print(f"Failed: {e}")
        return False, None

def test_mark_as_paid(token, appt_id):
    print(f"\nTesting Mark as Paid for Appointment {appt_id}...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.post(f"{BASE_URL}/api/v1/payment/confirm/{appt_id}", headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        return r.status_code == 200 and r.json().get("success") == True
    except Exception as e:
        print(f"Failed: {e}")
        return False

def test_consultation_complete(token, appt_id):
    print(f"\nTesting Consultation Complete for Appointment {appt_id}...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "clinical_notes": "Patient is recovery-stable. Heart rhythm checked.",
            "prescription": "Aspirin 75mg daily, Atorvastatin 20mg night",
            "follow_up_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }
        r = requests.post(f"{BASE_URL}/api/v1/appointments/{appt_id}/complete", data=payload, headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        return r.status_code == 200 and r.json().get("success") == True
    except Exception as e:
        print(f"Failed: {e}")
        return False

def test_prescription_fetch(patient_token, appt_id):
    print(f"\nTesting Prescription Fetch for Appointment {appt_id}...")
    try:
        headers = {"Authorization": f"Bearer {patient_token}"}
        r = requests.get(f"{BASE_URL}/api/v1/patient/appointments/{appt_id}/prescription", headers=headers)
        print(f"Status: {r.status_code}")
        res = r.json()
        print(f"Response: {res}")
        return r.status_code == 200 and res.get("has_prescription") == True
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    print("=== STARTING SMOKE TESTS ===")
    results = {}
    
    results["health"] = test_health()
    
    token = test_login()
    results["staff_login"] = token is not None
    
    if token:
        reb_success, reb_appt_id = test_receptionist_booking(token)
        results["receptionist_booking"] = reb_success
        
        if reb_appt_id:
            results["mark_as_paid"] = test_mark_as_paid(token, reb_appt_id)
            results["consultation_complete"] = test_consultation_complete(token, reb_appt_id)
        else:
            results["mark_as_paid"] = False
            results["consultation_complete"] = False
            
        patient_token = test_patient_portal_auth()
        results["patient_portal_auth"] = patient_token is not None
        
        if patient_token:
            pb_success, pb_appt_id = test_patient_booking_and_duplicate(patient_token)
            results["patient_booking"] = pb_success
            results["duplicate_booking"] = pb_success
            
            if reb_appt_id:
                results["prescription_fetch"] = test_prescription_fetch(patient_token, reb_appt_id)
            else:
                results["prescription_fetch"] = False
        else:
            results["patient_booking"] = False
            results["duplicate_booking"] = False
            results["prescription_fetch"] = False
    else:
        results["receptionist_booking"] = False
        results["mark_as_paid"] = False
        results["consultation_complete"] = False
        results["patient_portal_auth"] = False
        results["patient_booking"] = False
        results["duplicate_booking"] = False
        results["prescription_fetch"] = False
        
    print("\n=== SMOKE TEST SUMMARY ===")
    overall_pass = True
    for test, passed in results.items():
        print(f"{test}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            overall_pass = False
            
    print(f"\nOVERALL STATUS: {'PASS' if overall_pass else 'FAIL'}")
    if not overall_pass:
        sys.exit(1)
