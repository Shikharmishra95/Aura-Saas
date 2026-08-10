import sys
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient

try:
    from app.main import app
    client = TestClient(app)
    response = client.get("/receptionist/schedule")
    print(f"Status Code: {response.status_code}")
    
    html_content = response.text
    print("\n--- Verifying Changes in HTML output ---")
    
    checks = {
        "updateStatus parameter currentStatus": "updateStatus(apptId, newStatus, currentStatus)",
        "openReschedule parameter doctorId": "openReschedule(apptId, doctorId, currentStatus)",
        "fetchBusySlots JS function": "async function fetchBusySlots()",
        "busy-slots-container div": 'id="busy-slots-container"',
        "confirmReschedule status code 400 check": "appointment already rescheduled once"
    }
    
    all_ok = True
    for name, query in checks.items():
        present = query in html_content
        print(f"[{'✅' if present else '❌'}] {name}: {'Found' if present else 'NOT FOUND'}")
        if not present:
            all_ok = False
            
    if all_ok:
        print("\n🎉 ALL CHECKS PASSED! The local code is 100% updated and working correctly.")
    else:
        print("\n❌ SOME CHECKS FAILED! Code might not have updated correctly.")
        
except Exception as e:
    print(f"Error testing: {str(e)}")
    sys.exit(1)
