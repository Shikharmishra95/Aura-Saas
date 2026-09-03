import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update fetchDoctorsAndDepartments
old_fetch_docs = '''      if (docRes.ok) {
        const docs = await docRes.json();
        setDoctorsList(docs);
        const uniqueDepts = Array.from(new Set(docs.map(d => d.department_id))).map(id => ({
          id,
          name: docs.find(d => d.department_id === id)?.department_name || 'General Medicine'
        }));
        setDepartmentsList(uniqueDepts);
      }'''

new_fetch_docs = '''      if (docRes.ok) {
        const docs = await docRes.json();
        const safeDocs = Array.isArray(docs) ? docs : [];
        setDoctorsList(safeDocs);
        const uniqueDepts = Array.from(new Set(safeDocs.map(d => d.department_id))).map(id => ({
          id,
          name: safeDocs.find(d => d.department_id === id)?.department_name || 'General Medicine'
        }));
        setDepartmentsList(uniqueDepts);
      } else {
        setDoctorsList([]);
      }'''

if old_fetch_docs in content:
    content = content.replace(old_fetch_docs, new_fetch_docs)
    print("Updated fetchDoctorsAndDepartments Array check.")

# 2. Update fetchAppointments
old_fetch_appts = '''      if (res.ok) {
        const data = await res.json();
        setAppointmentsList(data);
      }'''

new_fetch_appts = '''      if (res.ok) {
        const data = await res.json();
        setAppointmentsList(Array.isArray(data) ? data : []);
      } else {
        setAppointmentsList([]);
      }'''

if old_fetch_appts in content:
    content = content.replace(old_fetch_appts, new_fetch_appts)
    print("Updated fetchAppointments Array check.")

# 3. Update fetchLeaves
old_fetch_leaves = '''      if (res.ok) {
        const data = await res.json();
        setLeavesList(data);
      }'''

new_fetch_leaves = '''      if (res.ok) {
        const data = await res.json();
        setLeavesList(Array.isArray(data) ? data : []);
      } else {
        setLeavesList([]);
      }'''

if old_fetch_leaves in content:
    content = content.replace(old_fetch_leaves, new_fetch_leaves)
    print("Updated fetchLeaves Array check.")

# 4. Make all array references in App.jsx bulletproof with Array.isArray checks
content = content.replace('(doctorsList || [])', '(Array.isArray(doctorsList) ? doctorsList : [])')
content = content.replace('(appointmentsList || [])', '(Array.isArray(appointmentsList) ? appointmentsList : [])')
content = content.replace('(doctorLeaves || [])', '(Array.isArray(doctorLeaves) ? doctorLeaves : [])')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Root cause array type validation fix applied successfully.")
