import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Scanning App.jsx for unsafe array calls or undefined state references...")

for i, line in enumerate(lines, 1):
    # Check for appointments without List
    if re.search(r'\bappointments\b', line) and not re.search(r'appointmentsList|setAppointmentsList|targetAppointment|prescAppointment|selectedAppointment', line):
        print(f"Line {i}: {line.strip()}")
