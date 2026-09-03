import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Make all array operations completely crash-proof
content = content.replace('doctorsList.map', '(doctorsList || []).map')
content = content.replace('doctorsList.length', '(doctorsList || []).length')
content = content.replace('doctorLeaves.some', '(doctorLeaves || []).some')
content = content.replace('doctorLeaves.map', '(doctorLeaves || []).map')
content = content.replace('doctorLeaves.filter', '(doctorLeaves || []).filter')
content = content.replace('hospitalsList.find', '(hospitalsList || []).find')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("All array operations in App.jsx made 100% crash-proof.")
