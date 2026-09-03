import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add modular imports at top of App.jsx
modular_imports = '''import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import PatientProfileModal from './components/common/Modals/PatientProfileModal';
'''

if 'import Header' not in content:
    content = modular_imports + content

# Replace Header render block in App.jsx
header_regex = r'<header className="dashboard-header".*?</header>'
header_replacement = '''<Header 
        token={token}
        userRole={userRole}
        username={username}
        lang={lang}
        toggleLanguage={toggleLanguage}
        logout={logout}
        patientSearchQuery={patientSearchQuery}
        setPatientSearchQuery={setPatientSearchQuery}
        patientSearchResults={patientSearchResults}
        setPatientSearchResults={setPatientSearchResults}
        handleSearchPatients={handleSearchPatients}
        setSelectedPatientRecord={setSelectedPatientRecord}
        t={t}
      />'''

content = re.sub(header_regex, header_replacement, content, flags=re.DOTALL)

# Replace Sidebar render block in App.jsx
sidebar_regex = r'<div className="sidebar".*?</div>\s*</div>'
sidebar_replacement = '''<Sidebar 
            token={token}
            userRole={userRole}
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            t={t}
          />'''

# Replace PatientProfileModal render block
patient_profile_modal_snippet = '''{/* Patient Profile & Appointments History Modal */}
      {selectedPatientRecord && ('''

patient_profile_modal_replacement = '''<PatientProfileModal 
        selectedPatientRecord={selectedPatientRecord} 
        setSelectedPatientRecord={setSelectedPatientRecord} 
      />
      {/* Patient Profile & Appointments History Modal */}
      {false && ('''

if patient_profile_modal_snippet in content:
    content = content.replace(patient_profile_modal_snippet, patient_profile_modal_replacement)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Step 1 Modular Components connected to App.jsx.")
