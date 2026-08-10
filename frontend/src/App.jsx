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
    receptionistLeaves: "Receptionist Leaves",
    adminOverview: "Admin Overview",
    staffManagement: "Staff Management",
    hospitalOverview: "Hospital Overview",
    adminLeaves: "Admin Leaves",
    appointments: "Appointments",
    doctorLeaves: "Doctor Leaves",
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
    receptionistLeaves: "रिसेप्शनिस्ट छुट्टियां",
    adminOverview: "एडमिन अवलोकन",
    staffManagement: "स्टाफ प्रबंधन",
    hospitalOverview: "अस्पताल प्रोफाइल",
    adminLeaves: "एडमिन छुट्टियां",
    appointments: "अपॉइंटमेंट्स",
    doctorLeaves: "डॉक्टर छुट्टियां",
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
    reschedule: "रीशेड्यूल करें",
    cancelBooking: "रद्द करें",
    // Settings
    profileSettings: "अस्पताल प्रोफाइल सेटिंग्स",
    opdSettings: "ओपीडी सेटिंग्स",
    whatsappConfig: "व्हाट्सएप नोटिफिकेशन नंबर",
    greetingConfig: "रिसेप्शनिस्ट वॉयस ग्रीटिंग",
    promptConfig: "वॉयस असिस्टेंट निर्देश प्रॉम्ट",
    // Table Column Headers
    col_time: "समय (Time)",
    col_patient: "मरीज (Patient)",
    col_mobile: "मोबाइल (Mobile)",
    col_reason: "समस्या (Reason)",
    col_payment: "भुगतान (Payment)",
    col_status_action: "स्थिति/कार्रवाई (Status/Action)",
    doc_fee_list: "डॉक्टर, समय एवं फीस सूची",
    // Date Nav Buttons
    btn_prev: "\u25c4 पिछला (Prev)",
    btn_today: "आज (Today)",
    btn_next: "अगला (Next) \u25ba",
    // Empty / Error States
    no_bookings_date: "इस तारीख के लिए कोई भी अपॉइंटमेंट बुक नहीं है।",
    search_failed: "खोज विफल रही। कृपया पुनः प्रयास करें।",
    no_patient_found: "कोई मरीज रिकॉर्ड नहीं मिला।",
    // Status Badges
    on_leave: "\u26a0\ufe0f छुट्टी पर (On Leave)",
    off_duty: "Off Duty / Closed (छुट्टी)",
    doc_on_leave_banner: "\u26a0\ufe0f DOCTOR IS ON LEAVE (डॉक्टर छुट्टी पर हैं)",
    // Section Headings
    patient_lookup_heading: "Patient Lookup Engine (मरीज़ खोज इंजन)",
    active_leaves_heading: "\ud83d\udcc5 Active Doctor Leaves (डॉक्टरों की छुट्टियाँ)",
    apply_leave_heading: "\ud83d\udcdd Apply For Leave (अवकाश के लिए आवेदन)",
    my_leaves_heading: "\ud83d\udcc5 My Registered Leaves (मेरे अवकाश)",
    recep_dashboard_sub: "रिसेप्शनिस्ट डैशबोर्ड \u2014 AI वॉयस बुकिंग सिस्टम",
    // Form Labels
    lbl_doctor: "Doctor (चिकित्सक)",
    lbl_receptionist: "Receptionist (रिसेप्शनिस्ट)",
    lbl_opd_fees: "OPD Fees (फीस \u20b9)",
    lbl_slot_dur: "Slot Duration (मिनट) *",
    lbl_sched_days: "Schedule Days (साप्ताहिक दिन) *",
    lbl_reason: "Reason (कारण)",
    lbl_admin_uname: "Admin Username (लॉगिन यूजरनेम) *",
    lbl_admin_pass: "Admin Password (लॉगिन पासवर्ड)",
    lbl_ai_greeting: "AI Greeting Message (नमस्ते स्वागत संदेश) *",
    lbl_sys_prompt: "Custom System Prompt (वर्चुअल डॉक्टर निर्देश - Optional)",
    lbl_doc_pass: "Doctor Password (लॉगिन पासवर्ड)",
    lbl_password_field: "Password (पासवर्ड)",
    err_select_doc: "कृपया डॉक्टर का चयन करें (Please select a doctor).",
    err_select_slot: "कृपया समय स्लॉट (Time Slot) का चयन करें.",
    payment_mode_heading: "\ud83d\udcb3 Payment Mode Selection (भुगतान विकल्प)",
    // Prescription Templates
    quick_presc_tmpl: "\u26a1 Quick Prescription Template (त्वरित पर्चा टेम्पलेट)",
    tmpl_fever: "Mild Fever & Body Pain (सामान्य बुखार)",
    tmpl_cold: "Cold, Cough & Throat Infection (सर्दी-खांसी)",
    tmpl_acidity: "Stomach Acidity & Gas (गैस-एसिडिटी)",
    tmpl_stomach: "Stomach Infection / Loose Motion (दस्त / दस्त-उल्टी)",
    lbl_clinical_notes: "Clinical Notes / Diagnosis Summary (क्लीनिकल नोट्स)",
    lbl_presc_meds: "Prescription Medicines & Dosage (दवाइयों की सूची)",
    // Day Abbreviations
    day_mon: "सोम (Mon)", day_tue: "मंगल (Tue)", day_wed: "बुध (Wed)", day_thu: "गुरु (Thu)",
    day_fri: "शुक्र (Fri)", day_sat: "शनि (Sat)", day_sun: "रवि (Sun)",
    // Confirmation Dialogs
    confirm_del_leave: "क्या आप सच में इस छुट्टी को हटाना चाहते हैं?",
    confirm_appr_leave: "क्या आप सच में इस छुट्टी को स्वीकृत (Approve) करना चाहते हैं?",
    confirm_rej_leave: "क्या आप सच में इस छुट्टी को अस्वीकृत (Reject) करना चाहते हैं?",
    confirm_del_staff: "क्या आप सच में इस स्टाफ को हटाना चाहते हैं?",
    // Misc
    default_schedule: "सोम\u2013शुक्र, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM",
    leave_reason_placeholder: "e.g. Sick Leave, Personal Work",
    ai_prompt_placeholder: "तुम अपोलो हॉस्पिटल की AI वर्चुअल रिसेप्शनिस्ट हो। तुम्हारा काम...",
  }
};

export default function App() {
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
  const [superAdminView, setSuperAdminView] = useState('hospitals'); // 'hospitals' | 'owners'
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
  const [staffOpdFees, setStaffOpdFees] = useState(500);
  const [hospitalStats, setHospitalStats] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [selectedScheduleDate, setSelectedScheduleDate] = useState(new Date().toISOString().split('T')[0]);
  const [doctorQueueSearch, setDoctorQueueSearch] = useState('');
  // Active Hospital Profile & Settings
  const [activeHospital, setActiveHospital] = useState(null);
  
  // New Booking Slots Grid state
  const [newBookingBookedSlots, setNewBookingBookedSlots] = useState([]);
  const [newBookingAllSlots, setNewBookingAllSlots] = useState([]);
  const [selectedNewBookingSlot, setSelectedNewBookingSlot] = useState('');
  
  // Edit Profile / Settings Modals state
  const [editHospitalProfileModalOpen, setEditHospitalProfileModalOpen] = useState(false);
  const [editHospitalSettingsModalOpen, setEditHospitalSettingsModalOpen] = useState(false);
  
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
      setLoginHospitalId('');
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
    } catch (err) {
      setOnboardError(err.message);
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
        setDoctorsList(docs);
        const uniqueDepts = Array.from(new Set(docs.map(d => d.department_id))).map(id => ({
          id,
          name: docs.find(d => d.department_id === id)?.department_name || 'General Medicine'
        }));
        setDepartmentsList(uniqueDepts);
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
        setAppointmentsList(data);
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
        setLeavesList(data);
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
    const DEFAULT_HOSPITAL_FALLBACK = [
      { id: 'hosp_default', name: 'Balaji Hospital', phone: '+918542996385', email: 'contact@balajihospital.com', address: 'Main Road', is_active: true, helpline: '+918542996385', slug: 'balaji-hospital', created_at: '2024-01-01' }
    ];
    try {
      const res = await fetch(`${API_BASE}/hospitals`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const finalData = data.length > 0 ? data : DEFAULT_HOSPITAL_FALLBACK;
        setHospitalsList(finalData);
        
        // Pre-populate input states with fetched settings
        const sids = {};
        const tokens = {};
        const helplines = {};
        const whatsappNums = {};
        finalData.forEach(h => {
          sids[h.id] = h.twilio_account_sid || '';
          tokens[h.id] = h.twilio_auth_token || '';
          helplines[h.id] = h.helpline || h.phone || '';
          whatsappNums[h.id] = h.whatsapp_number || '';
        });
        setTwilioAccountSids(sids);
        setTwilioAuthTokens(tokens);
        setTwilioHelplines(helplines);
        setTwilioWhatsappNumbers(whatsappNums);
      } else {
        setHospitalsList(DEFAULT_HOSPITAL_FALLBACK);
      }
    } catch (e) {
      console.error(e);
      setHospitalsList(DEFAULT_HOSPITAL_FALLBACK);
    }
  }, [token, userRole]);

  useEffect(() => {
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
  }, [token, refreshTrigger, hospitalId, fetchDoctorsAndDepartments, fetchAppointments, fetchHospitals, fetchHospitalStats, fetchDepartments, fetchLeaves, fetchActiveHospitalProfile]);

  // Auto-refresh receptionist queue every 5 seconds
  useEffect(() => {
    if (token && userRole === 'RECEPTIONIST') {
      const interval = setInterval(() => {
        fetchAppointments();
        fetchDoctorsAndDepartments();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [token, userRole, fetchAppointments, fetchDoctorsAndDepartments]);

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
        if (staffStartTime2 && staffEndTime2) {
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
    // Pre-fill session times from existing schedule or sensible defaults
    // Parse timings string like {t('default_schedule')}
    let s1Start = '10:00', s1End = '13:00', s2Start = '', s2End = '';
    if (doc.timings) {
      const parts = doc.timings.split('|').map(p => p.trim());
      const toHH = (t) => {
        if (!t) return '';
        const m = t.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
        if (!m) return '';
        let h = parseInt(m[1]); const min = m[2]; const ampm = m[3].toUpperCase();
        if (ampm === 'PM' && h !== 12) h += 12;
        if (ampm === 'AM' && h === 12) h = 0;
        return `${String(h).padStart(2,'0')}:${min}`;
      };
      if (parts[0]) {
        const times = parts[0].match(/(\d{1,2}:\d{2}\s*[AP]M)/gi) || [];
        if (times[0]) s1Start = toHH(times[0]);
        if (times[1]) s1End = toHH(times[1]);
      }
      if (parts[1]) {
        const times2 = parts[1].match(/(\d{1,2}:\d{2}\s*[AP]M)/gi) || [];
        if (times2[0]) s2Start = toHH(times2[0]);
        if (times2[1]) s2End = toHH(times2[1]);
      }
    }
    setEditDocStartTime(s1Start);
    setEditDocEndTime(s1End);
    setEditDocStartTime2(s2Start);
    setEditDocEndTime2(s2End);
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
      if (editDocStartTime2 && editDocEndTime2) {
        formData.append('schedule_start_time_2', editDocStartTime2);
        formData.append('schedule_end_time_2', editDocEndTime2);
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

  // Complete Consultation API call (used by both doctor and receptionist)
  const handleCompleteConsultation = async (e, customApptId = null, notesInput = null, medicinesInput = null, followUpInput = null) => {
    if (e) e.preventDefault();
    
    const targetId = customApptId || selectedAppointment?.id;
    const finalNotes = notesInput !== null ? notesInput : clinicalNotes;
    const finalPrescription = medicinesInput !== null ? medicinesInput : prescriptionText;
    const finalFollowUp = followUpInput !== null ? followUpInput : followUpDate;

    if (!targetId) return;

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

  // Delete/Deboard Hospital (Super Admin only)
  const handleDeleteHospital = async (hospId) => {
    if (!window.confirm("क्या आप सच में इस हॉस्पिटल को हटाना चाहते हैं? इसके सभी डॉक्टर और अपॉइंटमेंट भी डिलीट हो जाएंगे। (Are you sure you want to delete this hospital?)")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/hospitals/${hospId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Hospital deleted successfully!");
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
  // --- PATIENT PORTAL HIJACK ---
  const currentPath = window.location.pathname;
  if (currentPath.startsWith('/p/')) {
    const slug = currentPath.split('/')[2];
    
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
      {/* Header */}
      <header className="dashboard-header">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={26} className="brand-accent" />
          <span>AURA <span className="brand-accent">SaaS</span></span>
          {userRole === 'ADMIN' && activeHospital?.slug && (
            <a 
              href={`/p/${activeHospital.slug}`} 
              target="_blank" 
              rel="noreferrer" 
              style={{ marginLeft: '12px', fontSize: '13px', color: 'var(--color-primary)', textDecoration: 'none', background: 'rgba(102,252,241,0.1)', padding: '4px 10px', borderRadius: '6px', fontWeight: 600, border: '1px solid rgba(102,252,241,0.3)' }}
            >
              🔗 Patient Portal
            </a>
          )}
        </div>
        
        <div className="header-controls" style={{ display: 'flex', alignItems: 'center', gap: '12px', marginLeft: 'auto', marginRight: token ? '12px' : '0px' }}>
          <button 
            onClick={toggleLanguage} 
            className="btn btn-secondary" 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px', 
              padding: '6px 12px', 
              fontSize: '13px', 
              fontWeight: 600,
              borderRadius: '8px',
              border: '1px solid rgba(102,252,241,0.2)',
              background: 'rgba(31,40,51,0.6)',
              color: 'var(--text-main)',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            <span>🌐</span>
            <span>{lang === 'en' ? 'हिंदी' : 'English'}</span>
          </button>
        </div>
        
        {token && (
          <div className="user-badge">
            <span className="role-tag">{userRole === 'SUPER_ADMIN' ? 'Platform Owner' : userRole}</span>
            <span style={{ fontWeight: 600 }}>{username}</span>
            <button onClick={logout} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '13px' }}>
              <LogOut size={14} />
            </button>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>

        {/* AUTH: shown when not logged in */}
        {!token && (
          <div style={{ minHeight: '90vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', background: 'var(--bg-main)' }}>
            <div style={{ width: '100%', maxWidth: '460px' }}>
              {!showRegisterHospital ? (
                <>
                  <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '56px', height: '56px', borderRadius: '16px', background: 'var(--primary-soft)', border: '1px solid var(--color-primary-border)', marginBottom: '12px' }}>
                      <Activity size={28} style={{ color: 'var(--primary)' }} />
                    </div>
                    <h1 style={{ fontSize: '26px', fontWeight: 800, color: 'var(--text-main)', margin: '0 0 6px 0' }}>AURA <span style={{ color: 'var(--primary)' }}>SaaS</span></h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: 0 }}>AI-Powered Hospital Management Platform</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '20px' }}>
                    {[
                      { id: 'RECEPTIONIST', label: 'Receptionist', icon: <Laptop size={20} /> },
                      { id: 'DOCTOR',       label: 'Doctor',       icon: <Heart size={20} /> },
                      { id: 'ADMIN',        label: 'Hospital\nAdmin', icon: <Sliders size={20} /> },
                      { id: 'OWNER',        label: 'Platform\nOwner', icon: <Shield size={20} /> },
                    ].map(role => (
                      <button key={role.id} type="button" onClick={() => { setLoginRole(role.id); setLoginError(''); }}
                        style={{ 
                          background: loginRole === role.id ? 'var(--primary)' : '#FFFFFF', 
                          border: `1.5px solid ${loginRole === role.id ? 'var(--primary)' : '#CBD5E1'}`, 
                          borderRadius: '14px', 
                          padding: '12px 6px', 
                          display: 'flex', 
                          flexDirection: 'column', 
                          alignItems: 'center', 
                          gap: '6px', 
                          cursor: 'pointer', 
                          color: loginRole === role.id ? '#FFFFFF' : '#334155', 
                          fontSize: '11px', 
                          fontWeight: 700, 
                          lineHeight: 1.3, 
                          whiteSpace: 'pre-line', 
                          textAlign: 'center', 
                          boxShadow: loginRole === role.id ? '0 4px 12px rgba(37,99,235,0.25)' : 'none',
                          transition: 'all 0.2s' 
                        }}
                      >
                        {role.icon}{role.label}
                      </button>
                    ))}
                  </div>

                  <div style={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '28px', boxShadow: 'var(--shadow)' }}>
                    <h3 style={{ color: 'var(--text-main)', fontSize: '18px', fontWeight: 800, marginBottom: '16px', textAlign: 'center' }}>
                      {loginRole === 'OWNER' ? '🔐 Platform Owner Console' : loginRole === 'ADMIN' ? '🏥 Hospital Admin Portal' : loginRole === 'DOCTOR' ? '👨‍⚕️ Doctor Workspace' : '🖥️ Receptionist Portal'}
                    </h3>



                    {loginError && <div style={{ color: '#f87171', fontSize: '13px', background: 'rgba(239,68,68,0.1)', padding: '10px 14px', borderRadius: '8px', marginBottom: '14px', border: '1px solid rgba(239,68,68,0.2)' }}>⚠️ {loginError}</div>}

                    <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div className="form-group">
                        <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Username</label>
                        <input type="text" className="form-control" value={loginUsername} onChange={e => setLoginUsername(e.target.value)} placeholder="Enter username" required style={{ borderRadius: '9px' }} />
                      </div>
                      <div className="form-group">
                        <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>{t('lbl_password_field')}</label>
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input 
                            type={showLoginPassword ? 'text' : 'password'} 
                            className="form-control" 
                            value={loginPassword} 
                            onChange={e => setLoginPassword(e.target.value)} 
                            placeholder="••••••••" 
                            required 
                            style={{ borderRadius: '9px', paddingRight: '40px' }} 
                          />
                          <button 
                            type="button" 
                            onClick={() => setShowLoginPassword(!showLoginPassword)}
                            style={{ position: 'absolute', right: '10px', background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px' }}
                            title={showLoginPassword ? "Hide Password" : "Show Password"}
                          >
                            {showLoginPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                      </div>
                      <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '13px', borderRadius: '11px', fontSize: '15px', fontWeight: 700, marginTop: '4px' }}>Sign In Securely →</button>
                    </form>

                    <div style={{ textAlign: 'center', marginTop: '14px' }}>
                      <button type="button" onClick={() => setShowRegisterHospital(true)} style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: '13px', textDecoration: 'underline' }}>+ Onboard a New Hospital</button>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: '18px', padding: '26px', backdropFilter: 'blur(16px)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                    <button onClick={() => { setShowRegisterHospital(false); setOnboardSuccess(null); setOnboardError(''); }} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', borderRadius: '8px', padding: '5px 11px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px' }}>← Back</button>
                    <h3 style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '17px', margin: 0 }}>🏥 Register New Hospital</h3>
                  </div>
                  {onboardError && <div style={{ color: '#f87171', fontSize: '13px', background: 'rgba(239,68,68,0.1)', padding: '10px 14px', borderRadius: '8px', marginBottom: '14px', border: '1px solid rgba(239,68,68,0.2)' }}>⚠️ {onboardError}</div>}
                  {onboardSuccess && <div style={{ color: '#10b981', fontSize: '14px', background: 'rgba(16,185,129,0.08)', padding: '16px', borderRadius: '10px', marginBottom: '14px', border: '1px solid rgba(16,185,129,0.3)' }}><p style={{ fontWeight: 700, marginBottom: '6px' }}>✅ Registration Successful!</p><p style={{ marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '13px' }}>Share this ID with your staff:</p><code style={{ color: 'var(--text-main)', background: 'rgba(255,255,255,0.1)', padding: '5px 10px', borderRadius: '6px', fontSize: '14px' }}>{onboardSuccess.hospital_id}</code></div>}
                  <form onSubmit={handleRegisterHospital} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div className="form-group"><label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Hospital Name *</label><input type="text" className="form-control" value={hospName} onChange={e => setHospName(e.target.value)} placeholder="e.g. Apollo Multispeciality" required style={{ borderRadius: '9px' }} /></div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      <div className="form-group"><label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Phone / Helpline *</label><input type="text" className="form-control" value={hospPhone} onChange={e => setHospPhone(e.target.value)} placeholder="+918..." required style={{ borderRadius: '9px' }} /></div>
                      <div className="form-group"><label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Address</label><input type="text" className="form-control" value={hospAddress} onChange={e => setHospAddress(e.target.value)} placeholder="City, State" style={{ borderRadius: '9px' }} /></div>
                      <div className="form-group"><label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Admin Username *</label><input type="text" className="form-control" value={hospAdminUsername} onChange={e => setHospAdminUsername(e.target.value)} required style={{ borderRadius: '9px' }} /></div>
                      <div className="form-group"><label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Admin Email *</label><input type="email" className="form-control" value={hospAdminEmail} onChange={e => setHospAdminEmail(e.target.value)} placeholder="admin@gmail.com" required style={{ borderRadius: '9px' }} /></div>
                    </div>
                    <div className="form-group"><label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px', display: 'block' }}>Admin Password *</label><input type="password" className="form-control" value={hospAdminPassword} onChange={e => setHospAdminPassword(e.target.value)} placeholder="••••••••" required style={{ borderRadius: '9px' }} /></div>
                    <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '13px', borderRadius: '11px', fontSize: '15px', fontWeight: 700, marginTop: '4px' }}>Register Hospital Account</button>
                  </form>
                </div>
              )}
            </div>
          </div>
        )}

        {/* DASHBOARD: shown when logged in */}
        {token && (
          <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
            <div className="tab-container">

              {userRole === 'RECEPTIONIST' && (
                <>
                  <button onClick={() => setActiveTab('overview')} className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}><Calendar size={18} /> {t('overview')}</button>
                  <button onClick={() => setActiveTab('new_booking')} className={`tab-btn ${activeTab === 'new_booking' ? 'active' : ''}`}><PlusCircle size={18} /> {t('newBooking')}</button>
                  <button onClick={() => setActiveTab('patient_search')} className={`tab-btn ${activeTab === 'patient_search' ? 'active' : ''}`}><User size={18} /> 🔍 {t('patientSearch')}</button>
                  <button onClick={() => { setActiveTab('receptionist_leaves'); fetchLeaves(); }} className={`tab-btn ${activeTab === 'receptionist_leaves' ? 'active' : ''}`}><Calendar size={18} /> {t('receptionistLeaves')}</button>
                </>
              )}
              {userRole === 'ADMIN' && (
                <>
                  <button onClick={() => { setActiveTab('admin_overview'); if (hospitalId) fetchHospitalStaff(hospitalId); }} className={`tab-btn ${activeTab === 'admin_overview' ? 'active' : ''}`}><Activity size={18} /> {t('adminOverview')}</button>
                  <button onClick={() => setActiveTab('staff_management')} className={`tab-btn ${activeTab === 'staff_management' ? 'active' : ''}`}><Shield size={18} /> {t('staffManagement')}</button>
                  <button onClick={() => setActiveTab('hospital_overview')} className={`tab-btn ${activeTab === 'hospital_overview' ? 'active' : ''}`}><Sliders size={18} /> {t('hospitalOverview')}</button>
                  <button onClick={() => { setActiveTab('admin_leaves'); fetchLeaves(); }} className={`tab-btn ${activeTab === 'admin_leaves' ? 'active' : ''}`}><Calendar size={18} /> {t('adminLeaves')}</button>
                </>
              )}
              {userRole === 'DOCTOR' && (
                <>
                  <button onClick={() => setActiveTab('appointments')} className={`tab-btn ${activeTab === 'appointments' ? 'active' : ''}`}><Activity size={18} /> {t('appointments')}</button>
                  <button onClick={() => { setActiveTab('doctor_leaves'); setLeaveDoctorId(userId); fetchLeaves(); }} className={`tab-btn ${activeTab === 'doctor_leaves' ? 'active' : ''}`}><Calendar size={18} /> {t('doctorLeaves')}</button>
                </>
              )}
              {userRole === 'SUPER_ADMIN' && (
                <button onClick={() => setActiveTab('super_admin')} className={`tab-btn ${activeTab === 'super_admin' ? 'active' : ''}`}><Shield size={18} /> {t('superAdminTab')}</button>
              )}
            </div>

            {/* Content viewports */}
            <div style={{ flexGrow: 1 }}>

              {/* 1. RECEPTIONIST: Live Schedule Tab */}
              {activeTab === 'overview' && userRole === 'RECEPTIONIST' && (
                <div style={{ textAlign: 'left' }}>
                  
                  {/* ── Receptionist Portal Header Banner ── */}
                  <div style={{
                    background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
                    borderRadius: '16px', padding: '20px 24px', marginBottom: '20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
                    boxShadow: '0 4px 20px rgba(30,58,138,0.25)', border: '1px solid var(--border)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{ width: '46px', height: '46px', borderRadius: '12px', background: 'rgba(255,255,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>
                        🏨
                      </div>
                      <div>
                        <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>
                          {activeHospital?.name || hospitalsList.find(h => h.id === hospitalId)?.name || 'CP Tiwari Hospital'}
                        </h2>
                        <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '12px', margin: '2px 0 0 0', fontWeight: 500 }}>
                          {t('recep_dashboard_sub')}
                        </p>
                      </div>
                    </div>
                    {/* Live Clock Card */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ background: 'var(--bg-muted)', border: '1px solid var(--border)', borderRadius: '10px', padding: '8px 16px', color: 'var(--text-main)', fontSize: '15px', fontWeight: 700, fontFamily: 'monospace', minWidth: '110px', textAlign: 'center' }}>
                        ⏱️ {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </div>
                      <button onClick={() => setRefreshTrigger(p => p+1)} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '13px' }}>
                        <RefreshCw size={14} style={{ marginRight: '6px' }} /> Sync Live
                      </button>
                    </div>
                  </div>

                  {/* ── Date Navigator Bar ── */}
                  <div style={{
                    background: '#FFFFFF', border: '1px solid var(--border)',
                    borderRadius: '12px', padding: '12px 20px', marginBottom: '20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div 
                        style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                        onClick={() => document.getElementById('dashboard-date-picker').showPicker()}
                      >
                        <span style={{ fontSize: '18px' }}>📅</span>
                        <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '15px' }}>
                          {safeFormatDate(selectedScheduleDate, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                        </div>
                      </div>
                      <input 
                        type="date" 
                        id="dashboard-date-picker" 
                        value={selectedScheduleDate} 
                        onChange={e => setSelectedScheduleDate(e.target.value)} 
                        style={{ opacity: 0, width: 0, height: 0, position: 'absolute' }}
                      />
                    </div>
                    {/* Date Navigation Buttons */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        onClick={() => {
                          const prev = new Date(selectedScheduleDate);
                          prev.setDate(prev.getDate() - 1);
                          setSelectedScheduleDate(prev.toISOString().split('T')[0]);
                        }}
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', color: 'var(--text-secondary)', borderRadius: '8px', padding: '6px 14px', fontSize: '13px', cursor: 'pointer' }}
                      >
                        {t('btn_prev')}
                      </button>
                      <button 
                        onClick={() => setSelectedScheduleDate(new Date().toISOString().split('T')[0])}
                        style={{ background: 'rgba(102,252,241,0.15)', border: '1px solid var(--color-primary)', color: 'var(--color-primary)', borderRadius: '8px', padding: '6px 14px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                      >
                        {t('btn_today')}
                      </button>
                      <button 
                        onClick={() => {
                          const next = new Date(selectedScheduleDate);
                          next.setDate(next.getDate() + 1);
                          setSelectedScheduleDate(next.toISOString().split('T')[0]);
                        }}
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', color: 'var(--text-secondary)', borderRadius: '8px', padding: '6px 14px', fontSize: '13px', cursor: 'pointer' }}
                      >
                        {t('btn_next')}
                      </button>
                    </div>
                  </div>

                  {/* ── Main Dual Column Body ── */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px', alignItems: 'start' }}>
                    
                    {/* Left Column: Doctor Queue List */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {doctorsList.length === 0 ? (
                        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No active doctors registered under this hospital tenant.
                        </div>
                      ) : (
                        doctorsList.map(doc => {
                          // Filter appointments for this doctor on the selected date
                          const docAppts = appointmentsList.filter(appt => {
                            const matchDoc = appt.doctor_id === doc.id;
                            const matchDate = appt.appointment_datetime ? appt.appointment_datetime.split('T')[0] === selectedScheduleDate : false;
                            return matchDoc && matchDate;
                          });

                          return (
                            <div key={doc.id} className="glass-panel" style={{ padding: '20px', borderLeft: '4px solid var(--color-primary)' }}>
                              
                              {/* Doctor Queue Header */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '10px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span style={{ fontSize: '18px' }}>🩺</span>
                                  <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '16px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                  <span style={{ background: 'rgba(102,252,241,0.1)', color: 'var(--color-primary)', border: '1px solid rgba(102,252,241,0.2)', borderRadius: '12px', padding: '2px 8px', fontSize: '11px', fontWeight: 600 }}>
                                    {doc.department_name}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>
                                    {docAppts.length} Appointments (अपॉइंटमेंट)
                                  </div>
                                  {docAppts.length > 0 && (
                                    <button 
                                      onClick={() => handleBulkCancel(doc.id, selectedScheduleDate)}
                                      className="btn btn-secondary" 
                                      style={{ padding: '4px 10px', fontSize: '11px', background: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px' }}
                                    >
                                      ❌ Cancel All (Day)
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
                                <div className="table-container" style={{ margin: 0 }}>
                                  <table className="custom-table" style={{ fontSize: '13px' }}>
                                    <thead>
                                      <tr>
                                        <th style={{ width: '40px' }}>#</th>
                                        <th>{t('col_time')}</th>
                                        <th>{t('col_patient')}</th>
                                        <th>{t('col_mobile')}</th>
                                        <th>{t('col_reason')}</th>
                                        <th>{t('col_payment')}</th>
                                        <th>{t('col_status_action')}</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {docAppts.map((appt, i) => (
                                        <tr key={appt.id}>
                                          <td>{i + 1}</td>
                                          <td style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                                            {new Date(appt.appointment_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                          </td>
                                          <td>
                                            <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{appt.patient_name}</div>
                                            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>ID: {appt.patient_id?.substring(0, 8)}...</span>
                                          </td>
                                          <td style={{ fontFamily: 'monospace' }}>{appt.patient_phone || 'N/A'}</td>
                                          <td>{appt.reason || 'General Checkup'}</td>
                                          <td>
                                            <span style={{
                                              background: appt.payment_status === 'PAID' ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
                                              color: appt.payment_status === 'PAID' ? '#10b981' : '#f59e0b',
                                              border: `1px solid ${appt.payment_status === 'PAID' ? '#10b98140' : '#f59e0b40'}`,
                                              borderRadius: '12px', padding: '2px 8px', fontSize: '11px', fontWeight: 700
                                            }}>
                                              {appt.payment_status || 'PENDING'}
                                            </span>
                                          </td>
                                          <td>
                                            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                              {appt.status === 'CANCELLED' ? (
                                                <span style={{ color: '#ef4444', fontWeight: 700 }}>❌ Cancelled</span>
                                              ) : appt.status === 'COMPLETED' ? (
                                                <span style={{ color: '#10b981', fontWeight: 700 }}>✅ Completed</span>
                                              ) : appt.status === 'MISSED' ? (
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                  <span style={{ color: '#ef4444', fontWeight: 700 }}>⚠️ Missed</span>
                                                  {appt.payment_status === 'PAID' && ((new Date() - new Date(appt.appointment_datetime)) <= 48 * 3600 * 1000) && (
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
                                                      style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px' }}
                                                    >
                                                      Reschedule
                                                    </button>
                                                  )}
                                                </div>
                                              ) : (
                                                <>
                                                  {appt.payment_status !== 'PAID' && (
                                                    <button 
                                                      onClick={() => {
                                                        if(window.confirm('Collect payment for this appointment?')) {
                                                          handleManualPayment(appt.id);
                                                        }
                                                      }}
                                                      className="btn btn-primary"
                                                      style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px', background: '#059669', borderColor: '#059669' }}
                                                    >
                                                      💰 Pay
                                                    </button>
                                                  )}
                                                  {appt.consultation_status === 'DONE' ? (
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
                                                      style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px' }}
                                                    >
                                                      👁️ View Consultation
                                                    </button>
                                                  ) : (
                                                    <button 
                                                      onClick={() => {
                                                        if (appt.payment_status !== 'PAID') {
                                                          alert('Payment must be collected and marked as PAID before completing the consultation.');
                                                          return;
                                                        }
                                                        setPrescAppointment(appt);
                                                        setPrescNotes('');
                                                        setPrescMedicines('');
                                                        setPrescFollowUp('');
                                                        setPrescIsViewMode(false);
                                                        setPrescriptionModalOpen(true);
                                                      }}
                                                      className="btn btn-primary"
                                                      style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px', opacity: appt.payment_status !== 'PAID' ? 0.5 : 1, cursor: appt.payment_status !== 'PAID' ? 'not-allowed' : 'pointer' }}
                                                    >
                                                      Complete
                                                    </button>
                                                  )}
                                                  <button 
                                                    onClick={() => {
                                                      if (window.confirm('Mark this appointment as MISSED? This will update status and send a WhatsApp alert.')) {
                                                        handleMarkSingleMissed(appt.id);
                                                      }
                                                    }}
                                                    className="btn btn-warning" 
                                                    style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px', backgroundColor: '#d97706', borderColor: '#d97706', color: 'var(--text-main)' }}
                                                  >
                                                    Missed
                                                  </button>
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
                                                    style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px' }}
                                                  >
                                                    Reschedule
                                                  </button>
                                                  <button 
                                                    onClick={() => {
                                                      setCancelAppointmentId(appt.id);
                                                      setCancelReason('');
                                                      setCancelIsPaid(appt.payment_status === 'PAID');
                                                      setCancelModalOpen(true);
                                                    }}
                                                    className="btn btn-danger" 
                                                    style={{ padding: '4px 8px', fontSize: '11px', borderRadius: '6px' }}
                                                  >
                                                    Cancel
                                                  </button>
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
                      <h3 style={{ color: 'var(--text-main)', fontSize: '15px', fontWeight: 700, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '10px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>👨‍⚕️</span> {t('doc_fee_list')}
                      </h3>
                      
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        {doctorsList.map(doc => {
                          // Define fallback timing and fees
                          const timingStr = doc.timings || t('default_schedule');
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
                            <div key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '10px', fontSize: '12px' }}>
                              <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '13px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                              <div style={{ color: 'var(--color-primary)', fontWeight: 600, marginTop: '2px' }}>{doc.department_name}</div>
                              
                              {isDoctorOnLeave ? (
                                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '6px', padding: '8px', marginTop: '8px', color: '#ef4444', textAlign: 'center', fontWeight: 'bold' }}>
                                  {t('on_leave')}
                                </div>
                              ) : (
                                <div style={{ color: 'rgba(255,255,255,0.5)', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                  <div>⏳ Timing: {isWorking ? timingStr.replace(/Timing:/gi, '').trim() : <span style={{ color: '#ef4444', fontWeight: 700 }}>Off Duty / Closed (छुट्टी)</span>}</div>
                                  <div>💰 OPD Fees: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{feesStr}</span></div>
                                  <div style={{ color: isWorking ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                                    Slots: {isWorking ? "72 slots free" : "0 slots free (Off-duty)"}
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
                          {doctorsList.map(doc => (
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
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: '#FFFFFF', padding: '16px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
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
                          <div className="slots-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>
                            {(() => {
                              if (newBookingAllSlots.length === 0) {
                                const onLeave = leavesList.find(l => l.doctor_id === bookingDoctorId && l.status === 'APPROVED' && new Date(l.start_date) <= new Date(bookingDate) && new Date(l.end_date) >= new Date(bookingDate));
                                if (onLeave) {
                                  const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  return (
                                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '15px', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                                      <strong style={{fontSize: '14px'}}>{t('doc_on_leave_banner')}</strong><br />
                                      <span style={{fontSize: '13px', marginTop: '4px', display: 'inline-block'}}>This doctor is on leave from {sd} to {ed}.</span>
                                    </div>
                                  );
                                }
                                return (
                                  <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '15px', color: '#ef4444', fontStyle: 'italic', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                                    Doctor is unavailable today (No active OPD schedule).
                                  </div>
                                );
                              }
                              return newBookingAllSlots.map(time => {
                              const slot24 = convertSlotTo24h(time);
                              const now = new Date();
                              // Convert local browser time to IST (UTC+5:30)
                              const istOffset = 5.5 * 60 * 60 * 1000;
                              const istDate = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
                              const todayStr = istDate.toISOString().split('T')[0];
                              const current24 = `${String(istDate.getHours()).padStart(2, '0')}:${String(istDate.getMinutes()).padStart(2, '0')}`;
                              
                              const isPast = (bookingDate === todayStr && slot24 <= current24);
                              const isBusy = newBookingBookedSlots.includes(time);
                              const isSelected = selectedNewBookingSlot === time;

                              let slotClass = 'available';
                              let slotStyle = { padding: '8px 4px', fontSize: '11px', textAlign: 'center', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.15s' };

                              if (isPast) {
                                slotClass = 'disabled-past';
                                slotStyle = { ...slotStyle, opacity: 0.35, cursor: 'not-allowed', background: '#FFFFFF', color: '#666', border: '1px dashed rgba(255,255,255,0.1)' };
                              } else if (isBusy) {
                                slotClass = 'busy';
                                slotStyle = { ...slotStyle, background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.5)', color: '#fca5a5', cursor: 'not-allowed' };
                              } else if (isSelected) {
                                slotClass = 'selected';
                                slotStyle = { ...slotStyle, background: 'linear-gradient(135deg, #10b981, #059669)', border: '1px solid #10b981', color: 'var(--text-main)', fontWeight: 'bold', boxShadow: '0 0 12px rgba(16, 185, 129, 0.5)' };
                              } else {
                                slotStyle = { ...slotStyle, background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#38bdf8' };
                              }

                              return (
                                <div
                                  key={time}
                                  className={`slot-item ${slotClass}`}
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
                            })
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
                  <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px', marginBottom: '20px' }}>
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
                        <div style={{ padding: '30px', textAlign: 'center', color: 'rgba(255,255,255,0.6)', background: '#FFFFFF', borderRadius: '12px' }}>
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
                                   <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px', marginBottom: '24px' }}>No upcoming bookings.</p>
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
                                               <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>{a.patientGender}, {a.patientAge} Yrs</div>
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
                                <h4 style={{ color: '#94a3b8', marginBottom: '12px', fontSize: '15px', fontWeight: 700 }}>📜 Past History & Prescriptions</h4>
                                {allHistory.length === 0 ? (
                                   <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px' }}>No past records.</p>
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
                                               <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>{a.patientGender}, {a.patientAge} Yrs</div>
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
                                               ) : <span style={{ color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>N/A</span>}
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
                              <tr key={leave.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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
              {activeTab === 'staff_management' && userRole === 'ADMIN' && (
                <div className="glass-panel" style={{ padding: '30px', textAlign: 'left', width: '100%' }}>
                  <h2 style={{ color: 'var(--text-main)', marginBottom: '20px' }}>Staff Onboarding & Allocation</h2>
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
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>{t('lbl_sched_days')}</label>
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
                                <label key={day.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#FFFFFF', border: '1px solid var(--border)', padding: '8px 14px', borderRadius: '10px', cursor: 'pointer', fontSize: '13px', color: staffScheduleDays.includes(day.id) ? 'var(--color-primary)' : 'var(--text-muted)', borderColor: staffScheduleDays.includes(day.id) ? 'var(--color-primary)' : 'rgba(255,255,255,0.08)' }}>
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
              )}

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
                      <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', margin: '4px 0 0 0' }}>Per-day booking statistics, payment tracking, missed appointments, and revenue analysis.</p>
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
                      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginTop: '4px' }}>Completed Consultations</div>
                    </div>

                    <div style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#818cf8', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>📅 {t('totalAppointments')}</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.total_bookings || 0}</div>
                      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginTop: '4px' }}>{lang === 'hi' ? 'सभी बुकिंग प्राप्त हुईं' : 'All Bookings Received'}</div>
                    </div>

                    <div style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#60a5fa', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>💰 Total Revenue</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>₹{hospitalStats?.total_revenue || 0}</div>
                      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginTop: '4px' }}>Revenue Received</div>
                    </div>

                    <div style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#fbbf24', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>⏳ {t('pendingPayment')}</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.pending_bookings || 0}</div>
                      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginTop: '4px' }}>{lang === 'hi' ? 'भुगतान लंबित है' : 'Payment Pending'}</div>
                    </div>

                    <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '16px', padding: '16px 18px', textAlign: 'left' }}>
                      <div style={{ color: '#f87171', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' }}>🚫 {t('missed')} / {t('cancelled')}</div>
                      <div style={{ color: 'var(--text-main)', fontSize: '26px', fontWeight: 800, marginTop: '4px' }}>{hospitalStats?.missed_bookings || 0}</div>
                      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginTop: '4px' }}>{lang === 'hi' ? 'छूटी या रद्द हुईं' : 'Missed or Cancelled'}</div>
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
                              <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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
                              <tr key={leave.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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

              {/* 5b. DOCTOR PORTAL: My Leaves tab */}
              {activeTab === 'doctor_leaves' && userRole === 'DOCTOR' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', textAlign: 'left' }}>
                  <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ color: 'var(--text-main)', fontSize: '18px', fontWeight: 700, marginBottom: '18px' }}>{t('apply_leave_heading')}</h3>
                    {leaveSuccess && <div style={{ color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>{leaveSuccess}</div>}
                    {leaveError && <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: '10px', borderRadius: '4px', marginBottom: '15px' }}>{leaveError}</div>}
                    
                    <form onSubmit={handleApplyLeave} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', alignItems: 'flex-end' }}>
                      <div className="form-group">
                        <label>Start Date</label>
                        <input type="date" className="form-control" value={leaveStartDate} onChange={e => setLeaveStartDate(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>End Date</label>
                        <input type="date" className="form-control" value={leaveEndDate} onChange={e => setLeaveEndDate(e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label>{t('lbl_reason')}</label>
                        <input type="text" className="form-control" placeholder="e.g. Sick Leave, Personal Work" value={leaveReason} onChange={e => setLeaveReason(e.target.value)} />
                      </div>
                      <button type="submit" className="btn btn-primary" style={{ height: '42px' }}>Submit Leave Request</button>
                    </form>
                  </div>

                  <div className="glass-panel" style={{ padding: '24px' }}>
                    <h3 style={{ color: 'var(--text-main)', fontSize: '18px', fontWeight: 700, marginBottom: '18px' }}>{t('my_leaves_heading')}</h3>
                    <div className="table-container">
                      <table className="custom-table">
                        <thead>
                          <tr>
                            <th>Start Date</th>
                            <th>End Date</th>
                            <th>Reason</th>
                            <th>Status</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {leavesList.filter(l => l.doctor_id === userId).length === 0 ? (
                            <tr>
                              <td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No leaves registered.</td>
                            </tr>
                          ) : (
                            leavesList.filter(l => l.doctor_id === userId).map(leave => (
                              <tr key={leave.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <td>{new Date(leave.start_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                                <td>{new Date(leave.end_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                                <td>{leave.reason || 'N/A'}</td>
                                <td>
                                  {leave.status === 'APPROVED' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(16,185,129,0.15)', color: '#10b981', fontSize: '12px', fontWeight: 600 }}>✅ Approved</span>}
                                  {leave.status === 'REJECTED' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(239,68,68,0.15)', color: '#f87171', fontSize: '12px', fontWeight: 600 }}>❌ Rejected</span>}
                                  {leave.status === 'PENDING' && <span style={{ padding: '4px 8px', borderRadius: '6px', background: 'rgba(245,158,11,0.15)', color: '#fbbf24', fontSize: '12px', fontWeight: 600 }}>⏳ Pending</span>}
                                </td>
                                <td>
                                  {leave.status === 'PENDING' && (
                                    <button 
                                      onClick={() => handleDeleteLeave(leave.id)}
                                      style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#f87171', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer' }}
                                    >
                                      🗑️ Cancel
                                    </button>
                                  )}
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

              {/* 5. DOCTOR PORTAL: Patient Queue tab */}
              {activeTab === 'appointments' && userRole === 'DOCTOR' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  
                  {/* Date Selector for Doctor */}
                  <div style={{
                    background: '#FFFFFF', border: '1px solid var(--border)',
                    borderRadius: '12px', padding: '12px 20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', textAlign: 'left'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div 
                        style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
                        onClick={() => document.getElementById('doctor-date-picker').showPicker()}
                      >
                        <span style={{ fontSize: '18px' }}>📅</span>
                        <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '15px' }}>
                          {new Date(selectedScheduleDate).toLocaleDateString('hi-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                        </div>
                      </div>
                      <input 
                        type="date" 
                        id="doctor-date-picker" 
                        value={selectedScheduleDate} 
                        onChange={e => setSelectedScheduleDate(e.target.value)} 
                        style={{ opacity: 0, width: 0, height: 0, position: 'absolute' }}
                      />
                    </div>
                    {/* Date Navigation Buttons */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        onClick={() => {
                          const prev = new Date(selectedScheduleDate);
                          prev.setDate(prev.getDate() - 1);
                          setSelectedScheduleDate(prev.toISOString().split('T')[0]);
                        }}
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', color: 'var(--text-secondary)', borderRadius: '8px', padding: '6px 14px', fontSize: '13px', cursor: 'pointer' }}
                      >
                        {t('btn_prev')}
                      </button>
                      <button 
                        onClick={() => setSelectedScheduleDate(new Date().toISOString().split('T')[0])}
                        style={{ background: 'rgba(102,252,241,0.15)', border: '1px solid var(--color-primary)', color: 'var(--color-primary)', borderRadius: '8px', padding: '6px 14px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
                      >
                        {t('btn_today')}
                      </button>
                      <button 
                        onClick={() => {
                          const next = new Date(selectedScheduleDate);
                          next.setDate(next.getDate() + 1);
                          setSelectedScheduleDate(next.toISOString().split('T')[0]);
                        }}
                        style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid var(--border)', color: 'var(--text-secondary)', borderRadius: '8px', padding: '6px 14px', fontSize: '13px', cursor: 'pointer' }}
                      >
                        {t('btn_next')}
                      </button>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px', textAlign: 'left' }}>
                    {/* Left Queue */}
                    <div className="glass-panel" style={{ padding: '20px' }}>
                      <h3 style={{ color: 'var(--text-main)', marginBottom: '12px' }}>Visits Queue ({new Date(selectedScheduleDate).toLocaleDateString()})</h3>
                      {/* Search Box */}
                      <div style={{ marginBottom: '12px' }}>
                        <input
                          type="text"
                          placeholder="🔍 Search patient by name..."
                          value={doctorQueueSearch}
                          onChange={e => setDoctorQueueSearch(e.target.value)}
                          style={{
                            width: '100%', padding: '8px 12px', borderRadius: '8px',
                            border: '1px solid var(--border)', background: 'var(--bg-muted)',
                            color: 'var(--text-main)', fontSize: '13px', outline: 'none', boxSizing: 'border-box'
                          }}
                        />
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', background: '#FFFFFF', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden' }}>
                        {(() => {
                          const filtered = appointmentsList.filter(a =>
                            a.appointment_datetime &&
                            a.appointment_datetime.split('T')[0] === selectedScheduleDate &&
                            (!doctorQueueSearch || a.patient_name?.toLowerCase().includes(doctorQueueSearch.toLowerCase()))
                          );
                          if (filtered.length === 0) return (
                            <div style={{ color: 'var(--text-muted)', padding: '20px', textAlign: 'center', fontSize: '13px' }}>
                              {doctorQueueSearch ? 'No patients match your search.' : 'No patients in queue for this date.'}
                            </div>
                          );
                          return filtered.map(appt => {
                            const paymentLabel = appt.payment_status === 'PAID' ? 'PAID' : 'Payment Pending';
                            const paymentColor = appt.payment_status === 'PAID' ? '#10b981' : '#f59e0b';
                            const paymentBg = appt.payment_status === 'PAID' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)';
                            return (
                              <div
                                key={appt.id}
                                onClick={() => {
                                  if (appt.status !== 'CANCELLED') {
                                    handleSelectDoctorAppointment(appt);
                                  } else {
                                    alert(`This appointment is already ${appt.status}.`);
                                  }
                                }}
                                style={{
                                  padding: '12px 16px',
                                  cursor: appt.status === 'CANCELLED' ? 'not-allowed' : 'pointer',
                                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                                  background: selectedAppointment?.id === appt.id ? 'rgba(102, 252, 241, 0.08)' : 'transparent',
                                  opacity: appt.status === 'CANCELLED' ? 0.6 : (appt.status === 'COMPLETED' ? 0.7 : 1),
                                  display: 'flex', flexDirection: 'column', gap: '5px',
                                  borderLeft: selectedAppointment?.id === appt.id ? '3px solid var(--color-primary)' : '3px solid transparent',
                                  transition: 'all 0.2s ease'
                                }}
                                onMouseOver={(e) => { if(appt.status !== 'CANCELLED' && selectedAppointment?.id !== appt.id) e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
                                onMouseOut={(e) => { if(selectedAppointment?.id !== appt.id) e.currentTarget.style.background = 'transparent' }}
                              >
                                {/* Row 1: Name + Payment Badge */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                  <div>
                                    <div style={{ fontWeight: 700, color: 'var(--text-main)', fontSize: '14px', lineHeight: '1.3' }}>
                                      {appt.patient_name}
                                      {appt.patient_age ? <span style={{ fontWeight: 400, fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginLeft: '6px' }}>({appt.patient_age} yrs)</span> : null}
                                    </div>
                                  </div>
                                  <span style={{ fontSize: '10px', padding: '3px 7px', borderRadius: '12px', fontWeight: 600, color: paymentColor, background: paymentBg, whiteSpace: 'nowrap', marginLeft: '6px' }}>
                                    {paymentLabel}
                                  </span>
                                </div>
                                {/* Row 2: Time */}
                                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  🕒 {new Date(appt.appointment_datetime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                </div>
                                {/* Row 3: Reason */}
                                <div style={{ fontSize: '12px', color: '#38bdf8', wordBreak: 'break-word', lineHeight: '1.4' }} title={appt.reason}>
                                  🩺 {appt.reason || 'General'}
                                </div>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    </div>

                  {/* Right: Workspace */}
                  <div>
                    {!selectedAppointment ? (
                      <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'rgba(255,255,255,0.4)', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', border: '1px dashed rgba(255,255,255,0.1)' }}>
                        <span style={{ fontSize: '32px', marginBottom: '10px' }}>🏥</span>
                        <h4 style={{ fontWeight: 500, margin: 0 }}>Select a patient from the queue to start consultation</h4>
                      </div>
                    ) : (
                      <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        {/* Compact Header for Workspace */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '15px' }}>
                          <div>
                            <h2 style={{ color: 'var(--text-main)', margin: '0 0 4px 0', fontSize: '18px' }}>Consultation: {selectedAppointment.patient_name}</h2>
                            <div style={{ fontSize: '12px', color: 'var(--color-primary)' }}>ID: {selectedAppointment.id.substring(0, 8).toUpperCase()} • {new Date(selectedAppointment.appointment_datetime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                          </div>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            <span className={`badge badge-${selectedAppointment.status.toLowerCase()}`} style={{ padding: '6px 12px', fontSize: '11px', height: 'fit-content' }}>
                              {selectedAppointment.status}
                            </span>
                          </div>
                        </div>

                        {completeSuccess && <div style={{ color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '10px', borderRadius: '4px', fontSize: '13px' }}>✅ {completeSuccess}</div>}
                        {completeError && <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: '10px', borderRadius: '4px', fontSize: '13px' }}>⚠️ {completeError}</div>}

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                          {/* AI Intake Summary */}
                          <div>
                            <h4 style={{ color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px', marginTop: 0 }}>AI Intake Summary</h4>
                            {intakeData ? (
                              <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', fontSize: '13px' }}>
                                <div style={{ marginBottom: '8px' }}>
                                  <strong style={{ color: 'var(--text-main)', display: 'block', marginBottom: '2px' }}>Symptoms:</strong>
                                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{intakeData.symptoms || 'General wellness check'}</span>
                                </div>
                                <div>
                                  <strong style={{ color: 'var(--text-main)', display: 'block', marginBottom: '2px' }}>History/Vitals:</strong>
                                  <span style={{ color: 'rgba(255,255,255,0.7)' }}>{intakeData.history || 'None declared'}</span>
                                </div>
                              </div>
                            ) : (
                              <div style={{ background: 'rgba(255,255,255,0.01)', padding: '12px', borderRadius: '8px', border: '1px dashed rgba(255,255,255,0.1)', fontSize: '12px', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
                                No AI Intake logged
                              </div>
                            )}
                          </div>

                          {/* Doctor's Workspace: Notes & Prescription */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div>
                              <h4 style={{ color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px', marginTop: 0 }}>Clinical Notes</h4>
                              <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', fontSize: '13px', color: 'var(--text-main)', minHeight: '60px' }}>
                                {selectedAppointment.clinical_notes || <span style={{color:'rgba(255,255,255,0.3)'}}>No notes entered.</span>}
                              </div>
                            </div>
                            
                            <div>
                              <h4 style={{ color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px', marginTop: 0 }}>Prescription</h4>
                              <div style={{ background: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', fontSize: '13px', color: 'var(--text-main)', minHeight: '60px', whiteSpace: 'pre-wrap' }}>
                                {selectedAppointment.prescription || <span style={{color:'rgba(255,255,255,0.3)'}}>No prescription.</span>}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Footer / Status Area */}
                        <div style={{ marginTop: 'auto', paddingTop: '15px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                             <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
                               Follow-up: <strong style={{ color: 'var(--text-main)' }}>{selectedAppointment.follow_up_date ? new Date(selectedAppointment.follow_up_date).toLocaleDateString() : 'None'}</strong>
                             </div>
                             
                             {selectedAppointment.status !== 'COMPLETED' && (
                               <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', background: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24', borderRadius: '20px', fontSize: '11px', fontWeight: 600 }}>
                                 <span className="spinner" style={{ width: '12px', height: '12px', borderWidth: '2px' }}></span>
                                 Awaiting Receptionist Payment/Prescription Entry
                               </div>
                             )}
                           </div>
                        </div>

                      </div>
                    )}
                  </div>
                </div>
                </div>
              )}

              {/* 6. SUPER ADMIN / OWNER PORTAL: Platform Stats & Assignment */}
              {activeTab === 'admin_overview' && userRole === 'ADMIN' && (() => {
                const myHosp = hospitalStats;
                const staffDoctors = hospitalStaff.doctors.length > 0 ? hospitalStaff.doctors : doctorsList.map(d => ({ ...d, username: d.id, department: d.department_name }));
                const staffReceptionists = hospitalStaff.receptionists;
                return (
                  <div style={{ textAlign: 'left', animation: 'fadeIn 0.5s ease', maxWidth: '1200px', margin: '0 auto' }}>
                    
                    {/* Compact Hero & Actions Bar */}
                    <div style={{
                      background: 'linear-gradient(to right, #0f172a, #1e1b4b)',
                      border: '1px solid rgba(139,92,246,0.2)',
                      borderRadius: '16px', padding: '16px 24px', marginBottom: '24px',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>🏥</div>
                        <div>
                          <div style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 700 }}>{myHosp?.hospital_name || 'Hospital Dashboard'}</div>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px' }}>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>Code: <strong style={{color: 'var(--text-main)'}}>{hospitalId}</strong></span>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>•</span>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>User: <strong style={{color: 'var(--text-main)'}}>{activeHospital?.admin_username || 'Admin'}</strong></span>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>•</span>
                            {(()=>{
                              const activeHelpline = myHosp?.hospital_phone || activeHospital?.phone || activeHospital?.helpline || activeHospital?.settings?.twilio_helpline;
                              return activeHelpline ? (
                                <span style={{color: '#10b981', fontSize: '12px', fontWeight: 600}}>✅ AI Active</span>
                              ) : (
                                <span style={{color: '#f59e0b', fontSize: '12px', fontWeight: 600}}>⚠️ No AI</span>
                              );
                            })()}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={() => setEditHospitalProfileModalOpen(true)} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>✏️ Profile</button>
                        <button onClick={() => setEditHospitalSettingsModalOpen(true)} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>⚙️ Settings</button>
                        <button onClick={() => { setActiveTab('admin_leaves'); fetchLeaves(); }} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>📅 Leaves</button>
                        <button onClick={() => setActiveTab('hospital_overview')} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>📈 Metrics</button>
                        <button onClick={() => setActiveTab('staff_management')} style={{ padding: '8px 16px', fontSize: '12px', borderRadius: '8px', background: '#8b5cf6', color: 'var(--text-main)', border: 'none', fontWeight: 600, cursor: 'pointer' }}>➕ Add Staff</button>
                      </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '32px' }}>
                      {/* Doctors Table Section */}
                      <div style={{ background: '#1e293b', borderRadius: '16px', border: '1px solid #334155', overflow: 'hidden' }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-muted)' }}>
                          <h2 style={{ color: '#f8fafc', fontSize: '16px', fontWeight: 700, margin: 0 }}>Doctors Directory</h2>
                          <span style={{ background: '#0ea5e9', color: 'var(--text-main)', padding: '2px 8px', borderRadius: '10px', fontSize: '12px', fontWeight: 700 }}>{staffDoctors.length}</span>
                        </div>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                              <tr style={{ background: '#FFFFFF', color: '#94a3b8', fontSize: '12px', textTransform: 'uppercase' }}>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Doctor</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Department</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Fee / Slot</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Credentials</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155', textAlign: 'right' }}>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {staffDoctors.length === 0 ? (
                                <tr><td colSpan="5" style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>No doctors found.</td></tr>
                              ) : staffDoctors.map(doc => (
                                <tr key={doc.id} style={{ borderBottom: '1px solid #334155', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background='rgba(255,255,255,0.02)'} onMouseOut={e => e.currentTarget.style.background='transparent'}>
                                  <td style={{ padding: '12px 20px' }}>
                                    <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '14px' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                    <div style={{ color: '#10b981', fontSize: '11px', fontWeight: 600, marginTop: '2px' }}>ACTIVE</div>
                                  </td>
                                  <td style={{ padding: '12px 20px', color: '#cbd5e1', fontSize: '13px' }}>{doc.department || doc.department_name || 'General'}</td>
                                  <td style={{ padding: '12px 20px' }}>
                                    <div style={{ color: '#f8fafc', fontSize: '13px', fontWeight: 600 }}>₹{doc.opd_fees || 0}</div>
                                    <div style={{ color: '#94a3b8', fontSize: '12px' }}>{doc.slot_duration_minutes || 30} mins</div>
                                  </td>
                                  <td style={{ padding: '12px 20px' }}>
                                    <div style={{ color: '#cbd5e1', fontSize: '12px' }}>U: <strong>{doc.username || doc.id}</strong></div>
                                    <div style={{ color: '#cbd5e1', fontSize: '12px' }}>P: <strong style={{ fontFamily: 'monospace' }}>{doc.password || '••••••••'}</strong></div>
                                  </td>
                                  <td style={{ padding: '12px 20px', textAlign: 'right' }}>
                                    <button onClick={() => handleOpenEditDoctorModal(doc)} style={{ padding: '6px', background: 'transparent', color: '#38bdf8', border: 'none', cursor: 'pointer', fontSize: '14px' }} title="Edit Doctor">✏️</button>
                                    <button onClick={() => handleDeleteStaff(doc.id)} style={{ padding: '6px', background: 'transparent', color: '#ef4444', border: 'none', cursor: 'pointer', fontSize: '14px', marginLeft: '4px' }} title="Delete Doctor">🗑️</button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Receptionists Table Section */}
                      <div style={{ background: '#1e293b', borderRadius: '16px', border: '1px solid #334155', overflow: 'hidden' }}>
                        <div style={{ padding: '16px 20px', borderBottom: '1px solid #334155', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-muted)' }}>
                          <h2 style={{ color: '#f8fafc', fontSize: '16px', fontWeight: 700, margin: 0 }}>Front Desk Staff</h2>
                          <span style={{ background: '#8b5cf6', color: 'var(--text-main)', padding: '2px 8px', borderRadius: '10px', fontSize: '12px', fontWeight: 700 }}>{staffReceptionists.length}</span>
                        </div>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                              <tr style={{ background: '#FFFFFF', color: '#94a3b8', fontSize: '12px', textTransform: 'uppercase' }}>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Staff Name</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Role</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155' }}>Credentials</th>
                                <th style={{ padding: '12px 20px', fontWeight: 600, borderBottom: '1px solid #334155', textAlign: 'right' }}>Actions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {staffReceptionists.length === 0 ? (
                                <tr><td colSpan="4" style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>No receptionists found.</td></tr>
                              ) : staffReceptionists.map(rec => (
                                <tr key={rec.id} style={{ borderBottom: '1px solid #334155', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background='rgba(255,255,255,0.02)'} onMouseOut={e => e.currentTarget.style.background='transparent'}>
                                  <td style={{ padding: '12px 20px' }}>
                                    <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '14px' }}>{rec.first_name || rec.username} {rec.last_name}</div>
                                    <div style={{ color: '#10b981', fontSize: '11px', fontWeight: 600, marginTop: '2px' }}>ACTIVE</div>
                                  </td>
                                  <td style={{ padding: '12px 20px', color: '#cbd5e1', fontSize: '13px' }}>Receptionist</td>
                                  <td style={{ padding: '12px 20px' }}>
                                    <div style={{ color: '#cbd5e1', fontSize: '12px' }}>U: <strong>{rec.username}</strong></div>
                                    <div style={{ color: '#cbd5e1', fontSize: '12px' }}>P: <strong style={{ fontFamily: 'monospace' }}>{rec.password || '••••••••'}</strong></div>
                                  </td>
                                  <td style={{ padding: '12px 20px', textAlign: 'right' }}>
                                    <button onClick={() => handleDeleteStaff(rec.id)} style={{ padding: '6px', background: 'transparent', color: '#ef4444', border: 'none', cursor: 'pointer', fontSize: '14px' }} title="Delete Account">🗑️</button>
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

                  {/* LEFT SIDEBAR */}
                  <div style={{
                    width: '220px', flexShrink: 0,
                    background: '#FFFFFF',
                    borderRight: '1px solid rgba(255,255,255,0.07)',
                    padding: '24px 14px',
                    display: 'flex', flexDirection: 'column', gap: '8px'
                  }}>
                    {/* Brand */}
                    <div style={{ marginBottom: '20px', padding: '0 6px' }}>
                      <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '14px' }}>Platform Control</div>
                      <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '11px' }}>AURA SaaS — Owner Panel</div>
                    </div>

                    {/* Nav Items */}
                    {[
                      { id: 'hospitals', icon: '🏥', label: 'Hospitals', count: hospitalsList.length },
                      { id: 'owners', icon: '🔐', label: 'Platform Owners', count: null },
                    ].map(item => (
                      <button key={item.id} onClick={() => { setSuperAdminView(item.id); setSelectedHospital(null); }}
                        style={{
                          background: superAdminView === item.id ? 'rgba(139,92,246,0.18)' : 'transparent',
                          border: `1px solid ${superAdminView === item.id ? 'rgba(139,92,246,0.5)' : 'transparent'}`,
                          borderRadius: '10px', padding: '10px 12px',
                          display: 'flex', alignItems: 'center', gap: '10px',
                          color: superAdminView === item.id ? '#c4b5fd' : 'rgba(255,255,255,0.5)',
                          cursor: 'pointer', fontSize: '13px', fontWeight: 600,
                          textAlign: 'left', width: '100%', transition: 'all 0.15s'
                        }}>
                        <span style={{ fontSize: '16px' }}>{item.icon}</span>
                        <span style={{ flex: 1 }}>{item.label}</span>
                        {item.count !== null && <span style={{ background: 'rgba(139,92,246,0.3)', color: '#c4b5fd', borderRadius: '20px', padding: '1px 7px', fontSize: '10px', fontWeight: 700 }}>{item.count}</span>}
                      </button>
                    ))}

                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '12px 0' }} />
                    <div style={{ color: 'rgba(255,255,255,0.25)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', padding: '0 6px' }}>Platform Stats</div>
                    {[
                      { label: 'Total Hospitals', value: hospitalsList.length, color: '#8b5cf6' },
                      { label: 'Active', value: hospitalsList.filter(h => h.is_active).length, color: '#10b981' },
                      { label: 'AI Lines', value: hospitalsList.filter(h => h.helpline).length, color: '#f59e0b' },
                    ].map(stat => (
                      <div key={stat.label} style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '11px' }}>{stat.label}</span>
                        <span style={{ color: stat.color, fontWeight: 800, fontSize: '13px' }}>{stat.value}</span>
                      </div>
                    ))}
                  </div>

                  {/* MAIN CONTENT AREA */}
                  <div style={{ flex: 1, padding: '24px 28px', overflow: 'auto' }}>

                    {/* ── VIEW: HOSPITALS LIST ── */}
                    {superAdminView === 'hospitals' && !selectedHospital && (
                      <div>
                        <div style={{ marginBottom: '20px' }}>
                          <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>🏥 Registered Hospitals</h2>
                          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '13px', margin: '4px 0 0 0' }}>Click a hospital to view details, configure Twilio, and see staff.</p>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                          {hospitalsList.map((hosp, idx) => {
                            const colors = ['#8b5cf6','#06b6d4','#f59e0b','#10b981','#ec4899'];
                            const c = colors[idx % colors.length];
                            return (
                              <div key={hosp.id}
                                onClick={() => { setSelectedHospital(hosp); fetchHospitalStaff(hosp.id); }}
                                style={{
                                  background: `rgba(${c === '#8b5cf6' ? '139,92,246' : c === '#06b6d4' ? '6,182,212' : c === '#f59e0b' ? '245,158,11' : c === '#10b981' ? '16,185,129' : '236,72,153'},0.06)`,
                                  border: `1px solid ${c}33`,
                                  borderRadius: '14px', padding: '18px 22px', cursor: 'pointer',
                                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                  transition: 'all 0.2s',
                                  ':hover': { borderColor: c }
                                }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = c}
                                onMouseLeave={e => e.currentTarget.style.borderColor = `${c}33`}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                  <div style={{ width: '46px', height: '46px', borderRadius: '14px', background: `${c}22`, border: `1px solid ${c}44`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>🏥</div>
                                  <div>
                                    <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '15px' }}>{hosp.name}</div>
                                    <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '11px', marginTop: '3px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                      <div>📱 <strong>Phone / Helpline:</strong> {hosp.phone || hosp.helpline || 'N/A'} | 📧 <strong>Admin Email:</strong> {hosp.email || 'N/A'}</div>
                                      <div>👤 <strong>Username:</strong> {hosp.admin_username || 'N/A'} | 🔑 <strong>Password:</strong> {hosp.admin_password || 'N/A'}</div>
                                      <div>📍 <strong>Address:</strong> {hosp.address || 'N/A'} | 🆔 <strong>Hospital ID:</strong> {hosp.id}</div>
                                    </div>
                                  </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ background: hosp.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: hosp.is_active ? '#10b981' : '#ef4444', border: `1px solid ${hosp.is_active ? '#10b98150' : '#ef444450'}`, borderRadius: '20px', padding: '3px 12px', fontSize: '11px', fontWeight: 700 }}>
                                    {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                                  </span>
                                  <span style={{ color: hosp.helpline ? '#f59e0b' : 'rgba(255,255,255,0.2)', fontSize: '11px', fontWeight: 600 }}>
                                    {hosp.helpline ? '📞 AI Active' : '📵 No AI Line'}
                                  </span>
                                  <span style={{ color: c, fontSize: '20px' }}>›</span>
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
                      const webhook = getWebhookUrl(hosp.id);
                      return (
                        <div>
                          {/* Back button + title */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '22px' }}>
                            <button onClick={() => { setSelectedHospital(null); setHospitalStaff({ doctors: [], receptionists: [] }); }}
                              style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '8px', padding: '6px 14px', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
                              ← Back
                            </button>
                            <div>
                              <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>{hosp.name}</h2>
                              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '12px' }}>{hosp.address || 'Address not set'}</div>
                            </div>
                            <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
                              <span style={{ background: hosp.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: hosp.is_active ? '#10b981' : '#ef4444', border: `1px solid ${hosp.is_active ? '#10b98150' : '#ef444450'}`, borderRadius: '20px', padding: '4px 14px', fontSize: '12px', fontWeight: 700 }}>
                                {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                              </span>
                              {hosp.id !== 'hosp_default' && (
                                <button onClick={() => handleDeleteHospital(hosp.id)}
                                  style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171', borderRadius: '20px', padding: '4px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}>
                                  🗑️ Delete Hospital
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Info pills */}
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                            {[
                              { icon: '🪪', label: 'Hospital ID', value: hosp.id, color: '#8b5cf6' },
                              { icon: '📞', label: 'Phone / Helpline', value: hosp.phone || hosp.helpline || 'Not set', color: '#06b6d4' },
                              { icon: '✉️', label: 'Email', value: hosp.email || 'Not set', color: '#f59e0b' },
                              { icon: '👤', label: 'Admin Username', value: hosp.admin_username || 'N/A', color: '#10b981' },
                              { icon: '🔑', label: 'Admin Password', value: hosp.admin_password || 'N/A', color: '#ec4899' },
                            ].map(pill => (
                              <div key={pill.label} style={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: '12px', padding: '12px 16px' }}>
                                <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px' }}>{pill.icon} {pill.label}</div>
                                <div style={{ color: pill.color, fontSize: '13px', fontWeight: 700, fontFamily: 'monospace', wordBreak: 'break-all' }}>{pill.value}</div>
                              </div>
                            ))}
                          </div>

                           {/* Twilio & WhatsApp Config */}
                           <div style={{ background: '#FFFFFF', border: '1px solid rgba(255,255,255,0.07)', borderRadius: '14px', padding: '18px', marginBottom: '20px' }}>
                             <div style={{ color: '#fb923c', fontWeight: 700, fontSize: '13px', marginBottom: '14px' }}>📡 Twilio AI Helpline & WhatsApp Integration</div>
                             
                             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr auto', gap: '10px', alignItems: 'end', marginBottom: '14px' }}>
                               <div className="form-group" style={{ margin: 0 }}>
                                 <label style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>Helpline Number</label>
                                 <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                   placeholder="+1415..." value={twilioHelplines[hosp.id] || hosp.helpline || ''}
                                   onChange={e => setTwilioHelplines(p => ({ ...p, [hosp.id]: e.target.value }))} />
                               </div>
                               <div className="form-group" style={{ margin: 0 }}>
                                 <label style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>WhatsApp Number</label>
                                 <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                   placeholder="whatsapp:+1415..." value={twilioWhatsappNumbers[hosp.id] || hosp.whatsapp_number || ''}
                                   onChange={e => setTwilioWhatsappNumbers(p => ({ ...p, [hosp.id]: e.target.value }))} />
                               </div>
                               <div className="form-group" style={{ margin: 0 }}>
                                 <label style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>Account SID</label>
                                 <input type="text" className="form-control" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                   placeholder="ACxxxxxxxx..." value={twilioAccountSids[hosp.id] || ''}
                                   onChange={e => setTwilioAccountSids(p => ({ ...p, [hosp.id]: e.target.value }))} />
                               </div>
                               <div className="form-group" style={{ margin: 0 }}>
                                 <label style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '5px', display: 'block' }}>Auth Token</label>
                                 <input type="password" className="form-control" style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                                   placeholder="••••••••••" value={twilioAuthTokens[hosp.id] || ''}
                                   onChange={e => setTwilioAuthTokens(p => ({ ...p, [hosp.id]: e.target.value }))} />
                               </div>
                               <button onClick={() => handleSaveTwilioConfig(hosp.id)}
                                 style={{ background: 'linear-gradient(135deg, #fb923c, #f59e0b)', border: 'none', borderRadius: '10px', padding: '10px 18px', color: '#1a1a1a', fontWeight: 700, fontSize: '12px', cursor: 'pointer', whiteSpace: 'nowrap', height: '36px' }}>
                                 💾 Save & Inject
                               </button>
                             </div>

                             {/* Webhook URLs Grid */}
                             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                               <div>
                                 <div style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>📞 Twilio Voice Webhook URL</div>
                                 <div style={{ display: 'flex', gap: '6px' }}>
                                   <input type="text" readOnly className="form-control" style={{ fontSize: '11px', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', fontFamily: 'monospace', color: '#888' }}
                                     value={`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/voice/inbound?hospital_id=${hosp.id}`} />
                                   <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => { navigator.clipboard.writeText(`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/voice/inbound?hospital_id=${hosp.id}`); alert("Voice Webhook copied!"); }}>Copy</button>
                                 </div>
                               </div>
                               <div>
                                 <div style={{ fontSize: '10px', color: '#60a5fa', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>💬 WhatsApp Webhook URL</div>
                                 <div style={{ display: 'flex', gap: '6px' }}>
                                   <input type="text" readOnly className="form-control" style={{ fontSize: '11px', padding: '5px 8px', background: 'rgba(0,0,0,0.3)', fontFamily: 'monospace', color: '#888' }}
                                     value={`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/whatsapp/webhook?hospital_id=${hosp.id}`} />
                                   <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => { navigator.clipboard.writeText(`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/whatsapp/webhook?hospital_id=${hosp.id}`); alert("WhatsApp Webhook copied!"); }}>Copy</button>
                                 </div>
                               </div>
                             </div>
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
                                <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>Loading...</div>
                              ) : hospitalStaff.doctors.length === 0 ? (
                                <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>No doctors registered</div>
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
                                        <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '14px' }}>{expandedStaffCard === doc.id ? '▲' : '▼'}</span>
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
                                              <span style={{ color: 'rgba(255,255,255,0.4)', minWidth: '90px' }}>{info.label}:</span>
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
                                <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>Loading...</div>
                              ) : hospitalStaff.receptionists.length === 0 ? (
                                <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>No receptionists registered</div>
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
                                        <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '14px' }}>{expandedStaffCard === rec.id ? '▲' : '▼'}</span>
                                      </div>
                                      {expandedStaffCard === rec.id && (
                                        <div style={{ marginTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '10px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                          {[
                                            { label: '🔑 Username', value: rec.username },
                                            { label: '✉️ Email', value: rec.email },
                                          ].map(info => (
                                            <div key={info.label} style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                                              <span style={{ color: 'rgba(255,255,255,0.4)', minWidth: '90px' }}>{info.label}:</span>
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
                          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '13px', margin: '4px 0 0 0' }}>Register new Platform Owner (SUPER_ADMIN) logins for this platform.</p>
                        </div>

                        {newOwnerSuccess && <div style={{ color: '#34d399', fontSize: '13px', background: 'rgba(52,211,153,0.1)', padding: '12px 16px', borderRadius: '10px', marginBottom: '18px', border: '1px solid rgba(52,211,153,0.2)' }}>✅ {newOwnerSuccess}</div>}
                        {newOwnerError && <div style={{ color: '#f87171', fontSize: '13px', background: 'rgba(239,68,68,0.1)', padding: '12px 16px', borderRadius: '10px', marginBottom: '18px', border: '1px solid rgba(239,68,68,0.2)' }}>⚠️ {newOwnerError}</div>}

                        <div style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '18px', padding: '24px', marginBottom: '24px' }}>
                          <div style={{ color: '#c4b5fd', fontWeight: 700, fontSize: '14px', marginBottom: '6px' }}>➕ Register New Platform Owner</div>
                          <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '12px', marginBottom: '18px' }}>
                            This creates a new database-backed SUPER_ADMIN account. The new owner can log in from Platform Owner tab and manage all hospitals.
                          </div>
                          <form onSubmit={handleRegisterSuperAdmin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, marginBottom: '6px', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Username *</label>
                                <input type="text" className="form-control" required style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                                  placeholder="e.g. admin_shiva" value={newOwnerUsername}
                                  onChange={e => setNewOwnerUsername(e.target.value)} />
                              </div>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, marginBottom: '6px', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Email *</label>
                                <input type="email" className="form-control" required style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                                  placeholder="e.g. admin@gmail.com" value={newOwnerEmail}
                                  onChange={e => setNewOwnerEmail(e.target.value)} />
                              </div>
                              <div className="form-group" style={{ margin: 0 }}>
                                <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontWeight: 700, marginBottom: '6px', display: 'block', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Password *</label>
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
                          <ol style={{ color: 'rgba(255,255,255,0.6)', fontSize: '12px', paddingLeft: '16px', lineHeight: '1.9', margin: 0 }}>
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
            <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginBottom: '15px' }}>
              Configure your dynamic AI Receptionist prompts and active Twilio WhatsApp integration.
            </p>
            
            <form onSubmit={handleUpdateHospitalSettings} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              
              <div className="form-group" style={{ background: '#FFFFFF', padding: '10px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
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
                <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginBottom: '4px', display: 'block' }}>
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
        <div className="modal-overlay">
          <div className="modal-content">
            <h3 style={{ color: 'var(--text-main)', marginBottom: '15px' }}>Reschedule Appointment: {targetAppointment.patient_name}</h3>
            {rescheduleError && <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: '8px', borderRadius: '4px', marginBottom: '10px' }}>{rescheduleError}</div>}
            
            <div className="form-group" style={{ marginBottom: '15px' }}>
              <label>Select Date</label>
              <input 
                type="date" 
                className="form-control" 
                value={rescheduleDate}
                onChange={e => handleDateChangeForReschedule(e.target.value)}
              />
            </div>

            {rescheduleDate && (
              <div style={{ marginBottom: '20px' }}>
                <label style={{ fontSize: '14px', fontWeight: 500 }}>Select Available Time Slot (RED slots are booked/busy)</label>
                <div className="slots-grid">
                  {(() => {
                    if (allSlots.length === 0) {
                      const onLeave = leavesList.find(l => l.doctor_id === targetAppointment.doctor_id && l.status === 'APPROVED' && new Date(l.start_date) <= new Date(rescheduleDate) && new Date(l.end_date) >= new Date(rescheduleDate));
                      if (onLeave) {
                        const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                        const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                        return (
                          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '15px', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                            <strong style={{fontSize: '14px'}}>{t('doc_on_leave_banner')}</strong><br />
                            <span style={{fontSize: '13px', marginTop: '4px', display: 'inline-block'}}>This doctor is on leave from {sd} to {ed}.</span>
                          </div>
                        );
                      }
                      return (
                        <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '15px', color: '#ef4444', fontStyle: 'italic', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                          Doctor is unavailable today (No active OPD schedule).
                        </div>
                      );
                    }
                    return allSlots.map(time => {
                    const isBusy = bookedSlots.includes(time);
                    const isSelected = selectedSlotTime === time;
                    return (
                      <div 
                        key={time} 
                        className={`slot-item ${isBusy ? 'busy' : isSelected ? 'selected' : 'available'}`}
                        onClick={() => {
                          if (!isBusy) setSelectedSlotTime(time);
                        }}
                      >
                        {time}
                      </div>
                    );
                  })
                  })()}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
              <button onClick={() => setRescheduleModalOpen(false)} className="btn btn-secondary">Close</button>
              <button onClick={executeReschedule} className="btn btn-primary">Reschedule Booking</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Doctor Modal */}
      {editDoctorModalOpen && (
        <div className="modal-overlay" style={{ backdropFilter: 'blur(10px)', zIndex: 9999 }}>
          <div className="modal-content" style={{ maxWidth: '850px', width: '92%', maxHeight: '92vh', overflowY: 'auto', textAlign: 'left', background: '#111827', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '20px', padding: '24px' }}>
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
                      style={{ position: 'absolute', right: '8px', background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px' }}
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

              {/* Row 5: Sessions Start/End Times */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Session 1 Start *</label>
                  <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocStartTime} onChange={e => setEditDocStartTime(e.target.value)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Session 1 End *</label>
                  <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocEndTime} onChange={e => setEditDocEndTime(e.target.value)} required />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Session 2 Start (Opt)</label>
                  <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocStartTime2} onChange={e => setEditDocStartTime2(e.target.value)} />
                </div>
                <div className="form-group" style={{ margin: 0 }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Session 2 End (Opt)</label>
                  <input type="time" className="form-control" style={{ padding: '7px 10px', fontSize: '12px' }} value={editDocEndTime2} onChange={e => setEditDocEndTime2(e.target.value)} />
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

      {/* Footer */}
      <footer style={{ padding: '20px', borderTop: '1px solid var(--border-color)', fontSize: '13px', color: 'var(--text-muted)' }}>
        &copy; {new Date().getFullYear()} Aura SaaS AI. Built with state-of-the-art Voice AI receptionists.
      </footer>
    </div>
  );
}
