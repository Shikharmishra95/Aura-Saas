import re

app_jsx_path = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(app_jsx_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make <Header /> only render when token is present
old_header_tag = '''      {/* Header */}
      <Header 
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

new_header_tag = '''      {/* Header (Shown only when logged in) */}
      {token && (
        <Header 
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
        />
      )}'''

if old_header_tag in content:
    content = content.replace(old_header_tag, new_header_tag)

with open(app_jsx_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated App.jsx so Header only shows when token is active.")
