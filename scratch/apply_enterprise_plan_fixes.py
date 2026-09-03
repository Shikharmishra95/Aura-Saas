import re

app_jsx_path = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'
app_endpoint_path = r'c:\Users\shiva\Desktop\AAA\app\api\v1\endpoints\appointments.py'

# 1. Update register_hospital in appointments.py to set 15-day expiry for STARTER plan
with open(app_endpoint_path, 'r', encoding='utf-8') as f:
    backend_code = f.read()

backend_code = backend_code.replace(
    'plan_expires_at=datetime.now() + timedelta(days=365)',
    'plan_expires_at=datetime.now() + timedelta(days=15 if selected_plan == "STARTER" else 30 if selected_plan == "PRO" else 365)'
)

with open(app_endpoint_path, 'w', encoding='utf-8') as f:
    f.write(backend_code)
print("Updated backend 15-day free trial expiry logic.")

# 2. Update App.jsx UI elements for AI Voice status, Helpline label, and Admin Plan Banner
with open(app_jsx_path, 'r', encoding='utf-8') as f:
    frontend_code = f.read()

# Fix AI Voice badge logic in Super Admin hospital cards
old_ai_badge = "{hosp.helpline ? '📞 AI Active' : '📵 No AI Line'}"
new_ai_badge = "{(hosp.ai_voice_enabled && hosp.helpline) ? '📞 AI Voice Active' : !hosp.ai_voice_enabled ? '🔒 AI Line Locked' : '📵 No AI Line'}"

if old_ai_badge in frontend_code:
    frontend_code = frontend_code.replace(old_ai_badge, new_ai_badge)

# Update Registration Form input label from "Phone / Helpline *" to "Hospital Contact Phone *"
frontend_code = frontend_code.replace('Phone / Helpline *', 'Hospital Contact Phone *')

# Update Starter Plan card text to specify 15-Day Free Trial
frontend_code = frontend_code.replace("{ id: 'STARTER', title: '🥉 Starter', price: 'Free', docs: 'Max 1 Doctor', ai: '📵 No AI Line', color: '#64748B' }", "{ id: 'STARTER', title: '🥉 Starter', price: '15-Day Free Trial', docs: 'Max 1 Doctor', ai: '📵 AI Line Locked', color: '#64748B' }")

with open(app_jsx_path, 'w', encoding='utf-8') as f:
    f.write(frontend_code)

print("App.jsx updated with 15-Day Free Trial & AI Voice status fixes.")
