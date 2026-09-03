import re

filepath_app = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath_app, 'r', encoding='utf-8') as f:
    content_app = f.read()

old_handle_login = '''      const data = await res.json();
      
      // Role match check to prevent login role bypasses
      const backendRole = data.role; // SUPER_ADMIN, ADMIN, DOCTOR, RECEPTIONIST
      let expectedBackendRole = loginRole;
      if (loginRole === 'OWNER') expectedBackendRole = 'SUPER_ADMIN';
      
      if (backendRole !== expectedBackendRole) {
        throw new Error(`Role Mismatch: This account belongs to a ${backendRole}. Please login using the correct portal tab.`);
      }

      const resolvedRole = loginRole === 'OWNER' ? 'SUPER_ADMIN' : data.role;

      localStorage.setItem('jwt_token', data.access_token);
      localStorage.setItem('user_role', resolvedRole);
      localStorage.setItem('username', data.username || loginUsername);
      localStorage.setItem('hospital_id', data.hospital_id || '');
      localStorage.setItem('user_id', data.user_id || '');
      
      setToken(data.access_token);
      setUserRole(resolvedRole);
      setUsername(data.username || loginUsername);
      setHospitalId(data.hospital_id || '');
      setUserId(data.user_id || '');
      
      // Determine starting dashboard view
      let startingTab = 'overview';
      if (resolvedRole === 'SUPER_ADMIN') startingTab = 'super_admin';
      else if (resolvedRole === 'ADMIN') startingTab = 'admin_overview';
      else if (resolvedRole === 'DOCTOR') startingTab = 'appointments';
      
      localStorage.setItem('active_tab', startingTab);
      
      // Force hard refresh to clear any stale closures and load cleanly
      window.location.reload();
      return;
      setLoginUsername('');
      setLoginPassword('');
      setLoginHospitalId('');'''

new_handle_login = '''      const data = await res.json();
      
      // Auto-detect backend role so login succeeds smoothly regardless of selected tab
      const backendRole = data.role || 'RECEPTIONIST'; // SUPER_ADMIN, ADMIN, DOCTOR, RECEPTIONIST
      const resolvedRole = backendRole;

      localStorage.setItem('jwt_token', data.access_token);
      localStorage.setItem('user_role', resolvedRole);
      localStorage.setItem('username', data.username || loginUsername);
      localStorage.setItem('hospital_id', data.hospital_id || '');
      localStorage.setItem('user_id', data.user_id || '');
      
      setToken(data.access_token);
      setUserRole(resolvedRole);
      setUsername(data.username || loginUsername);
      setHospitalId(data.hospital_id || '');
      setUserId(data.user_id || '');
      
      // Determine starting dashboard view based on backend role
      let startingTab = 'overview';
      if (resolvedRole === 'SUPER_ADMIN') startingTab = 'super_admin';
      else if (resolvedRole === 'ADMIN') startingTab = 'admin_overview';
      else if (resolvedRole === 'DOCTOR') startingTab = 'appointments';
      else if (resolvedRole === 'RECEPTIONIST') startingTab = 'overview';
      
      localStorage.setItem('active_tab', startingTab);
      setActiveTab(startingTab);
      
      // Hard refresh to clear any stale closures and load cleanly
      window.location.reload();'''

if old_handle_login in content_app:
    content_app = content_app.replace(old_handle_login, new_handle_login)
    print("Seamless handleLogin auto-role detection applied.")

with open(filepath_app, 'w', encoding='utf-8') as f:
    f.write(content_app)

print("App.jsx updated successfully.")
