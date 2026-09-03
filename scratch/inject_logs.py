import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Inject console logs into main useEffect and 5s auto-refresh interval
old_main_effect = '''  useEffect(() => {
    if (token) {
      fetchDoctorsAndDepartments();
      fetchAppointments();
      fetchHospitals();
      fetchHospitalStats();
      fetchDepartments();
      fetchLeaves();
      fetchActiveHospitalProfile();
      if (hospitalId) {
        fetchHospitalStaff(hospitalId);
      }
    }
  }, [token, refreshTrigger, hospitalId, fetchDoctorsAndDepartments, fetchAppointments, fetchHospitals, fetchHospitalStats, fetchDepartments, fetchLeaves, fetchActiveHospitalProfile]);'''

new_main_effect = '''  useEffect(() => {
    if (token) {
      console.log("[DEBUG] Main Data Fetch Effect triggered. Fetching dashboard state...");
      fetchDoctorsAndDepartments();
      fetchAppointments();
      fetchHospitals();
      fetchHospitalStats();
      fetchDepartments();
      fetchLeaves();
      fetchActiveHospitalProfile();
      if (hospitalId) {
        fetchHospitalStaff(hospitalId);
      }
    }
  }, [token, refreshTrigger, hospitalId, fetchDoctorsAndDepartments, fetchAppointments, fetchHospitals, fetchHospitalStats, fetchDepartments, fetchLeaves, fetchActiveHospitalProfile]);'''

old_refresh_effect = '''  // Auto-refresh receptionist queue every 5 seconds
  useEffect(() => {
    if (token && userRole === 'RECEPTIONIST') {
      const interval = setInterval(() => {
        fetchAppointments();
        fetchDoctorsAndDepartments();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [token, userRole, fetchAppointments, fetchDoctorsAndDepartments]);'''

new_refresh_effect = '''  // Auto-refresh receptionist queue every 5 seconds
  useEffect(() => {
    if (token && userRole === 'RECEPTIONIST') {
      console.log("[DEBUG] Initializing 5s Receptionist auto-refresh timer");
      const interval = setInterval(() => {
        console.log("[DEBUG 5s AUTO-REFRESH] Refreshing appointments & doctors list safely...");
        fetchAppointments();
        fetchDoctorsAndDepartments();
      }, 5000);
      return () => {
        console.log("[DEBUG] Cleaning up 5s Receptionist auto-refresh timer");
        clearInterval(interval);
      };
    }
  }, [token, userRole, fetchAppointments, fetchDoctorsAndDepartments]);'''

if old_main_effect in content:
    content = content.replace(old_main_effect, new_main_effect)

if old_refresh_effect in content:
    content = content.replace(old_refresh_effect, new_refresh_effect)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected debug console logs into App.jsx useEffect hooks.")
