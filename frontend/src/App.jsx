import LoginPage from './pages/LoginPage';
import DoctorQueue from './components/doctor/DoctorQueue';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import PatientProfileModal from './components/common/Modals/PatientProfileModal';
import ProfileModal from './components/common/ProfileModal';
import CopilotWidget from './components/copilot/CopilotWidget';
import SuperAdminDashboard from './components/superadmin/SuperAdminDashboard';
import HospitalAdminDashboard from './components/admin/HospitalAdminDashboard';
import ReceptionistDashboard from './components/receptionist/ReceptionistDashboard';
import PrescriptionModal from './components/modals/PrescriptionModal';
import RescheduleModal from './components/modals/RescheduleModal';
import CancelAppointmentModal from './components/modals/CancelAppointmentModal';
import UpgradeSubscriptionModal from './components/modals/UpgradeSubscriptionModal';

import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import PatientPortal from './PatientPortal';

// API base - always use relative path (Vite proxy forwards /api → localhost:8000)
const API_BASE = '/api/v1';

import { TRANSLATIONS } from './i18n/translations';
import { formatDoctorTimingsToEnglish } from './utils/formatters';
export { formatDoctorTimingsToEnglish };


function App() {
  const [token, setToken] = useState(localStorage.getItem('jwt_token') || '');
  const [userRole, setUserRole] = useState(localStorage.getItem('user_role') || '');
  const [username, setUsername] = useState(localStorage.getItem('username') || '');
  const [hospitalId, setHospitalId] = useState(localStorage.getItem('hospital_id') || '');
  const [userId, setUserId] = useState(localStorage.getItem('user_id') || '');
  
  const [lang, setLang] = useState(localStorage.getItem('preferred_lang') || 'en');

  const toggleLanguage = () => {
    const newLang = lang === 'en' ? 'hi' : 'en';
    setLang(newLang);
    localStorage.setItem('preferred_lang', newLang);
  };

  const t = (key) => {
    return TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key] || key;
  };
  
  // Login Role / Tab State
  const [loginRole, setLoginRole] = useState('RECEPTIONIST'); // 'OWNER' | 'ADMIN' | 'DOCTOR' | 'RECEPTIONIST'
  const [showRegisterHospital, setShowRegisterHospital] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('STARTER');
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const [upgradingHospId, setUpgradingHospId] = useState(null);
  const [demoCardNum, setDemoCardNum] = useState('4111 2222 3333 4444');
  const [demoCvv, setDemoCvv] = useState('123');
  const [demoExpiry, setDemoExpiry] = useState('12/28');
  const [paymentSuccessMsg, setPaymentSuccessMsg] = useState('');


  // Forms state
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [loginHospitalId, setLoginHospitalId] = useState('');
  const [loginError, setLoginError] = useState('');

  // Hospital Onboarding State
  const [hospName, setHospName] = useState('');
  const [hospAddress, setHospAddress] = useState('');
  const [hospPhone, setHospPhone] = useState('');
  const [hospAdminUsername, setHospAdminUsername] = useState('');
  const [hospAdminEmail, setHospAdminEmail] = useState('');
  const [hospAdminPassword, setHospAdminPassword] = useState('');
  const [onboardSuccess, setOnboardSuccess] = useState(null); 
  const [onboardError, setOnboardError] = useState('');

  // Super Admin drilldown state
  const [selectedHospital, setSelectedHospital] = useState(null); // null = list view, hosp obj = detail view
  const [superAdminView, setSuperAdminView] = useState('control_tower'); // 'control_tower' | 'hospitals' | 'owners'
  const [hospitalStaff, setHospitalStaff] = useState({ doctors: [], receptionists: [] });
  const [hospitalStaffLoading, setHospitalStaffLoading] = useState(false);

  // Dashboard Tabs
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('active_tab');
    if (saved) return saved;
    const role = localStorage.getItem('user_role') || '';
    if (role === 'SUPER_ADMIN') return 'super_admin';
    if (role === 'ADMIN') return 'admin_overview';
    if (role === 'DOCTOR') return 'appointments';
    return 'overview';
  });

  // Shared Lists
  const [doctorsList, setDoctorsList] = useState([]);
  const [departmentsList, setDepartmentsList] = useState([]);
  const [appointmentsList, setAppointmentsList] = useState([]);
  const [hospitalsList, setHospitalsList] = useState([]); 

  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Receptionist Complete & Prescription Modal
  const [prescriptionModalOpen, setPrescriptionModalOpen] = useState(false);
  const [prescAppointment, setPrescAppointment] = useState(null);
  const [prescNotes, setPrescNotes] = useState('');
  const [prescIsViewMode, setPrescIsViewMode] = useState(false);
  const [prescMedicines, setPrescMedicines] = useState('');
  const [prescFollowUp, setPrescFollowUp] = useState('');

  // Receptionist Reschedule Modal
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [targetAppointment, setTargetAppointment] = useState(null);
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [bookedSlots, setBookedSlots] = useState([]);
  const [allSlots, setAllSlots] = useState([]);
  const [selectedSlotTime, setSelectedSlotTime] = useState('');
  const [rescheduleError, setRescheduleError] = useState('');

  // Receptionist Cancel Modal
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelAppointmentId, setCancelAppointmentId] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const [cancelIsPaid, setCancelIsPaid] = useState(false);

  // Staff registration schedule state
  const [hospitalStats, setHospitalStats] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [selectedScheduleDate, setSelectedScheduleDate] = useState(new Date().toISOString().split('T')[0]);
  const [doctorQueueSearch, setDoctorQueueSearch] = useState('');
  // Active Hospital Profile & Settings
  const [activeHospital, setActiveHospital] = useState(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  
  // New Booking Slots Grid state
  const [selectedPatientRecord, setSelectedPatientRecord] = useState(null);
  
  // Edit Profile / Settings Modals state
  
  // Plan Upgrade Modals State
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeSelectedPlan, setUpgradeSelectedPlan] = useState('PRO');
  const [upgradeCheckoutModal, setUpgradeCheckoutModal] = useState(false);
  const [upgradePaymentMethod, setUpgradePaymentMethod] = useState('UPI / QR');
  const [plansList, setPlansList] = useState([]);
  
  // Edit Hospital fields
  
  // Edit Settings fields

  const [currentTime, setCurrentTime] = useState(new Date());

  // Clock timer
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch live subscription plans dynamically from backend
  useEffect(() => {
    const fetchLivePlans = async () => {
      try {
        const res = await fetch(`${API_BASE}/plans`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) setPlansList(data);
        }
      } catch (err) {
        console.error('Failed to fetch live subscription plans:', err);
      }
    };
    fetchLivePlans();
  }, [showUpgradeModal, refreshTrigger]);

  // Persist activeTab across refreshes & sanitize for active userRole
  useEffect(() => {
    if (activeTab) {
      localStorage.setItem('active_tab', activeTab);
    }
  }, [activeTab]);

  useEffect(() => {
    if (userRole === 'RECEPTIONIST' && !['overview', 'new_booking', 'patient_search', 'receptionist_leaves'].includes(activeTab)) {
      setActiveTab('overview');
    } else if (userRole === 'ADMIN' && !['admin_overview', 'staff_management', 'hospital_overview', 'admin_leaves'].includes(activeTab)) {
      setActiveTab('admin_overview');
    } else if (userRole === 'DOCTOR' && !['appointments', 'doctor_leaves'].includes(activeTab)) {
      setActiveTab('appointments');
    } else if (userRole === 'SUPER_ADMIN' && activeTab !== 'super_admin') {
      setActiveTab('super_admin');
    }
  }, [userRole]);

  const safeFormatDate = (dateStr, options = {}) => {
    if (!dateStr) return 'N/A';
    try {
      const parts = String(dateStr).split('T')[0].split('-');
      if (parts.length === 3) {
        const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        if (!isNaN(d.getTime())) {
          return d.toLocaleDateString(typeof lang !== 'undefined' && lang === 'en' ? 'en-IN' : 'hi-IN', options);
        }
      }
      const d = new Date(dateStr);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString(typeof lang !== 'undefined' && lang === 'en' ? 'en-IN' : 'hi-IN', options);
      }
    } catch (e) {}
    return dateStr || 'N/A';
  };

  const translateScheduleString = (rawStr, currentLang) => {
    if (!rawStr) return '';
    let str = rawStr.replace(/Timing:/gi, '').trim();
    if (currentLang === 'hi') {
      return str
        .replace(/Monday|Mon/gi, 'सोम')
        .replace(/Tuesday|Tue/gi, 'मंगल')
        .replace(/Wednesday|Wed/gi, 'बुध')
        .replace(/Thursday|Thu/gi, 'गुरु')
        .replace(/Friday|Fri/gi, 'शुक्र')
        .replace(/Saturday|Sat/gi, 'शनि')
        .replace(/Sunday|Sun/gi, 'रवि');
    } else {
      return str
        .replace(/सोम/g, 'Mon')
        .replace(/मंगल/g, 'Tue')
        .replace(/बुध/g, 'Wed')
        .replace(/गुरु/g, 'Thu')
        .replace(/शुक्र/g, 'Fri')
        .replace(/शनि/g, 'Sat')
        .replace(/रवि/g, 'Sun');
    }
  };



  // Patient Lookup Engine (Search) State
  const [patientSearchQuery, setPatientSearchQuery] = useState('');
  const [patientSearchResults, setPatientSearchResults] = useState(null);
  const [patientSearchLoading, setPatientSearchLoading] = useState(false);
  const [patientSearchError, setPatientSearchError] = useState('');

  // Staff registration form (Hospital Admin)

  // Slot Duration

  // Leaves Management State
  const [leavesList, setLeavesList] = useState([]);
  const [leaveDoctorId, setLeaveDoctorId] = useState('');
  const [leaveStartDate, setLeaveStartDate] = useState('');
  const [leaveEndDate, setLeaveEndDate] = useState('');
  const [leaveReason, setLeaveReason] = useState('');
  const [leaveSuccess, setLeaveSuccess] = useState('');
  const [leaveError, setLeaveError] = useState('');

  // Edit Doctor Modal State

  // Doctor Workspace state
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [intakeData, setIntakeData] = useState(null);
  const [clinicalNotes, setClinicalNotes] = useState('');
  const [prescriptionText, setPrescriptionText] = useState('');
  const [followUpDate, setFollowUpDate] = useState('');
  const [completeSuccess, setCompleteSuccess] = useState('');
  const [completeError, setCompleteError] = useState('');

  // Twilio settings configuration state per Hospital (Owner portal)
  const [twilioAccountSids, setTwilioAccountSids] = useState({});
  const [twilioAuthTokens, setTwilioAuthTokens] = useState({});
  const [showTwilioTokens, setShowTwilioTokens] = useState({});
  const [twilioHelplines, setTwilioHelplines] = useState({});
  const [twilioWhatsappNumbers, setTwilioWhatsappNumbers] = useState({});
  const [metricsDateFilter, setMetricsDateFilter] = useState('');

  const logout = () => {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('username');
    localStorage.removeItem('hospital_id');
    localStorage.removeItem('user_id');
    localStorage.removeItem('active_tab');
    localStorage.setItem('redirect_login', 'true');
    sessionStorage.clear();
    window.location.reload();
  };

  // Secure Authentication API call
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', loginUsername);
      formData.append('password', loginPassword);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });

      if (!res.ok) {
        let errData = {};
        try {
          errData = await res.json();
        } catch (e) {
          errData = { detail: 'Server error. Please check backend logs.' };
        }
        throw new Error(errData.detail || 'Incorrect credentials.');
      }

      const data = await res.json();
      const resolvedRole = data.role || 'RECEPTIONIST';

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
      window.location.reload();
    } catch (err) {
      setLoginError(err.message);
    }
  };


  // Register new hospital tenant
  const handleRegisterHospital = async (e) => {
    e.preventDefault();
    setOnboardError('');
    setOnboardSuccess(null);
    try {
      const formData = new URLSearchParams();
      formData.append('name', hospName);
      formData.append('address', hospAddress);
      formData.append('phone', hospPhone);
      formData.append('admin_username', hospAdminUsername);
      formData.append('admin_email', hospAdminEmail);
      formData.append('admin_password', hospAdminPassword);
      formData.append('plan_name', selectedPlan);

      const res = await fetch(`${API_BASE}/auth/register-hospital`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Hospital registration failed.');
      }

      const data = await res.json();
      setOnboardSuccess(data);
      setHospName('');
      setHospAddress('');
      setHospPhone('');
      setHospAdminUsername('');
      setHospAdminEmail('');
      setHospAdminPassword('');
      return data;
    } catch (err) {
      setOnboardError(err.message);
      throw err;
    }
  };

  // Fetch doctors and departments
  const fetchDoctorsAndDepartments = useCallback(async () => {
    if (!token) return;
    try {
      const docRes = await fetch(`${API_BASE}/doctors`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (docRes.ok) {
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
      }
    } catch (e) {
      console.error(e);
    }
  }, [token]);

  // Fetch appointments list
  const fetchAppointments = useCallback(async () => {
    if (!token) return;
    try {
      const url = userRole === 'DOCTOR' 
        ? `${API_BASE}/appointments?doctor_id=${userId}` 
        : `${API_BASE}/appointments`;
      
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAppointmentsList(Array.isArray(data) ? data : []);
      } else {
        setAppointmentsList([]);
      }
    } catch (e) {
      console.error(e);
    }
  }, [token, userRole, hospitalId, userId]);

  // Fetch hospital stats (Admin only)
  const fetchHospitalStats = useCallback(async (dateVal) => {
    if (userRole !== 'ADMIN') return;
    try {
      const url = dateVal ? `${API_BASE}/hospital/stats?target_date=${dateVal}` : `${API_BASE}/hospital/stats`;
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHospitalStats(data);
      }
    } catch (e) {
      console.error(e);
    }
  }, [token, userRole]);

  // Fetch doctor leaves
  const fetchLeaves = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/leaves`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLeavesList(Array.isArray(data) ? data : []);
      } else {
        setLeavesList([]);
      }
    } catch (e) {
      console.error(e);
    }
  }, [token]);

  // Fetch departments list
  const fetchDepartments = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/departments`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDepartments(data);
      }
    } catch (e) {
      console.error(e);
    }
  }, [token]);

  // Fetch Active Hospital Profile & Settings
  const fetchActiveHospitalProfile = useCallback(async () => {
    if (!token || userRole === 'SUPER_ADMIN') return;
    try {
      const res = await fetch(`${API_BASE}/hospital/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setActiveHospital(data);
        setEditHospitalName(data.name || '');
        setEditHospitalAddress(data.address || '');
        setEditHospitalPhone(data.phone || '');
        setEditHospitalEmail(data.email || '');
        setEditHospitalAdminUsername(data.admin_username || '');
        setEditHospitalAdminPassword(data.admin_password || '');
        
        if (data.settings) {
          setHospSettingsWhatsapp(data.settings.whatsapp_number || '');
          setHospSettingsGreeting(data.settings.greeting_prompt || '');
          setHospSettingsFullPrompt(data.settings.full_custom_prompt || '');
        }
      }
    } catch (e) {
      console.error("Error fetching active hospital profile:", e);
    }
  }, [token, userRole]);

  // Booking slots calculation moved into ReceptionistDashboard

// Fetch hospitals list (Super Admin only)
  const fetchHospitals = useCallback(async () => {
    if (userRole !== 'SUPER_ADMIN') return;
    try {
      const res = await fetch(`${API_BASE}/hospitals`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const finalData = Array.isArray(data) ? data : [];
        setHospitalsList(finalData);
        
        // Pre-populate input states with fetched settings
        const sids = {};
        const tokens = {};
        const helplines = {};
        const whatsappNums = {};
        finalData.forEach(h => {
          sids[h.id] = h.twilio_account_sid || '';
          tokens[h.id] = h.twilio_auth_token || '';
          helplines[h.id] = h.helpline || '';
          whatsappNums[h.id] = h.whatsapp_number || '';
        });
        setTwilioAccountSids(sids);
        setTwilioAuthTokens(tokens);
        setTwilioHelplines(helplines);
        setTwilioWhatsappNumbers(whatsappNums);
      } else {
        setHospitalsList([]);
      }
    } catch (e) {
      console.error(e);
      setHospitalsList([]);
    }
  }, [token, userRole]);

  useEffect(() => {
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
  }, [token, refreshTrigger, hospitalId, fetchDoctorsAndDepartments, fetchAppointments, fetchHospitals, fetchHospitalStats, fetchDepartments, fetchLeaves, fetchActiveHospitalProfile]);

  // Auto-refresh queue every 5 seconds for Receptionist & Doctor
  useEffect(() => {
    if (token && (userRole === 'RECEPTIONIST' || userRole === 'DOCTOR')) {
      const interval = setInterval(() => {
        fetchAppointments();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [token, userRole, fetchAppointments]);

  // Fetch staff for a specific hospital (super admin drilldown)
  const fetchHospitalStaff = async (hospId) => {
    setHospitalStaffLoading(true);
    try {
      const res = await fetch(`${API_BASE}/hospital/staff?hospital_id=${hospId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHospitalStaff(data);
      } else {
        setHospitalStaff({ doctors: [], receptionists: [] });
      }
    } catch (e) {
      console.error(e);
      setHospitalStaff({ doctors: [], receptionists: [] });
    } finally {
      setHospitalStaffLoading(false);
    }
  };

  // Dynamic slots fetch on date select (Reschedule modal)
  const handleDateChangeForReschedule = async (dateStr) => {
    setRescheduleDate(dateStr);
    setSelectedSlotTime('');
    setBookedSlots([]);
    setAllSlots([]);
    if (!targetAppointment || !dateStr) return;
    
    try {
      const res = await fetch(`${API_BASE}/receptionist/booked-slots?doctor_id=${targetAppointment.doctor_id}&date_str=${dateStr}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch booked slots.');
      const data = await res.json();
      setBookedSlots(data.booked_slots || []);
      setAllSlots(data.all_slots || []);
    } catch (err) {
      setRescheduleError(err.message);
    }
  };

  // Perform Reschedule API call
  const executeReschedule = async () => {
    if (!targetAppointment || !rescheduleDate || !selectedSlotTime) {
      setRescheduleError('Select both a date and an available slot.');
      return;
    }
    setRescheduleError('');
    try {
      const timeClean = selectedSlotTime.replace(/(AM|PM)/i, '').trim();
      const isPm = selectedSlotTime.toLowerCase().includes('pm');
      let [hours, minutes] = timeClean.split(':').map(Number);
      if (isPm && hours !== 12) hours += 12;
      if (!isPm && hours === 12) hours = 0;
      
      const pad = (num) => String(num).padStart(2, '0');
      const formattedDatetime = `${rescheduleDate}T${pad(hours)}:${pad(minutes)}:00`;

      const formData = new URLSearchParams();
      formData.append('new_status', 'RESCHEDULED');
      formData.append('new_datetime', formattedDatetime);

      const res = await fetch(`${API_BASE}/appointments/${targetAppointment.id}/status`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Reschedule rejected.');
      }

      setRescheduleModalOpen(false);
      setRefreshTrigger(prev => prev + 1);
      alert('Reschedule completed! WhatsApp confirmation sent to patient.');
    } catch (err) {
      setRescheduleError(err.message);
    }
  };

  // Cancellation action
  const executeCancellation = async () => {
    try {
      const formData = new URLSearchParams();
      formData.append('new_status', 'CANCELLED');
      formData.append('cancellation_reason', cancelReason);

      const res = await fetch(`${API_BASE}/appointments/${cancelAppointmentId}/status`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Cancellation failed.');
      }

      setCancelModalOpen(false);
      setCancelReason('');
      setRefreshTrigger(prev => prev + 1);
      alert('Appointment cancelled. ' + (cancelIsPaid ? 'WhatsApp alert sent with refund timeline (3 working days).' : 'WhatsApp alert sent.'));
    } catch (err) {
      alert(err.message);
    }
  };

  // Staff registration
  // Handle Apply Leave (Doctor or Admin)
  const handleApplyLeave = async (e) => {
    e.preventDefault();
    setLeaveSuccess('');
    setLeaveError('');
    try {
      const res = await fetch(`${API_BASE}/hospital/leaves`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          doctor_id: userRole === 'DOCTOR' ? userId : leaveDoctorId,
          start_date: leaveStartDate,
          end_date: leaveEndDate,
          reason: leaveReason
        })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to apply leave.');
      }
      setLeaveSuccess('Leave marked successfully!');
      setLeaveStartDate('');
      setLeaveEndDate('');
      setLeaveReason('');
      setRefreshTrigger(prev => prev + 1);
    } catch (err) {
      setLeaveError(err.message);
    }
  };

  // Handle Delete Leave
  const handleDeleteLeave = async (leaveId) => {
    if (!window.confirm(t("confirm_del_leave"))) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/leaves/${leaveId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Leave deleted successfully!");
        setRefreshTrigger(prev => prev + 1);
      } else {
        const errData = await res.json();
        alert(errData.detail || "Failed to delete leave.");
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Handle Approve Leave
  const handleApproveLeave = async (leaveId) => {
    if (!window.confirm(t("confirm_appr_leave"))) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/leaves/${leaveId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Leave approved successfully!");
        setRefreshTrigger(prev => prev + 1);
      } else {
        const errData = await res.json();
        alert(errData.detail || "Failed to approve leave.");
      }
    } catch (err) {
      alert("Error approving leave: " + err.message);
    }
  };

  // Handle Reject Leave
  const handleRejectLeave = async (leaveId) => {
    if (!window.confirm(t("confirm_rej_leave"))) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/leaves/${leaveId}/reject`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Leave rejected successfully!");
        setRefreshTrigger(prev => prev + 1);
      } else {
        const errData = await res.json();
        alert(errData.detail || "Failed to reject leave.");
      }
    } catch (err) {
      alert("Error rejecting leave: " + err.message);
    }
  };

  // Handle Delete Staff
  const handleDeleteStaff = async (userId) => {
    if (!window.confirm(t("confirm_del_staff"))) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/staff/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Staff deleted successfully!");
        setRefreshTrigger(prev => prev + 1);
      } else {
        const errData = await res.json();
        alert(errData.detail || "Failed to delete staff.");
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Search Patients (Patient Lookup Engine)
  const handleSearchPatients = async (e) => {
    if (e) e.preventDefault();
    if (!patientSearchQuery.trim()) return;
    setPatientSearchLoading(true);
    setPatientSearchError('');
    try {
      const res = await fetch(`${API_BASE}/hospital/patients/search?query=${encodeURIComponent(patientSearchQuery.trim())}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPatientSearchResults(data);
      } else {
        setPatientSearchError(t('search_failed'));
      }
    } catch (err) {
      setPatientSearchError('Network error while searching patients.');
    } finally {
      setPatientSearchLoading(false);
    }
  };

  // handleNewBooking moved to ReceptionistDashboard

// Select Doctor queue item & fetch details
  const handleSelectDoctorAppointment = async (appt) => {
    setSelectedAppointment(appt);
    setIntakeData(null);
    setClinicalNotes('');
    setPrescriptionText('');
    setCompleteSuccess('');
    setCompleteError('');

    try {
      const res = await fetch(`${API_BASE}/patients/${appt.patient_id}/intake`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIntakeData(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // handleManualPayment & handleMarkSingleMissed moved to ReceptionistDashboard

// Doctor Action: Finish Consultation (Moves status to CONSULTATION_FINISHED)
  const handleDoctorFinishConsultation = async (apptId) => {
    const targetId = typeof apptId === 'string' ? apptId : selectedAppointment?.id;
    if (!targetId) return;

    try {
      const res = await fetch(`${API_BASE}/appointments/${targetId}/finish-consultation`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await res.json();
      if (res.ok) {
        alert("✅ Doctor Consultation Finished! Sent to Receptionist for prescription digitizing & billing.");
        setSelectedAppointment(null);
        setRefreshTrigger(prev => prev + 1);
      } else {
        alert(data.detail || 'Failed to finish consultation.');
      }
    } catch (e) {
      console.error(e);
      alert('Network error: ' + e.message);
    }
  };

  // Receptionist & Universal Action Modal Openers
  const handleOpenPrescriptionModal = (appt, isViewMode = false) => {
    setPrescAppointment(appt);
    setPrescNotes(appt.clinical_notes || '');
    setPrescMedicines(appt.prescription || '');
    setPrescFollowUp(appt.follow_up_date ? appt.follow_up_date.split('T')[0] : '');
    setPrescIsViewMode(isViewMode);
    setPrescriptionModalOpen(true);
  };

  const handleOpenRescheduleModal = (appt) => {
    setTargetAppointment(appt);
    setRescheduleDate('');
    setBookedSlots([]);
    setSelectedSlotTime('');
    setRescheduleError('');
    setRescheduleModalOpen(true);
  };

  const handleOpenCancelModal = (appt) => {
    setCancelAppointmentId(appt.id);
    setCancelReason('');
    setCancelIsPaid(appt.payment_status === 'PAID');
    setCancelModalOpen(true);
  };

  // Complete Consultation API call (used by both doctor and receptionist)
  const handleCompleteConsultation = async (e, customApptId = null, notesInput = null, medicinesInput = null, followUpInput = null) => {
    let targetId = null;
    if (e && typeof e === 'object' && e.preventDefault) {
      e.preventDefault();
      targetId = customApptId || selectedAppointment?.id;
    } else if (typeof e === 'string' || typeof e === 'number') {
      targetId = e;
    } else {
      targetId = customApptId || selectedAppointment?.id;
    }
    
    const finalNotes = notesInput !== null ? notesInput : clinicalNotes;
    const finalPrescription = medicinesInput !== null ? medicinesInput : prescriptionText;
    const finalFollowUp = followUpInput !== null ? followUpInput : followUpDate;

    if (!targetId) {
      alert("Please select an appointment to finish consultation.");
      return;
    }

    try {
      const formData = new URLSearchParams();
      formData.append('clinical_notes', finalNotes);
      formData.append('prescription', finalPrescription);
      if (finalFollowUp) {
        formData.append('follow_up_date', finalFollowUp);
      }

      const res = await fetch(`${API_BASE}/appointments/${targetId}/complete`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Consultation completion failed.');
      }

      if (customApptId) {
        setPrescriptionModalOpen(false);
        setPrescNotes('');
        setPrescMedicines('');
        alert('Consultation completed successfully! Prescription sent to WhatsApp.');
      } else {
        alert('✅ Consultation finished & sent to Receptionist!');
        setCompleteSuccess('Consultation completed successfully! Prescription sent to WhatsApp.');
        setSelectedAppointment(null);
      }
      setRefreshTrigger(prev => prev + 1);
    } catch (err) {
      if (customApptId) {
        alert(err.message);
      } else {
        setCompleteError(err.message);
      }
    }
  };

  const handleMarkMissed = async () => {
    if (!window.confirm("Are you sure you want to mark all past uncompleted appointments as MISSED?")) return;
    try {
      const res = await fetch(`${API_BASE}/appointments/mark-missed`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Successfully marked ${data.marked_count} past appointments as MISSED.`);
        setRefreshTrigger(p => p + 1);
      } else {
        alert("Failed to mark missed appointments.");
      }
    } catch (e) {
      alert("Network error.");
    }
  };

  // handleBulkCancel moved to ReceptionistDashboard

// Owner settings assignment action (Persisted to database)
  const handleSaveTwilioConfig = async (hospId) => {
    const sid = twilioAccountSids[hospId] || '';
    const tokenVal = twilioAuthTokens[hospId] || '';
    const helpline = twilioHelplines[hospId] || '';

    if (!sid || !tokenVal || !helpline) {
      alert('Please fill in Twilio Account SID, Auth Token, and Phone Number.');
      return;
    }

    try {
      const formData = new URLSearchParams();
      formData.append('account_sid', sid);
      formData.append('auth_token', tokenVal);
      formData.append('helpline', helpline);
      if (twilioWhatsappNumbers[hospId]) {
        formData.append('whatsapp_number', twilioWhatsappNumbers[hospId]);
      }

      const res = await fetch(`${API_BASE}/hospitals/${hospId}/twilio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (res.ok) {
        alert(`Twilio credentials configured, saved to Database, & injected successfully for Hospital ID: ${hospId}!`);
        fetchHospitals();
      } else {
        const errData = await res.json();
        alert("Error saving settings: " + (errData.detail || "Unknown error"));
      }
    } catch (e) {
      console.error(e);
      alert("Network error: " + e.message);
    }
  };


  // Upgrade Hospital Subscription Plan (Razorpay Integration)
  const handleRazorpayUpgradePlan = async (hospId, targetPlan) => {
    const matchedPlan = plansList.find(p => p.plan_code === targetPlan);
    let planAmount = matchedPlan ? Number(matchedPlan.price_inr) : 2999;
    if (!matchedPlan) {
      if (targetPlan === 'ENTERPRISE') planAmount = 29999;
      if (targetPlan === 'BASIC' || targetPlan === 'STARTER') planAmount = 1500;
    }

    if (planAmount === 0) {
      await handleUpgradePlan(hospId, targetPlan);
      return;
    }

    const loadRazorpaySDK = () => {
      return new Promise((resolve) => {
        if (window.Razorpay) {
          resolve(true);
          return;
        }
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = () => resolve(true);
        script.onerror = () => resolve(false);
        document.body.appendChild(script);
      });
    };

    const loaded = await loadRazorpaySDK();
    if (!loaded) {
      alert("Failed to load Razorpay Payment Gateway. Please check your internet connection.");
      return;
    }

    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY_ID || "rzp_test_TDfSGFZwtVgpme",
      amount: planAmount * 100, // Amount in paise
      currency: "INR",
      name: activeHospital?.name || "AURA SaaS Hospital Platform",
      description: `Hospital Subscription (${targetPlan} Plan Upgrade)`,
      image: "https://cdn-icons-png.flaticon.com/512/2966/2966327.png",
      prefill: {
        name: username || "Hospital Admin",
        email: activeHospital?.email || "admin@hospital.com",
        contact: activeHospital?.phone || "9532399202"
      },
      theme: {
        color: "#2563EB"
      },
      handler: async function (response) {
        console.log("Razorpay Plan Upgrade Success:", response);
        await handleUpgradePlan(hospId, targetPlan);
      }
    };

    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const handleUpgradePlan = async (hospId, targetPlan) => {
    try {
      const targetId = hospId || hospitalId || activeHospital?.id;
      if (!targetId) {
        alert("Hospital ID not found.");
        return;
      }
      const formData = new URLSearchParams();
      formData.append('plan_name', targetPlan);
      const res = await fetch(`${API_BASE}/hospitals/${targetId}/upgrade-plan`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}` 
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        if (data.subscription_plan) {
          setActiveHospital(prev => ({
            ...(prev || {}),
            subscription_plan: data.subscription_plan,
            max_doctors: data.max_doctors,
            ai_voice_enabled: data.ai_voice_enabled,
            plan_expires_at: data.plan_expires_at,
            days_left: data.days_left,
            is_expired: false
          }));
        }
        setShowUpgradeModal(false);
        alert(data.message || `🎉 Successfully upgraded to ${targetPlan} Plan!`);
        await fetchActiveHospitalProfile();
        if (typeof fetchHospitalStats === 'function') await fetchHospitalStats();
        await fetchHospitals();
        if (hospitalId) {
          await fetchHospitalStaff(hospitalId);
        }
      } else {
        alert(data.detail || 'Plan upgrade failed');
      }
    } catch (e) {
      console.error(e);
      alert('Network error: ' + e.message);
    }
  };

  // Renew Existing Hospital Subscription Plan (Razorpay Integration)
  const handleRazorpayRenewPlan = async (hospId) => {
    const plan = activeHospital?.subscription_plan || 'PRO';
    const matchedPlan = plansList.find(p => p.plan_code === plan);
    let planAmount = matchedPlan ? Number(matchedPlan.price_inr) : 2999;
    if (!matchedPlan) {
      if (plan === 'ENTERPRISE') planAmount = 29999;
      if (plan === 'STARTER' || plan === 'BASIC') planAmount = 1500;
    }

    if (planAmount === 0) {
      await handleRenewPlan(hospId);
      return;
    }

    const loadRazorpaySDK = () => {
      return new Promise((resolve) => {
        if (window.Razorpay) {
          resolve(true);
          return;
        }
        const script = document.createElement('script');
        script.src = 'https://checkout.razorpay.com/v1/checkout.js';
        script.onload = () => resolve(true);
        script.onerror = () => resolve(false);
        document.body.appendChild(script);
      });
    };

    const loaded = await loadRazorpaySDK();
    if (!loaded) {
      alert("Failed to load Razorpay Payment Gateway. Please check your internet connection.");
      return;
    }

    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY_ID || "rzp_test_TDfSGFZwtVgpme",
      amount: planAmount * 100, // Amount in paise
      currency: "INR",
      name: activeHospital?.name || "AURA SaaS Hospital Platform",
      description: `Hospital Subscription Renewal (${plan} Plan — +${plan === 'ENTERPRISE' ? '365' : '30'} Days)`,
      image: "https://cdn-icons-png.flaticon.com/512/2966/2966327.png",
      prefill: {
        name: username || "Hospital Admin",
        email: activeHospital?.email || "admin@hospital.com",
        contact: activeHospital?.phone || "9532399202"
      },
      theme: {
        color: "#059669"
      },
      handler: async function (response) {
        console.log("Razorpay Plan Renewal Success:", response);
        await handleRenewPlan(hospId);
      }
    };

    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const handleRenewPlan = async (hospId) => {
    try {
      const targetId = hospId || hospitalId || activeHospital?.id;
      if (!targetId) {
        alert("Hospital ID not found.");
        return;
      }
      const res = await fetch(`${API_BASE}/hospitals/${targetId}/renew-plan`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}` 
        }
      });
      const data = await res.json();
      if (res.ok) {
        if (data.subscription_plan) {
          setActiveHospital(prev => ({
            ...(prev || {}),
            subscription_plan: data.subscription_plan,
            max_doctors: data.max_doctors,
            ai_voice_enabled: data.ai_voice_enabled,
            plan_expires_at: data.plan_expires_at,
            days_left: data.days_left,
            is_expired: false
          }));
        }
        setShowUpgradeModal(false);
        alert(data.message || `🎉 Subscription renewed successfully!`);
        await fetchActiveHospitalProfile();
        if (typeof fetchHospitalStats === 'function') await fetchHospitalStats();
        await fetchHospitals();
      } else {
        alert(data.detail || 'Plan renewal failed');
      }
    } catch (e) {
      console.error(e);
      alert('Network error: ' + e.message);
    }
  };

  // Delete/Deboard Hospital (Super Admin only)
  const handleDeleteHospital = async (hospId) => {
    if (!window.confirm("Are you sure you want to delete this hospital? All associated doctors and appointments will be permanently removed.")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/hospitals/${hospId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Hospital deleted successfully!");
        setSelectedHospital(null);
        fetchHospitals(); // refresh list
      } else {
        const errData = await res.json();
        alert("Error deleting hospital: " + (errData.detail || "Unknown error"));
      }
    } catch (e) {
      console.error(e);
      alert("Network error: " + e.message);
    }
  };

  // Toggle Active/Inactive Hospital Status (Super Admin only)
  const handleToggleHospitalStatus = async (hospId) => {
    try {
      const res = await fetch(`${API_BASE}/hospitals/${hospId}/toggle-status`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        fetchHospitals(); // refresh list
      } else {
        const errData = await res.json();
        alert("Error toggling status: " + (errData.detail || "Unknown error"));
      }
    } catch (e) {
      console.error(e);
      alert("Network error: " + e.message);
    }
  };

  // Helper to copy webhook URL to clipboard
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('Copied Webhook URL to clipboard!');
  };

  // Resolve webhook url template
  const getWebhookUrl = (hospId) => {
    const domain = window.location.origin.includes('localhost') ? 'https://aura-saas-api.herokuapp.com' : window.location.origin;
    return `${domain}/api/v1/voice/inbound?hospital_id=${hospId}`;
  };
  // --- PATIENT PORTAL ROUTING HIJACK ---
  const currentPath = window.location.pathname;
  if (currentPath.startsWith('/p/') || currentPath.startsWith('/patient')) {
    const parts = currentPath.split('/');
    let rawSlug = parts[2] ? decodeURIComponent(parts[2]).trim() : '';
    if (!rawSlug) {
      const urlParams = new URLSearchParams(window.location.search);
      rawSlug = urlParams.get('slug') || urlParams.get('hospital_id') || '';
    }
    if (!rawSlug) {
      rawSlug = localStorage.getItem('hospital_id') || '';
    }
    const slug = rawSlug ? rawSlug.toLowerCase().replace(/\s+/g, '-') : '';
    
    // Force global reset for Patient Portal to avoid Dashboard CSS leaking
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.body.style.width = '100vw';
    document.body.style.height = '100vh';
    document.body.style.background = '#f0f4f8';
    
    const rootEl = document.getElementById('root');
    if (rootEl) {
      rootEl.style.width = '100%';
      rootEl.style.height = '100%';
      rootEl.style.margin = '0';
      rootEl.style.padding = '0';
    }
    
    return <PatientPortal slug={slug} lang={lang} />;
  }

  return (
    <div className="dashboard-layout">
      {/* Header (Shown only when logged in and not DOCTOR, since DOCTOR has unified executive banner) */}
      {token && userRole !== 'DOCTOR' && (
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
          activeHospital={activeHospital}
          onOpenProfile={() => setIsProfileModalOpen(true)}
          t={t}
        />
      )}

      {/* Main Content */}
      <main style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>

        {/* AUTH: shown when not logged in */}
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

        {/* DASHBOARD: shown when logged in */}
        {token && (
          <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ flexGrow: 1, padding: '0' }}>
              {/* ── HARD SUBSCRIPTION PAYWALL LOCKOUT SCREEN ── */}
              {activeHospital?.is_expired && userRole !== 'SUPER_ADMIN' ? (
                <div style={{
                  maxWidth: '740px',
                  margin: '40px auto',
                  background: '#FFFFFF',
                  borderRadius: '24px',
                  padding: '48px 36px',
                  textAlign: 'center',
                  boxShadow: '0 20px 60px rgba(220, 38, 38, 0.12)',
                  border: '2px solid #FECACA',
                  animation: 'fadeIn 0.4s ease'
                }}>
                  <div style={{
                    width: '80px', height: '80px', borderRadius: '50%',
                    background: '#FEF2F2', border: '2px solid #FCA5A5',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '40px', margin: '0 auto 20px auto'
                  }}>
                    🔒
                  </div>

                  <span style={{
                    background: '#FEE2E2', color: '#DC2626', border: '1.5px solid #FCA5A5',
                    padding: '6px 16px', borderRadius: '20px', fontSize: '12px', fontWeight: 800,
                    letterSpacing: '0.05em', textTransform: 'uppercase'
                  }}>
                    🚨 Service Suspended — Plan Expired
                  </span>

                  <h1 style={{ fontSize: '28px', fontWeight: 900, color: '#0F172A', marginTop: '20px', marginBottom: '8px' }}>
                    {activeHospital?.name || 'Hospital'} Workspace is Locked
                  </h1>

                  <p style={{ color: '#64748B', fontSize: '15px', lineHeight: 1.6, maxWidth: '560px', margin: '0 auto 28px auto' }}>
                    {lang === 'hi'
                      ? `आपके अस्पताल का ${activeHospital?.subscription_plan || 'STARTER'} प्लान ${activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at).toLocaleDateString() : 'समाप्त'} हो चुका है। डॉक्टर शेड्यूलिंग, फ्रंट डेस्क बुकिंग और 24/7 AI वॉइस रिसेप्शन सेवाएं अस्थायी रूप से रोक दी गई हैं।`
                      : `The ${activeHospital?.subscription_plan || 'STARTER'} subscription plan for this hospital expired on ${activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at).toLocaleDateString() : 'recently'}. Automated AI Voice reception, doctor queues, and patient operations are locked until renewed.`}
                  </p>

                  <div style={{
                    background: '#F8FAFC', border: '1.5px solid #E2E8F0', borderRadius: '16px',
                    padding: '18px 24px', display: 'flex', justifyContent: 'space-around',
                    alignItems: 'center', marginBottom: '32px', textAlign: 'left', flexWrap: 'wrap', gap: '16px'
                  }}>
                    <div>
                      <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 700 }}>EXPIRED PLAN</div>
                      <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginTop: '2px' }}>
                        {activeHospital?.subscription_plan || 'STARTER'}
                      </div>
                    </div>
                    <div style={{ height: '36px', width: '1.5px', background: '#E2E8F0' }} />
                    <div>
                      <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 700 }}>EXPIRATION DATE</div>
                      <div style={{ fontSize: '16px', fontWeight: 800, color: '#DC2626', marginTop: '2px' }}>
                        {activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Expired'}
                      </div>
                    </div>
                    <div style={{ height: '36px', width: '1.5px', background: '#E2E8F0' }} />
                    <div>
                      <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 700 }}>SERVICE STATUS</div>
                      <div style={{ fontSize: '16px', fontWeight: 800, color: '#DC2626', marginTop: '2px' }}>
                        ⛔ Suspended
                      </div>
                    </div>
                  </div>

                  {userRole === 'ADMIN' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '440px', margin: '0 auto' }}>
                      <button
                        onClick={() => handleRazorpayRenewPlan(activeHospital?.id || hospitalId)}
                        style={{
                          background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
                          color: '#FFFFFF', border: 'none', borderRadius: '14px', padding: '16px 28px',
                          fontSize: '15px', fontWeight: 800, cursor: 'pointer',
                          boxShadow: '0 4px 18px rgba(16, 185, 129, 0.35)', transition: 'transform 0.15s',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                        }}
                      >
                        💳 {lang === 'hi' ? 'Razorpay से अभी प्लान रिन्यू करें' : `Renew ${activeHospital?.subscription_plan || 'Plan'} Now via Razorpay`}
                      </button>

                      <button
                        onClick={() => setShowUpgradeModal(true)}
                        style={{
                          background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                          color: '#FFFFFF', border: 'none', borderRadius: '14px', padding: '14px 28px',
                          fontSize: '14px', fontWeight: 800, cursor: 'pointer',
                          boxShadow: '0 4px 14px rgba(37, 99, 235, 0.25)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                        }}
                      >
                        🚀 {lang === 'hi' ? 'सभी प्लान्स देखें या अपग्रेड करें' : 'View All Plans & Upgrade Tier'}
                      </button>

                      <button
                        onClick={logout}
                        style={{
                          background: 'transparent', color: '#94A3B8', border: 'none',
                          padding: '8px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', marginTop: '8px'
                        }}
                      >
                        ← {lang === 'hi' ? 'लॉगआउट करें' : 'Sign out from workspace'}
                      </button>
                    </div>
                  ) : (
                    <div style={{ maxWidth: '420px', margin: '0 auto' }}>
                      <div style={{
                        background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '12px',
                        padding: '14px', color: '#92400E', fontSize: '13px', fontWeight: 600, marginBottom: '20px'
                      }}>
                        ⚠️ {lang === 'hi'
                          ? 'केवल अस्पताल एडमिनिस्ट्रेटर ही प्लान रिन्यू कर सकते हैं। कृपया अपने एडमिनिस्ट्रेटर से संपर्क करें।'
                          : 'Only the Hospital Administrator can renew the subscription plan. Please contact your administrator to reactivate services.'}
                      </div>
                      <button
                        onClick={logout}
                        style={{
                          background: '#F1F5F9', color: '#334155', border: '1px solid #CBD5E1',
                          borderRadius: '12px', padding: '12px 28px', fontSize: '14px', fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        ← {lang === 'hi' ? 'लॉगआउट करें' : 'Sign Out'}
                      </button>
                    </div>
                  )}
                </div>
              ) : (
              <>
                {/* 1. RECEPTIONIST DASHBOARD */}
                {userRole === 'RECEPTIONIST' && (
                  <ReceptionistDashboard
                    activeTab={activeTab}
                    setActiveTab={setActiveTab}
                    token={token}
                    userRole={userRole}
                    hospitalId={hospitalId}
                    lang={lang}
                    t={t}
                    API_BASE={API_BASE}
                    activeHospital={activeHospital}
                    hospitalsList={hospitalsList}
                    doctorsList={doctorsList}
                    appointmentsList={appointmentsList}
                    leavesList={leavesList}
                    fetchLeaves={fetchLeaves}
                    refreshTrigger={refreshTrigger}
                    setRefreshTrigger={setRefreshTrigger}
                    selectedScheduleDate={selectedScheduleDate}
                    setSelectedScheduleDate={setSelectedScheduleDate}
                    currentTime={currentTime}
                    onOpenPrescriptionModal={handleOpenPrescriptionModal}
                    onOpenRescheduleModal={handleOpenRescheduleModal}
                    onOpenCancelModal={handleOpenCancelModal}
                    onOpenUpgradeModal={() => {
                      if (activeHospital?.subscription_plan === 'PRO') {
                        setUpgradeSelectedPlan('ENTERPRISE');
                      } else {
                        setUpgradeSelectedPlan('PRO');
                      }
                      setShowUpgradeModal(true);
                    }}
                    handleApproveLeave={handleApproveLeave}
                    handleRejectLeave={handleRejectLeave}
                    handleDeleteLeave={handleDeleteLeave}
                    patientSearchQuery={patientSearchQuery}
                    setPatientSearchQuery={setPatientSearchQuery}
                    patientSearchResults={patientSearchResults}
                    setPatientSearchResults={setPatientSearchResults}
                    patientSearchLoading={patientSearchLoading}
                    patientSearchError={patientSearchError}
                    handleSearchPatients={handleSearchPatients}
                  />
                )}


              {/* 3. HOSPITAL ADMIN PORTAL */}
              {userRole === 'ADMIN' && (
                <HospitalAdminDashboard
                  activeTab={activeTab}
                  setActiveTab={setActiveTab}
                  token={token}
                  userRole={userRole}
                  username={username}
                  hospitalId={hospitalId}
                  userId={userId}
                  lang={lang}
                  t={t}
                  API_BASE={API_BASE}
                  activeHospital={activeHospital}
                  fetchActiveHospitalProfile={fetchActiveHospitalProfile}
                  hospitalStats={hospitalStats}
                  fetchHospitalStats={fetchHospitalStats}
                  doctorsList={doctorsList}
                  fetchDoctorsAndDepartments={fetchDoctorsAndDepartments}
                  departmentsList={departmentsList}
                  hospitalStaff={hospitalStaff}
                  fetchHospitalStaff={fetchHospitalStaff}
                  hospitalStaffLoading={hospitalStaffLoading}
                  leavesList={leavesList}
                  fetchLeaves={fetchLeaves}
                  handleApproveLeave={handleApproveLeave}
                  handleRejectLeave={handleRejectLeave}
                  handleDeleteLeave={handleDeleteLeave}
                  handleDeleteStaff={handleDeleteStaff}
                  setShowUpgradeModal={setShowUpgradeModal}
                  setUpgradeSelectedPlan={setUpgradeSelectedPlan}
                  fetchAppointments={fetchAppointments}
                  setRefreshTrigger={setRefreshTrigger}
                />
              )}
              {/* 5. DOCTOR: Patient Queue & Workstation (With Persistent Sidebar) */}
              {(activeTab === 'appointments' || activeTab === 'doctor_leaves') && userRole === 'DOCTOR' && (() => {
                const loggedDoctor = (doctorsList || []).find(d => d.id === userId || d.first_name?.toLowerCase()?.includes(username?.toLowerCase()) || d.email?.includes(username)) || (doctorsList && doctorsList.length > 0 ? doctorsList[0] : null);
                const doctorHospitalName = activeHospital?.name || hospitalStats?.hospital_name || (appointmentsList.length > 0 ? appointmentsList[0].hospital_name : '') || 'AURA Partner Hospital';
                const doctorSpecialty = loggedDoctor?.department_name || loggedDoctor?.department || 'General OPD';
                const doctorTimings = loggedDoctor?.timings || 'Mon – Sat: 10:00 AM – 01:00 PM';
                const doctorOpdFees = loggedDoctor?.opd_fees || 400;
                const doctorFullName = loggedDoctor ? `${loggedDoctor.first_name} ${loggedDoctor.last_name}`.trim() : username;

                return (
                  <DoctorQueue 
                    appointments={appointmentsList}
                    selectedAppointment={selectedAppointment}
                    setSelectedAppointment={setSelectedAppointment}
                    handleCompleteConsultation={handleDoctorFinishConsultation}
                    selectedDate={selectedScheduleDate}
                    setSelectedDate={setSelectedScheduleDate}
                    activeTab={activeTab}
                    setActiveTab={(tab) => {
                      setActiveTab(tab);
                      if (tab === 'doctor_leaves') {
                        setLeaveDoctorId(userId);
                        fetchLeaves();
                      }
                    }}
                    leavesList={leavesList}
                    leaveStartDate={leaveStartDate}
                    setLeaveStartDate={setLeaveStartDate}
                    leaveEndDate={leaveEndDate}
                    setLeaveEndDate={setLeaveEndDate}
                    leaveReason={leaveReason}
                    setLeaveReason={setLeaveReason}
                    handleApplyLeave={handleApplyLeave}
                    handleDeleteLeave={handleDeleteLeave}
                    leaveSuccess={leaveSuccess}
                    leaveError={leaveError}
                    userId={userId}
                    hospitalName={doctorHospitalName}
                    doctorName={doctorFullName}
                    doctorSpecialty={doctorSpecialty}
                    doctorTimings={doctorTimings}
                    doctorOpdFees={doctorOpdFees}
                    logout={logout}
                    username={username}
                    lang={lang}
                    toggleLanguage={toggleLanguage}
                    onOpenProfile={() => setIsProfileModalOpen(true)}
                    t={t}
                  />
                );
              })()}

              {/* ── SUPER ADMIN: Platform Control Centre (Sidebar + Drilldown) ── */}
              {activeTab === 'super_admin' && userRole === 'SUPER_ADMIN' && (
                <SuperAdminDashboard
                  API_BASE={API_BASE}
                  token={token}
                  lang={lang}
                  hospitalsList={hospitalsList}
                  fetchHospitals={fetchHospitals}
                  handleToggleHospitalStatus={handleToggleHospitalStatus}
                  handleDeleteHospital={handleDeleteHospital}
                  handleSaveTwilioConfig={handleSaveTwilioConfig}
                  twilioHelplines={twilioHelplines}
                  setTwilioHelplines={setTwilioHelplines}
                  twilioWhatsappNumbers={twilioWhatsappNumbers}
                  setTwilioWhatsappNumbers={setTwilioWhatsappNumbers}
                  twilioAccountSids={twilioAccountSids}
                  setTwilioAccountSids={setTwilioAccountSids}
                  twilioAuthTokens={twilioAuthTokens}
                  setTwilioAuthTokens={setTwilioAuthTokens}
                  showTwilioTokens={showTwilioTokens}
                  setShowTwilioTokens={setShowTwilioTokens}
                  fetchHospitalStaff={fetchHospitalStaff}
                  hospitalStaff={hospitalStaff}
                  setHospitalStaff={setHospitalStaff}
                  hospitalStaffLoading={hospitalStaffLoading}
                  selectedHospital={selectedHospital}
                  setSelectedHospital={setSelectedHospital}
                  superAdminView={superAdminView}
                  setSuperAdminView={setSuperAdminView}
                />
              )}

                </>
              )}
            </div>
          </div>
        )}
      </main>

      {/* MODALS */}

      {/* A. Receptionist Prescription Complete Modal */}
      <PrescriptionModal
        isOpen={prescriptionModalOpen}
        onClose={() => setPrescriptionModalOpen(false)}
        appointment={prescAppointment}
        isViewMode={prescIsViewMode}
        prescNotes={prescNotes}
        setPrescNotes={setPrescNotes}
        prescMedicines={prescMedicines}
        setPrescMedicines={setPrescMedicines}
        prescFollowUp={prescFollowUp}
        setPrescFollowUp={setPrescFollowUp}
        onComplete={handleCompleteConsultation}
        t={t}
      />

      {/* B. Reschedule Modal */}
      <RescheduleModal
        isOpen={rescheduleModalOpen}
        onClose={() => setRescheduleModalOpen(false)}
        appointment={targetAppointment}
        rescheduleDate={rescheduleDate}
        onDateChange={handleDateChangeForReschedule}
        allSlots={allSlots}
        bookedSlots={bookedSlots}
        selectedSlotTime={selectedSlotTime}
        onSelectSlot={setSelectedSlotTime}
        leavesList={leavesList}
        rescheduleError={rescheduleError}
        onConfirm={executeReschedule}
        t={t}
      />

      {/* C. Cancel Modal */}
      <CancelAppointmentModal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        isPaid={cancelIsPaid}
        cancelReason={cancelReason}
        setCancelReason={setCancelReason}
        onConfirm={executeCancellation}
      />

      {/* D. Patient Profile & Appointments History Modal */}
      <PatientProfileModal
        selectedPatientRecord={selectedPatientRecord}
        setSelectedPatientRecord={setSelectedPatientRecord}
      />

      {/* ── INTERACTIVE PLAN RENEWAL & UPGRADE MODAL ── */}
      <UpgradeSubscriptionModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        activeHospital={activeHospital}
        hospitalStats={hospitalStats}
        plansList={plansList}
        hospitalId={hospitalId}
        onRenewPlan={handleRazorpayRenewPlan}
        onUpgradePlan={handleRazorpayUpgradePlan}
        lang={lang}
      />

      {/* Universal Profile & Self-Password Management Modal */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        token={token}
        username={username}
        userRole={userRole}
        activeHospital={activeHospital}
        t={t}
      />

      {/* Floating Context-Aware AI Copilot */}
      <CopilotWidget 
        token={token}
        userRole={userRole}
        username={username}
        activeHospital={activeHospital}
        activeTab={activeTab}
        selectedDate={selectedScheduleDate}
        t={t}
      />

      {/* Footer */}
      <footer style={{ padding: '20px', borderTop: '1px solid var(--border-color)', fontSize: '13px', color: 'var(--text-muted)' }}>
        &copy; {new Date().getFullYear()} Aura SaaS AI. Built with state-of-the-art Voice AI receptionists.
      </footer>
    </div>
  );
}


class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("CRITICAL REACT RUNTIME ERROR CAUGHT BY BOUNDARY:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', background: '#FEE2E2', border: '2px solid #DC2626', borderRadius: '16px', margin: '40px', color: '#991B1B', fontFamily: 'monospace', textAlign: 'left' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '10px' }}>⚠️ React Runtime Exception Captured!</h2>
          <div style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', background: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid #FECACA' }}>
            {this.state.error && this.state.error.toString()}
          </div>
          <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>Component Stack Trace:</div>
          <pre style={{ fontSize: '12px', background: '#FFFFFF', padding: '16px', borderRadius: '8px', overflowX: 'auto', border: '1px solid #FECACA', color: '#0F172A' }}>
            {this.state.errorInfo && this.state.errorInfo.componentStack}
          </pre>
          <button onClick={() => { localStorage.clear(); window.location.reload(); }} style={{ marginTop: '16px', padding: '12px 24px', background: '#DC2626', color: '#FFFFFF', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: 700, fontSize: '14px' }}>
            Clear Cache & Reload Page 🔄
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function RootApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
