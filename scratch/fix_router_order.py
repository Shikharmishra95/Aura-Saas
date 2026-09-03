import re

filepath = r'c:\Users\shiva\Desktop\AAA\app\api\v1\endpoints\appointments.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove line 98 router = APIRouter()
content = content.replace("router = APIRouter()\n", "")

# Add router = APIRouter() right after imports at top
imports_end = "from app.database.models.call_log import User, Role, UserRole\n"
new_imports_end = imports_end + "\nrouter = APIRouter()\n"

if imports_end in content:
    content = content.replace(imports_end, new_imports_end)
    print("Moved router = APIRouter() to top of appointments.py.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
