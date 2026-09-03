import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at top
if 'import DoctorQueue' not in content:
    content = "import DoctorQueue from './components/doctor/DoctorQueue';\n" + content

# Replace DoctorQueue render block
doctor_render_regex = r'\{/\* ── DOCTOR VIEW: MY APPOINTMENTS QUEUE ── \*/\}.*?\{/\* ── ADMIN OVERVIEW TAB ── \*/\}'

doctor_render_replacement = '''{/* ── DOCTOR VIEW: MY APPOINTMENTS QUEUE ── */}
              {activeTab === 'appointments' && userRole === 'DOCTOR' && (
                <DoctorQueue 
                  appointments={appointments}
                  selectedAppointment={selectedAppointment}
                  setSelectedAppointment={setSelectedAppointment}
                  notesInput={notesInput}
                  setNotesInput={setNotesInput}
                  prescriptionInput={prescriptionInput}
                  setPrescriptionInput={setPrescriptionInput}
                  followUpDate={followUpDate}
                  setFollowUpDate={setFollowUpDate}
                  handleCompleteConsultation={handleCompleteConsultation}
                  handleCancelAppointment={handleCancelAppointment}
                  selectedDate={selectedDate}
                  setSelectedDate={setSelectedDate}
                  t={t}
                />
              )}

              {/* ── ADMIN OVERVIEW TAB ── */}'''

content = re.sub(doctor_render_regex, doctor_render_replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("DoctorQueue component connected to App.jsx.")
