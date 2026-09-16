import LoginPage from './pages/LoginPage';
import DoctorQueue from './components/doctor/DoctorQueue';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import PatientProfileModal from './components/common/Modals/PatientProfileModal';
import ProfileModal from './components/common/ProfileModal';
import CopilotWidget from './components/copilot/CopilotWidget';
import ControlTower from './components/superadmin/ControlTower';
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Shield, 
  Activity, 
  Calendar, 
  Clock, 
  User, 
  PlusCircle, 
  CheckCircle, 
  AlertTriangle, 
  LogOut, 
  Phone, 
  FileText, 
  Plus,
  RefreshCw,
  Sliders,
  DollarSign,
  Heart,
  FileSpreadsheet,
  Key,
  Copy,
  Laptop,
  Eye,
  EyeOff
} from 'lucide-react';
import './App.css';
import PatientPortal from './PatientPortal';

// API base - always use relative path (Vite proxy forwards /api → localhost:8000)
const API_BASE = '/api/v1';

const TRANSLATIONS = {
  en: {
    // Auth & Common
    login: "Login",
    logout: "Logout",
    username: "Username",
    password: "Password",
    hospitalId: "Hospital ID",
    selectRole: "Select Your Role",
    welcome: "Welcome",
    platformOwner: "Platform Owner",
    superAdmin: "Super Admin",
    receptionist: "Receptionist",
    doctor: "Doctor",
    admin: "Admin",
    status: "Status",
    actions: "Actions",
    date: "Date",
    time: "Time",
    reason: "Reason",
    phone: "Phone Number",
    age: "Age",
    name: "Name",
    gender: "Gender",
    search: "Search",
    loading: "Loading...",
    success: "Success",
    error: "Error",
    close: "Close",
    cancel: "Cancel",
    confirm: "Confirm",
    save: "Save Changes",
    // Tabs & Navigation
    overview: "Overview",
    newBooking: "New Booking",
    patientSearch: "Patient Search",
    receptionistLeaves: "🏖️ Doctor Leaves",
    adminOverview: "Admin Overview",
    staffManagement: "Staff Management",
    hospitalOverview: "Hospital Overview",
    adminLeaves: "Admin Leaves",
    appointments: "Patient Queue",
    doctorLeaves: "🏖️ Apply Leave",
    superAdminTab: "Super Admin Dashboard",
    // Dashboard Stats
    totalAppointments: "Total Appointments",
    scheduled: "Scheduled",
    completed: "Completed",
    cancelled: "Cancelled",
    activeDoctors: "Active Doctors",
    pendingPayment: "Pending Payment",
    paid: "Paid",
    missed: "Missed",
    // Action Buttons
    complete: "Complete",
    reschedule: "Reschedule",
    cancelBooking: "Cancel Booking",
    // Settings
    profileSettings: "Hospital Profile Settings",
    opdSettings: "OPD Settings",
    whatsappConfig: "WhatsApp Notification Number",
    greetingConfig: "Voice Receptionist Greeting",
    promptConfig: "Voice Assistant Instruction Prompt",
    // Table Column Headers
    col_time: "Time",
    col_patient: "Patient",
    col_mobile: "Mobile",
    col_reason: "Reason / Problem",
    col_payment: "Payment",
    col_status_action: "Status / Action",
    doc_fee_list: "Doctor, Schedule & Fee List",
    // Date Nav Buttons
    btn_prev: "\u25c4 Prev",
    btn_today: "Today",
    btn_next: "Next \u25ba",
    // Empty / Error States
    no_bookings_date: "No appointments booked for this date.",
    search_failed: "Search failed. Please try again.",
    no_patient_found: "No patient record found.",
    // Status Badges
    on_leave: "\u26a0\ufe0f On Leave",
    off_duty: "Off Duty / Closed",
    doc_on_leave_banner: "\u26a0\ufe0f DOCTOR IS ON LEAVE",
    // Section Headings
    patient_lookup_heading: "Patient Lookup Engine",
    active_leaves_heading: "\ud83d\udcc5 Active Doctor Leaves",
    apply_leave_heading: "\ud83d\udcdd Apply For Leave",
    my_leaves_heading: "\ud83d\udcc5 My Registered Leaves",
    recep_dashboard_sub: "Receptionist Dashboard \u2014 AI Voice Booking System",
    // Form Labels
    lbl_doctor: "Doctor",
    lbl_receptionist: "Receptionist",
    lbl_opd_fees: "OPD Fees (\u20b9)",
    lbl_slot_dur: "Slot Duration (min) *",
    lbl_sched_days: "Schedule Days (Weekly) *",
    lbl_reason: "Reason",
    lbl_admin_uname: "Admin Username *",
    lbl_admin_pass: "Admin Password",
    lbl_ai_greeting: "AI Greeting Message *",
    lbl_sys_prompt: "Custom System Prompt (Optional)",
    lbl_doc_pass: "Doctor Password",
    lbl_password_field: "Password",
    err_select_doc: "Please select a doctor.",
    err_select_slot: "Please select a time slot.",
    payment_mode_heading: "\ud83d\udcb3 Payment Mode",
    // Prescription Templates
    quick_presc_tmpl: "\u26a1 Quick Prescription Template",
    tmpl_fever: "Mild Fever & Body Pain",
    tmpl_cold: "Cold, Cough & Throat Infection",
    tmpl_acidity: "Stomach Acidity & Gas",
    tmpl_stomach: "Stomach Infection / Loose Motion",
    lbl_clinical_notes: "Clinical Notes / Diagnosis Summary",
    lbl_presc_meds: "Prescription Medicines & Dosage",
    // Day Abbreviations
    day_mon: "Mon", day_tue: "Tue", day_wed: "Wed", day_thu: "Thu",
    day_fri: "Fri", day_sat: "Sat", day_sun: "Sun",
    // Confirmation Dialogs
    confirm_del_leave: "Are you sure you want to delete this leave?",
    confirm_appr_leave: "Are you sure you want to approve this leave?",
    confirm_rej_leave: "Are you sure you want to reject this leave?",
    confirm_del_staff: "Are you sure you want to remove this staff member?",
    // Misc
    default_schedule: "Mon\u2013Fri, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM",
    leave_reason_placeholder: "e.g. Sick Leave, Personal Work",
    ai_prompt_placeholder: "You are the AI virtual receptionist. Your job is...",
  },
  hi: {
    // Auth & Common
    login: "लॉगिन करें",
    logout: "लॉगआउट",
    username: "यूज़रनेम",
    password: "पासवर्ड",
    hospitalId: "अस्पताल आईडी",
    selectRole: "अपनी भूमिका चुनें",
    welcome: "स्वागत है",
    platformOwner: "प्लेटफॉर्म ओनर",
    superAdmin: "सुपर एडमिन",
    receptionist: "रिसेप्शनिस्ट",
    doctor: "डॉक्टर",
    admin: "एडमिन",
    status: "स्थिति",
    actions: "कार्रवाई",
    date: "तारीख",
    time: "समय",
    reason: "कारण",
    phone: "फ़ोन नंबर",
    age: "उम्र",
    name: "नाम",
    gender: "लिंग",
    search: "खोजें",
    loading: "लोड हो रहा है...",
    success: "सफलता",
    error: "त्रुटि",
    close: "बंद करें",
    cancel: "रद्द करें",
    confirm: "पुष्टि करें",
    save: "बदलाव सहेजें",
    // Tabs & Navigation
    overview: "मुख्य विवरण",
    newBooking: "नया अपॉइंटमेंट",
    patientSearch: "मरीज़ खोज",
    receptionistLeaves: "🏖️ डॉक्टर छुट्टियां",
    adminOverview: "एडमिन अवलोकन",
    staffManagement: "स्टाफ प्रबंधन",
    hospitalOverview: "अस्पताल प्रोफाइल",
    adminLeaves: "एडमिन छुट्टियां",
    appointments: "मरीज़ कतार",
    doctorLeaves: "🏖️ अवकाश आवेदन",
    superAdminTab: "सुपर एडमिन डैशबोर्ड",
    // Dashboard Stats
    totalAppointments: "कुल अपॉइंटमेंट्स",
    scheduled: "निर्धारित",
    completed: "पूरा हुआ",
    cancelled: "रद्द",
    activeDoctors: "सक्रिय डॉक्टर",
    pendingPayment: "भुगतान लंबित",
    paid: "भुगतान हो गया",
    missed: "छूट गया",
    // Action Buttons
    complete: "पूरा करें",
    reschedule: "समय बदलें",
    cancelBooking: "रद्द करें",
    // Settings
    profileSettings: "अस्पताल प्रोफाइल सेटिंग्स",
    opdSettings: "ओपीडी सेटिंग्स",
    whatsappConfig: "व्हाट्सएप नोटिफिकेशन नंबर",
    greetingConfig: "रिसेप्शनिस्ट वॉयस ग्रीटिंग",
    promptConfig: "वॉयस असिस्टेंट निर्देश प्रॉम्ट",
    // Table Column Headers
    col_time: "समय",
    col_patient: "मरीज़",
    col_mobile: "मोबाइल",
    col_reason: "समस्या / कारण",
    col_payment: "भुगतान",
    col_status_action: "स्थिति / कार्रवाई",
    doc_fee_list: "डॉक्टर, समय एवं फीस सूची",
    // Date Nav Buttons
    btn_prev: "◄ पिछला",
    btn_today: "आज",
    btn_next: "अगला ►",
    // Empty / Error States
    no_bookings_date: "इस तारीख के लिए कोई भी अपॉइंटमेंट बुक नहीं है।",
    search_failed: "खोज विफल रही। कृपया पुनः प्रयास करें।",
    no_patient_found: "कोई मरीज रिकॉर्ड नहीं मिला।",
    // Status Badges
    on_leave: "⚠️ अवकाश पर",
    off_duty: "ड्यूटी समाप्त / बंद",
    doc_on_leave_banner: "⚠️ डॉक्टर अवकाश पर हैं",
    // Section Headings
    patient_lookup_heading: "मरीज़ खोज इंजन",
    active_leaves_heading: "📅 सक्रिय डॉक्टर अवकाश",
    apply_leave_heading: "📝 अवकाश के लिए आवेदन",
    my_leaves_heading: "📅 मेरे पंजीकृत अवकाश",
    recep_dashboard_sub: "रिसेप्शनिस्ट डैशबोर्ड — AI वॉयस बुकिंग सिस्टम",
    // Form Labels
    lbl_doctor: "डॉक्टर",
    lbl_receptionist: "रिसेप्शनिस्ट",
    lbl_opd_fees: "ओपीडी फीस (₹)",
    lbl_slot_dur: "स्लॉट अवधि (मिनट) *",
    lbl_sched_days: "साप्ताहिक दिन *",
    lbl_reason: "कारण",
    lbl_admin_uname: "एडमिन यूज़रनेम *",
    lbl_admin_pass: "एडमिन पासवर्ड",
    lbl_ai_greeting: "AI स्वागत संदेश *",
    lbl_sys_prompt: "कस्टम AI निर्देश (वैकल्पिक)",
    lbl_doc_pass: "डॉक्टर पासवर्ड",
    lbl_password_field: "पासवर्ड",
    err_select_doc: "कृपया डॉक्टर का चयन करें।",
    err_select_slot: "कृपया समय स्लॉट का चयन करें।",
    payment_mode_heading: "💳 भुगतान विकल्प",
    // Prescription Templates
    quick_presc_tmpl: "⚡ त्वरित पर्चा टेम्पलेट",
    tmpl_fever: "सामान्य बुखार एवं बदन दर्द",
    tmpl_cold: "सर्दी, खांसी एवं गले में संक्रमण",
    tmpl_acidity: "गैस एवं एसिडिटी",
    tmpl_stomach: "पेट दर्द एवं दस्त",
    lbl_clinical_notes: "क्लीनिकल नोट्स / निदान सारांश",
    lbl_presc_meds: "दवाइयों की सूची एवं खुराक",
    // Day Abbreviations
    day_mon: "सोम", day_tue: "मंगल", day_wed: "बुध", day_thu: "गुरु",
    day_fri: "शुक्र", day_sat: "शनि", day_sun: "रवि",
    // Confirmation Dialogs
    confirm_del_leave: "क्या आप सच में इस छुट्टी को हटाना चाहते हैं?",
    confirm_appr_leave: "क्या आप सच में इस छुट्टी को स्वीकृत (Approve) करना चाहते हैं?",
    confirm_rej_leave: "क्या आप सच में इस छुट्टी को अस्वीकृत (Reject) करना चाहते हैं?",
    confirm_del_staff: "क्या आप सच में इस स्टाफ को हटाना चाहते हैं?",
    // Misc
    default_schedule: "सोम–शुक्र, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM",
    leave_reason_placeholder: "उदा. अस्वस्थता, व्यक्तिगत कार्य",
    ai_prompt_placeholder: "तुम अपोलो हॉस्पिटल की AI वर्चुअल रिसेप्शनिस्ट हो। तुम्हारा काम...",
  }
};

export const formatDoctorTimingsToEnglish = (timings) => {
  if (!timings) return 'Mon – Sat: 10:00 AM – 01:00 PM';
  return timings
    .replace(/सोम–शनि/g, 'Mon–Sat')
    .replace(/सोम–शुक्र/g, 'Mon–Fri')
    .replace(/सोम/g, 'Mon')
    .replace(/मंगल/g, 'Tue')
    .replace(/बुध/g, 'Wed')
    .replace(/गुरु/g, 'Thu')
    .replace(/शुक्र/g, 'Fri')
    .replace(/शनि/g, 'Sat')
    .replace(/रवि/g, 'Sun');
};

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
  const [showEditDocPassword, setShowEditDocPassword] = useState(false);
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

  // Platform Owner registration state
  const [newOwnerUsername, setNewOwnerUsername] = useState('');
  const [newOwnerEmail, setNewOwnerEmail] = useState('');
  const [newOwnerPassword, setNewOwnerPassword] = useState('');
  const [newOwnerSuccess, setNewOwnerSuccess] = useState('');
  const [newOwnerError, setNewOwnerError] = useState('');

  // Super Admin drilldown state
  const [selectedHospital, setSelectedHospital] = useState(null); // null = list view, hosp obj = detail view
  const [superAdminView, setSuperAdminView] = useState('control_tower'); // 'control_tower' | 'hospitals' | 'owners'
  const [hospitalStaff, setHospitalStaff] = useState({ doctors: [], receptionists: [] });
  const [hospitalStaffLoading, setHospitalStaffLoading] = useState(false);
  const [expandedStaffCard, setExpandedStaffCard] = useState(null); // id of expanded staff card

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
  const [staffScheduleDays, setStaffScheduleDays] = useState([1,2,3,4,5]);
  const [staffStartTime, setStaffStartTime] = useState('10:00');
  const [staffEndTime, setStaffEndTime] = useState('13:00');
  const [staffStartTime2, setStaffStartTime2] = useState('14:00');
  const [staffEndTime2, setStaffEndTime2] = useState('17:00');
  const [staffHasShift2, setStaffHasShift2] = useState(false);
  const [staffOpdFees, setStaffOpdFees] = useState(500);
  const [hospitalStats, setHospitalStats] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [selectedScheduleDate, setSelectedScheduleDate] = useState(new Date().toISOString().split('T')[0]);
  const [receptionistTimeRange, setReceptionistTimeRange] = useState('today');
  const [doctorQueueSearch, setDoctorQueueSearch] = useState('');
  // Active Hospital Profile & Settings
  const [activeHospital, setActiveHospital] = useState(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  
  // New Booking Slots Grid state
  const [newBookingBookedSlots, setNewBookingBookedSlots] = useState([]);
  const [newBookingAllSlots, setNewBookingAllSlots] = useState([]);
  const [selectedNewBookingSlot, setSelectedNewBookingSlot] = useState('');
  const [selectedPatientRecord, setSelectedPatientRecord] = useState(null);
  
  // Edit Profile / Settings Modals state
  const [editHospitalProfileModalOpen, setEditHospitalProfileModalOpen] = useState(false);
  const [editHospitalSettingsModalOpen, setEditHospitalSettingsModalOpen] = useState(false);
  
  // Plan Upgrade Modals State
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeSelectedPlan, setUpgradeSelectedPlan] = useState('PRO');
  const [upgradeCheckoutModal, setUpgradeCheckoutModal] = useState(false);
  const [upgradePaymentMethod, setUpgradePaymentMethod] = useState('UPI / QR');
  const [plansList, setPlansList] = useState([]);
  
  // Edit Hospital fields
  const [editHospitalName, setEditHospitalName] = useState('');
  const [editHospitalAddress, setEditHospitalAddress] = useState('');
  const [editHospitalPhone, setEditHospitalPhone] = useState('');
  const [editHospitalEmail, setEditHospitalEmail] = useState('');
  const [editHospitalAdminUsername, setEditHospitalAdminUsername] = useState('');
  const [editHospitalAdminPassword, setEditHospitalAdminPassword] = useState('');
  
  // Edit Settings fields
  const [hospSettingsWhatsapp, setHospSettingsWhatsapp] = useState('');
  const [hospSettingsGreeting, setHospSettingsGreeting] = useState('');
  const [hospSettingsFullPrompt, setHospSettingsFullPrompt] = useState('');

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

  // Book New Appointment Form
  const [patientFirstName, setPatientFirstName] = useState('');
  const [patientLastName, setPatientLastName] = useState('');
  const [patientPhone, setPatientPhone] = useState('');
  const [patientGender, setPatientGender] = useState('Male');
  const [patientDob, setPatientDob] = useState('');
  const [bookingDoctorId, setBookingDoctorId] = useState('');
  const [bookingDate, setBookingDate] = useState(new Date().toLocaleDateString('en-CA'));
  const [bookingTime, setBookingTime] = useState('');
  const [bookingReason, setBookingReason] = useState('');
  const [receptionistPaymentMode, setReceptionistPaymentMode] = useState('CASH'); // 'CASH' | 'ONLINE'
  const [bookingSuccessMsg, setBookingSuccessMsg] = useState('');
  const [bookingErrorMsg, setBookingErrorMsg] = useState('');

  // Patient Lookup Engine (Search) State
  const [patientSearchQuery, setPatientSearchQuery] = useState('');
  const [patientSearchResults, setPatientSearchResults] = useState(null);
  const [patientSearchLoading, setPatientSearchLoading] = useState(false);
  const [patientSearchError, setPatientSearchError] = useState('');

  // Staff registration form (Hospital Admin)
  const [staffRole, setStaffRole] = useState('DOCTOR');
  const [staffUsername, setStaffUsername] = useState('');
  const [staffEmail, setStaffEmail] = useState('');
  const [staffPassword, setStaffPassword] = useState('');
  const [staffFirstName, setStaffFirstName] = useState('');
  const [staffLastName, setStaffLastName] = useState('');
  const [staffPhone, setStaffPhone] = useState('');
  const [staffDeptId, setStaffDeptId] = useState('');
  const [staffLicense, setStaffLicense] = useState('');
  const [staffRegSuccess, setStaffRegSuccess] = useState('');
  const [staffRegError, setStaffRegError] = useState('');

  // Slot Duration
  const [slotDurationMinutes, setSlotDurationMinutes] = useState(30);

  // Leaves Management State
  const [leavesList, setLeavesList] = useState([]);
  const [leaveDoctorId, setLeaveDoctorId] = useState('');
  const [leaveStartDate, setLeaveStartDate] = useState('');
  const [leaveEndDate, setLeaveEndDate] = useState('');
  const [leaveReason, setLeaveReason] = useState('');
  const [leaveSuccess, setLeaveSuccess] = useState('');
  const [leaveError, setLeaveError] = useState('');

  // Edit Doctor Modal State
  const [editDoctorModalOpen, setEditDoctorModalOpen] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState(null);
  const [editDocFirstName, setEditDocFirstName] = useState('');
  const [editDocLastName, setEditDocLastName] = useState('');
  const [editDocEmail, setEditDocEmail] = useState('');
  const [editDocPhone, setEditDocPhone] = useState('');
  const [editDocLicense, setEditDocLicense] = useState('');
  const [editDocOpdFees, setEditDocOpdFees] = useState(500);
  const [editDocScheduleDays, setEditDocScheduleDays] = useState([1,2,3,4,5]);
  const [editDocStartTime, setEditDocStartTime] = useState('10:00');
  const [editDocEndTime, setEditDocEndTime] = useState('13:00');
  const [editDocStartTime2, setEditDocStartTime2] = useState('14:00');
  const [editDocEndTime2, setEditDocEndTime2] = useState('17:00');
  const [editDocHasShift2, setEditDocHasShift2] = useState(false);
  const [editDocSlotDuration, setEditDocSlotDuration] = useState(30);
  const [editDocUsername, setEditDocUsername] = useState('');
  const [editDocPassword, setEditDocPassword] = useState('');
  const [editDocError, setEditDocError] = useState('');
  const [editDocSuccess, setEditDocSuccess] = useState('');

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

  const handleRegisterSuperAdmin = async (e) => {
    e.preventDefault();
    setNewOwnerSuccess('');
    setNewOwnerError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', newOwnerUsername);
      formData.append('email', newOwnerEmail);
      formData.append('password', newOwnerPassword);

      const res = await fetch(`${API_BASE}/super-admin/register`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to create Platform Owner.');
      }

      setNewOwnerSuccess('Platform Owner registered successfully!');
      setNewOwnerUsername('');
      setNewOwnerEmail('');
      setNewOwnerPassword('');
    } catch (err) {
      setNewOwnerError(err.message);
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

  const handleNewBookingDateOrDoctorChange = useCallback(async (docId, dateVal) => {
    if (!token || !docId || !dateVal) return;
    try {
      const res = await fetch(`${API_BASE}/receptionist/booked-slots?doctor_id=${docId}&date_str=${dateVal}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNewBookingBookedSlots(data.booked_slots || []);
        setNewBookingAllSlots(data.all_slots || []);
      }
    } catch (err) {
      console.error("Error fetching booked slots for new booking:", err);
    }
  }, [token]);

  useEffect(() => {
    if (bookingDoctorId && bookingDate) {
      handleNewBookingDateOrDoctorChange(bookingDoctorId, bookingDate);
    } else {
      setNewBookingBookedSlots([]);
      setNewBookingAllSlots([]);
    }
  }, [bookingDoctorId, bookingDate, refreshTrigger, handleNewBookingDateOrDoctorChange]);

  const convertSlotTo24h = (slotStr) => {
    const timeClean = slotStr.replace(/(AM|PM)/i, '').trim();
    const isPm = slotStr.toLowerCase().includes('pm');
    let [hours, minutes] = timeClean.split(':').map(Number);
    if (isPm && hours !== 12) hours += 12;
    if (!isPm && hours === 12) hours = 0;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  };

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
  const handleRegisterStaff = async (e) => {
    e.preventDefault();
    setStaffRegError('');
    setStaffRegSuccess('');

    // Check Plan Authority Doctor Limit
    if (staffRole === 'DOCTOR') {
      const plan = activeHospital?.subscription_plan || hospitalStats?.subscription_plan || 'PRO';
      const staffDocs = hospitalStaff.doctors.length > 0 ? hospitalStaff.doctors : (Array.isArray(doctorsList) ? doctorsList : []);
      const maxDocs = activeHospital?.max_doctors || ((plan === 'ENTERPRISE') ? 999 : ((plan === 'PRO' || plan === 'PRO_AI') ? 5 : 1));
      if (staffDocs.length >= maxDocs && plan !== 'ENTERPRISE') {
        setStaffRegError(`🔒 Doctor limit reached (${staffDocs.length}/${maxDocs}) for your ${plan} plan. Please upgrade your subscription plan to register more doctors!`);
        setShowUpgradeModal(true);
        return;
      }
    }

    try {
      const formData = new URLSearchParams();
      formData.append('role', staffRole);
      formData.append('username', staffUsername);
      formData.append('email', staffEmail);
      formData.append('password', staffPassword);
      formData.append('first_name', staffFirstName);
      formData.append('last_name', staffLastName);
      formData.append('phone', staffPhone);
      if (staffRole === 'DOCTOR') {
        formData.append('department_id', staffDeptId);
        formData.append('license_number', staffLicense);
        formData.append('schedule_days', staffScheduleDays.join(','));
        formData.append('schedule_start_time', staffStartTime);
        formData.append('schedule_end_time', staffEndTime);
        if (staffHasShift2 && staffStartTime2 && staffEndTime2 && staffStartTime2 !== '00:00') {
          formData.append('schedule_start_time_2', staffStartTime2);
          formData.append('schedule_end_time_2', staffEndTime2);
        }
        formData.append('opd_fees', staffOpdFees.toString());
        formData.append('slot_duration_minutes', slotDurationMinutes.toString());
      }

      const res = await fetch(`${API_BASE}/hospital/register-staff`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded' 
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Staff registration failed.');
      }

      setStaffRegSuccess(`Account generated. WhatsApp credentials sent to ${staffPhone}.`);
      setStaffUsername('');
      setStaffEmail('');
      setStaffPassword('');
      setStaffFirstName('');
      setStaffLastName('');
      setStaffPhone('');
      setStaffLicense('');
      setStaffScheduleDays([1,2,3,4,5]);
      setStaffStartTime('10:00');
      setStaffEndTime('13:00');
      setStaffStartTime2('14:00');
      setStaffEndTime2('17:00');
      setStaffHasShift2(false);
      setStaffOpdFees(500);
      fetchHospitalStats();
    } catch (err) {
      setStaffRegError(err.message);
    }
  };

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

  // Handle Hospital Profile Update
  const handleUpdateHospitalProfile = async (e) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('name', editHospitalName);
      formData.append('address', editHospitalAddress);
      formData.append('phone', editHospitalPhone);
      formData.append('email', editHospitalEmail);
      formData.append('admin_username', editHospitalAdminUsername);
      formData.append('admin_password', editHospitalAdminPassword);

      const res = await fetch(`${API_BASE}/hospital/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (res.ok) {
        alert("Hospital profile updated successfully!");
        setEditHospitalProfileModalOpen(false);
        fetchActiveHospitalProfile();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to update hospital profile.");
      }
    } catch (e) {
      console.error(e);
      alert("Error updating profile.");
    }
  };

  // Handle Hospital Settings Update
  const handleUpdateHospitalSettings = async (e) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('whatsapp_number', hospSettingsWhatsapp);
      formData.append('greeting_prompt', hospSettingsGreeting);
      formData.append('full_custom_prompt', hospSettingsFullPrompt);

      const res = await fetch(`${API_BASE}/hospital/settings`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (res.ok) {
        alert("Hospital settings saved successfully!");
        setEditHospitalSettingsModalOpen(false);
        fetchActiveHospitalProfile();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to save settings.");
      }
    } catch (e) {
      console.error(e);
      alert("Error saving settings.");
    }
  };

  // Handle Edit Doctor (open modal and pre-fill)
  const handleOpenEditDoctorModal = (doc) => {
    setEditingDoctor(doc);
    setEditDocFirstName(doc.first_name || '');
    setEditDocLastName(doc.last_name || '');
    setEditDocEmail(doc.email || '');
    setEditDocPhone(doc.phone || '');
    setEditDocLicense(doc.license_number || '');
    setEditDocOpdFees(doc.opd_fees || 500);
    setEditDocScheduleDays(doc.work_days || [1,2,3,4,5]);
    setEditDocSlotDuration(doc.slot_duration_minutes || 30);
    setEditDocUsername(doc.username || '');
    setEditDocPassword(doc.password || '');
    
    // Read exact structured session times from doctor object
    const s1Start = doc.session_1_start || '10:00';
    const s1End = doc.session_1_end || '13:00';
    const s2Start = doc.session_2_start || '';
    const s2End = doc.session_2_end || '';
    const hasShift2 = Boolean(doc.has_shift_2 || (s2Start && s2End && s2Start !== '00:00' && s2Start !== s1Start));

    setEditDocStartTime(s1Start);
    setEditDocEndTime(s1End);
    setEditDocStartTime2(hasShift2 ? s2Start : '14:00');
    setEditDocEndTime2(hasShift2 ? s2End : '17:00');
    setEditDocHasShift2(hasShift2);

    setEditDocError('');
    setEditDocSuccess('');
    setShowEditDocPassword(false);
    setEditDoctorModalOpen(true);
  };

  // Handle Update Doctor Submit
  const handleUpdateDoctorSubmit = async (e) => {
    e.preventDefault();
    setEditDocError('');
    setEditDocSuccess('');
    try {
      const formData = new URLSearchParams();
      formData.append('first_name', editDocFirstName);
      formData.append('last_name', editDocLastName);
      formData.append('email', editDocEmail);
      formData.append('phone', editDocPhone);
      formData.append('license_number', editDocLicense);
      formData.append('username', editDocUsername);
      formData.append('password', editDocPassword);
      formData.append('opd_fees', editDocOpdFees.toString());
      formData.append('schedule_days', editDocScheduleDays.join(','));
      formData.append('schedule_start_time', editDocStartTime);
      formData.append('schedule_end_time', editDocEndTime);
      if (editDocHasShift2 && editDocStartTime2 && editDocEndTime2 && editDocStartTime2 !== '00:00') {
        formData.append('schedule_start_time_2', editDocStartTime2);
        formData.append('schedule_end_time_2', editDocEndTime2);
      } else {
        formData.append('schedule_start_time_2', '');
        formData.append('schedule_end_time_2', '');
      }
      formData.append('slot_duration_minutes', editDocSlotDuration.toString());

      const res = await fetch(`${API_BASE}/hospital/staff/doctor/${editingDoctor.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json();
        let errMsg = 'Failed to update doctor profile.';
        if (errData.detail) {
          if (typeof errData.detail === 'object' && errData.detail.message) {
            errMsg = errData.detail.message;
          } else if (typeof errData.detail === 'string') {
            errMsg = errData.detail;
          } else {
            errMsg = JSON.stringify(errData.detail);
          }
        }
        throw new Error(errMsg);
      }

      setEditDocSuccess('Doctor profile updated and schedules rebuilt successfully!');
      fetchDoctorsAndDepartments();
      fetchAppointments();
      setTimeout(() => {
        setEditDoctorModalOpen(false);
        setRefreshTrigger(prev => prev + 1);
        fetchDoctorsAndDepartments();
        fetchAppointments();
      }, 1200);
    } catch (err) {
      setEditDocError(err.message);
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

  // Book new appointment
  const handleNewBooking = async (e) => {
    e.preventDefault();
    setBookingErrorMsg('');
    setBookingSuccessMsg('');

    if (!bookingDoctorId) {
      setBookingErrorMsg('कृपया डॉक्टर का चयन करें (Please select a doctor).');
      return;
    }
    if (!bookingTime) {
      setBookingErrorMsg('कृपया समय स्लॉट (Time Slot) का चयन करें.');
      return;
    }

    let cleanPhone = patientPhone.trim();
    if (/^\d{10}$/.test(cleanPhone)) {
      cleanPhone = '+91' + cleanPhone;
    } else if (cleanPhone.startsWith('+1') && cleanPhone.length === 12 && '6789'.includes(cleanPhone[2])) {
      cleanPhone = '+91' + cleanPhone.slice(2);
    }

    try {
      const apptData = {
        hospital_id: hospitalId,
        patient_name: `${patientFirstName} ${patientLastName}`.trim(),
        patient_phone: cleanPhone,
        patient_gender: patientGender,
        patient_dob: patientDob,
        doctor_id: bookingDoctorId,
        appointment_datetime: `${bookingDate}T${bookingTime}:00`,
        reason: bookingReason,
        payment_mode: receptionistPaymentMode
      };

      const apptRes = await fetch(`${API_BASE}/receptionist/book-appointment`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(apptData)
      });

      if (!apptRes.ok) {
        const errData = await apptRes.json();
        const errMsg = Array.isArray(errData.detail)
          ? errData.detail.map(e => `${e.loc[e.loc.length - 1]}: ${e.msg}`).join(', ')
          : (errData.detail || 'Failed to book appointment.');
        throw new Error(errMsg);
      }

      const bookedAppt = await apptRes.json();
      if (receptionistPaymentMode === 'CASH') {
        setBookingSuccessMsg('Appointment booked & marked PAID (Cash)! WhatsApp confirmation sent (no link).');
      } else {
        setBookingSuccessMsg('Appointment booked successfully! Payment checkout link sent via WhatsApp.');
      }
      setPatientFirstName('');
      setPatientLastName('');
      setPatientPhone('');
      setBookingReason('');
      setRefreshTrigger(prev => prev + 1);
    } catch (err) {
      setBookingErrorMsg(err.message);
    }
  };

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

  const handleManualPayment = async (appointmentId) => {
    try {
      const res = await fetch(`${API_BASE}/payment/confirm/${appointmentId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await res.json();
      if (data.success) {
        alert('Payment confirmed successfully!');
        setRefreshTrigger(prev => prev + 1);
      } else {
        alert('Failed to confirm payment: ' + (data.detail || data.message || 'Unknown error'));
      }
    } catch (e) {
      console.error(e);
      alert('Network error confirming payment.');
    }
  };

  const handleMarkSingleMissed = async (appointmentId) => {
    try {
      const formData = new FormData();
      formData.append('new_status', 'MISSED');
      const res = await fetch(`${API_BASE}/appointments/${appointmentId}/status`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        alert('Appointment marked as MISSED successfully! WhatsApp alert sent to patient.');
        setRefreshTrigger(prev => prev + 1);
      } else {
        alert('Failed to mark missed: ' + (data.detail || 'Unknown error'));
      }
    } catch (e) {
      console.error(e);
      alert('Network error.');
    }
  };

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

  const handleBulkCancel = async (docId, dateStr) => {
    const reason = window.prompt("Reason for cancelling all appointments for this doctor today (e.g. Doctor Absent):", "Doctor is unavailable today");
    if (!reason) return;
    
    if (!window.confirm(`Are you SURE you want to cancel ALL appointments for this doctor on ${dateStr}? Patients who paid will get a refund notification.`)) return;
    
    try {
      const res = await fetch(`${API_BASE}/appointments/bulk-cancel`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({
          doctor_id: docId,
          target_date: dateStr,
          reason: reason
        })
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Successfully cancelled ${data.cancelled_count} appointments.`);
        setRefreshTrigger(p => p + 1);
      } else {
        alert("Failed to bulk cancel appointments.");
      }
    } catch (e) {
      alert("Network error.");
    }
  };

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
          <div style={{ flexGrow: 1, display: 'flex', flexDirection: userRole === 'RECEPTIONIST' ? 'row' : 'column' }}>
            
            {/* 📌 Left Vertical Sidebar for Receptionist Role */}
            {userRole === 'RECEPTIONIST' && !activeHospital?.is_expired && (
              <aside style={{ 
                width: '240px', 
                background: '#FFFFFF', 
                borderRight: '1.5px solid var(--border)', 
                padding: '24px 14px', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '8px', 
                flexShrink: 0,
                boxShadow: 'var(--shadow-sm)'
              }}>
                <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', padding: '0 10px 8px 10px', letterSpacing: '0.05em' }}>
                  Main Menu
                </div>
                <button onClick={() => setActiveTab('overview')} className={`sidebar-btn ${activeTab === 'overview' ? 'active' : ''}`}>
                  <Calendar size={18} /> {t('overview')}
                </button>
                <button onClick={() => setActiveTab('new_booking')} className={`sidebar-btn ${activeTab === 'new_booking' ? 'active' : ''}`}>
                  <PlusCircle size={18} /> {t('newBooking')}
                </button>

                <button onClick={() => { setActiveTab('receptionist_leaves'); fetchLeaves(); }} className={`sidebar-btn ${activeTab === 'receptionist_leaves' ? 'active' : ''}`}>
                  <Calendar size={18} /> {t('receptionistLeaves')}
                </button>
                
                <div style={{ marginTop: 'auto', background: 'var(--primary-soft)', border: '1px solid var(--primary-border)', borderRadius: '14px', padding: '14px', textAlign: 'center' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: 'var(--primary)', marginBottom: '3px' }}>🟢 Voice AI System</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>Live Receptionist Active</div>
                </div>
              </aside>
            )}

            {/* Hospital Admin Top Navigation Bar */}
            {userRole === 'ADMIN' && !activeHospital?.is_expired && (
              <div className="tab-container" style={{ margin: '0 0 16px 0' }}>
                <button onClick={() => { setActiveTab('admin_overview'); if (hospitalId) fetchHospitalStaff(hospitalId); }} className={`tab-btn ${activeTab === 'admin_overview' ? 'active' : ''}`}><Activity size={18} /> {t('adminOverview')}</button>
                <button onClick={() => setActiveTab('staff_management')} className={`tab-btn ${activeTab === 'staff_management' ? 'active' : ''}`}><Shield size={18} /> {t('staffManagement')}</button>
                <button onClick={() => setActiveTab('hospital_overview')} className={`tab-btn ${activeTab === 'hospital_overview' ? 'active' : ''}`}><Sliders size={18} /> {t('hospitalOverview')}</button>
                <button onClick={() => { setActiveTab('admin_leaves'); fetchLeaves(); }} className={`tab-btn ${activeTab === 'admin_leaves' ? 'active' : ''}`}><Calendar size={18} /> {t('adminLeaves')}</button>
              </div>
            )}

            {/* Content viewports */}
            <div style={{ flexGrow: 1, padding: (userRole === 'RECEPTIONIST' && !activeHospital?.is_expired) ? '24px' : '0' }}>

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
                  {/* 1. RECEPTIONIST: Live Schedule Tab */}
                  {activeTab === 'overview' && userRole === 'RECEPTIONIST' && (
                <div style={{ textAlign: 'left' }}>
                  
                  {/* ── UNIFIED BALAJI HOSPITAL CARD WITH KPI METRICS INSIDE (MATCHING SCREENSHOT 3) ── */}
                  <div style={{
                    background: '#FFFFFF',
                    borderRadius: '24px', padding: '24px', marginBottom: '24px',
                    boxShadow: 'var(--shadow-md)', border: '1.5px solid var(--border)'
                  }}>
                    {/* Hospital Banner Header Row */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                        <div style={{ width: '52px', height: '52px', borderRadius: '16px', background: 'var(--primary-soft)', border: '1px solid var(--primary-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px' }}>
                          🏨
                        </div>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <h2 style={{ color: '#0F172A', fontSize: '24px', fontWeight: 800, margin: 0 }}>
                              {activeHospital?.name || (hospitalsList || []).find(h => h.id === hospitalId)?.name || 'Hospital Workspace'}
                            </h2>
                            <span style={{
                              background: activeHospital?.subscription_plan === 'ENTERPRISE' ? '#F3E8FF' : activeHospital?.subscription_plan === 'PRO' ? '#EFF6FF' : '#FEF3C7',
                              color: activeHospital?.subscription_plan === 'ENTERPRISE' ? '#7E22CE' : activeHospital?.subscription_plan === 'PRO' ? '#1E40AF' : '#92400E',
                              border: `1px solid ${activeHospital?.subscription_plan === 'ENTERPRISE' ? '#D8B4FE' : activeHospital?.subscription_plan === 'PRO' ? '#BFDBFE' : '#FDE68A'}`,
                              padding: '4px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: 800
                            }}>
                              {activeHospital?.subscription_plan === 'ENTERPRISE' ? '🥇 ENTERPRISE' : activeHospital?.subscription_plan === 'PRO' ? '🥈 PRO AI' : '🥉 STARTER (15-Day Free Trial)'}
                            </span>
                            
                            {/* Expiry Badge */}
                            {(() => {
                              const expDate = activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at) : null;
                              const expStr = expDate ? expDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
                              const today = new Date();
                              const daysLeft = expDate ? Math.max(0, Math.ceil((expDate - today) / (1000 * 60 * 60 * 24))) : 15;
                              const isExpired = daysLeft <= 0;
                              const isUrgent = daysLeft <= 7;

                              return (
                                <span style={{
                                  background: isExpired ? '#FEE2E2' : isUrgent ? '#FEF2F2' : '#F8FAFC',
                                  color: (isExpired || isUrgent) ? '#DC2626' : '#475569',
                                  border: `1.5px solid ${isExpired ? '#FECACA' : isUrgent ? '#F87171' : '#CBD5E1'}`,
                                  padding: '4px 12px', borderRadius: '16px', fontSize: '11px', fontWeight: 800,
                                  boxShadow: isUrgent ? '0 0 10px rgba(220, 38, 38, 0.15)' : 'none'
                                }}>
                                  {isExpired 
                                    ? '🚨 Service Suspended — Plan Expired!' 
                                    : isUrgent 
                                    ? `🚨 Expires: ${expStr} (${daysLeft} ${daysLeft === 1 ? 'Day' : 'Days'} Left — Renew Now!)` 
                                    : `⌛ Expires: ${expStr || 'Active'} (${daysLeft} ${daysLeft === 1 ? 'Day' : 'Days'} Left)`}
                                </span>
                              );
                            })()}

                            {/* Renew / Upgrade Plan Button */}
                            <button 
                              onClick={() => {
                                if (activeHospital?.subscription_plan === 'PRO') {
                                  setUpgradeSelectedPlan('ENTERPRISE');
                                } else {
                                  setUpgradeSelectedPlan('PRO');
                                }
                                setShowUpgradeModal(true);
                              }}
                              style={{ 
                                background: activeHospital?.subscription_plan === 'ENTERPRISE' 
                                  ? 'linear-gradient(135deg, #059669 0%, #047857 100%)' 
                                  : 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', 
                                color: '#FFF', border: 'none', padding: '5px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 800, cursor: 'pointer', 
                                boxShadow: '0 2px 8px rgba(37,99,235,0.3)', transition: 'all 0.2s'
                              }}
                            >
                              {activeHospital?.subscription_plan === 'ENTERPRISE' ? '🔄 Renew Subscription' : '⚡ Renew / Upgrade Plan'}
                            </button>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', flexWrap: 'wrap' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: 600 }}>
                              AI Voice Booking System • Live Receptionist Active
                            </span>
                            {(() => {
                              const assignedHelpline = 
                                activeHospital?.twilio_helpline || 
                                activeHospital?.settings?.twilio_helpline || 
                                activeHospital?.settings?.helpline_number || 
                                activeHospital?.assigned_helpline;

                              if (!activeHospital?.ai_voice_enabled) {
                                return (
                                  <span style={{color: '#92400E', background: '#FEF3C7', border: '1px solid #FDE68A', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 800}}>
                                    🔒 AI Line Locked
                                  </span>
                                );
                              }

                              return assignedHelpline ? (
                                <span style={{color: '#166534', background: '#DCFCE7', border: '1px solid #BBF7D0', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 800}}>
                                  📞 AI Voice Line Active: {assignedHelpline}
                                </span>
                              ) : (
                                <span style={{color: '#92400E', background: '#FEF3C7', border: '1px solid #FDE68A', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 800}}>
                                  ⏳ AI Voice Line Provisioning in Progress (Max 24-42 Hours Window)
                                </span>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                      {/* Live Clock Card & Sync Button */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ background: '#F8FAFC', border: '1.5px solid var(--border-input)', borderRadius: '14px', padding: '10px 20px', color: '#0F172A', fontSize: '16px', fontWeight: 800, fontFamily: 'monospace', minWidth: '130px', textAlign: 'center' }}>
                          ⏱️ {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </div>
                        <button onClick={() => setRefreshTrigger(p => p+1)} className="btn btn-primary" style={{ padding: '0 20px', fontSize: '14px', height: '44px' }}>
                          <RefreshCw size={16} style={{ marginRight: '6px' }} /> Sync Live
                        </button>
                      </div>
                    </div>

                    {/* 5 KPI Metric Cards Embedded Inside Hospital Card (Real-Time Selected Time Range Calculation) */}
                    {(() => {
                      const safeDocs = Array.isArray(doctorsList) ? doctorsList : [];
                      const safeAppts = Array.isArray(appointmentsList) ? appointmentsList : [];
                      const safeLeaves = Array.isArray(leavesList) ? leavesList : [];
                      const todayStr = new Date().toISOString().split('T')[0];

                      // Helper function for Receptionist Time Range Filtering
                      const isApptInReceptionistRange = (a) => {
                        if (!a || !a.appointment_datetime) return false;
                        const aDateStr = a.appointment_datetime.split('T')[0];
                        if (receptionistTimeRange === 'today') {
                          return aDateStr === selectedScheduleDate;
                        }
                        if (receptionistTimeRange === 'week') {
                          const aTime = new Date(aDateStr).getTime();
                          const nowTime = new Date(todayStr).getTime();
                          const diffDays = (nowTime - aTime) / (1000 * 3600 * 24);
                          return diffDays >= 0 && diffDays <= 7;
                        }
                        if (receptionistTimeRange === 'month') {
                          const aD = new Date(aDateStr);
                          const nowD = new Date();
                          return aD.getMonth() === nowD.getMonth() && aD.getFullYear() === nowD.getFullYear();
                        }
                        if (receptionistTimeRange === 'all') {
                          return true;
                        }
                        return aDateStr === selectedScheduleDate;
                      };

                      // Appointments for the selected range
                      const dateAppts = safeAppts.filter(isApptInReceptionistRange);
                      const totalRangeCount = dateAppts.length;

                      // Pending Collection for selected range
                      const pendingAppts = dateAppts.filter(a => a.payment_status === 'PENDING' && a.status !== 'CANCELLED');
                      const collectionDueAmount = pendingAppts.reduce((sum, a) => {
                        const doc = safeDocs.find(d => String(d.id) === String(a.doctor_id));
                        return sum + (a.opd_fees || a.fee || doc?.opd_fees || 500);
                      }, 0);

                      // Collected for selected range
                      const paidAppts = dateAppts.filter(a => a.payment_status === 'PAID' || a.status === 'COMPLETED');
                      const collectedAmount = paidAppts.reduce((sum, a) => {
                        const doc = safeDocs.find(d => String(d.id) === String(a.doctor_id));
                        return sum + (a.opd_fees || a.fee || doc?.opd_fees || 500);
                      }, 0);

                      // Doctors Online on selected date
                      const doctorsOnlineCount = safeDocs.filter(doc => {
                        const isOnLeave = safeLeaves.some(l => {
                          if (String(l.doctor_id) !== String(doc.id) || l.status === 'REJECTED') return false;
                          const sd = new Date(l.start_date);
                          const ed = new Date(l.end_date);
                          const target = new Date(selectedScheduleDate);
                          return target >= sd && target <= ed;
                        });
                        return !isOnLeave;
                      }).length;

                      // Missed/Cancelled on selected range
                      const missedCount = dateAppts.filter(a => a.status === 'CANCELLED' || a.status === 'MISSED').length;

                      return (
                        <div className="kpi-grid-5">
                          <div className="kpi-card-light" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
                            <div className="kpi-header-row">
                              <span style={{ fontSize: '18px' }}>📅</span>
                              <span className="kpi-pill" style={{ background: '#DBEAFE', color: '#1E40AF', textTransform: 'capitalize' }}>
                                {receptionistTimeRange === 'today' ? 'Today' : receptionistTimeRange === 'week' ? 'This Week' : receptionistTimeRange === 'month' ? 'This Month' : 'All Time'}
                              </span>
                            </div>
                            <div>
                              <div className="kpi-value">{totalRangeCount}</div>
                              <div className="kpi-title" style={{ color: '#1E3A8A' }}>Total Appointments</div>
                            </div>
                          </div>

                          <div className="kpi-card-light" style={{ background: '#FEF3C7', border: '1px solid #FDE68A' }}>
                            <div className="kpi-header-row">
                              <span style={{ fontSize: '18px' }}>💰</span>
                              <span className="kpi-pill" style={{ background: '#FDE68A', color: '#92400E' }}>Pending</span>
                            </div>
                            <div>
                              <div className="kpi-value">₹{collectionDueAmount.toLocaleString()}</div>
                              <div className="kpi-title" style={{ color: '#78350F' }}>Collection Due</div>
                            </div>
                          </div>

                          <div className="kpi-card-light" style={{ background: '#DCFCE7', border: '1px solid #BBF7D0' }}>
                            <div className="kpi-header-row">
                              <span style={{ fontSize: '18px' }}>✅</span>
                              <span className="kpi-pill" style={{ background: '#BBF7D0', color: '#166534' }}>Paid</span>
                            </div>
                            <div>
                              <div className="kpi-value">₹{collectedAmount.toLocaleString()}</div>
                              <div className="kpi-title" style={{ color: '#14532D' }}>Revenue Collected</div>
                            </div>
                          </div>

                          <div className="kpi-card-light" style={{ background: '#F3E8FF', border: '1px solid #E9D5FF' }}>
                            <div className="kpi-header-row">
                              <span style={{ fontSize: '18px' }}>🩺</span>
                              <span className="kpi-pill" style={{ background: '#E9D5FF', color: '#6B21A8' }}>Active</span>
                            </div>
                            <div>
                              <div className="kpi-value">{doctorsOnlineCount} / {safeDocs.length}</div>
                              <div className="kpi-title" style={{ color: '#581C87' }}>Doctors Available</div>
                            </div>
                          </div>

                          <div className="kpi-card-light" style={{ background: '#FEE2E2', border: '1px solid #FECACA' }}>
                            <div className="kpi-header-row">
                              <span style={{ fontSize: '18px' }}>❌</span>
                              <span className="kpi-pill" style={{ background: '#FECACA', color: '#991B1B' }}>Missed</span>
                            </div>
                            <div>
                              <div className="kpi-value">{missedCount}</div>
                              <div className="kpi-title" style={{ color: '#7F1D1D' }}>Missed / Cancelled</div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                  </div>

                  {/* ── Date Navigator & Multi-Range Filter Toolbar ── */}
                  <div style={{
                    background: '#FFFFFF', border: '1.5px solid var(--border)',
                    borderRadius: '16px', padding: '14px 22px', marginBottom: '22px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px',
                    boxShadow: '0 2px 10px rgba(15,23,42,0.03)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                      <div 
                        style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                        onClick={() => document.getElementById('dashboard-date-picker').showPicker()}
                      >
                        <span style={{ fontSize: '18px' }}>📅</span>
                        <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '15px' }}>
                          {receptionistTimeRange === 'today'
                            ? `Today: ${safeFormatDate(selectedScheduleDate, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}`
                            : receptionistTimeRange === 'week'
                            ? '📊 Last 7 Days (This Week)'
                            : receptionistTimeRange === 'month'
                            ? `📊 This Month (${new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })})`
                            : '📊 All Time Records'}
                        </div>
                      </div>
                      <input 
                        type="date" 
                        id="dashboard-date-picker" 
                        value={selectedScheduleDate} 
                        onChange={e => {
                          setSelectedScheduleDate(e.target.value);
                          setReceptionistTimeRange('today');
                        }} 
                        style={{ opacity: 0, width: 0, height: 0, position: 'absolute' }}
                      />
                    </div>

                    {/* Quick Range Filter Pills (Today, Week, Month, All Time) */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <div style={{ display: 'flex', gap: '4px', background: '#F1F5F9', padding: '4px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
                        {[
                          { id: 'today', label: 'Today' },
                          { id: 'week', label: 'This Week' },
                          { id: 'month', label: 'This Month' },
                          { id: 'all', label: 'All Time' }
                        ].map(pill => (
                          <button
                            key={pill.id}
                            onClick={() => {
                              setReceptionistTimeRange(pill.id);
                              if (pill.id === 'today') {
                                setSelectedScheduleDate(new Date().toISOString().split('T')[0]);
                              }
                            }}
                            style={{
                              background: receptionistTimeRange === pill.id ? '#2563EB' : 'transparent',
                              color: receptionistTimeRange === pill.id ? '#FFFFFF' : '#475569',
                              border: 'none',
                              borderRadius: '8px',
                              padding: '5px 14px',
                              fontSize: '12px',
                              fontWeight: 800,
                              cursor: 'pointer',
                              transition: 'all 0.15s',
                              boxShadow: receptionistTimeRange === pill.id ? '0 2px 6px rgba(37,99,235,0.25)' : 'none'
                            }}
                          >
                            {pill.label}
                          </button>
                        ))}
                      </div>

                      {/* Day Navigators when in Today/Day mode */}
                      {receptionistTimeRange === 'today' && (
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button 
                            onClick={() => {
                              const prev = new Date(selectedScheduleDate);
                              prev.setDate(prev.getDate() - 1);
                              setSelectedScheduleDate(prev.toISOString().split('T')[0]);
                            }}
                            style={{ background: '#F8FAFC', border: '1px solid #CBD5E1', color: '#475569', borderRadius: '8px', padding: '5px 12px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                          >
                            {t('btn_prev')}
                          </button>
                          <button 
                            onClick={() => {
                              const next = new Date(selectedScheduleDate);
                              next.setDate(next.getDate() + 1);
                              setSelectedScheduleDate(next.toISOString().split('T')[0]);
                            }}
                            style={{ background: '#F8FAFC', border: '1px solid #CBD5E1', color: '#475569', borderRadius: '8px', padding: '5px 12px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                          >
                            {t('btn_next')}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* ── Main Dual Column Body ── */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px', alignItems: 'start' }}>
                    
                    {/* Left Column: Doctor Queue List with Live Performance Breakdown */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {(Array.isArray(doctorsList) ? doctorsList : []).length === 0 ? (
                        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No active doctors registered under this hospital tenant.
                        </div>
                      ) : (
                        (Array.isArray(doctorsList) ? doctorsList : []).map(doc => {
                          const todayStr = new Date().toISOString().split('T')[0];
                          const isApptInReceptionistRange = (a) => {
                            if (!a || !a.appointment_datetime) return false;
                            const aDateStr = a.appointment_datetime.split('T')[0];
                            if (receptionistTimeRange === 'today') {
                              return aDateStr === selectedScheduleDate;
                            }
                            if (receptionistTimeRange === 'week') {
                              const aTime = new Date(aDateStr).getTime();
                              const nowTime = new Date(todayStr).getTime();
                              const diffDays = (nowTime - aTime) / (1000 * 3600 * 24);
                              return diffDays >= 0 && diffDays <= 7;
                            }
                            if (receptionistTimeRange === 'month') {
                              const aD = new Date(aDateStr);
                              const nowD = new Date();
                              return aD.getMonth() === nowD.getMonth() && aD.getFullYear() === nowD.getFullYear();
                            }
                            if (receptionistTimeRange === 'all') {
                              return true;
                            }
                            return aDateStr === selectedScheduleDate;
                          };

                          const docAppts = appointmentsList.filter(appt => {
                            const matchDoc = appt.doctor_id === doc.id;
                            return matchDoc && isApptInReceptionistRange(appt);
                          });

                          const docCompleted = docAppts.filter(a => a.status === 'COMPLETED' || a.status === 'CONSULTATION_FINISHED').length;
                          const docWaiting = docAppts.filter(a => a.status === 'CONFIRMED' || a.status === 'WAITING' || a.status === 'SCHEDULED' || !a.status).length;
                          const docMissed = docAppts.filter(a => a.status === 'CANCELLED' || a.status === 'MISSED').length;
                          const docFee = Number(doc.opd_fees) || 500;
                          const docRevenue = docCompleted * docFee;

                          return (
                            <div key={doc.id} style={{
                              background: '#FFFFFF',
                              borderRadius: '18px',
                              border: '1.5px solid #DBEAFE',
                              padding: '20px',
                              boxShadow: '0 4px 20px rgba(37, 99, 235, 0.05)',
                              borderLeft: '5px solid #2563EB'
                            }}>
                              
                              {/* Doctor Queue Header with Live Performance Scorecard */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid #E2E8F0', paddingBottom: '12px', flexWrap: 'wrap', gap: '10px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ fontSize: '20px' }}>🩺</span>
                                  <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                      <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '16px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                      <span style={{ background: 'rgba(37,99,235,0.08)', color: '#2563EB', border: '1px solid rgba(37,99,235,0.2)', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', fontWeight: 700 }}>
                                        {doc.department_name}
                                      </span>
                                    </div>
                                    <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, marginTop: '2px' }}>
                                      OPD Fee: <strong style={{ color: '#2563EB' }}>₹{docFee}</strong> • Timings: {formatDoctorTimingsToEnglish(doc.timings)}
                                    </div>
                                  </div>
                                </div>

                                {/* Doctor Performance Metrics for Selected Range */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                  <div style={{ background: '#EFF6FF', color: '#1E40AF', padding: '4px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800 }}>
                                    👥 {docAppts.length} Booked
                                  </div>
                                  <div style={{ background: '#DCFCE7', color: '#166534', padding: '4px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800 }}>
                                    ✅ {docCompleted} Done
                                  </div>
                                  <div style={{ background: '#FEF3C7', color: '#92400E', padding: '4px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800 }}>
                                    ⏳ {docWaiting} Waiting
                                  </div>
                                  <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '4px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800 }}>
                                    ⚠️ {docMissed} Missed
                                  </div>
                                  <div style={{ background: 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)', color: '#14532D', border: '1px solid #86EFAC', padding: '4px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 900 }}>
                                    💰 ₹{docRevenue.toLocaleString()}
                                  </div>
                                  {docAppts.length > 0 && receptionistTimeRange === 'today' && (
                                    <button 
                                      onClick={() => handleBulkCancel(doc.id, selectedScheduleDate)}
                                      className="btn btn-secondary" 
                                      style={{ padding: '4px 10px', fontSize: '11px', background: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px' }}
                                    >
                                      ❌ Cancel All
                                    </button>
                                  )}
                                </div>
                              </div>

                              {/* Appointment Table */}
                              {docAppts.length === 0 ? (
                                <div style={{ color: 'var(--text-muted)', padding: '16px', fontSize: '13px' }}>
                                  {t('no_bookings_date')}
                                </div>
                              ) : (
                                <div className="table-container" style={{ margin: 0, border: '1.5px solid #DBEAFE', borderRadius: '14px', overflow: 'hidden', boxShadow: '0 2px 10px rgba(37,99,235,0.04)' }}>
                                  <table className="custom-table" style={{ fontSize: '13px', borderCollapse: 'collapse', width: '100%' }}>
                                    <thead style={{ background: '#F8FAFC', borderBottom: '2px solid #DBEAFE' }}>
                                      <tr>
                                        <th style={{ width: '40px', color: '#475569', fontWeight: 800, padding: '12px 14px' }}>#</th>
                                        <th style={{ color: '#475569', fontWeight: 800, padding: '12px 14px' }}>
                                          {receptionistTimeRange === 'today' ? t('col_time') : 'Date & Time'}
                                        </th>
                                        <th style={{ color: '#475569', fontWeight: 800, padding: '12px 14px' }}>{t('col_patient')}</th>
                                        <th style={{ color: '#475569', fontWeight: 800, padding: '12px 14px' }}>{t('col_mobile')}</th>
                                        <th style={{ color: '#475569', fontWeight: 800, padding: '12px 14px' }}>{t('col_reason')}</th>
                                        <th style={{ color: '#475569', fontWeight: 800, padding: '12px 14px' }}>{t('col_payment')}</th>
                                        <th style={{ color: '#475569', fontWeight: 800, padding: '12px 14px' }}>{t('col_status_action')}</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {docAppts.map((appt, i) => (
                                        <tr key={appt.id} style={{ borderBottom: '1px solid #F1F5F9', transition: 'background 0.15s' }}>
                                          <td style={{ padding: '12px 14px', color: '#64748B', fontWeight: 700 }}>{i + 1}</td>
                                          <td style={{ padding: '12px 14px', fontWeight: 800, color: '#0F172A' }}>
                                            {receptionistTimeRange === 'today'
                                              ? new Date(appt.appointment_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                                              : new Date(appt.appointment_datetime).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) + ', ' + new Date(appt.appointment_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                          </td>
                                          <td style={{ padding: '12px 14px' }}>
                                            <div style={{ fontWeight: 800, color: '#0F172A' }}>{appt.patient_name}</div>
                                            {appt.booked_by_name && appt.booked_by_name !== appt.patient_name && (
                                              <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 600 }}>
                                                👤 {lang === 'hi' ? 'द्वारा बुक किया गया:' : 'Booked by:'} {appt.booked_by_name}
                                              </div>
                                            )}
                                            <span style={{ fontSize: '10px', color: '#64748B', fontWeight: 600 }}>ID: {appt.patient_id?.substring(0, 8)}...</span>
                                          </td>
                                          <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontWeight: 600, color: '#334155' }}>{appt.patient_phone || 'N/A'}</td>
                                          <td style={{ padding: '12px 14px', color: '#475569', fontWeight: 600 }}>{appt.reason || 'General Checkup'}</td>
                                          <td style={{ padding: '12px 14px' }}>
                                            <span style={{
                                              background: appt.payment_status === 'PAID' ? '#DCFCE7' : '#FEF3C7',
                                              color: appt.payment_status === 'PAID' ? '#15803D' : '#B45309',
                                              border: `1px solid ${appt.payment_status === 'PAID' ? '#86EFAC' : '#FDE68A'}`,
                                              borderRadius: '8px', padding: '3px 8px', fontSize: '11px', fontWeight: 800
                                            }}>
                                              {appt.payment_status === 'PAID' ? '✓ PAID' : '⏳ PENDING'}
                                            </span>
                                          </td>
                                          <td style={{ padding: '12px 14px' }}>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-start', minWidth: '220px' }}>
                                              {appt.status === 'CANCELLED' ? (
                                                <span style={{ background: '#FEE2E2', color: '#991B1B', border: '1px solid #FECACA', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800 }}>
                                                  ❌ {lang === 'hi' ? 'रद्द (Cancelled)' : 'Cancelled'}
                                                </span>
                                              ) : appt.status === 'COMPLETED' ? (
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%' }}>
                                                  <span style={{ background: '#DCFCE7', color: '#166534', border: '1px solid #BBF7D0', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '4px', width: 'fit-content' }}>
                                                    ✅ {lang === 'hi' ? 'सम्पन्न (Completed)' : 'Completed'}
                                                  </span>
                                                  <button 
                                                    onClick={() => {
                                                      setPrescAppointment(appt);
                                                      setPrescNotes(appt.clinical_notes || '');
                                                      setPrescMedicines(appt.prescription || '');
                                                      setPrescFollowUp(appt.follow_up_date ? appt.follow_up_date.split('T')[0] : '');
                                                      setPrescIsViewMode(true);
                                                      setPrescriptionModalOpen(true);
                                                    }}
                                                    className="btn btn-secondary"
                                                    style={{ padding: '6px 12px', fontSize: '11px', borderRadius: '8px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', fontWeight: 800, width: 'fit-content', cursor: 'pointer', transition: 'all 0.2s' }}
                                                  >
                                                    👁️ {lang === 'hi' ? 'पर्चा देखें' : 'View Prescription'}
                                                  </button>
                                                </div>
                                              ) : appt.status === 'MISSED' ? (
                                                 <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%' }}>
                                                   <span style={{ background: '#FEF2F2', color: '#B91C1C', border: '1px solid #FCA5A5', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '4px', width: 'fit-content' }}>
                                                     ⚠️ {lang === 'hi' ? 'छूट गया (Missed)' : 'Missed'}
                                                   </span>
                                                   {appt.payment_status === 'PAID' && (appt.reschedule_count || 0) < 1 && ((new Date() - new Date(appt.appointment_datetime)) <= 48 * 3600 * 1000) ? (
                                                     <button 
                                                       onClick={() => {
                                                         setTargetAppointment(appt);
                                                         setRescheduleDate('');
                                                         setBookedSlots([]);
                                                         setSelectedSlotTime('');
                                                         setRescheduleError('');
                                                         setRescheduleModalOpen(true);
                                                       }} 
                                                       className="btn btn-secondary" 
                                                       style={{ padding: '6px 12px', fontSize: '11px', borderRadius: '8px', background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', fontWeight: 800, width: 'fit-content', cursor: 'pointer' }}
                                                     >
                                                       🔄 {t('reschedule')} (1-Time)
                                                     </button>
                                                   ) : (appt.reschedule_count || 0) >= 1 ? (
                                                     <span style={{ fontSize: '10px', color: '#64748B', background: '#F1F5F9', padding: '3px 8px', borderRadius: '8px', width: 'fit-content' }}>
                                                       🔒 Already Rescheduled (1/1)
                                                     </span>
                                                   ) : (
                                                     <span style={{ fontSize: '10px', color: '#DC2626', background: '#FEF2F2', padding: '3px 8px', borderRadius: '8px', width: 'fit-content' }}>
                                                       🚫 Unpaid (No Reschedule)
                                                     </span>
                                                   )}
                                                 </div>
                                               ) : (
                                                 <>
                                                   {/* 1. Status Badge Header */}
                                                   {(appt.status === 'CONSULTATION_FINISHED' || appt.consultation_status === 'FINISHED') ? (
                                                     <span style={{ background: '#EEF2FF', color: '#4338CA', border: '1px solid #C7D2FE', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                                       🟢 {lang === 'hi' ? 'परामर्श पूर्ण' : 'Doctor Consultation Finished'}
                                                     </span>
                                                   ) : (
                                                     <span style={{ background: '#FEF3C7', color: '#92400E', border: '1px solid #FDE68A', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                                       ⏳ {lang === 'hi' ? 'परामर्श प्रतीक्षित' : 'Consultation Pending'}
                                                     </span>
                                                   )}

                                                   {/* 2. Primary Action Button */}
                                                   {appt.payment_status !== 'PAID' ? (
                                                     <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                       <button 
                                                         onClick={() => {
                                                           if(window.confirm('Collect payment for this appointment?')) {
                                                             handleManualPayment(appt.id);
                                                           }
                                                         }}
                                                         style={{ padding: '6px 14px', fontSize: '12px', borderRadius: '8px', background: 'linear-gradient(135deg, #059669 0%, #047857 100%)', border: 'none', color: '#FFFFFF', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(5,150,105,0.25)', transition: 'all 0.15s' }}
                                                       >
                                                         💰 {lang === 'hi' ? 'भुगतान प्राप्त करें' : 'Collect Payment'}
                                                       </button>
                                                       <button 
                                                         onClick={() => alert("⚠️ Payment is PENDING! Please click 💰 Collect Payment first before completing the appointment.")}
                                                         style={{ background: '#F8FAFC', color: '#94A3B8', border: '1px solid #E2E8F0', padding: '6px 10px', fontSize: '11px', borderRadius: '8px', fontWeight: 700, cursor: 'not-allowed' }}
                                                         title="Collect Payment First"
                                                       >
                                                         🔒 Complete
                                                       </button>
                                                     </div>
                                                   ) : (
                                                     <button 
                                                       onClick={() => {
                                                         setPrescAppointment(appt);
                                                         setPrescNotes(appt.clinical_notes || '');
                                                         setPrescMedicines(appt.prescription || '');
                                                         setPrescFollowUp(appt.follow_up_date ? appt.follow_up_date.split('T')[0] : '');
                                                         setPrescIsViewMode(false);
                                                         setPrescriptionModalOpen(true);
                                                       }}
                                                       style={{ padding: '6px 14px', fontSize: '12px', borderRadius: '8px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', border: 'none', color: '#FFFFFF', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)', transition: 'all 0.15s' }}
                                                     >
                                                       🩺 {lang === 'hi' ? 'पर्चा लिखें एवं पूरा करें →' : 'Complete & Add Prescription →'}
                                                     </button>
                                                   )}

                                                   {/* 3. Secondary Actions Row (Reschedule / Missed / Cancel) */}
                                                   <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                     <button 
                                                       onClick={() => {
                                                         setTargetAppointment(appt);
                                                         setRescheduleDate('');
                                                         setBookedSlots([]);
                                                         setSelectedSlotTime('');
                                                         setRescheduleError('');
                                                         setRescheduleModalOpen(true);
                                                       }} 
                                                       style={{ background: '#F8FAFC', border: '1px solid #CBD5E1', color: '#334155', borderRadius: '6px', padding: '4px 8px', fontSize: '11px', fontWeight: 700, cursor: 'pointer' }}
                                                     >
                                                       🔄 {t('reschedule')}
                                                     </button>
                                                     <button 
                                                       onClick={() => {
                                                         if (window.confirm('Mark this appointment as MISSED? This will update status and send a WhatsApp alert.')) {
                                                           handleMarkSingleMissed(appt.id);
                                                         }
                                                       }}
                                                       style={{ background: '#FFFBEB', border: '1px solid #FDE68A', color: '#B45309', borderRadius: '6px', padding: '4px 8px', fontSize: '11px', fontWeight: 700, cursor: 'pointer' }}
                                                     >
                                                       ⚠️ Missed
                                                     </button>
                                                     <button 
                                                       onClick={() => {
                                                         setCancelAppointmentId(appt.id);
                                                         setCancelReason('');
                                                         setCancelIsPaid(appt.payment_status === 'PAID');
                                                         setCancelModalOpen(true);
                                                       }}
                                                       style={{ background: '#FEF2F2', border: '1px solid #FECACA', color: '#DC2626', borderRadius: '6px', padding: '4px 8px', fontSize: '11px', fontWeight: 700, cursor: 'pointer' }}
                                                     >
                                                       ❌ Cancel
                                                     </button>
                                                   </div>
                                                 </>
                                               )}
                                            </div>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>

                    {/* Right Column: Doctors timing sidebar list */}
                    <div className="glass-panel" style={{ padding: '20px' }}>
                      <h3 style={{ color: 'var(--text-main)', fontSize: '15px', fontWeight: 700, borderBottom: '1px solid #E2E8F0', paddingBottom: '10px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>👨‍⚕️</span> {t('doc_fee_list')}
                      </h3>
                      
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        {(Array.isArray(doctorsList) ? doctorsList : []).map(doc => {
                          // Define fallback timing and fees
                          const timingStr = formatDoctorTimingsToEnglish(doc.timings);
                          const feesStr = doc.opd_fees ? `₹${doc.opd_fees}` : "₹500";
                          
                          // Check if doctor works on selectedScheduleDate
                          // Use LOCAL date parsing (split Y/M/D) to avoid UTC midnight shift bug
                          const [_y, _m, _d] = selectedScheduleDate.split('-').map(Number);
                          const localDateObj = new Date(_y, _m - 1, _d);
                          let dayOfWeek = localDateObj.getDay(); // 0 = Sunday, 1 = Monday...
                          if (dayOfWeek === 0) dayOfWeek = 7; // Map Sunday to 7
                          const isWorking = doc.work_days && doc.work_days.includes(dayOfWeek);
                          
                          // Check for active leaves on selected date
                          const isDoctorOnLeave = leavesList?.some(leave => {
                            if (leave.doctor_id !== doc.id || leave.status !== 'APPROVED') return false;
                            const checkDate = new Date(selectedScheduleDate);
                            checkDate.setHours(0,0,0,0);
                            const start = new Date(leave.start_date);
                            start.setHours(0,0,0,0);
                            const end = new Date(leave.end_date);
                            end.setHours(23,59,59,999);
                            return checkDate >= start && checkDate <= end;
                          });

                          return (
                            <div key={doc.id} style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: '10px', fontSize: '12px' }}>
                              <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '13px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                              <div style={{ color: 'var(--color-primary)', fontWeight: 600, marginTop: '2px' }}>{doc.department_name}</div>
                              
                              {isDoctorOnLeave ? (
                                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '6px', padding: '8px', marginTop: '8px', color: '#ef4444', textAlign: 'center', fontWeight: 'bold' }}>
                                  {t('on_leave')}
                                </div>
                              ) : (
                                <div style={{ color: '#334155', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
                                  <div style={{ color: '#0F172A', fontWeight: 600 }}>
                                    ⏳ {lang === 'hi' ? 'समय' : 'Timing'}: <span style={{ color: '#2563EB', fontWeight: 700 }}>
                                      {isWorking ? translateScheduleString(timingStr, lang) : <span style={{ color: '#DC2626', fontWeight: 700 }}>{lang === 'hi' ? 'ड्यूटी बंद / अवकाश' : 'Off Duty / Closed'}</span>}
                                    </span>
                                  </div>
                                  <div style={{ color: '#0F172A', fontWeight: 600 }}>
                                    💰 {lang === 'hi' ? 'ओपीडी शुल्क' : 'OPD Fees'}: <span style={{ color: '#059669', fontWeight: 700 }}>{feesStr}</span>
                                  </div>
                                  <div style={{ color: isWorking ? '#166534' : '#DC2626', fontWeight: 700 }}>
                                    {lang === 'hi' ? (isWorking ? "72 स्लॉट उपलब्ध हैं" : "0 स्लॉट (अवकाश)") : (isWorking ? "72 slots free" : "0 slots free (Off-duty)")}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                  </div>
                </div>
              )}

              {/* 2a. RECEPTIONIST: Book Appointment Tab */}
              {activeTab === 'new_booking' && userRole === 'RECEPTIONIST' && (
                <div className="glass-panel" style={{ padding: '24px', textAlign: 'left', maxWidth: '1050px', margin: '0 auto' }}>
                  <h2 style={{ color: 'var(--text-main)', marginBottom: '16px', fontSize: '20px', fontWeight: 700 }}>📅 Book Appointment & Dispatch Payment Link</h2>
                  {bookingErrorMsg && <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', padding: '10px 14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>⚠️ {bookingErrorMsg}</div>}
                  {bookingSuccessMsg && <div style={{ color: '#10b981', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', padding: '10px 14px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>✅ {bookingSuccessMsg}</div>}

                  <form onSubmit={handleNewBooking} style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '24px' }}>
                    
                    {/* LEFT COLUMN: Patient Info & Doctor */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <h4 style={{ color: 'var(--color-primary)', margin: 0, fontSize: '14px', fontWeight: 600 }}>1. Patient Information</h4>
                      
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <div className="form-group">
                          <label style={{ fontSize: '12px' }}>First Name</label>
                          <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={patientFirstName} onChange={e => setPatientFirstName(e.target.value)} required />
                        </div>
                        <div className="form-group">
                          <label style={{ fontSize: '12px' }}>Last Name</label>
                          <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={patientLastName} onChange={e => setPatientLastName(e.target.value)} required />
                        </div>
                      </div>

                      <div className="form-group">
                        <label style={{ fontSize: '12px' }}>WhatsApp Mobile Number (Direct +91)</label>
                        <input
                          type="text"
                          className="form-control"
                          style={{ padding: '8px 12px', fontSize: '13px' }}
                          placeholder="+919532399202"
                          value={patientPhone}
                          onChange={e => {
                            let val = e.target.value;
                            if (/^\d{10}$/.test(val.trim())) {
                              val = '+91' + val.trim();
                            }
                            setPatientPhone(val);
                          }}
                          required
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '10px' }}>
                        <div className="form-group">
                          <label style={{ fontSize: '12px' }}>Gender</label>
                          <select className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={patientGender} onChange={e => setPatientGender(e.target.value)}>
                            <option>Male</option>
                            <option>Female</option>
                            <option>Other</option>
                          </select>
                        </div>
                        <div className="form-group">
                          <label style={{ fontSize: '12px' }}>Date of Birth</label>
                          <input type="date" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={patientDob} onChange={e => setPatientDob(e.target.value)} required />
                        </div>
                      </div>

                      <div className="form-group" style={{ marginTop: '4px' }}>
                        <label style={{ fontSize: '12px', color: 'var(--color-primary)' }}>Select Consulting Doctor *</label>
                        <select className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={bookingDoctorId} onChange={e => setBookingDoctorId(e.target.value)} required>
                          <option value="">-- Choose Doctor --</option>
                          {(Array.isArray(doctorsList) ? doctorsList : []).map(doc => (
                            <option key={doc.id} value={doc.id}>Dr. {doc.first_name} {doc.last_name} ({doc.department_name})</option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label style={{ fontSize: '12px' }}>Reason for Visit / Symptoms</label>
                        <textarea className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} rows="2" placeholder="Brief symptom summary..." value={bookingReason} onChange={e => setBookingReason(e.target.value)} required></textarea>
                      </div>

                      <div className="form-group" style={{ background: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <label style={{ fontSize: '12px', color: 'var(--color-primary)', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                          {t('payment_mode_heading')}
                        </label>
                        <div style={{ display: 'flex', gap: '16px' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer', color: 'var(--text-main)' }}>
                            <input
                              type="radio"
                              name="receptionist_payment_mode"
                              value="CASH"
                              checked={receptionistPaymentMode === 'CASH'}
                              onChange={e => setReceptionistPaymentMode(e.target.value)}
                            />
                            💵 Cash (Mark Paid)
                          </label>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer', color: 'var(--text-main)' }}>
                            <input
                              type="radio"
                              name="receptionist_payment_mode"
                              value="ONLINE"
                              checked={receptionistPaymentMode === 'ONLINE'}
                              onChange={e => setReceptionistPaymentMode(e.target.value)}
                            />
                            💳 Online (Send Link)
                          </label>
                        </div>
                      </div>

                      <button type="submit" className="btn btn-primary" style={{ padding: '10px 18px', fontSize: '14px', fontWeight: 600, marginTop: '6px' }}>
                        {receptionistPaymentMode === 'CASH' ? '💵 Book & Mark Cash Paid' : '🚀 Book & Send WhatsApp Payment Link'}
                      </button>
                    </div>

                    {/* RIGHT COLUMN: Date & Time Slot Grid */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: '#FFFFFF', padding: '16px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
                      <h4 style={{ color: 'var(--color-primary)', margin: 0, fontSize: '14px', fontWeight: 600 }}>2. Appointment Date & Slot Selection</h4>
                      
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                        <button
                          type="button"
                          className={`btn ${bookingDate === new Date().toLocaleDateString('en-CA') ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                          onClick={() => setBookingDate(new Date().toLocaleDateString('en-CA'))}
                        >
                          📅 Today ({new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })})
                        </button>
                        <button
                          type="button"
                          className={`btn ${bookingDate === new Date(Date.now() + 86400000).toLocaleDateString('en-CA') ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                                                        onClick={() => setBookingDate(new Date(Date.now() + 86400000).toLocaleDateString('en-CA'))}
                        >
                          📅 Tomorrow ({new Date(Date.now() + 86400000).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })})
                        </button>
                        <input
                          type="date"
                          className="form-control"
                          style={{ maxWidth: '140px', padding: '5px 8px', fontSize: '12px' }}
                          value={bookingDate}
                          onChange={e => setBookingDate(e.target.value)}
                          required
                        />
                      </div>

                      {bookingDoctorId && bookingDate ? (
                        <div>
                          <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
                            Choose Time Slot (<span style={{ color: '#10b981', fontWeight: 'bold' }}>Green = Selected</span> | <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>Blue = Available</span> | <span style={{ color: '#ef4444', fontWeight: 'bold' }}>Red = Booked</span> | <span style={{ color: '#666' }}>Grey = Passed</span>):
                          </label>
                          <div>
                            {(() => {
                              if (newBookingAllSlots.length === 0) {
                                const onLeave = leavesList.find(l => l.doctor_id === bookingDoctorId && l.status === 'APPROVED' && new Date(l.start_date) <= new Date(bookingDate) && new Date(l.end_date) >= new Date(bookingDate));
                                if (onLeave) {
                                  const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  return (
                                    <div style={{ textAlign: 'center', padding: '15px', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                                      <strong style={{fontSize: '14px'}}>{t('doc_on_leave_banner')}</strong><br />
                                      <span style={{fontSize: '13px', marginTop: '4px', display: 'inline-block'}}>This doctor is on leave from {sd} to {ed}.</span>
                                    </div>
                                  );
                                }
                                return (
                                  <div style={{ textAlign: 'center', padding: '15px', color: '#ef4444', fontStyle: 'italic', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                                    Doctor is unavailable today (No active OPD schedule).
                                  </div>
                                );
                              }

                              // Group slots into Morning, Afternoon, Evening sessions
                              const morningSlots = [];
                              const afternoonSlots = [];
                              const eveningSlots = [];

                              newBookingAllSlots.forEach(time => {
                                const s24 = convertSlotTo24h(time);
                                const hour = parseInt(s24.split(':')[0], 10);
                                if (hour < 13) {
                                  morningSlots.push(time);
                                } else if (hour >= 13 && hour < 17) {
                                  afternoonSlots.push(time);
                                } else {
                                  eveningSlots.push(time);
                                }
                              });

                              const renderSlotPill = (time) => {
                                const slot24 = convertSlotTo24h(time);
                                const now = new Date();
                                const istOffset = 5.5 * 60 * 60 * 1000;
                                const istDate = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
                                const todayStr = istDate.toISOString().split('T')[0];
                                const current24 = `${String(istDate.getHours()).padStart(2, '0')}:${String(istDate.getMinutes()).padStart(2, '0')}`;
                                
                                const isPast = (bookingDate === todayStr && slot24 <= current24);
                                const isBusy = newBookingBookedSlots.includes(time);
                                const isSelected = selectedNewBookingSlot === time;

                                let slotStyle = { padding: '9px 6px', fontSize: '12px', textAlign: 'center', borderRadius: '10px', cursor: 'pointer', fontWeight: 600, transition: 'all 0.2s' };

                                if (isPast) {
                                  slotStyle = { ...slotStyle, opacity: 0.5, cursor: 'not-allowed', background: '#F1F5F9', color: '#94A3B8', border: '1px dashed #CBD5E1' };
                                } else if (isBusy) {
                                  slotStyle = { ...slotStyle, background: '#FEE2E2', border: '1px solid #FECACA', color: '#991B1B', cursor: 'not-allowed' };
                                } else if (isSelected) {
                                  slotStyle = { ...slotStyle, background: '#2563EB', border: '1px solid #1D4ED8', color: '#FFFFFF', fontWeight: 800, boxShadow: '0 4px 12px rgba(37,99,235,0.3)' };
                                } else {
                                  slotStyle = { ...slotStyle, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8' };
                                }

                                return (
                                  <div
                                    key={time}
                                    style={slotStyle}
                                    onClick={() => {
                                      if (!isPast && !isBusy) {
                                        setSelectedNewBookingSlot(time);
                                        setBookingTime(slot24);
                                      }
                                    }}
                                  >
                                    {time} {isPast ? '(Passed)' : ''}
                                  </div>
                                );
                              };

                              return (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                  {morningSlots.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span>🌅</span> Morning Session (10:00 AM - 01:00 PM)
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                        {morningSlots.map(renderSlotPill)}
                                      </div>
                                    </div>
                                  )}

                                  {afternoonSlots.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span>☀️</span> Afternoon Session (01:00 PM - 05:00 PM)
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                        {afternoonSlots.map(renderSlotPill)}
                                      </div>
                                    </div>
                                  )}

                                  {eveningSlots.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span>🌙</span> Evening Session (05:00 PM - 08:00 PM)
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                        {eveningSlots.map(renderSlotPill)}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                      ) : (
                        <div style={{ color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic', padding: '20px 0' }}>
                          👉 Select a Doctor above to load available time slots.
                        </div>
                      )}
                    </div>

                  </form>
                </div>
              )}

              {/* 2b. RECEPTIONIST: Patient Search Engine Tab */}
              {activeTab === 'patient_search' && userRole === 'RECEPTIONIST' && (
                <div className="glass-panel" style={{ padding: '24px', textAlign: 'left', maxWidth: '1100px', margin: '0 auto' }}>
                  <h2 style={{ color: 'var(--text-main)', marginBottom: '6px', fontSize: '22px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span>🔍</span> {t('patient_lookup_heading')}
                  </h2>
                  <p style={{ color: '#334155', fontSize: '13px', marginBottom: '20px' }}>
                    10-अंकों का मोबाइल नंबर या नाम लिखकर मुख्य मरीज और उनके परिवार के सभी सदस्यों की सूची, अपॉइंटमेंट्स और मेडिकल हिस्ट्री खोजें।
                  </p>

                  <form onSubmit={handleSearchPatients} style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
                    <input
                      type="text"
                      className="form-control"
                      style={{ padding: '12px 16px', fontSize: '15px', borderRadius: '10px', background: 'rgba(255,255,255,0.08)', color: 'var(--text-main)', border: '1px solid rgba(255,255,255,0.2)' }}
                      placeholder="Enter 10-digit Mobile Number or Patient/Family Name..."
                      value={patientSearchQuery}
                      onChange={e => setPatientSearchQuery(e.target.value)}
                      required
                    />
                    <button type="submit" className="btn btn-primary" style={{ padding: '12px 24px', fontSize: '15px', fontWeight: 700, borderRadius: '10px', whiteSpace: 'nowrap' }}>
                      🔍 Search Patient
                    </button>
                  </form>

                  {patientSearchLoading && <div style={{ color: '#38bdf8', padding: '20px', textAlign: 'center' }}>Searching patient database...</div>}
                  {patientSearchError && <div style={{ color: '#ef4444', padding: '14px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px' }}>⚠️ {patientSearchError}</div>}

                  {patientSearchResults && (
                    <div>
                      {patientSearchResults.groups.length === 0 ? (
                        <div style={{ padding: '30px', textAlign: 'center', color: '#475569', background: '#FFFFFF', borderRadius: '12px' }}>
                          ❌ "<strong>{patientSearchResults.query}</strong>" से कोई मरीज रिकॉर्ड नहीं मिला।
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                          {patientSearchResults.groups.map((group, gIdx) => {
                            const allUpcoming = [];
                            const allHistory = [];
                            
                            group.members.forEach(member => {
                              member.upcoming_appointments.forEach(a => {
                                if (a.status !== 'CANCELLED' && a.status !== 'MISSED' && a.status !== 'FAILED') {
                                  allUpcoming.push({ ...a, patientName: member.name, patientGender: member.gender, patientAge: member.age });
                                }
                              });
                              member.history_appointments.forEach(a => {
                                if (a.status !== 'CANCELLED' && a.status !== 'MISSED' && a.status !== 'FAILED') {
                                  allHistory.push({ ...a, patientName: member.name, patientGender: member.gender, patientAge: member.age });
                                }
                              });
                            });

                            allUpcoming.sort((a, b) => new Date(a.datetime) - new Date(b.datetime));
                            allHistory.sort((a, b) => new Date(b.datetime) - new Date(a.datetime));

                            return (
                              <div key={gIdx} className="glass-panel" style={{ padding: '24px', marginBottom: '10px' }}>
                                <div style={{ fontSize: '18px', fontWeight: 800, color: '#38bdf8', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  📱 Account: {group.primary_phone}
                                </div>
                                
                                {/* Upcoming Table */}
                                <h4 style={{ color: '#10b981', marginBottom: '12px', fontSize: '15px', fontWeight: 700 }}>📅 Upcoming Appointments</h4>
                                {allUpcoming.length === 0 ? (
                                   <p style={{ color: '#64748B', fontSize: '14px', marginBottom: '24px' }}>No upcoming bookings.</p>
                                ) : (
                                   <div className="table-container" style={{ marginBottom: '30px' }}>
                                     <table className="custom-table">
                                       <thead>
                                         <tr>
                                           <th>Patient Name</th>
                                           <th>Doctor</th>
                                           <th>Date & Time</th>
                                           <th>Payment</th>
                                           <th>Status</th>
                                         </tr>
                                       </thead>
                                       <tbody>
                                         {allUpcoming.map((a, i) => (
                                           <tr key={i}>
                                             <td>
                                               <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>{a.patientName}</div>
                                               <div style={{ fontSize: '11px', color: '#475569' }}>{a.patientGender}, {a.patientAge} Yrs</div>
                                             </td>
                                             <td>{a.doctor_name}</td>
                                             <td>{a.datetime_display}</td>
                                             <td>
                                               <span style={{ padding: '3px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 700, background: a.payment_status === 'PAID' ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)', color: a.payment_status === 'PAID' ? '#10b981' : '#f59e0b' }}>
                                                 {a.payment_status === 'PAID' ? `PAID (${a.payment_method})` : 'PENDING'}
                                               </span>
                                             </td>
                                             <td><span className={`status-badge status-${(a.status || '').toLowerCase()}`}>{a.status}</span></td>
                                           </tr>
                                         ))}
                                       </tbody>
                                     </table>
                                   </div>
                                )}

                                {/* History Table */}
                                <h4 style={{ color: '#475569', marginBottom: '12px', fontSize: '15px', fontWeight: 700 }}>📜 Past History & Prescriptions</h4>
                                {allHistory.length === 0 ? (
                                   <p style={{ color: '#64748B', fontSize: '14px' }}>No past records.</p>
                                ) : (
                                   <div className="table-container">
                                     <table className="custom-table">
                                       <thead>
                                         <tr>
                                           <th>Patient Name</th>
                                           <th>Doctor</th>
                                           <th>Date & Time</th>
                                           <th>Status</th>
                                           <th>Prescription / Notes</th>
                                         </tr>
                                       </thead>
                                       <tbody>
                                         {allHistory.map((a, i) => (
                                           <tr key={i}>
                                             <td>
                                               <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>{a.patientName}</div>
                                               <div style={{ fontSize: '11px', color: '#475569' }}>{a.patientGender}, {a.patientAge} Yrs</div>
                                             </td>
                                             <td>{a.doctor_name}</td>
                                             <td>{a.datetime_display}</td>
                                             <td><span className={`status-badge status-${(a.status || '').toLowerCase()}`}>{a.status}</span></td>
                                             <td>
                                               {a.has_prescription && a.prescription ? (
                                                 <div style={{ fontSize: '12px', background: 'var(--bg-muted)', padding: '8px', borderRadius: '6px' }}>
                                                   <div style={{marginBottom:'4px'}}><strong style={{color:'#94a3b8'}}>Notes:</strong> {a.prescription.clinical_notes || 'N/A'}</div>
                                                   <div><strong style={{color:'#94a3b8'}}>Rx:</strong> {a.prescription.prescription || 'N/A'}</div>
                                                 </div>
                                               ) : <span style={{ color: '#64748B', fontStyle: 'italic' }}>N/A</span>}
                                             </td>
                                           </tr>
                                         ))}
                                       </tbody>
                                     </table>
                                   </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}

                </div>
              )}

              {/* 2b. RECEPTIONIST: Leaves Management Tab */}
              {activeTab === 'receptionist_leaves' && userRole === 'RECEPTIONIST' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', textAlign: 'left', maxWidth: '900px', margin: '0 auto' }}>
                  <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ color: 'var(--text-main)', fontSize: '18px', fontWeight: 700, marginBottom: '18px' }}>{t('active_leaves_heading')}</h3>
                    <div className="table-container">
                      <table className="custom-table">
                        <thead>
                          <tr>
                            <th>Doctor Name</th>
                            <th>Start Date</th>
                            <th>End Date</th>
                            <th>Reason</th>
                            <th>Status</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {leavesList.length === 0 ? (
                            <tr>
                              <td colSpan="6" style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No doctor leaves registered.</td>
                            </tr>
                          ) : (
                            leavesList.map(leave => (
                              <tr key={leave.id} style={{ borderBottom: '1px solid #E2E8F0' }}>
                                <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{leave.doctor_name}</td>
                                <td>{new Date(leave.start_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                                <td>{new Date(leave.end_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                                <td>{leave.reason || 'N/A'}</td>
                                <td>
                                  {leave.status === 'APPROVED' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(16,185,129,0.15)', color: '#10b981', fontSize: '12px', fontWeight: 600 }}>✅ Approved</span>}
                                  {leave.status === 'REJECTED' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(239,68,68,0.15)', color: '#f87171', fontSize: '12px', fontWeight: 600 }}>❌ Rejected</span>}
                                  {leave.status === 'PENDING' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', fontSize: '12px', fontWeight: 600 }}>⏳ Pending</span>}
                                </td>
                                <td>
                                  <div style={{ display: 'flex', gap: '8px' }}>
                                    {leave.status === 'PENDING' && (
                                      <>
                                        <button 
                                          onClick={() => handleApproveLeave(leave.id)}
                                          style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', color: '#34d399', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                        >
                                          ✔️ Approve
                                        </button>
                                        <button 
                                          onClick={() => handleRejectLeave(leave.id)}
                                          style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#f87171', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                        >
                                          ❌ Reject
                                        </button>
                                      </>
                                    )}
                                    {leave.status === 'PENDING' && (
                                      <button 
                                        onClick={() => handleDeleteLeave(leave.id)}
                                        style={{ background: 'var(--bg-muted)', border: '1px solid rgba(255,255,255,0.2)', color: 'var(--text-secondary)', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', marginTop: '5px' }}
                                      >
                                        🗑️ Delete
                                      </button>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* 3. HOSPITAL ADMIN: Staff Allocation Tab */}
              {activeTab === 'staff_management' && userRole === 'ADMIN' && (() => {
                const plan = activeHospital?.subscription_plan || 'PRO';
                const maxDocs = activeHospital?.max_doctors || ((plan === 'ENTERPRISE') ? 999 : ((plan === 'PRO' || plan === 'PRO_AI') ? 5 : 1));
                const staffDocs = hospitalStaff.doctors.length > 0 ? hospitalStaff.doctors : (Array.isArray(doctorsList) ? doctorsList : []);
                const currentDocCount = staffDocs.length;
                const isLimitReached = plan !== 'ENTERPRISE' && currentDocCount >= maxDocs;

                return (
                <div className="glass-panel" style={{ padding: '30px', textAlign: 'left', width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
                    <div>
                      <h2 style={{ color: 'var(--text-main)', margin: 0 }}>Staff Onboarding & Allocation</h2>
                      <div style={{ fontSize: '13px', color: '#64748B', marginTop: '4px', fontWeight: 600 }}>
                        Active Plan: <strong style={{ color: '#2563EB' }}>{plan}</strong> • Registered Doctors: <strong style={{ color: isLimitReached ? '#DC2626' : '#166534' }}>{currentDocCount} / {maxDocs === 999 ? 'Unlimited' : maxDocs}</strong>
                      </div>
                    </div>
                    {isLimitReached && (
                      <button
                        type="button"
                        onClick={() => {
                          setUpgradeSelectedPlan(plan === 'PRO' ? 'ENTERPRISE' : 'PRO');
                          setShowUpgradeModal(true);
                        }}
                        style={{
                          background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                          color: '#FFFFFF', border: 'none', padding: '8px 16px', borderRadius: '10px',
                          fontSize: '13px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 10px rgba(37,99,235,0.3)'
                        }}
                      >
                        ⚡ Upgrade Plan to Add More Doctors
                      </button>
                    )}
                  </div>

                  {isLimitReached && (
                    <div style={{ background: '#FEF2F2', border: '1.5px solid #FECACA', borderRadius: '12px', padding: '12px 16px', marginBottom: '20px', color: '#991B1B', fontSize: '13px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span>🔒 Doctor Quota Full: Your {plan} plan includes up to {maxDocs} Doctor(s). Please upgrade to add more doctors.</span>
                      <button
                        type="button"
                        onClick={() => {
                          setUpgradeSelectedPlan(plan === 'PRO' ? 'ENTERPRISE' : 'PRO');
                          setShowUpgradeModal(true);
                        }}
                        style={{ background: '#DC2626', color: '#FFF', border: 'none', padding: '5px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 800, cursor: 'pointer' }}
                      >
                        Upgrade Now →
                      </button>
                    </div>
                  )}

                  {staffRegError && <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>{staffRegError}</div>}
                  {staffRegSuccess && <div style={{ color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>{staffRegSuccess}</div>}

                  <form onSubmit={handleRegisterStaff} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', alignItems: 'end' }}>
                      <div className="form-group">
                        <label>Allocate Role</label>
                        <select className="form-control" value={staffRole} onChange={e => setStaffRole(e.target.value)}>
                          <option value="DOCTOR">{t('lbl_doctor')}</option>
                          <option value="RECEPTIONIST">{t('lbl_receptionist')}</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Username</label>
                        <input type="text" className="form-control" value={staffUsername} onChange={e => setStaffUsername(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>Password (Temporary)</label>
                        <input type="password" className="form-control" value={staffPassword} onChange={e => setStaffPassword(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>First Name</label>
                        <input type="text" className="form-control" value={staffFirstName} onChange={e => setStaffFirstName(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>Last Name</label>
                        <input type="text" className="form-control" value={staffLastName} onChange={e => setStaffLastName(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>WhatsApp Phone (For Alerts)</label>
                        <input type="text" className="form-control" placeholder="+91..." value={staffPhone} onChange={e => setStaffPhone(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>Email Address</label>
                        <input type="email" className="form-control" value={staffEmail} onChange={e => setStaffEmail(e.target.value)} required />
                      </div>

                      {staffRole === 'DOCTOR' && (
                        <>
                          <div className="form-group">
                            <label>Department</label>
                            <select className="form-control" value={staffDeptId} onChange={e => setStaffDeptId(e.target.value)} required>
                              <option value="">-- Choose Department --</option>
                              {departments.map(d => (
                                <option key={d.id} value={d.id}>{d.name}</option>
                              ))}
                            </select>
                          </div>
                          <div className="form-group">
                            <label>License Registration Number</label>
                            <input type="text" className="form-control" value={staffLicense} onChange={e => setStaffLicense(e.target.value)} required />
                          </div>
                          <div className="form-group">
                            <label>{t('lbl_opd_fees')}</label>
                            <input type="number" className="form-control" value={staffOpdFees} onChange={e => setStaffOpdFees(parseInt(e.target.value) || 500)} required />
                          </div>
                          <div className="form-group">
                            <label>{t('lbl_slot_dur')}</label>
                            <input type="number" className="form-control" value={slotDurationMinutes} onChange={e => setSlotDurationMinutes(parseInt(e.target.value) || 30)} required style={{ borderRadius: '9px' }} />
                          </div>
                          
                          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 700, color: '#0F172A' }}>{t('lbl_sched_days')}</label>
                            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                              {[
                                { id: 1, label: t('day_mon') },
                                { id: 2, label: t('day_tue') },
                                { id: 3, label: t('day_wed') },
                                { id: 4, label: t('day_thu') },
                                { id: 5, label: t('day_fri') },
                                { id: 6, label: t('day_sat') },
                                { id: 7, label: t('day_sun') }
                              ].map(day => (
                                <label key={day.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#FFFFFF', border: '1.5px solid #CBD5E1', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 600, color: staffScheduleDays.includes(day.id) ? '#2563EB' : '#475569', borderColor: staffScheduleDays.includes(day.id) ? '#2563EB' : '#CBD5E1' }}>
                                  <input 
                                    type="checkbox" 
                                    checked={staffScheduleDays.includes(day.id)}
                                    onChange={e => {
                                      if (e.target.checked) {
                                        setStaffScheduleDays([...staffScheduleDays, day.id]);
                                      } else {
                                        setStaffScheduleDays(staffScheduleDays.filter(id => id !== day.id));
                                      }
                                    }}
                                  />
                                  {day.label}
                                </label>
                              ))}
                            </div>
                          </div>

                          {/* OPD Shift Timings Builder (Shift 1 & Optional Shift 2) */}
                          <div style={{ gridColumn: '1 / -1', background: '#F8FAFC', padding: '18px', borderRadius: '12px', border: '1.5px solid #CBD5E1', marginTop: '6px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: staffHasShift2 ? '1fr 1fr' : '1fr', gap: '20px' }}>
                              <div>
                                <label style={{ fontWeight: 700, fontSize: '13px', color: '#0F172A', marginBottom: '6px', display: 'block' }}>
                                  🌅 Shift 1 (Morning OPD Timings) *
                                </label>
                                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                  <input type="time" className="form-control" value={staffStartTime} onChange={e => setStaffStartTime(e.target.value)} required style={{ borderRadius: '8px' }} />
                                  <span style={{ fontWeight: 700, color: '#64748B' }}>to</span>
                                  <input type="time" className="form-control" value={staffEndTime} onChange={e => setStaffEndTime(e.target.value)} required style={{ borderRadius: '8px' }} />
                                </div>
                              </div>

                              {staffHasShift2 && (
                                <div className="animate-fade-in">
                                  <label style={{ fontWeight: 700, fontSize: '13px', color: '#0F172A', marginBottom: '6px', display: 'block' }}>
                                    ☀️ Shift 2 (Evening OPD Timings)
                                  </label>
                                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                    <input type="time" className="form-control" value={staffStartTime2} onChange={e => setStaffStartTime2(e.target.value)} required style={{ borderRadius: '8px' }} />
                                    <span style={{ fontWeight: 700, color: '#64748B' }}>to</span>
                                    <input type="time" className="form-control" value={staffEndTime2} onChange={e => setStaffEndTime2(e.target.value)} required style={{ borderRadius: '8px' }} />
                                  </div>
                                </div>
                              )}
                            </div>

                            <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px dashed #CBD5E1' }}>
                              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 700, color: '#2563EB' }}>
                                <input 
                                  type="checkbox" 
                                  checked={staffHasShift2} 
                                  onChange={e => setStaffHasShift2(e.target.checked)} 
                                />
                                <span>+ Add 2nd Daily Shift / Evening OPD Slot (Optional)</span>
                              </label>
                            </div>
                          </div>
                        </>
                      )}

                    </div>

                    <div className="form-group" style={{ marginTop: '10px' }}>
                      <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                        Register Account & Dispatch WhatsApp SMS
                      </button>
                    </div>
                  </form>
                </div>
              ); })()}

              {/* 4. HOSPITAL ADMIN: Metrics tab */}
              {activeTab === 'hospital_overview' && userRole === 'ADMIN' && (
                <div style={{ textAlign: 'left' }}>
                  {/* Header & Per-Day Date Filter */}
                  <div style={{
                    background: 'linear-gradient(135deg, rgba(6,182,212,0.15) 0%, rgba(16,185,129,0.10) 100%)',
                    border: '1px solid rgba(6,182,212,0.25)',
                    borderRadius: '20px', padding: '24px 32px', marginBottom: '24px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px'
                  }}>
                    <div>
                      <h2 style={{ color: 'var(--text-main)', fontSize: '22px', fontWeight: 800, margin: 0 }}>📊 Hospital Analytics & Per-Day Metrics</h2>
                      <p style={{ color: '#64748B', fontSize: '13px', margin: '4px 0 0 0' }}>Per-day booking statistics, payment tracking, missed appointments, and revenue analysis.</p>
                    </div>

                    {/* Date Filter Toolbar */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(0,0,0,0.3)', padding: '8px 14px', borderRadius: '14px', border: '1px solid var(--border)' }}>
                      <span style={{ fontSize: '12px', color: '#aaa', fontWeight: 700 }}>📅 Filter Date:</span>
                      <input 
                        type="date" 
                        className="form-control" 
                        style={{ padding: '4px 8px', fontSize: '12px', width: '135px' }} 
                        value={metricsDateFilter}
                        onChange={e => {
                          setMetricsDateFilter(e.target.value);
                          fetchHospitalStats(e.target.value);
                        }}
                      />
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '5px 10px', fontSize: '11px', background: metricsDateFilter === new Date().toISOString().split('T')[0] ? '#10b981' : '' }}
                        onClick={() => {
                          const todayStr = new Date().toISOString().split('T')[0];
                          setMetricsDateFilter(todayStr);
                          fetchHospitalStats(todayStr);
                        }}
                      >
                        Today
                      </button>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '5px 10px', fontSize: '11px' }}
                        onClick={() => {
                          const yest = new Date();
                          yest.setDate(yest.getDate() - 1);
                          const yestStr = yest.toISOString().split('T')[0];
                          setMetricsDateFilter(yestStr);
                          fetchHospitalStats(yestStr);
                        }}
                      >
                        Yesterday
                      </button>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '5px 10px', fontSize: '11px', background: metricsDateFilter === '' ? '#3b82f6' : '' }}
                        onClick={() => {
                          setMetricsDateFilter('');
                          fetchHospitalStats('');
                        }}
                      >
                        All Time
                      </button>
                    </div>
                  </div>

                  {/* 5 Per-Day KPI Cards Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px', marginBottom: '24px' }}>
                    <div style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#10b981', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>✅ Completed Bookings</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.completed_bookings || 0}</div>
                      <div style={{ color: '#64748B', fontSize: '10px', marginTop: '4px' }}>Completed Consultations</div>
                    </div>

                    <div style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#818cf8', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>📅 {t('totalAppointments')}</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.total_bookings || 0}</div>
                      <div style={{ color: '#64748B', fontSize: '10px', marginTop: '4px' }}>{lang === 'hi' ? 'सभी बुकिंग प्राप्त हुईं' : 'All Bookings Received'}</div>
                    </div>

                    <div style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#60a5fa', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>💰 Total Revenue</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>₹{hospitalStats?.total_revenue || 0}</div>
                      <div style={{ color: '#64748B', fontSize: '10px', marginTop: '4px' }}>Revenue Received</div>
                    </div>

                    <div style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#fbbf24', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>⏳ {t('pendingPayment')}</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.pending_bookings || 0}</div>
                      <div style={{ color: '#64748B', fontSize: '10px', marginTop: '4px' }}>{lang === 'hi' ? 'भुगतान लंबित है' : 'Payment Pending'}</div>
                    </div>

                    <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#f87171', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>🚫 {t('missed')} / {t('cancelled')}</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.missed_bookings || 0}</div>
                      <div style={{ color: '#64748B', fontSize: '10px', marginTop: '4px' }}>{lang === 'hi' ? 'छूटी या रद्द हुईं' : 'Missed or Cancelled'}</div>
                    </div>
                  </div>


                  {/* Doctor Performance Table */}
                  <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ color: 'var(--text-main)', marginBottom: '18px', fontSize: '18px', fontWeight: 700 }}>👨‍⚕️ Doctor-wise Performance Breakdown ({metricsDateFilter ? `Date: ${metricsDateFilter}` : 'All Time'})</h3>
                    <div className="table-container">
                      <table className="custom-table">
                        <thead>
                          <tr>
                            <th>Doctor Name</th>
                            <th>Department</th>
                            <th>License No.</th>
                            <th>OPD Fee</th>
                            <th>Confirmed</th>
                            <th>Missed / Cancelled</th>
                            <th>Revenue</th>
                            <th>Status</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(!hospitalStats?.doctors || hospitalStats.doctors.length === 0) ? (
                            <tr>
                              <td colSpan="9" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                                No registered doctors found in insights.
                              </td>
                            </tr>
                          ) : (
                            hospitalStats.doctors.map(doc => (
                              <tr key={doc.id} style={{ borderBottom: '1px solid #E2E8F0' }}>
                                <td>
                                  <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{doc.name}</div>
                                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>ID: {doc.id}</span>
                                </td>
                                <td>{doc.department}</td>
                                <td><code style={{ color: '#a5b4fc', fontSize: '12px' }}>{doc.license}</code></td>
                                <td style={{ fontWeight: 600 }}>₹{doc.opd_fees}</td>
                                <td style={{ fontWeight: 700, color: '#10b981' }}>{doc.confirmed_count || doc.booking_count}</td>
                                <td style={{ fontWeight: 600, color: '#ef4444' }}>{doc.missed_count || 0}</td>
                                <td style={{ fontWeight: 700, color: '#60a5fa' }}>₹{doc.revenue}</td>
                                <td>
                                  <span style={{
                                    background: doc.is_active ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                                    color: doc.is_active ? '#10b981' : '#ef4444',
                                    border: `1px solid ${doc.is_active ? '#10b98140' : '#ef444440'}`,
                                    borderRadius: '12px', padding: '2px 8px', fontSize: '11px', fontWeight: 700
                                  }}>
                                    {doc.is_active ? 'ACTIVE' : 'INACTIVE'}
                                  </span>
                                </td>
                                <td>
                                  <div style={{ display: 'flex', gap: '8px' }}>

                                    <button 
                                      onClick={() => handleDeleteStaff(doc.id)}
                                      style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#f87171', borderRadius: '8px', padding: '6px 12px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                    >
                                      🗑️ Delete
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* 4b. HOSPITAL ADMIN: Leaves Management tab */}
              {activeTab === 'admin_leaves' && userRole === 'ADMIN' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', textAlign: 'left' }}>
                  <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ color: 'var(--text-main)', fontSize: '18px', fontWeight: 700, marginBottom: '18px' }}>{t('active_leaves_heading')}</h3>
                    <div className="table-container">
                      <table className="custom-table">
                        <thead>
                          <tr>
                            <th>Doctor Name</th>
                            <th>Start Date</th>
                            <th>End Date</th>
                            <th>Reason</th>
                            <th>Status</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {leavesList.length === 0 ? (
                            <tr>
                              <td colSpan="6" style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No doctor leaves registered.</td>
                            </tr>
                          ) : (
                            leavesList.map(leave => (
                              <tr key={leave.id} style={{ borderBottom: '1px solid #E2E8F0' }}>
                                <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{leave.doctor_name}</td>
                                <td>{new Date(leave.start_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                                <td>{new Date(leave.end_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                                <td>{leave.reason || 'N/A'}</td>
                                <td>
                                  {leave.status === 'APPROVED' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(16,185,129,0.15)', color: '#10b981', fontSize: '12px', fontWeight: 600 }}>✅ Approved</span>}
                                  {leave.status === 'REJECTED' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(239,68,68,0.15)', color: '#f87171', fontSize: '12px', fontWeight: 600 }}>❌ Rejected</span>}
                                  {leave.status === 'PENDING' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', fontSize: '12px', fontWeight: 600 }}>⏳ Pending</span>}
                                </td>
                                <td>
                                  <div style={{ display: 'flex', gap: '8px' }}>
                                    {leave.status === 'PENDING' && (
                                      <>
                                        <button 
                                          onClick={() => handleApproveLeave(leave.id)}
                                          style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', color: '#34d399', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                        >
                                          ✔️ Approve
                                        </button>
                                        <button 
                                          onClick={() => handleRejectLeave(leave.id)}
                                          style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#f87171', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                        >
                                          ❌ Reject
                                        </button>
                                      </>
                                    )}
                                    {leave.status === 'PENDING' && (
                                      <button 
                                        onClick={() => handleDeleteLeave(leave.id)}
                                        style={{ background: 'var(--bg-muted)', border: '1px solid rgba(255,255,255,0.2)', color: 'var(--text-secondary)', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', marginTop: '5px' }}
                                      >
                                        🗑️ Delete
                                      </button>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
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

              {/* 6. HOSPITAL ADMIN PORTAL: Executive Overview, Plan Posture & Staff Directory */}
              {activeTab === 'admin_overview' && userRole === 'ADMIN' && (() => {
                const myHosp = hospitalStats;
                const staffDoctors = hospitalStaff.doctors.length > 0 ? hospitalStaff.doctors : (Array.isArray(doctorsList) ? doctorsList : []).map(d => ({ ...d, username: d.id, department: d.department_name }));
                const staffReceptionists = hospitalStaff.receptionists;
                const currentPlan = activeHospital?.subscription_plan || hospitalStats?.subscription_plan || 'PRO';
                const isEnterprise = currentPlan === 'ENTERPRISE';
                const maxDocs = activeHospital?.max_doctors || (isEnterprise ? 999 : (currentPlan === 'STARTER' ? 1 : 5));
                const quotaPct = isEnterprise ? 0 : Math.min(100, Math.round((staffDoctors.length / maxDocs) * 100));

                return (
                  <div style={{ textAlign: 'left', animation: 'fadeIn 0.5s ease', maxWidth: '1200px', margin: '0 auto' }}>
                    
                    {/* ── URGENT EXPIRY ALERT RIBBON (When <= 7 Days remain & not expired) ── */}
                    {activeHospital?.days_left !== undefined && activeHospital?.days_left <= 7 && !activeHospital?.is_expired && (
                      <div style={{
                        background: 'linear-gradient(135deg, #FEF2F2 0%, #FFF1F2 100%)',
                        border: '1.5px solid #FCA5A5',
                        borderRadius: '16px', padding: '14px 20px', marginBottom: '20px',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px',
                        boxShadow: '0 4px 14px rgba(239, 68, 68, 0.08)'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span style={{ fontSize: '24px' }}>🚨</span>
                          <div>
                            <div style={{ color: '#991B1B', fontWeight: 900, fontSize: '14px' }}>
                              {lang === 'hi' ? 'तत्काल सूचना: आपका अस्पताल प्लान समाप्त होने वाला है!' : 'Urgent Action Required: Subscription Expiring Soon!'}
                            </div>
                            <div style={{ color: '#B91C1C', fontSize: '12px', fontWeight: 600 }}>
                              {lang === 'hi'
                                ? `आपका ${activeHospital?.subscription_plan || 'PRO'} प्लान ${activeHospital?.days_left} दिनों में समाप्त हो जाएगा (${activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at).toLocaleDateString() : ''})। AI वॉइस और रिसेप्शन जारी रखने के लिए अभी रिन्यू करें।`
                                : `Your ${activeHospital?.subscription_plan || 'PRO'} Plan expires in ${activeHospital?.days_left} days (${activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at).toLocaleDateString() : ''}). Renew or upgrade now to prevent AI Voice and reception stoppage.`}
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => setShowUpgradeModal(true)}
                          style={{
                            background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
                            color: '#FFFFFF', border: 'none', borderRadius: '10px', padding: '9px 18px',
                            fontSize: '13px', fontWeight: 800, cursor: 'pointer',
                            boxShadow: '0 2px 10px rgba(220, 38, 38, 0.25)', transition: 'all 0.15s'
                          }}
                        >
                          ⚡ {lang === 'hi' ? 'प्लान रिन्यू या अपग्रेड करें →' : 'Renew / Upgrade Plan Now →'}
                        </button>
                      </div>
                    )}

                    {/* ── HARD EXPIRED PAYWALL BANNER (When 0 Days Left) ── */}
                    {activeHospital?.is_expired && (
                      <div style={{
                        background: '#FFFFFF', border: '2px solid #FCA5A5', borderRadius: '20px',
                        padding: '32px 24px', textAlign: 'center', marginBottom: '24px',
                        boxShadow: '0 12px 40px rgba(220, 38, 38, 0.12)'
                      }}>
                        <div style={{ fontSize: '48px', marginBottom: '10px' }}>🔒</div>
                        <h2 style={{ fontSize: '24px', fontWeight: 900, color: '#991B1B', margin: 0 }}>
                          {lang === 'hi' ? 'अस्पताल सब्सक्रिप्शन समाप्त हो गया है' : 'Hospital Subscription Expired'}
                        </h2>
                        <p style={{ color: '#475569', fontSize: '14px', maxWidth: '640px', margin: '8px auto 20px auto', lineHeight: 1.5 }}>
                          {lang === 'hi'
                            ? 'आपके अस्पताल का ट्रायल/प्लान समाप्त हो चुका है। AI वॉइस रिसेप्शनिस्ट, डॉक्टर शेड्यूलिंग और फ्रंट डेस्क सेवाओं को दोबारा चालू करने के लिए नीचे दिए गए प्लान्स में से रिन्यू या अपग्रेड करें।'
                            : 'Your hospital subscription has expired. To restore automated AI Voice reception, doctor queues, and patient bookings, please select a plan below to reactivate immediately.'}
                        </p>
                        <button
                          onClick={() => setShowUpgradeModal(true)}
                          style={{
                            background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                            color: '#FFFFFF', border: 'none', borderRadius: '12px', padding: '12px 30px',
                            fontSize: '14px', fontWeight: 800, cursor: 'pointer',
                            boxShadow: '0 4px 16px rgba(37, 99, 235, 0.3)'
                          }}
                        >
                          ⚡ {lang === 'hi' ? 'प्लान चुनें और अभी चालू करें →' : 'Choose Plan & Reactivate Now →'}
                        </button>
                      </div>
                    )}

                    {/* ── TOP EXECUTIVE HOSPITAL HERO CARD ── */}
                    <div style={{
                      background: '#FFFFFF',
                      border: '1.5px solid #DBEAFE',
                      borderRadius: '20px', padding: '24px 28px', marginBottom: '24px',
                      display: 'flex', flexDirection: 'column', gap: '18px',
                      boxShadow: '0 4px 20px -2px rgba(37, 99, 235, 0.06)'
                    }}>
                      {/* Identity Row */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                          <div style={{
                            width: '52px', height: '52px', borderRadius: '16px',
                            background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
                            border: '1.5px solid #BFDBFE', display: 'flex', alignItems: 'center',
                            justifyContent: 'center', fontSize: '26px', boxShadow: '0 4px 12px rgba(37,99,235,0.1)'
                          }}>🏥</div>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                              <h1 style={{ color: '#0F172A', fontSize: '22px', fontWeight: 900, margin: 0, letterSpacing: '-0.3px' }}>
                                {myHosp?.hospital_name || activeHospital?.name || 'Hospital Dashboard'}
                              </h1>
                              
                              {/* Plan Badge */}
                              <span style={{
                                background: (activeHospital?.subscription_plan === 'ENTERPRISE') ? '#F3E8FF' : (activeHospital?.subscription_plan === 'STARTER' ? '#FEF3C7' : '#EFF6FF'),
                                color: (activeHospital?.subscription_plan === 'ENTERPRISE') ? '#7E22CE' : (activeHospital?.subscription_plan === 'STARTER' ? '#92400E' : '#2563EB'),
                                border: `1px solid ${(activeHospital?.subscription_plan === 'ENTERPRISE') ? '#C084FC' : (activeHospital?.subscription_plan === 'STARTER' ? '#FDE68A' : '#93C5FD')}`,
                                padding: '3px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800
                              }}>
                                {activeHospital?.subscription_plan === 'ENTERPRISE' ? '👑 ENTERPRISE 360' : (activeHospital?.subscription_plan === 'STARTER' ? '⭐ STARTER (15-Day Trial)' : '⚡ PRO AI PLAN')}
                              </span>

                              {/* Live Status Badge */}
                              <span style={{
                                background: activeHospital?.is_expired ? '#FEF2F2' : (activeHospital?.days_left <= 7 ? '#FEF3C7' : '#DCFCE7'),
                                color: activeHospital?.is_expired ? '#DC2626' : (activeHospital?.days_left <= 7 ? '#B45309' : '#15803D'),
                                border: `1px solid ${activeHospital?.is_expired ? '#F87171' : (activeHospital?.days_left <= 7 ? '#FCD34D' : '#86EFAC')}`,
                                padding: '3px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800
                              }}>
                                {activeHospital?.is_expired ? '🔴 EXPIRED' : (activeHospital?.days_left <= 7 ? '⚠️ EXPIRING SOON' : '🟢 ACTIVE TENANT')}
                              </span>
                            </div>

                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap' }}>
                              <span style={{ color: '#64748B', fontSize: '12px', fontWeight: 600 }}>Code: <strong style={{ color: '#0F172A', fontFamily: 'monospace' }}>{hospitalId}</strong></span>
                              <span style={{ color: '#CBD5E1' }}>•</span>
                              <span style={{ color: '#64748B', fontSize: '12px', fontWeight: 600 }}>Admin: <strong style={{ color: '#0F172A' }}>{activeHospital?.admin_username || username || 'Admin'}</strong></span>
                              <span style={{ color: '#CBD5E1' }}>•</span>
                              
                              {/* AI Helpline Badge */}
                              {(() => {
                                const assignedHelpline = 
                                  activeHospital?.twilio_helpline || 
                                  activeHospital?.settings?.twilio_helpline || 
                                  activeHospital?.settings?.helpline_number || 
                                  activeHospital?.assigned_helpline || 
                                  myHosp?.settings?.twilio_helpline || 
                                  myHosp?.twilio_helpline || 
                                  '';

                                const isAiEnabled = activeHospital?.ai_voice_enabled === true && activeHospital?.subscription_plan !== 'STARTER';

                                if (!isAiEnabled) {
                                  return (
                                    <button 
                                      onClick={() => setShowUpgradeModal(true)}
                                      style={{ color: '#92400E', background: '#FEF3C7', border: '1px solid #FDE68A', padding: '2px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                    >
                                      🔒 AI Line Locked (Upgrade Plan)
                                    </button>
                                  );
                                }

                                return assignedHelpline ? (
                                  <span style={{ color: '#166534', background: '#DCFCE7', border: '1px solid #BBF7D0', padding: '2px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800 }}>
                                    📞 AI Voice Line: {assignedHelpline}
                                  </span>
                                ) : (
                                  <span style={{ color: '#92400E', background: '#FEF3C7', border: '1px solid #FDE68A', padding: '2px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800 }} title="Platform Owner will assign your dedicated Twilio number within 24-48 hours">
                                    ⏳ AI Voice Line Activation in Progress (Takes 24–48 Hours)
                                  </span>
                                );
                              })()}
                            </div>
                          </div>
                        </div>

                        {/* Action Buttons Toolbar */}
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <button onClick={() => setEditHospitalProfileModalOpen(true)} className="btn btn-secondary" style={{ padding: '7px 12px', fontSize: '12px', borderRadius: '8px', fontWeight: 700 }}>✏️ Profile</button>
                          <button onClick={() => setEditHospitalSettingsModalOpen(true)} className="btn btn-secondary" style={{ padding: '7px 12px', fontSize: '12px', borderRadius: '8px', fontWeight: 700 }}>⚙️ Settings</button>
                          <button onClick={() => { setActiveTab('admin_leaves'); fetchLeaves(); }} className="btn btn-secondary" style={{ padding: '7px 12px', fontSize: '12px', borderRadius: '8px', fontWeight: 700 }}>📅 Leaves</button>
                          <button onClick={() => setActiveTab('hospital_overview')} className="btn btn-secondary" style={{ padding: '7px 12px', fontSize: '12px', borderRadius: '8px', fontWeight: 700 }}>📈 Metrics</button>
                          <button onClick={() => setActiveTab('staff_management')} className="btn btn-primary" style={{ padding: '7px 14px', fontSize: '12px', borderRadius: '8px', fontWeight: 800 }}>➕ Add Staff</button>
                          <button 
                            onClick={() => setShowUpgradeModal(true)}
                            style={{
                              background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                              color: '#FFFFFF', border: 'none', borderRadius: '8px', padding: '7px 14px',
                              fontSize: '12px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)'
                            }}
                          >
                            ⚡ Renew / Upgrade
                          </button>
                        </div>
                      </div>

                      {/* Middle Stat Bar: Plan Validity & Doctor Capacity Gauge */}
                      <div style={{
                        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px',
                        background: '#F8FAFC', padding: '14px 18px', borderRadius: '14px', border: '1px solid #E2E8F0'
                      }}>
                        {/* Validity Countdown */}
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>⏳ Plan Validity & Expiry</span>
                            <span style={{
                              fontSize: '12px', fontWeight: 900,
                              color: activeHospital?.days_left <= 7 ? '#DC2626' : '#15803D'
                            }}>
                              {activeHospital?.days_left !== undefined ? (activeHospital.days_left <= 0 ? 'Expired' : `${activeHospital.days_left} Days Left`) : '28 Days Left'}
                            </span>
                          </div>
                          <div style={{ fontSize: '12px', color: '#475569', fontWeight: 600 }}>
                            Expires: <strong>{activeHospital?.plan_expires_at ? new Date(activeHospital.plan_expires_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '26 Sept 2026'}</strong>
                          </div>
                        </div>

                        {/* Doctor Quota Meter */}
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>👨‍⚕️ Doctor Capacity (Quota)</span>
                            <span style={{ fontSize: '12px', fontWeight: 900, color: '#2563EB' }}>
                              {isEnterprise ? `${staffDoctors.length} / Unlimited Doctors (0%)` : `${staffDoctors.length} / ${maxDocs} Doctors (${quotaPct}%)`}
                            </span>
                          </div>
                          <div style={{ width: '100%', height: '7px', background: '#E2E8F0', borderRadius: '10px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${quotaPct}%`,
                              height: '100%', borderRadius: '10px',
                              background: staffDoctors.length >= maxDocs ? '#DC2626' : '#2563EB',
                              transition: 'width 0.4s ease'
                            }} />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* ── DOCTORS & FRONT DESK TABLES ── */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
                      {/* Doctors Table Section */}
                      <div className="luxury-card" style={{ overflow: 'hidden' }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1.5px solid #DBEAFE', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC' }}>
                          <h2 style={{ color: '#0F172A', fontSize: '16px', fontWeight: 800, margin: 0 }}>👨‍⚕️ Doctors Directory</h2>
                          <span style={{ background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 800 }}>
                            {staffDoctors.length} Doctors
                          </span>
                        </div>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                            <thead>
                              <tr style={{ background: '#FFFFFF', color: '#475569', fontSize: '12px', textTransform: 'uppercase' }}>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Doctor</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Department</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Fee / Slot</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Credentials</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0', textAlign: 'right' }}>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {staffDoctors.length === 0 ? (
                                <tr><td colSpan="5" style={{ padding: '30px', textAlign: 'center', color: '#64748B' }}>No doctors found.</td></tr>
                              ) : staffDoctors.map(doc => (
                                <tr key={doc.id} style={{ borderBottom: '1px solid #F1F5F9', transition: 'background 0.15s' }}>
                                  <td style={{ padding: '14px 20px' }}>
                                    <div style={{ color: '#0F172A', fontWeight: 800, fontSize: '14px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                    <div style={{ color: '#15803D', fontSize: '11px', fontWeight: 800, marginTop: '2px' }}>● ACTIVE</div>
                                  </td>
                                  <td style={{ padding: '14px 20px' }}>
                                    <span style={{ background: '#F1F5F9', color: '#334155', padding: '3px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 700 }}>
                                      {doc.department || doc.department_name || 'General'}
                                    </span>
                                  </td>
                                  <td style={{ padding: '14px 20px' }}>
                                    <div style={{ color: '#15803D', fontSize: '13px', fontWeight: 900 }}>₹{doc.opd_fees || 0}</div>
                                    <div style={{ color: '#64748B', fontSize: '11px' }}>{doc.slot_duration_minutes || 30} mins slot</div>
                                  </td>
                                  <td style={{ padding: '14px 20px' }}>
                                    <div style={{ color: '#334155', fontSize: '12px' }}>U: <strong>{doc.username || doc.id}</strong></div>
                                    <div style={{ color: '#334155', fontSize: '12px' }}>P: <strong style={{ fontFamily: 'monospace' }}>{doc.password || '••••••••'}</strong></div>
                                  </td>
                                  <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                                    <button onClick={() => handleOpenEditDoctorModal(doc)} style={{ padding: '6px 10px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }} title="Edit Doctor">✏️ Edit</button>
                                    <button onClick={() => handleDeleteStaff(doc.id)} style={{ padding: '6px 10px', background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700, marginLeft: '6px' }} title="Delete Doctor">🗑️</button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Receptionists Table Section */}
                      <div className="luxury-card" style={{ overflow: 'hidden' }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1.5px solid #DBEAFE', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F8FAFC' }}>
                          <h2 style={{ color: '#0F172A', fontSize: '16px', fontWeight: 800, margin: 0 }}>Front Desk Staff</h2>
                          <span style={{ background: '#F3E8FF', color: '#7E22CE', border: '1px solid #E9D5FF', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 800 }}>
                            {staffReceptionists.length} Staff
                          </span>
                        </div>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                            <thead>
                              <tr style={{ background: '#FFFFFF', color: '#475569', fontSize: '12px', textTransform: 'uppercase' }}>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Staff Name</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Role</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0' }}>Credentials</th>
                                <th style={{ padding: '12px 20px', fontWeight: 800, borderBottom: '1px solid #E2E8F0', textAlign: 'right' }}>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {staffReceptionists.length === 0 ? (
                                <tr><td colSpan="4" style={{ padding: '30px', textAlign: 'center', color: '#64748B' }}>No receptionists found.</td></tr>
                              ) : staffReceptionists.map(rec => (
                                <tr key={rec.id} style={{ borderBottom: '1px solid #F1F5F9', transition: 'background 0.15s' }}>
                                  <td style={{ padding: '14px 20px' }}>
                                    <div style={{ color: '#0F172A', fontWeight: 800, fontSize: '14px' }}>{rec.first_name || rec.username} {rec.last_name}</div>
                                    <div style={{ color: '#15803D', fontSize: '11px', fontWeight: 800, marginTop: '2px' }}>● ACTIVE</div>
                                  </td>
                                  <td style={{ padding: '14px 20px' }}>
                                    <span style={{ background: '#F3E8FF', color: '#7E22CE', padding: '3px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 700 }}>
                                      Receptionist
                                    </span>
                                  </td>
                                  <td style={{ padding: '14px 20px' }}>
                                    <div style={{ color: '#334155', fontSize: '12px' }}>U: <strong>{rec.username}</strong></div>
                                    <div style={{ color: '#334155', fontSize: '12px' }}>P: <strong style={{ fontFamily: 'monospace' }}>{rec.password || '••••••••'}</strong></div>
                                  </td>
                                  <td style={{ padding: '14px 20px', textAlign: 'right' }}>
                                    <button onClick={() => handleDeleteStaff(rec.id)} style={{ padding: '6px 10px', background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }} title="Delete Account">🗑️ Delete</button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                    </div>
                  </div>
                );
              })()}

              {/* ── SUPER ADMIN: Platform Control Centre (Sidebar + Drilldown) ── */}
              {activeTab === 'super_admin' && userRole === 'SUPER_ADMIN' && (
                <div style={{ display: 'flex', gap: '0', minHeight: '80vh', textAlign: 'left' }}>

                  {/* LEFT SIDEBAR (Luxury Enterprise Light Theme) */}
                  <div style={{
                    width: '240px', flexShrink: 0,
                    background: '#FFFFFF',
                    borderRight: '1.5px solid #DBEAFE',
                    padding: '24px 16px',
                    display: 'flex', flexDirection: 'column', gap: '8px',
                    boxShadow: '2px 0 12px rgba(15, 23, 42, 0.02)'
                  }}>
                    {/* Brand */}
                    <div style={{ marginBottom: '18px', padding: '0 8px' }}>
                      <div style={{ color: '#0F172A', fontWeight: 900, fontSize: '15px', letterSpacing: '-0.3px' }}>Platform Control</div>
                      <div style={{ color: '#64748B', fontSize: '12px', fontWeight: 600 }}>AURA SaaS — Owner Panel</div>
                    </div>

                    {/* Nav Items */}
                    {[
                      { id: 'control_tower', icon: '🛰️', label: 'Control Tower', count: 'LIVE' },
                      { id: 'hospitals', icon: '🏥', label: 'Hospitals & Config', count: hospitalsList.length },
                      { id: 'owners', icon: '🔐', label: 'Platform Owners', count: null },
                    ].map(item => (
                      <button key={item.id} onClick={() => { setSuperAdminView(item.id); setSelectedHospital(null); }}
                        style={{
                          background: superAdminView === item.id ? 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)' : '#F8FAFC',
                          border: `1.5px solid ${superAdminView === item.id ? '#1D4ED8' : '#E2E8F0'}`,
                          borderRadius: '12px', padding: '10px 14px',
                          display: 'flex', alignItems: 'center', gap: '10px',
                          color: superAdminView === item.id ? '#FFFFFF' : '#334155',
                          cursor: 'pointer', fontSize: '13px', fontWeight: 800,
                          textAlign: 'left', width: '100%',
                          boxShadow: superAdminView === item.id ? '0 4px 14px rgba(37, 99, 235, 0.28)' : 'none',
                          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
                        }}>
                        <span style={{ fontSize: '16px' }}>{item.icon}</span>
                        <span style={{ flex: 1 }}>{item.label}</span>
                        {item.count !== null && (
                          <span style={{
                            background: superAdminView === item.id ? 'rgba(255,255,255,0.25)' : '#DBEAFE',
                            color: superAdminView === item.id ? '#FFFFFF' : '#1E40AF',
                            borderRadius: '20px', padding: '2px 8px', fontSize: '11px', fontWeight: 900
                          }}>
                            {item.count}
                          </span>
                        )}
                      </button>
                    ))}

                    <div style={{ borderTop: '1px solid #E2E8F0', margin: '14px 0 8px 0' }} />
                    <div style={{ color: '#475569', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px', padding: '0 8px', marginBottom: '4px' }}>Platform Stats</div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {[
                        { label: 'Total Hospitals', value: hospitalsList.length, color: '#2563EB', bg: '#EFF6FF', border: '#DBEAFE' },
                        { label: 'Active Tenants', value: hospitalsList.filter(h => h.is_active).length, color: '#166534', bg: '#F0FDF4', border: '#DCFCE7' },
                        { label: 'AI Voice Lines', value: hospitalsList.filter(h => h.helpline).length, color: '#D97706', bg: '#FEF3C7', border: '#FDE68A' },
                      ].map(stat => (
                        <div key={stat.label} style={{
                          padding: '8px 12px', borderRadius: '10px',
                          background: stat.bg, border: `1px solid ${stat.border}`,
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                        }}>
                          <span style={{ color: '#334155', fontSize: '12px', fontWeight: 700 }}>{stat.label}</span>
                          <span style={{ color: stat.color, fontWeight: 900, fontSize: '13px' }}>{stat.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* MAIN CONTENT AREA */}
                  <div style={{ flex: 1, padding: '0', overflow: 'auto' }}>

                    {/* ── VIEW: CONTROL TOWER ── */}
                    {superAdminView === 'control_tower' && (
                      <ControlTower API_BASE={API_BASE} token={token} lang={lang} />
                    )}

                    {/* ── VIEW: HOSPITALS LIST ── */}
                    {superAdminView === 'hospitals' && !selectedHospital && (
                      <div style={{ padding: '24px 28px' }}>
                        <div style={{ marginBottom: '20px' }}>
                          <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>🏥 Registered Hospitals</h2>
                          <p style={{ color: '#64748B', fontSize: '13px', margin: '4px 0 0 0' }}>Click a hospital to view details, configure Twilio, and see staff.</p>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                          {hospitalsList.map((hosp, idx) => {
                            const colors = ['#8b5cf6','#06b6d4','#f59e0b','#10b981','#ec4899'];
                            const c = colors[idx % colors.length];
                            const isProOrEnt = (hosp.subscription_plan === 'PRO' || hosp.subscription_plan === 'ENTERPRISE' || hosp.ai_voice_enabled === true);
                            return (
                              <div key={hosp.id}
                                onClick={() => { setSelectedHospital(hosp); fetchHospitalStaff(hosp.id); }}
                                style={{
                                  background: `rgba(${c === '#8b5cf6' ? '139,92,246' : c === '#06b6d4' ? '6,182,212' : c === '#f59e0b' ? '245,158,11' : c === '#10b981' ? '16,185,129' : '236,72,153'},0.06)`,
                                  border: `1px solid ${c}33`,
                                  borderRadius: '14px', padding: '18px 22px', cursor: 'pointer',
                                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                  transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = c}
                                onMouseLeave={e => e.currentTarget.style.borderColor = `${c}33`}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                  <div style={{ width: '46px', height: '46px', borderRadius: '14px', background: `${c}22`, border: `1px solid ${c}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>🏥</div>
                                  <div>
                                    <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '15px' }}>{hosp.name}</div>
                                    <div style={{ color: '#475569', fontSize: '11px', marginTop: '3px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                      <div>📞 <strong>Contact Phone:</strong> {hosp.phone || 'N/A'} {hosp.helpline ? `| 📱 AI Helpline: ${hosp.helpline}` : ''} | 📧 <strong>Admin Email:</strong> {hosp.email || 'N/A'}</div>
                                      <div>👤 <strong>Username:</strong> {hosp.admin_username || 'N/A'} | 🔑 <strong>Password:</strong> {hosp.admin_password || 'N/A'}</div>
                                      <div>📍 <strong>Address:</strong> {hosp.address || 'N/A'} | 🆔 <strong>Hospital ID:</strong> {hosp.id}</div>
                                    </div>
                                  </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ background: hosp.is_active ? '#DCFCE7' : '#FEE2E2', color: hosp.is_active ? '#166534' : '#991B1B', border: `1px solid ${hosp.is_active ? '#BBF7D0' : '#FECACA'}`, borderRadius: '20px', padding: '3px 12px', fontSize: '11px', fontWeight: 800 }}>
                                    {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                                  </span>
                                  <span style={{ 
                                    background: !isProOrEnt ? '#F3F4F6' : hosp.helpline ? '#FEF3C7' : '#EFF6FF', 
                                    color: !isProOrEnt ? '#6B7280' : hosp.helpline ? '#B45309' : '#1E40AF', 
                                    border: `1px solid ${!isProOrEnt ? '#E5E7EB' : hosp.helpline ? '#FDE68A' : '#DBEAFE'}`,
                                    borderRadius: '20px', padding: '3px 12px', fontSize: '11px', fontWeight: 800 
                                  }}>
                                    {!isProOrEnt ? '🔒 STARTER' : hosp.helpline ? `📞 ${hosp.helpline}` : '⏳ PENDING'}
                                  </span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleToggleHospitalStatus(hosp.id);
                                    }}
                                    style={{
                                      background: hosp.is_active ? '#FEF3C7' : '#DCFCE7',
                                      color: hosp.is_active ? '#92400E' : '#166534',
                                      border: `1px solid ${hosp.is_active ? '#FDE68A' : '#BBF7D0'}`,
                                      borderRadius: '8px', padding: '5px 10px', fontSize: '12px', fontWeight: 800,
                                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                                    }}
                                    title="Toggle Active/Inactive Tenant Status"
                                  >
                                    ⚡ {hosp.is_active ? 'Deactivate' : 'Activate'}
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeleteHospital(hosp.id);
                                    }}
                                    style={{
                                      background: '#FEE2E2', color: '#DC2626', border: '1px solid #FECACA',
                                      borderRadius: '8px', padding: '5px 10px', fontSize: '12px', fontWeight: 700,
                                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                                    }}
                                    title="Delete Hospital Tenant"
                                  >
                                    🗑️ Delete
                                  </button>
                                  <span style={{ color: '#2563EB', fontSize: '20px', fontWeight: 800 }}>›</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* ── VIEW: HOSPITAL DETAIL (after clicking a hospital) ── */}
                    {superAdminView === 'hospitals' && selectedHospital && (() => {
                      const hosp = selectedHospital;
                      const isStarter = hosp.subscription_plan === 'STARTER' || hosp.ai_voice_enabled === false;
                      const webhook = getWebhookUrl(hosp.id);

                      // Calculate 48-Hour SLA Remaining Time
                      const createdDate = hosp.created_at ? new Date(hosp.created_at) : new Date();
                      const slaDeadline = new Date(createdDate.getTime() + (48 * 60 * 60 * 1000));
                      const now = new Date();
                      const diffMs = slaDeadline.getTime() - now.getTime();
                      const hoursLeft = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60)));
                      const slaStatusBadge = hoursLeft > 0
                        ? `⏳ Pending AI Line Assignment (${hoursLeft} Hours Left in 48h SLA)`
                        : `⚠️ AI Line Assignment Overdue (48h SLA Exceeded)`;

                      return (
                        <div style={{ padding: '24px 28px' }}>
                          {/* Back button + title */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '22px', flexWrap: 'wrap' }}>
                            <button onClick={() => { setSelectedHospital(null); setHospitalStaff({ doctors: [], receptionists: [] }); }}
                              style={{ background: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '8px', padding: '6px 14px', color: '#334155', cursor: 'pointer', fontSize: '13px', fontWeight: 700 }}>
                              ← Back
                            </button>
                            <div>
                              <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>{hosp.name}</h2>
                              <div style={{ color: '#64748B', fontSize: '12px' }}>{hosp.address || 'Address not set'}</div>
                            </div>
                            <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <button onClick={() => {
                                const cleanSlug = (hosp.slug || hosp.id).replace(/^\/+|\/+$/g, '');
                                const url = `${window.location.origin}/p/${cleanSlug}`;
                                navigator.clipboard.writeText(url);
                                alert(`📋 Patient Portal Link copied for ${hosp.name}!\n\n${url}`);
                              }}
                              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#2563EB', borderRadius: '20px', padding: '6px 14px', fontSize: '12px', fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}
                              title="Copy Patient Portal Link for this Hospital">
                                🔗 Patient Portal Link
                              </button>
                              <button onClick={() => handleToggleHospitalStatus(hosp.id)}
                                style={{ background: hosp.is_active ? '#FEF3C7' : '#DCFCE7', border: `1px solid ${hosp.is_active ? '#FDE68A' : '#BBF7D0'}`, color: hosp.is_active ? '#92400E' : '#166534', borderRadius: '20px', padding: '6px 16px', fontSize: '12px', fontWeight: 800, cursor: 'pointer' }}>
                                ⚡ {hosp.is_active ? 'Deactivate Hospital' : 'Activate Hospital'}
                              </button>
                              <span style={{ background: hosp.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: hosp.is_active ? '#10b981' : '#ef4444', border: `1px solid ${hosp.is_active ? '#10b98150' : '#ef444450'}`, borderRadius: '20px', padding: '4px 14px', fontSize: '12px', fontWeight: 700 }}>
                                {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                              </span>
                              <button onClick={() => handleDeleteHospital(hosp.id)}
                                style={{ background: '#FEE2E2', border: '1px solid #FECACA', color: '#DC2626', borderRadius: '20px', padding: '6px 16px', fontSize: '12px', fontWeight: 800, cursor: 'pointer' }}>
                                🗑️ Delete Hospital
                              </button>
                            </div>
                          </div>

                          {/* Info pills */}
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                            {[
                              { icon: '🪪', label: 'Hospital ID', value: hosp.id, color: '#8b5cf6' },
                              { icon: '📞', label: 'Contact Phone', value: hosp.phone || 'Not set', color: '#06b6d4' },
                              { icon: '💳', label: 'Plan & AI Voice', value: isStarter ? 'Starter (AI Locked)' : (hosp.helpline ? `Pro/Ent (${hosp.helpline})` : `Pro/Ent (${hoursLeft}h SLA)`), color: isStarter ? '#d97706' : (hosp.helpline ? '#10b981' : '#f59e0b') },
                              { icon: '✉️', label: 'Email', value: hosp.email || 'Not set', color: '#f59e0b' },
                              { icon: '👤', label: 'Admin Username', value: hosp.admin_username || 'N/A', color: '#10b981' },
                              { icon: '🔑', label: 'Admin Password', value: hosp.admin_password || 'N/A', color: '#ec4899' },
                            ].map(pill => (
                              <div key={pill.label} style={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: '12px', padding: '12px 16px' }}>
                                <div style={{ color: '#64748B', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px' }}>{pill.icon} {pill.label}</div>
                                <div style={{ color: pill.color, fontSize: '13px', fontWeight: 700, fontFamily: 'monospace', wordBreak: 'break-all' }}>{pill.value}</div>
                              </div>
                            ))}
                          </div>

                          {/* Twilio & WhatsApp Config */}
                          <div style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '18px', marginBottom: '20px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                              <div style={{ color: '#0F172A', fontWeight: 800, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>📡</span>
                                <span>Twilio AI Helpline & WhatsApp Integration</span>
                              </div>
                              {isStarter ? (
                                <span style={{ background: '#FEF3C7', color: '#92400E', border: '1px solid #FDE68A', padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800 }}>
                                  🔒 AI Voice Locked (Starter Free Trial)
                                </span>
                              ) : (hosp.helpline ? (
                                <span style={{ background: '#DCFCE7', color: '#166534', border: '1px solid #BBF7D0', padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800 }}>
                                  🟢 AI Voice Line Active: {hosp.helpline}
                                </span>
                              ) : (
                                <span style={{ background: '#FEF3C7', color: '#B45309', border: '1px solid #FDE68A', padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800 }}>
                                  {slaStatusBadge}
                                </span>
                              ))}
                            </div>

                            {isStarter ? (
                              <div style={{ background: '#FFFBEB', border: '1.5px solid #FDE68A', borderRadius: '10px', padding: '12px 16px', color: '#92400E', fontSize: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span>ℹ️</span>
                                <span>This hospital is on the <strong>Starter Plan (15-Day Free Trial)</strong>. AI Voice helpline is locked for this tier. When the hospital upgrades to <strong>Pro AI</strong> or <strong>Enterprise</strong>, you can assign a dedicated Twilio AI helpline number here.</span>
                              </div>
                            ) : (
                              <>
                                {/* autoComplete=off form wrapper with hidden dummy fields to absorb Chrome autofill */}
                                <form autoComplete="off" onSubmit={e => e.preventDefault()} style={{ margin: 0 }}>
                                  <input type="text" style={{ display: 'none' }} autoComplete="username" tabIndex={-1} readOnly />
                                  <input type="password" style={{ display: 'none' }} autoComplete="current-password" tabIndex={-1} readOnly />
                                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto', gap: '10px', alignItems: 'end', marginBottom: '14px' }}>
                                    <div className="form-group" style={{ margin: 0 }}>
                                      <label style={{ fontSize: '10px', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>Helpline Number</label>
                                      <input type="text" className="form-control" autoComplete="off" name="twilio_helpline_x" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                        placeholder="+91XXXXXXXXXX" value={twilioHelplines[hosp.id] !== undefined ? twilioHelplines[hosp.id] : (hosp.helpline || '')}
                                        onChange={e => setTwilioHelplines(p => ({ ...p, [hosp.id]: e.target.value }))} />
                                    </div>
                                    <div className="form-group" style={{ margin: 0 }}>
                                      <label style={{ fontSize: '10px', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>WhatsApp Number (Master Line)</label>
                                      <input type="text" className="form-control" autoComplete="off" name="twilio_whatsapp_x" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                        placeholder="whatsapp:+1415..." value={twilioWhatsappNumbers[hosp.id] !== undefined ? twilioWhatsappNumbers[hosp.id] : (hosp.whatsapp_number || 'whatsapp:+14155238886')}
                                        onChange={e => setTwilioWhatsappNumbers(p => ({ ...p, [hosp.id]: e.target.value }))} />
                                    </div>
                                    <div className="form-group" style={{ margin: 0 }}>
                                      <label style={{ fontSize: '10px', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>Account SID</label>
                                      <input type="text" className="form-control" autoComplete="off" name="twilio_sid_x" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                        placeholder="ACxxxxxxxx..." value={twilioAccountSids[hosp.id] !== undefined ? twilioAccountSids[hosp.id] : (hosp.twilio_account_sid || '')}
                                        onChange={e => setTwilioAccountSids(p => ({ ...p, [hosp.id]: e.target.value }))} />
                                    </div>
                                    <div className="form-group" style={{ margin: 0 }}>
                                      <label style={{ fontSize: '10px', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>
                                        Auth Token
                                        <button type="button" onClick={() => setShowTwilioTokens(p => ({ ...p, [hosp.id]: !p[hosp.id] }))}
                                          style={{ marginLeft: '6px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '10px', color: '#94a3b8', fontWeight: 600, padding: 0 }}>
                                          {showTwilioTokens?.[hosp.id] ? '🙈 Hide' : '👁 Show'}
                                        </button>
                                      </label>
                                      <input type="text" className="form-control" autoComplete="off" name="twilio_token_x"
                                        style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', WebkitTextSecurity: showTwilioTokens?.[hosp.id] ? 'none' : 'disc' }}
                                        placeholder="Enter Auth Token" value={twilioAuthTokens[hosp.id] !== undefined ? twilioAuthTokens[hosp.id] : (hosp.twilio_auth_token || '')}
                                        onChange={e => setTwilioAuthTokens(p => ({ ...p, [hosp.id]: e.target.value }))} />
                                    </div>
                                    <button type="button" onClick={() => handleSaveTwilioConfig(hosp.id)}
                                      style={{ background: 'linear-gradient(135deg, #fb923c, #f59e0b)', border: 'none', borderRadius: '10px', padding: '10px 18px', color: '#1a1a1a', fontWeight: 700, fontSize: '12px', cursor: 'pointer', whiteSpace: 'nowrap', height: '36px' }}>
                                      💾 Save & Inject
                                    </button>
                                  </div>
                                </form>


                                {/* Webhook URLs Grid */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px', paddingTop: '10px', borderTop: '1px solid #E2E8F0' }}>
                                  <div>
                                    <div style={{ fontSize: '10px', color: '#0284C7', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>📞 Twilio Voice Webhook URL</div>
                                    <div style={{ display: 'flex', gap: '6px' }}>
                                      <input type="text" readOnly className="form-control" style={{ fontSize: '11px', padding: '5px 8px', background: '#F8FAFC', fontFamily: 'monospace', color: '#475569' }}
                                        value={`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/voice/inbound?hospital_id=${hosp.id}`} />
                                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => { navigator.clipboard.writeText(`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/voice/inbound?hospital_id=${hosp.id}`); alert("Voice Webhook copied!"); }}>Copy</button>
                                    </div>
                                  </div>
                                  <div>
                                    <div style={{ fontSize: '10px', color: '#2563EB', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>💬 WhatsApp Webhook URL</div>
                                    <div style={{ display: 'flex', gap: '6px' }}>
                                      <input type="text" readOnly className="form-control" style={{ fontSize: '11px', padding: '5px 8px', background: '#F8FAFC', fontFamily: 'monospace', color: '#475569' }}
                                        value={`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/whatsapp/webhook?hospital_id=${hosp.id}`} />
                                      <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => { navigator.clipboard.writeText(`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/whatsapp/webhook?hospital_id=${hosp.id}`); alert("WhatsApp Webhook copied!"); }}>Copy</button>
                                    </div>
                                  </div>
                                </div>
                              </>
                            )}
                          </div>

                          {/* Staff Section: Doctors + Receptionists */}
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '18px' }}>
                            {/* Doctors */}
                            <div style={{ background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '16px', padding: '18px' }}>
                              <div style={{ color: '#10b981', fontWeight: 800, fontSize: '14px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                👨‍⚕️ Doctors
                                <span style={{ background: 'rgba(16,185,129,0.2)', color: '#10b981', borderRadius: '20px', padding: '1px 8px', fontSize: '11px' }}>{hospitalStaff.doctors.length}</span>
                              </div>
                              {hospitalStaffLoading ? (
                                <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>Loading...</div>
                              ) : hospitalStaff.doctors.length === 0 ? (
                                <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>No doctors registered</div>
                              ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                  {hospitalStaff.doctors.map(doc => (
                                    <div key={doc.id}
                                      onClick={() => setExpandedStaffCard(expandedStaffCard === doc.id ? null : doc.id)}
                                      style={{ background: '#FFFFFF', border: `1px solid ${expandedStaffCard === doc.id ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.08)'}`, borderRadius: '10px', padding: '12px', cursor: 'pointer', transition: 'all 0.15s' }}>
                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div>
                                          <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '13px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                          <div style={{ color: '#10b981', fontSize: '11px', marginTop: '1px' }}>{doc.department}</div>
                                        </div>
                                        <span style={{ color: '#94A3B8', fontSize: '14px' }}>{expandedStaffCard === doc.id ? '▲' : '▼'}</span>
                                      </div>
                                      {expandedStaffCard === doc.id && (
                                        <div style={{ marginTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                          {[
                                            { label: '🔑 Username', value: doc.username },
                                            { label: '✉️ Email', value: doc.email },
                                            { label: '📞 Phone', value: doc.phone || 'N/A' },
                                            { label: '📋 License', value: doc.license_number || 'N/A' },
                                            { label: '💰 OPD Fee', value: `₹${doc.opd_fees}` },
                                          ].map(info => (
                                            <div key={info.label} style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                                              <span style={{ color: '#64748B', minWidth: '90px' }}>{info.label}:</span>
                                              <span style={{ color: 'var(--text-main)', fontWeight: 600, wordBreak: 'break-all' }}>{info.value}</span>
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>

                            {/* Receptionists */}
                            <div style={{ background: 'rgba(6,182,212,0.04)', border: '1px solid rgba(6,182,212,0.2)', borderRadius: '16px', padding: '18px' }}>
                              <div style={{ color: '#06b6d4', fontWeight: 800, fontSize: '14px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                🖥️ Receptionists
                                <span style={{ background: 'rgba(6,182,212,0.2)', color: '#06b6d4', borderRadius: '20px', padding: '1px 8px', fontSize: '11px' }}>{hospitalStaff.receptionists.length}</span>
                              </div>
                              {hospitalStaffLoading ? (
                                <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>Loading...</div>
                              ) : hospitalStaff.receptionists.length === 0 ? (
                                <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>No receptionists registered</div>
                              ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                  {hospitalStaff.receptionists.map(rec => (
                                    <div key={rec.id}
                                      onClick={() => setExpandedStaffCard(expandedStaffCard === rec.id ? null : rec.id)}
                                      style={{ background: '#FFFFFF', border: `1px solid ${expandedStaffCard === rec.id ? 'rgba(6,182,212,0.5)' : 'rgba(255,255,255,0.08)'}`, borderRadius: '10px', padding: '12px', cursor: 'pointer', transition: 'all 0.15s' }}>
                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div>
                                          <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '13px' }}>{rec.first_name} {rec.last_name}</div>
                                          <div style={{ color: '#06b6d4', fontSize: '11px', marginTop: '1px' }}>Receptionist</div>
                                        </div>
                                        <span style={{ color: '#94A3B8', fontSize: '14px' }}>{expandedStaffCard === rec.id ? '▲' : '▼'}</span>
                                      </div>
                                      {expandedStaffCard === rec.id && (
                                        <div style={{ marginTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                          {[
                                            { label: '🔑 Username', value: rec.username },
                                            { label: '✉️ Email', value: rec.email },
                                          ].map(info => (
                                            <div key={info.label} style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                                              <span style={{ color: '#64748B', minWidth: '90px' }}>{info.label}:</span>
                                              <span style={{ color: 'var(--text-main)', fontWeight: 600, wordBreak: 'break-all' }}>{info.value}</span>
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* ── VIEW: PLATFORM OWNERS MANAGEMENT ── */}
                    {superAdminView === 'owners' && (
                      <div>
                        <div style={{ marginBottom: '22px' }}>
                          <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>🔐 Platform Owner Accounts</h2>
                          <p style={{ color: '#64748B', fontSize: '13px', margin: '4px 0 0 0' }}>Register new Platform Owner (SUPER_ADMIN) logins for this platform.</p>
                        </div>

                        {newOwnerSuccess && <div style={{ color: '#34d399', fontSize: '13px', background: 'rgba(52,211,153,0.1)', padding: '12px 16px', borderRadius: '10px', marginBottom: '18px', border: '1px solid rgba(52,211,153,0.2)' }}>✅ {newOwnerSuccess}</div>}
                        {newOwnerError && <div style={{ color: '#f87171', fontSize: '13px', background: 'rgba(239,68,68,0.1)', padding: '12px 16px', borderRadius: '10px', marginBottom: '18px', border: '1px solid rgba(239,68,68,0.2)' }}>⚠️ {newOwnerError}</div>}

                        <div style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '18px', padding: '24px', marginBottom: '24px' }}>
                          <div style={{ color: '#c4b5fd', fontWeight: 700, fontSize: '14px', marginBottom: '6px' }}>➕ Register New Platform Owner</div>
                          <div style={{ color: '#64748B', fontSize: '12px', marginBottom: '18px' }}>
                            This creates a new database-backed SUPER_ADMIN account. The new owner can log in from Platform Owner tab and manage all hospitals.
                          </div>
                          <form onSubmit={handleRegisterSuperAdmin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label style={{ fontSize: '11px', color: '#64748B', fontWeight: 700, marginBottom: '6px', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Username *</label>
                                <input type="text" className="form-control" required style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                                  placeholder="e.g. admin_shiva" value={newOwnerUsername}
                                  onChange={e => setNewOwnerUsername(e.target.value)} />
                              </div>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label style={{ fontSize: '11px', color: '#64748B', fontWeight: 700, marginBottom: '6px', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Email *</label>
                                <input type="email" className="form-control" required style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                                  placeholder="e.g. admin@gmail.com" value={newOwnerEmail}
                                  onChange={e => setNewOwnerEmail(e.target.value)} />
                              </div>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label style={{ fontSize: '11px', color: '#64748B', fontWeight: 700, marginBottom: '6px', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Password *</label>
                                <input type="password" className="form-control" required style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                                  placeholder="••••••••" value={newOwnerPassword}
                                  onChange={e => setNewOwnerPassword(e.target.value)} />
                              </div>
                            </div>
                            <div>
                              <button type="submit" style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)', border: 'none', borderRadius: '10px', padding: '12px 28px', color: 'var(--text-main)', fontWeight: 800, fontSize: '14px', cursor: 'pointer' }}>
                                ➕ Create Platform Owner Account
                              </button>
                            </div>
                          </form>
                        </div>

                        {/* Setup Guide */}
                        <div style={{ background: 'rgba(251,146,60,0.06)', border: '1px solid rgba(251,146,60,0.2)', borderRadius: '14px', padding: '18px 22px' }}>
                          <div style={{ color: '#fb923c', fontWeight: 700, fontSize: '13px', marginBottom: '10px' }}>📋 Setup Guide — How to Activate AI Helpline</div>
                          <ol style={{ color: '#475569', fontSize: '12px', paddingLeft: '16px', lineHeight: '1.9', margin: 0 }}>
                            <li>Buy a Twilio number → go to <strong style={{ color: 'var(--text-main)' }}>console.twilio.com</strong></li>
                            <li>Go to Hospitals → click your hospital → enter Helpline, SID, Token → click <strong style={{ color: '#fb923c' }}>Save & Inject</strong></li>
                            <li>Copy the Webhook URL → paste in Twilio Console under <strong style={{ color: 'var(--text-main)' }}>"A call comes in"</strong></li>
                            <li>Test by calling the Twilio number — AI receptionist will answer!</li>
                          </ol>
                        </div>
                      </div>
                    )}

                  </div>
                </div>
              )}

                </>
              )}
            </div>
          </div>
        )}
      </main>

      {/* MODALS */}

      {/* Edit Hospital Profile Modal */}
      {editHospitalProfileModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '550px', background: '#111827', border: '1px solid var(--border)' }}>
            <h3 style={{ color: 'var(--text-main)', marginBottom: '15px', fontWeight: 700 }}>✏️ Edit Hospital Profile</h3>
            <form onSubmit={handleUpdateHospitalProfile} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <div className="form-group">
                <label>Hospital Name *</label>
                <input type="text" className="form-control" value={editHospitalName} onChange={e => setEditHospitalName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Address</label>
                <input type="text" className="form-control" value={editHospitalAddress} onChange={e => setEditHospitalAddress(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Helpline Phone (Only Platform Owner can modify)</label>
                <input type="text" className="form-control" value={editHospitalPhone} disabled style={{ opacity: 0.8, cursor: 'not-allowed', background: '#FFFFFF' }} />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input type="email" className="form-control" value={editHospitalEmail} onChange={e => setEditHospitalEmail(e.target.value)} />
              </div>
              <div className="form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label>{t('lbl_admin_uname')}</label>
                  <input type="text" className="form-control" value={editHospitalAdminUsername} onChange={e => setEditHospitalAdminUsername(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>{t('lbl_admin_pass')}</label>
                  <input type="text" className="form-control" value={editHospitalAdminPassword} onChange={e => setEditHospitalAdminPassword(e.target.value)} placeholder="Type new password to change..." />
                </div>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="button" onClick={() => setEditHospitalProfileModalOpen(false)} className="btn btn-secondary">Cancel</button>
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Hospital Settings Modal */}
      {editHospitalSettingsModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '650px', background: '#111827', border: '1px solid var(--border)' }}>
            <h3 style={{ color: 'var(--text-main)', marginBottom: '10px', fontWeight: 700 }}>⚙️ AI Voice & WhatsApp Settings</h3>
            <p style={{ color: '#64748B', fontSize: '12px', marginBottom: '15px' }}>
              Configure your dynamic AI Receptionist prompts and active Twilio WhatsApp integration.
            </p>
            
            <form onSubmit={handleUpdateHospitalSettings} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              
              <div className="form-group" style={{ background: '#FFFFFF', padding: '10px 14px', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
                <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: 0 }}>
                  <span style={{ color: '#888', fontSize: '12px' }}>Assigned WhatsApp Business Number: <strong style={{ color: '#60a5fa' }}>{hospSettingsWhatsapp || activeHospital?.whatsapp_number || 'Configured by Platform Owner'}</strong></span>
                  <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '2px 8px', borderRadius: '4px' }}>Managed by Super Admin</span>
                </label>
              </div>

              <div className="form-group">
                <label>{t('lbl_ai_greeting')}</label>
                <textarea 
                  className="form-control" 
                  rows="3" 
                  placeholder="नमस्ते! सी पी तिवारी हॉस्पिटल में आपका स्वागत है। मैं आपकी अपॉइंटमेंट असिस्टेंट हूँ..." 
                  value={hospSettingsGreeting} 
                  onChange={e => setHospSettingsGreeting(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>{t('lbl_sys_prompt')}</label>
                <span style={{ fontSize: '11px', color: '#64748B', marginBottom: '4px', display: 'block' }}>
                  Leave empty to use our standard receptionist engine instructions.
                </span>
                <textarea 
                  className="form-control" 
                  rows="5" 
                  placeholder="तुम अपोलो हॉस्पिटल की AI वर्चुअल रिसेप्शनिस्ट हो। तुम्हारा काम..." 
                  value={hospSettingsFullPrompt} 
                  onChange={e => setHospSettingsFullPrompt(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="button" onClick={() => setEditHospitalSettingsModalOpen(false)} className="btn btn-secondary">Cancel</button>
                <button type="submit" className="btn btn-primary">Save Settings</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* A. Receptionist Prescription Complete Modal */}
      {prescriptionModalOpen && prescAppointment && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <h3 style={{ color: 'var(--text-main)', marginBottom: '15px' }}>
              {prescIsViewMode ? `Consultation Details: ${prescAppointment.patient_name}` : `Prescribe & Complete Consultation: ${prescAppointment.patient_name}`}
            </h3>
            {prescIsViewMode && prescAppointment.consultation_completed_at && (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '15px' }}>
                Completed on: {new Date(prescAppointment.consultation_completed_at).toLocaleString('hi-IN')}
              </div>
            )}
            
            <form onSubmit={(e) => handleCompleteConsultation(e, prescAppointment.id, prescNotes, prescMedicines, prescFollowUp)} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              
              {!prescIsViewMode && (
                <div className="form-group" style={{ background: 'rgba(102,252,241,0.04)', border: '1px solid rgba(102,252,241,0.15)', padding: '12px', borderRadius: '8px', marginBottom: '5px' }}>
                  <label style={{ fontWeight: 700, color: 'var(--color-primary)', display: 'block', marginBottom: '8px', fontSize: '13px' }}>{t('quick_presc_tmpl')}</label>
                  <select 
                    className="form-control"
                    onChange={e => {
                      const templates = [
                        { notes: "", prescription: "" },
                        {
                          notes: "Patient complained of mild viral fever, headache and body ache for 2 days. Chest clear. Advised hydration.",
                          prescription: "1. Tab Paracetamol 650mg - 1 Tab twice daily after meals - 3 Days\n2. Tab Pantocid 40mg - 1 Tab once daily before breakfast - 3 Days\n3. Drink plenty of warm water and take complete rest."
                        },
                        {
                          notes: "Sore throat, dry cough, mild nasal congestion. No difficulty breathing.",
                          prescription: "1. Tab Cetirizine 10mg - 1 Tab once daily at bedtime - 5 Days\n2. Syrup Alex Cough Syrup - 5ml thrice daily - 5 Days\n3. Tab Vitamin C 500mg - 1 Tab daily - 10 Days\n4. Steam inhalation twice daily."
                        },
                        {
                          notes: "Epigastric burning sensation, bloating after meals. Advised light non-spicy meals.",
                          prescription: "1. Cap Pantoprazole 40mg + Domperidone 30mg - 1 Cap empty stomach in morning - 5 Days\n2. Syrup Digene - 10ml twice daily after meals - 5 Days\n3. Avoid tea, coffee and oily foods."
                        },
                        {
                          notes: "Watery stools 4-5 times, mild abdominal cramp, dehydration symptoms.",
                          prescription: "1. Tab Ofloxacin 200mg + Ornidazole 500mg - 1 Tab twice daily after meals - 5 Days\n2. ORS Solution - 1 sachet dissolved in 1L water, sip throughout the day - 3 Days\n3. Tab Loperamide 2mg - 1 Tab only if loose motion persists - SOS"
                        }
                      ];
                      const idx = e.target.selectedIndex;
                      if (idx > 0) {
                        const t = templates[idx];
                        setPrescNotes(t.notes);
                        setPrescMedicines(t.prescription);
                      }
                    }}
                  >
                    <option value="">-- Choose Diagnosis Template --</option>
                    <option value="fever">{t('tmpl_fever')}</option>
                    <option value="cold">{t('tmpl_cold')}</option>
                    <option value="acidity">{t('tmpl_acidity')}</option>
                    <option value="loose_motion">{t('tmpl_stomach')}</option>
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>{t('lbl_clinical_notes')}</label>
                <textarea 
                  className="form-control" 
                  rows="3" 
                  placeholder="Advised medications and rest." 
                  value={prescNotes} 
                  onChange={e => setPrescNotes(e.target.value)}
                  required
                  readOnly={prescIsViewMode}
                />
              </div>

              <div className="form-group">
                <label>{t('lbl_presc_meds')}</label>
                <textarea 
                  className="form-control" 
                  rows="4" 
                  placeholder="Paracetamol 650mg - twice daily for 3 days." 
                  value={prescMedicines} 
                  onChange={e => setPrescMedicines(e.target.value)}
                  required
                  readOnly={prescIsViewMode}
                />
              </div>

              <div className="form-group" style={{ maxWidth: '250px' }}>
                <label>Follow-up Date (optional)</label>
                <input 
                  type="date" 
                  className="form-control" 
                  value={prescFollowUp} 
                  onChange={e => setPrescFollowUp(e.target.value)} 
                  readOnly={prescIsViewMode}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '10px' }}>
                {prescIsViewMode && (
                  <button type="button" onClick={() => window.print()} className="btn btn-secondary">
                    🖨️ Print Prescription
                  </button>
                )}
                <button type="button" onClick={() => setPrescriptionModalOpen(false)} className="btn btn-secondary">Close</button>
                {!prescIsViewMode && (
                  <button type="submit" className="btn btn-primary">Complete & Send to Patient</button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {/* B. Reschedule Modal */}
      {rescheduleModalOpen && targetAppointment && (
        <div className="modal-overlay" style={{ backdropFilter: 'blur(8px)', zIndex: 9999 }}>
          <div className="modal-content" style={{ maxWidth: '560px', width: '92%', background: '#FFFFFF', borderRadius: '20px', padding: '24px', border: '1px solid #E2E8F0', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ color: '#0F172A', margin: 0, fontWeight: 800, fontSize: '18px' }}>
                🔄 Reschedule Appointment
              </h3>
              <button onClick={() => setRescheduleModalOpen(false)} style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '20px', cursor: 'pointer', padding: '2px 6px' }}>✕</button>
            </div>

            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '12px', padding: '12px 14px', marginBottom: '16px', fontSize: '12px', color: '#334155' }}>
              <div>👤 <strong>Patient:</strong> {targetAppointment.patient_name}</div>
              <div style={{ marginTop: '3px' }}>👨‍⚕️ <strong>Doctor:</strong> {targetAppointment.doctor_name} ({targetAppointment.department_name})</div>
              <div style={{ marginTop: '3px', color: '#B45309', fontWeight: 600 }}>ℹ️ Authority: Allowed 1-Time only (Strictly within the next 2 days).</div>
            </div>

            {rescheduleError && (
              <div style={{ color: '#DC2626', background: '#FEF2F2', border: '1px solid #FECACA', padding: '10px 14px', borderRadius: '10px', marginBottom: '14px', fontSize: '12px', fontWeight: 600 }}>
                ⚠️ {rescheduleError}
              </div>
            )}
            
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label style={{ fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px', display: 'block' }}>
                📅 Select Date (Next 2 Days Only)
              </label>
              <input 
                type="date" 
                className="form-control" 
                value={rescheduleDate}
                min={new Date().toISOString().split('T')[0]}
                max={new Date(Date.now() + 2 * 24 * 3600 * 1000).toISOString().split('T')[0]}
                onChange={e => handleDateChangeForReschedule(e.target.value)}
                style={{ padding: '10px 12px', fontSize: '13px', borderRadius: '10px', background: '#F8FAFC', border: '1.5px solid #CBD5E1', width: '100%' }}
              />
            </div>

            {rescheduleDate && (
              <div style={{ marginBottom: '20px' }}>
                <label style={{ fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '8px', display: 'block' }}>
                  ⏰ Select Available Time Slot:
                </label>
                <div>
                  {(() => {
                    if (allSlots.length === 0) {
                      const onLeave = leavesList.find(l => l.doctor_id === targetAppointment.doctor_id && l.status === 'APPROVED' && new Date(l.start_date) <= new Date(rescheduleDate) && new Date(l.end_date) >= new Date(rescheduleDate));
                      if (onLeave) {
                        const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                        const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                        return (
                          <div style={{ textAlign: 'center', padding: '15px', color: '#DC2626', background: '#FEF2F2', borderRadius: '10px', border: '1px solid #FECACA', fontSize: '12px' }}>
                            <strong>{t('doc_on_leave_banner')}</strong><br />
                            <span style={{ marginTop: '4px', display: 'inline-block' }}>Doctor is on approved leave from {sd} to {ed}.</span>
                          </div>
                        );
                      }
                      return (
                        <div style={{ textAlign: 'center', padding: '15px', color: '#64748B', background: '#F8FAFC', borderRadius: '10px', border: '1px solid #E2E8F0', fontSize: '12px', fontStyle: 'italic' }}>
                          No active OPD schedule found for this doctor on selected date.
                        </div>
                      );
                    }
                    return (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(95px, 1fr))', gap: '8px', maxHeight: '200px', overflowY: 'auto', padding: '4px' }}>
                        {allSlots.map(time => {
                          const isBusy = bookedSlots.includes(time);
                          const isSelected = selectedSlotTime === time;
                          return (
                            <button 
                              type="button"
                              key={time} 
                              disabled={isBusy}
                              onClick={() => {
                                if (!isBusy) setSelectedSlotTime(time);
                              }}
                              style={{
                                padding: '9px 6px',
                                borderRadius: '10px',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: isBusy ? 'not-allowed' : 'pointer',
                                transition: 'all 0.15s ease',
                                border: isSelected
                                  ? '2px solid #2563EB'
                                  : isBusy
                                  ? '1px solid #FECACA'
                                  : '1.5px solid #CBD5E1',
                                background: isSelected
                                  ? '#2563EB'
                                  : isBusy
                                  ? '#FEF2F2'
                                  : '#FFFFFF',
                                color: isSelected
                                  ? '#FFFFFF'
                                  : isBusy
                                  ? '#EF4444'
                                  : '#1E293B',
                                boxShadow: isSelected ? '0 4px 10px rgba(37,99,235,0.25)' : 'none',
                                textAlign: 'center'
                              }}
                            >
                              {time}
                              {isBusy && <span style={{ display: 'block', fontSize: '8px', fontWeight: 600, color: '#EF4444' }}>Booked</span>}
                            </button>
                          );
                        })}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px', borderTop: '1px solid #E2E8F0', paddingTop: '16px' }}>
              <button type="button" onClick={() => setRescheduleModalOpen(false)} style={{ background: '#F1F5F9', border: '1px solid #CBD5E1', color: '#334155', borderRadius: '10px', padding: '9px 18px', fontSize: '13px', fontWeight: 700, cursor: 'pointer' }}>Cancel</button>
              <button 
                type="button"
                disabled={!rescheduleDate || !selectedSlotTime}
                onClick={executeReschedule} 
                style={{
                  background: (!rescheduleDate || !selectedSlotTime) ? '#94A3B8' : 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                  border: 'none',
                  color: '#FFFFFF',
                  borderRadius: '10px',
                  padding: '9px 20px',
                  fontSize: '13px',
                  fontWeight: 800,
                  cursor: (!rescheduleDate || !selectedSlotTime) ? 'not-allowed' : 'pointer',
                  boxShadow: '0 4px 12px rgba(37,99,235,0.25)'
                }}
              >
                Confirm Reschedule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Doctor Modal */}
      {editDoctorModalOpen && (
        <div className="modal-overlay" style={{ backdropFilter: 'blur(10px)', zIndex: 9999 }}>
          <div className="modal-content" style={{ maxWidth: '850px', width: '92%', maxHeight: '92vh', overflowY: 'auto', textAlign: 'left', background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '20px', padding: '24px', color: '#0F172A' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px' }}>
              <h3 style={{ color: 'var(--text-main)', margin: 0, fontWeight: 700, fontSize: '18px' }}>✏️ Edit Doctor Profile & OPD Schedule</h3>
              <button onClick={() => setEditDoctorModalOpen(false)} style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: '20px', cursor: 'pointer' }}>✕</button>
            </div>

            {editDocError && <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', padding: '10px 14px', borderRadius: '8px', marginBottom: '14px', fontSize: '13px' }}>⚠️ {editDocError}</div>}
            {editDocSuccess && <div style={{ color: '#10b981', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)', padding: '10px 14px', borderRadius: '8px', marginBottom: '14px', fontSize: '13px' }}>✅ {editDocSuccess}</div>}
            
            <form onSubmit={handleUpdateDoctorSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {/* Row 1: Name & Email */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.2fr', gap: '10px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>First Name *</label>
                  <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocFirstName} onChange={e => setEditDocFirstName(e.target.value)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Last Name *</label>
                  <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocLastName} onChange={e => setEditDocLastName(e.target.value)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Email Address *</label>
                  <input type="email" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocEmail} onChange={e => setEditDocEmail(e.target.value)} required />
                </div>
              </div>

              {/* Row 2: Phone, Username & Password with Eye button */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.2fr', gap: '10px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>WhatsApp Phone *</label>
                  <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocPhone} onChange={e => setEditDocPhone(e.target.value)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Doctor Username *</label>
                  <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocUsername} onChange={e => setEditDocUsername(e.target.value)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>{t('lbl_doc_pass')}</label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <input 
                      type={showEditDocPassword ? 'text' : 'password'} 
                      className="form-control" 
                      style={{ padding: '8px 12px', paddingRight: '38px', fontSize: '13px' }} 
                      value={editDocPassword} 
                      onChange={e => setEditDocPassword(e.target.value)} 
                      placeholder="Type password..." 
                    />
                    <button 
                      type="button" 
                      onClick={() => setShowEditDocPassword(!showEditDocPassword)}
                      style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', color: '#64748B', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px' }}
                      title={showEditDocPassword ? "Hide Password" : "Show Password"}
                    >
                      {showEditDocPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>
              </div>

              {/* Row 3: License, OPD Fees, Slot Duration */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>License No.</label>
                  <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocLicense} onChange={e => setEditDocLicense(e.target.value)} />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>OPD Fees (₹) *</label>
                  <input type="number" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocOpdFees} onChange={e => setEditDocOpdFees(parseInt(e.target.value) || 500)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Slot Duration (mins) *</label>
                  <input type="number" className="form-control" style={{ padding: '8px 12px', fontSize: '13px' }} value={editDocSlotDuration} onChange={e => setEditDocSlotDuration(parseInt(e.target.value) || 30)} required />
                </div>
              </div>

              {/* Row 4: Schedule Days */}
              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>{t('lbl_sched_days')}</label>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {[
                    { id: 1, label: 'Mon' },
                    { id: 2, label: 'Tue' },
                    { id: 3, label: 'Wed' },
                    { id: 4, label: 'Thu' },
                    { id: 5, label: 'Fri' },
                    { id: 6, label: 'Sat' },
                    { id: 7, label: 'Sun' }
                  ].map(day => (
                    <label key={day.id} style={{ display: 'flex', alignItems: 'center', gap: '5px', background: editDocScheduleDays.includes(day.id) ? 'rgba(102,252,241,0.12)' : 'rgba(255,255,255,0.03)', border: editDocScheduleDays.includes(day.id) ? '1px solid var(--color-primary)' : '1px solid rgba(255,255,255,0.08)', padding: '5px 10px', borderRadius: '8px', cursor: 'pointer', fontSize: '12px', color: editDocScheduleDays.includes(day.id) ? 'var(--color-primary)' : 'var(--text-muted)' }}>
                      <input 
                        type="checkbox" 
                        checked={editDocScheduleDays.includes(day.id)}
                        onChange={e => {
                          if (e.target.checked) {
                            setEditDocScheduleDays([...editDocScheduleDays, day.id]);
                          } else {
                            setEditDocScheduleDays(editDocScheduleDays.filter(id => id !== day.id));
                          }
                        }}
                      />
                      {day.label}
                    </label>
                  ))}
                </div>
              </div>

              {/* Row 5: Sessions Start/End Times with Optional 2nd Shift Toggle */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '14px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '8px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: editDocHasShift2 ? '1fr 1fr 1fr 1fr' : '1fr 1fr', gap: '10px' }}>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>🌅 Session 1 Start *</label>
                    <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocStartTime} onChange={e => setEditDocStartTime(e.target.value)} required />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>🌅 Session 1 End *</label>
                    <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocEndTime} onChange={e => setEditDocEndTime(e.target.value)} required />
                  </div>
                  {editDocHasShift2 && (
                    <>
                      <div className="form-group animate-fade-in" style={{ margin: 0 }}>
                        <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>☀️ Session 2 Start</label>
                        <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocStartTime2} onChange={e => setEditDocStartTime2(e.target.value)} required />
                      </div>
                      <div className="form-group animate-fade-in" style={{ margin: 0 }}>
                        <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>☀️ Session 2 End</label>
                        <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocEndTime2} onChange={e => setEditDocEndTime2(e.target.value)} required />
                      </div>
                    </>
                  )}
                </div>

                <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px dashed rgba(255,255,255,0.08)' }}>
                  <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', fontWeight: 700, color: 'var(--color-primary)' }}>
                    <input 
                      type="checkbox" 
                      checked={editDocHasShift2} 
                      onChange={e => {
                        setEditDocHasShift2(e.target.checked);
                        if (!e.target.checked) {
                          setEditDocStartTime2('');
                          setEditDocEndTime2('');
                        } else if (!editDocStartTime2 || editDocStartTime2 === '00:00') {
                          setEditDocStartTime2('14:00');
                          setEditDocEndTime2('17:00');
                        }
                      }} 
                    />
                    <span>+ {editDocHasShift2 ? '2nd Shift Active (Uncheck to remove)' : 'Enable 2nd Shift / Evening OPD (Optional)'}</span>
                  </label>
                </div>
              </div>

              {/* Form Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                <button type="button" onClick={() => setEditDoctorModalOpen(false)} className="btn btn-secondary" style={{ padding: '8px 18px', fontSize: '13px' }}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ padding: '8px 22px', fontSize: '13px', fontWeight: 700 }}>💾 Save Profile & Rebuild Schedule</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* C. Cancel Modal */}
      {cancelModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ color: 'var(--text-main)', marginBottom: '15px' }}>Cancel Appointment</h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '15px' }}>
              Are you sure you want to cancel? {cancelIsPaid && <span style={{ color: '#f59e0b' }}>Note: This is a PAID appointment. Refund will be initiated.</span>}
            </p>
            
            <div className="form-group" style={{ marginBottom: '15px' }}>
              <label>Reason for Cancellation (for WhatsApp alert)</label>
              <textarea 
                className="form-control" 
                rows="3" 
                placeholder="Reason..."
                value={cancelReason}
                onChange={e => setCancelReason(e.target.value)}
                required
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button onClick={() => setCancelModalOpen(false)} className="btn btn-secondary">Discard</button>
              <button onClick={executeCancellation} className="btn btn-danger">Confirm Cancel & Refund</button>
            </div>
          </div>
        </div>
      )}

      {/* D. Patient Profile & Appointments History Modal */}
      {selectedPatientRecord && (
        <div className="modal-backdrop" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '20px' }}>
          <div className="modal-content" style={{ background: '#FFFFFF', borderRadius: '24px', width: '100%', maxWidth: '780px', maxHeight: '90vh', overflowY: 'auto', padding: '28px', boxShadow: '0 20px 45px rgba(15, 23, 42, 0.25)', border: '1.5px solid var(--border)', textAlign: 'left' }}>
            
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1.5px solid #F1F5F9', paddingBottom: '16px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: '#EFF6FF', border: '1px solid #BFDBFE', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' }}>
                  👤
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                      {selectedPatientRecord.name}
                    </h2>
                    {selectedPatientRecord.is_primary && (
                      <span style={{ background: '#DCFCE7', color: '#166534', border: '1px solid #BBF7D0', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                        Primary Patient
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '13px', color: '#64748B', marginTop: '2px', fontWeight: 600 }}>
                    📞 {selectedPatientRecord.phone} • Gender: {selectedPatientRecord.gender || 'N/A'} • Age: {selectedPatientRecord.age || 'N/A'}
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedPatientRecord(null)}
                style={{ background: '#F1F5F9', border: 'none', width: '36px', height: '36px', borderRadius: '10px', fontSize: '18px', color: '#64748B', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                ✕
              </button>
            </div>

            {/* 1. Upcoming & Confirmed Appointments Section */}
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📅</span> Confirmed & Upcoming Appointments ({selectedPatientRecord.upcoming_appointments?.length || 0})
              </h3>
              
              {(!selectedPatientRecord.upcoming_appointments || selectedPatientRecord.upcoming_appointments.length === 0) ? (
                <div style={{ padding: '16px', background: '#F8FAFC', borderRadius: '12px', color: '#64748B', fontSize: '13px', textAlign: 'center', border: '1px solid #E2E8F0' }}>
                  No upcoming appointments scheduled for this patient.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedPatientRecord.upcoming_appointments.map(appt => (
                    <div key={appt.appointment_id} style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '14px', padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '14px', color: '#1E3A8A' }}>
                          🩺 {appt.doctor_name}
                        </div>
                        <div style={{ fontSize: '13px', color: '#1E40AF', marginTop: '2px', fontWeight: 600 }}>
                          ⏱️ Date & Time: <strong>{appt.datetime_display}</strong>
                        </div>
                        <div style={{ fontSize: '12px', color: '#475569', marginTop: '2px' }}>
                          Reason: {appt.reason}
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ background: '#DBEAFE', color: '#1E40AF', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 800 }}>
                          {appt.status || 'CONFIRMED'}
                        </span>
                        <span style={{ background: appt.payment_status === 'PAID' ? '#DCFCE7' : '#FEF3C7', color: appt.payment_status === 'PAID' ? '#166534' : '#92400E', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 800 }}>
                          {appt.payment_status === 'PAID' ? '💰 PAID' : '⏳ PENDING'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 2. Past History & Completed Appointments Section */}
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📜</span> Past Consultation History & Prescriptions ({selectedPatientRecord.history_appointments?.length || 0})
              </h3>
              
              {(!selectedPatientRecord.history_appointments || selectedPatientRecord.history_appointments.length === 0) ? (
                <div style={{ padding: '16px', background: '#F8FAFC', borderRadius: '12px', color: '#64748B', fontSize: '13px', textAlign: 'center', border: '1px solid #E2E8F0' }}>
                  No past appointment history found.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedPatientRecord.history_appointments.map(appt => (
                    <div key={appt.appointment_id} style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '14px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: appt.has_prescription ? '10px' : '0' }}>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '14px', color: '#0F172A' }}>
                            🩺 {appt.doctor_name}
                          </div>
                          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                            📅 {appt.datetime_display} • Reason: {appt.reason}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ background: '#F1F5F9', color: '#334155', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                            {appt.status}
                          </span>
                          <span style={{ background: appt.payment_status === 'PAID' ? '#DCFCE7' : '#FEE2E2', color: appt.payment_status === 'PAID' ? '#166534' : '#991B1B', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                            {appt.payment_status}
                          </span>
                        </div>
                      </div>

                      {/* Prescription details if available */}
                      {appt.has_prescription && appt.prescription && (
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '10px', padding: '12px', marginTop: '8px', fontSize: '12px' }}>
                          <div style={{ fontWeight: 700, color: '#2563EB', marginBottom: '4px' }}>📋 Prescription & Clinical Notes:</div>
                          {appt.prescription.clinical_notes && <div><strong>Notes:</strong> {appt.prescription.clinical_notes}</div>}
                          {appt.prescription.prescription && <div style={{ marginTop: '2px' }}><strong>Medicines:</strong> {appt.prescription.prescription}</div>}
                          {appt.prescription.follow_up_date && <div style={{ marginTop: '2px', color: '#059669', fontWeight: 600 }}>🗓️ Follow-up Date: {appt.prescription.follow_up_date}</div>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ textAlign: 'right', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #F1F5F9' }}>
              <button onClick={() => setSelectedPatientRecord(null)} className="btn btn-secondary" style={{ padding: '8px 20px', fontSize: '13px', borderRadius: '10px', fontWeight: 700 }}>
                Close Modal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── INTERACTIVE PLAN RENEWAL & UPGRADE MODAL ── */}
      {showUpgradeModal && (() => {
        const currentActivePlan = activeHospital?.subscription_plan || hospitalStats?.subscription_plan || 'PRO';
        const isEnterprise = currentActivePlan === 'ENTERPRISE';
        const isStarter = currentActivePlan === 'STARTER';
        const isPro = currentActivePlan === 'PRO';

        const starterPlan = plansList.find(p => p.plan_code === 'STARTER');
        const proPlan = plansList.find(p => p.plan_code === 'PRO');
        const enterprisePlan = plansList.find(p => p.plan_code === 'ENTERPRISE');

        const starterPrice = starterPlan ? Number(starterPlan.price_inr) : 1500;
        const proPrice = proPlan ? Number(proPlan.price_inr) : 2999;
        const enterprisePrice = enterprisePlan ? Number(enterprisePlan.price_inr) : 29999;

        return (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '20px' }}>
          <div className="animate-modal-pop" style={{ background: '#FFFFFF', borderRadius: '24px', width: '100%', maxWidth: '780px', padding: '32px', boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.3)', border: '1.5px solid #DBEAFE', textAlign: 'left' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9', paddingBottom: '16px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                  ⚡ {lang === 'hi' ? 'सब्सक्रिप्शन एवं प्लान प्रबंधन' : 'Subscription & Plan Management'}
                </h3>
                <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 600, marginTop: '2px' }}>
                  {lang === 'hi' ? 'वर्तमान सक्रिय प्लान:' : 'Current Active Plan:'} <strong style={{ color: isEnterprise ? '#7E22CE' : (isPro ? '#2563EB' : '#D97706') }}>
                    {isEnterprise ? '👑 ENTERPRISE 360' : (isPro ? '⚡ PRO AI PLAN' : '⭐ STARTER (15-Day Trial)')}
                  </strong> • {activeHospital?.days_left !== undefined ? `${activeHospital.days_left} ${lang === 'hi' ? 'दिन शेष' : 'Days Left'}` : ''}
                </div>
              </div>
              <button onClick={() => setShowUpgradeModal(false)} style={{ background: '#F1F5F9', border: 'none', width: '32px', height: '32px', borderRadius: '50%', fontSize: '16px', cursor: 'pointer', color: '#64748B', fontWeight: 800 }}>✕</button>
            </div>

            <div style={{
              background: activeHospital?.is_expired ? '#FEF2F2' : (activeHospital?.days_left <= 7 ? '#FFFBEB' : '#F0FDF4'),
              border: `1.5px solid ${activeHospital?.is_expired ? '#FECACA' : (activeHospital?.days_left <= 7 ? '#FDE68A' : '#BBF7D0')}`,
              borderRadius: '12px', padding: '12px 16px', marginBottom: '20px',
              color: activeHospital?.is_expired ? '#991B1B' : (activeHospital?.days_left <= 7 ? '#92400E' : '#166534'),
              fontSize: '12px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px'
            }}>
              <span>{activeHospital?.is_expired ? '🚨' : (activeHospital?.days_left <= 7 ? '⚠️' : '✓')}</span>
              <span>
                {activeHospital?.is_expired
                  ? (lang === 'hi' ? 'आपका प्लान समाप्त हो चुका है। सेवाओं को तुरंत सक्रिय करने के लिए नीचे दिए गए प्लान का चयन करें।' : 'Your subscription has expired. Please select a plan below to reactivate all services.')
                  : (lang === 'hi' ? 'प्लान समाप्ति से पहले रिन्यू या अपग्रेड करें ताकि AI रिसेप्शनिस्ट और व्हाट्सएप सेवाएं बिना रुकावट चलती रहें।' : 'Renew or upgrade before expiration to maintain uninterrupted 24/7 AI Voice reception and doctor operations.')}
              </span>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: isStarter ? 'repeat(auto-fit, minmax(220px, 1fr))' : (isEnterprise ? '1fr' : '1fr 1fr'),
              gap: '16px',
              marginBottom: '20px'
            }}>
              {/* Option 1: Starter Renewal (Only shown for Starter Hospitals) */}
              {isStarter && (
                <div 
                  style={{
                    background: '#F8FAFC',
                    border: '2px solid #CBD5E1',
                    borderRadius: '18px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                    boxShadow: '0 4px 14px rgba(15, 23, 42, 0.04)'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '14px', fontWeight: 800, color: '#334155' }}>
                        🥉 {lang === 'hi' ? 'स्टार्टर रिन्यूअल' : 'Starter Renewal'}
                      </span>
                      <span style={{ background: '#F1F5F9', color: '#475569', padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 800 }}>
                        +30 Days
                      </span>
                    </div>
                    <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '8px 0 4px 0' }}>
                      ₹{starterPrice.toLocaleString()} <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>/ month</span>
                    </div>
                    <ul style={{ listStyle: 'none', padding: 0, margin: '10px 0 16px 0', fontSize: '11px', color: '#475569', display: 'flex', flexDirection: 'column', gap: '6px', fontWeight: 600 }}>
                      <li>✓ 👨‍⚕️ <strong>{starterPlan?.max_doctors || 1} {lang === 'hi' ? 'डॉक्टर प्रोफाइल' : 'Doctor Profile'}</strong></li>
                      <li>✓ 🖥️ {lang === 'hi' ? 'रिसेप्शनिस्ट वर्कस्पेस' : 'Receptionist Portal'}</li>
                      <li>✓ 📱 {lang === 'hi' ? 'ऑनलाइन बुकिंग' : 'Online Booking'}</li>
                      <li>❌ 🔒 <strong>{lang === 'hi' ? 'AI वॉइस हेल्पलाइन बंद' : 'AI Voice Helpline Locked'}</strong></li>
                    </ul>
                  </div>
                  <button
                    onClick={() => handleRazorpayRenewPlan(hospitalId)}
                    style={{
                      width: '100%', padding: '12px', borderRadius: '10px', border: '1.5px solid #CBD5E1',
                      background: '#FFFFFF', color: '#0F172A', fontWeight: 800, fontSize: '13px', cursor: 'pointer',
                      boxShadow: '0 2px 8px rgba(15,23,42,0.05)'
                    }}
                  >
                    {lang === 'hi' ? `स्टार्टर रिन्यू करें (₹${starterPrice.toLocaleString()})` : `Renew Starter (₹${starterPrice.toLocaleString()}) →`}
                  </button>
                </div>
              )}

              {/* Option 2: Pro AI Plan (Upgrade or Renew) */}
              <div 
                style={{
                  background: '#F0FDF4',
                  border: '2.5px solid #2563EB',
                  borderRadius: '18px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                  boxShadow: '0 8px 24px rgba(37, 99, 235, 0.12)', position: 'relative'
                }}
              >
                {isStarter && (
                  <span style={{ position: 'absolute', top: '-12px', right: '16px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', color: '#FFFFFF', fontSize: '10px', fontWeight: 800, padding: '3px 10px', borderRadius: '12px' }}>
                    RECOMMENDED
                  </span>
                )}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '14px', fontWeight: 800, color: '#2563EB' }}>
                      {isStarter ? '⚡ PRO AI PLAN' : (isEnterprise ? '🔄 Renew Enterprise' : '🔄 Renew PRO Plan')}
                    </span>
                    <span style={{ background: '#DBEAFE', color: '#1E40AF', padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 800 }}>
                      +{isEnterprise ? '365' : '30'} Days
                    </span>
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '8px 0 4px 0' }}>
                    ₹{isEnterprise ? enterprisePrice.toLocaleString() : proPrice.toLocaleString()} <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>{isEnterprise ? '/ year' : '/ month'}</span>
                  </div>
                  <ul style={{ listStyle: 'none', padding: 0, margin: '10px 0 16px 0', fontSize: '11px', color: '#334155', display: 'flex', flexDirection: 'column', gap: '6px', fontWeight: 600 }}>
                    <li>✓ 📞 <strong>{lang === 'hi' ? '24/7 AI वॉइस रिसेप्शनिस्ट' : '24/7 AI Voice Receptionist'}</strong></li>
                    <li>✓ 👨‍⚕️ <strong>{isEnterprise ? 'Unlimited' : (proPlan?.max_doctors || '5')} {lang === 'hi' ? 'डॉक्टर क्षमता' : 'Doctors Capacity'}</strong></li>
                    <li>✓ 💬 <strong>{lang === 'hi' ? 'व्हाट्सएप ऑटोमेशन' : 'WhatsApp Automation'}</strong></li>
                    <li>✓ 💳 <strong>{lang === 'hi' ? 'ऑनलाइन OPD पेमेंट' : 'Online OPD Payments'}</strong></li>
                  </ul>
                </div>
                <button
                  onClick={() => {
                    if (isStarter) {
                      handleRazorpayUpgradePlan(hospitalId, 'PRO');
                    } else {
                      handleRazorpayRenewPlan(hospitalId);
                    }
                  }}
                  style={{
                    width: '100%', padding: '12px', borderRadius: '10px', border: 'none',
                    background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                    color: '#FFFFFF', fontWeight: 800, fontSize: '13px', cursor: 'pointer',
                    boxShadow: '0 4px 12px rgba(37,99,235,0.3)'
                  }}
                >
                  {isStarter ? `Upgrade to Pro (₹${proPrice.toLocaleString()}) →` : `Pay & Renew (₹${isEnterprise ? enterprisePrice.toLocaleString() : proPrice.toLocaleString()}) →`}
                </button>
              </div>

              {/* Option 3: Upgrade to Enterprise 360 */}
              {!isEnterprise && (
                <div 
                  style={{
                    background: '#FAF5FF',
                    border: '2px solid #7E22CE',
                    borderRadius: '18px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                    boxShadow: '0 4px 14px rgba(126, 34, 206, 0.08)'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '14px', fontWeight: 800, color: '#7E22CE' }}>👑 ENTERPRISE 360</span>
                      <span style={{ background: '#F3E8FF', color: '#6B21A8', padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 800 }}>
                        +365 Days
                      </span>
                    </div>
                    <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: '8px 0 4px 0' }}>
                      ₹{enterprisePrice.toLocaleString()} <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>/ year</span>
                    </div>
                    <ul style={{ listStyle: 'none', padding: 0, margin: '10px 0 16px 0', fontSize: '11px', color: '#334155', display: 'flex', flexDirection: 'column', gap: '6px', fontWeight: 600 }}>
                      <li>✓ 👨‍⚕️ <strong>{lang === 'hi' ? 'असीमित डॉक्टर्स (Unlimited)' : 'Unlimited Doctors'}</strong></li>
                      <li>✓ ⚡ <strong>{lang === 'hi' ? 'प्राथमिकता AI वॉइस रूटिंग' : 'Priority AI Voice Routing'}</strong></li>
                      <li>✓ 🎨 <strong>{lang === 'hi' ? 'कस्टम डोमेन एवं ब्रांडिंग' : 'Custom Domain & Branding'}</strong></li>
                      <li>✓ 🛡️ <strong>{lang === 'hi' ? '99.99% SRE अपटाइम गारंटी' : '99.99% SRE Uptime SLA'}</strong></li>
                    </ul>
                  </div>
                  <button
                    onClick={() => handleRazorpayUpgradePlan(hospitalId, 'ENTERPRISE')}
                    style={{
                      width: '100%', padding: '12px', borderRadius: '10px', border: 'none',
                      background: 'linear-gradient(135deg, #7E22CE 0%, #6B21A8 100%)',
                      color: '#FFFFFF', fontWeight: 800, fontSize: '13px', cursor: 'pointer',
                      boxShadow: '0 4px 12px rgba(126,34,206,0.25)'
                    }}
                  >
                    Upgrade Enterprise (₹{enterprisePrice.toLocaleString()}) →
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        );
      })()}

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
