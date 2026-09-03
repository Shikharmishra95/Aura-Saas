import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace appointments.filter with appointmentsList.filter
content = content.replace('appointments.filter', 'appointmentsList.filter')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx appointments -> appointmentsList ReferenceError fix completed.")
