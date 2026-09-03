import re

app_jsx_path = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(app_jsx_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at top
if 'import LoginPage' not in content:
    content = "import LoginPage from './pages/LoginPage';\n" + content

# Replace !token section in App.jsx
login_regex = r'\{/\* AUTH: shown when not logged in \*/\}.*?\{/\* DASHBOARD: shown when logged in \*/\}'

login_replacement = '''{/* AUTH: shown when not logged in */}
        {!token && (
          <LoginPage 
            loginRole={loginRole}
            setLoginRole={setLoginRole}
            loginUsername={loginUsername}
            setLoginUsername={setLoginUsername}
            loginPassword={loginPassword}
            setLoginPassword={setLoginPassword}
            showLoginPassword={showLoginPassword}
            setShowLoginPassword={setShowLoginPassword}
            loginError={loginError}
            handleLogin={handleLogin}
            showRegisterHospital={showRegisterHospital}
            setShowRegisterHospital={setShowRegisterHospital}
            hospName={hospName}
            setHospName={setHospName}
            hospPhone={hospPhone}
            setHospPhone={setHospPhone}
            hospAddress={hospAddress}
            setHospAddress={setHospAddress}
            hospAdminUsername={hospAdminUsername}
            setHospAdminUsername={setHospAdminUsername}
            hospAdminEmail={hospAdminEmail}
            setHospAdminEmail={setHospAdminEmail}
            hospAdminPassword={hospAdminPassword}
            setHospAdminPassword={setHospAdminPassword}
            selectedPlan={selectedPlan}
            setSelectedPlan={setSelectedPlan}
            onboardError={onboardError}
            onboardSuccess={onboardSuccess}
            handleRegisterHospital={handleRegisterHospital}
            t={t}
          />
        )}

        {/* DASHBOARD: shown when logged in */}'''

content = re.sub(login_regex, login_replacement, content, flags=re.DOTALL)

with open(app_jsx_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("LoginPage component connected to App.jsx.")
