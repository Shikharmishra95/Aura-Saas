import React, { useState } from 'react';
import { 
  Activity, 
  Shield, 
  Sliders, 
  Calendar, 
  Eye, 
  EyeOff, 
  User, 
  Clock, 
  DollarSign, 
  FileText 
} from 'lucide-react';
import { formatDoctorTimingsToEnglish } from '../../utils/formatters';

export default function HospitalAdminDashboard({
  activeTab,
  setActiveTab,
  token,
  userRole,
  username,
  hospitalId,
  userId,
  lang = 'en',
  t,
  API_BASE,
  activeHospital,
  fetchActiveHospitalProfile,
  hospitalStats,
  fetchHospitalStats,
  doctorsList = [],
  fetchDoctorsAndDepartments,
  departmentsList = [],
  hospitalStaff = { doctors: [], receptionists: [] },
  fetchHospitalStaff,
  hospitalStaffLoading = false,
  leavesList = [],
  fetchLeaves,
  handleApproveLeave,
  handleRejectLeave,
  handleDeleteLeave,
  handleDeleteStaff,
  setShowUpgradeModal,
  setUpgradeSelectedPlan,
  fetchAppointments,
  setRefreshTrigger,
}) {
  // ── 1. Staff Onboarding & Registration State ──
  const [staffRole, setStaffRole] = useState('DOCTOR');
  const [staffUsername, setStaffUsername] = useState('');
  const [staffPassword, setStaffPassword] = useState('');
  const [staffFirstName, setStaffFirstName] = useState('');
  const [staffLastName, setStaffLastName] = useState('');
  const [staffEmail, setStaffEmail] = useState('');
  const [staffPhone, setStaffPhone] = useState('');
  const [staffDeptId, setStaffDeptId] = useState('');
  const [staffLicense, setStaffLicense] = useState('');
  const [staffOpdFees, setStaffOpdFees] = useState(500);
  const [slotDurationMinutes, setSlotDurationMinutes] = useState(30);
  const [staffScheduleDays, setStaffScheduleDays] = useState([1, 2, 3, 4, 5]);
  const [staffStartTime, setStaffStartTime] = useState('10:00');
  const [staffEndTime, setStaffEndTime] = useState('13:00');
  const [staffHasShift2, setStaffHasShift2] = useState(false);
  const [staffStartTime2, setStaffStartTime2] = useState('14:00');
  const [staffEndTime2, setStaffEndTime2] = useState('17:00');
  const [staffRegError, setStaffRegError] = useState('');
  const [staffRegSuccess, setStaffRegSuccess] = useState('');

  // ── 2. Analytics Date Filter State ──
  const [metricsDateFilter, setMetricsDateFilter] = useState('');

  // ── 3. Edit Hospital Profile Modal State ──
  const [editHospitalProfileModalOpen, setEditHospitalProfileModalOpen] = useState(false);
  const [editHospitalName, setEditHospitalName] = useState(activeHospital?.name || '');
  const [editHospitalAddress, setEditHospitalAddress] = useState(activeHospital?.address || '');
  const [editHospitalPhone, setEditHospitalPhone] = useState(activeHospital?.phone || '');
  const [editHospitalEmail, setEditHospitalEmail] = useState(activeHospital?.email || '');
  const [editHospitalAdminUsername, setEditHospitalAdminUsername] = useState(activeHospital?.admin_username || '');
  const [editHospitalAdminPassword, setEditHospitalAdminPassword] = useState('');

  // ── 4. Edit Hospital AI & Voice Settings Modal State ──
  const [editHospitalSettingsModalOpen, setEditHospitalSettingsModalOpen] = useState(false);
  const [hospSettingsGreeting, setHospSettingsGreeting] = useState(activeHospital?.greeting_prompt || '');
  const [hospSettingsFullPrompt, setHospSettingsFullPrompt] = useState(activeHospital?.full_custom_prompt || '');
  const [hospSettingsWhatsapp, setHospSettingsWhatsapp] = useState(activeHospital?.whatsapp_number || '');

  // ── 5. Edit Doctor & OPD Schedule Modal State ──
  const [editDoctorModalOpen, setEditDoctorModalOpen] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState(null);
  const [editDocFirstName, setEditDocFirstName] = useState('');
  const [editDocLastName, setEditDocLastName] = useState('');
  const [editDocEmail, setEditDocEmail] = useState('');
  const [editDocPhone, setEditDocPhone] = useState('');
  const [editDocLicense, setEditDocLicense] = useState('');
  const [editDocOpdFees, setEditDocOpdFees] = useState(500);
  const [editDocScheduleDays, setEditDocScheduleDays] = useState([1, 2, 3, 4, 5]);
  const [editDocSlotDuration, setEditDocSlotDuration] = useState(30);
  const [editDocUsername, setEditDocUsername] = useState('');
  const [editDocPassword, setEditDocPassword] = useState('');
  const [showEditDocPassword, setShowEditDocPassword] = useState(false);
  const [editDocStartTime, setEditDocStartTime] = useState('10:00');
  const [editDocEndTime, setEditDocEndTime] = useState('13:00');
  const [editDocStartTime2, setEditDocStartTime2] = useState('14:00');
  const [editDocEndTime2, setEditDocEndTime2] = useState('17:00');
  const [editDocHasShift2, setEditDocHasShift2] = useState(false);
  const [editDocError, setEditDocError] = useState('');
  const [editDocSuccess, setEditDocSuccess] = useState('');

  // Handlers
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
        if (typeof setShowUpgradeModal === 'function') setShowUpgradeModal(true);
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
      setStaffScheduleDays([1, 2, 3, 4, 5]);
      setStaffStartTime('10:00');
      setStaffEndTime('13:00');
      setStaffStartTime2('14:00');
      setStaffEndTime2('17:00');
      setStaffHasShift2(false);
      setStaffOpdFees(500);
      if (typeof fetchHospitalStats === 'function') fetchHospitalStats();
      if (typeof fetchHospitalStaff === 'function' && hospitalId) fetchHospitalStaff(hospitalId);
      if (typeof fetchDoctorsAndDepartments === 'function') fetchDoctorsAndDepartments();
    } catch (err) {
      setStaffRegError(err.message);
    }
  };

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
        if (typeof fetchActiveHospitalProfile === 'function') fetchActiveHospitalProfile();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to update hospital profile.");
      }
    } catch (e) {
      console.error(e);
      alert("Error updating profile.");
    }
  };

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
        if (typeof fetchActiveHospitalProfile === 'function') fetchActiveHospitalProfile();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to save settings.");
      }
    } catch (e) {
      console.error(e);
      alert("Error saving settings.");
    }
  };

  const handleOpenEditDoctorModal = (doc) => {
    setEditingDoctor(doc);
    setEditDocFirstName(doc.first_name || '');
    setEditDocLastName(doc.last_name || '');
    setEditDocEmail(doc.email || '');
    setEditDocPhone(doc.phone || '');
    setEditDocLicense(doc.license_number || '');
    setEditDocOpdFees(doc.opd_fees || 500);
    setEditDocScheduleDays(doc.work_days || [1, 2, 3, 4, 5]);
    setEditDocSlotDuration(doc.slot_duration_minutes || 30);
    setEditDocUsername(doc.username || '');
    setEditDocPassword(doc.password || '');
    
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
      if (typeof fetchDoctorsAndDepartments === 'function') fetchDoctorsAndDepartments();
      if (typeof fetchAppointments === 'function') fetchAppointments();
      setTimeout(() => {
        setEditDoctorModalOpen(false);
        if (typeof setRefreshTrigger === 'function') setRefreshTrigger(prev => prev + 1);
        if (typeof fetchDoctorsAndDepartments === 'function') fetchDoctorsAndDepartments();
        if (typeof fetchAppointments === 'function') fetchAppointments();
      }, 1200);
    } catch (err) {
      setEditDocError(err.message);
    }
  };

  return (
    <>
      {/* Hospital Admin Top Navigation Bar */}
      {!activeHospital?.is_expired && (
        <div className="tab-container" style={{ margin: '0 0 16px 0' }}>
          <button 
            type="button"
            onClick={() => { 
              setActiveTab('admin_overview'); 
              if (hospitalId && typeof fetchHospitalStaff === 'function') fetchHospitalStaff(hospitalId); 
            }} 
            className={`tab-btn ${activeTab === 'admin_overview' ? 'active' : ''}`}
          >
            <Activity size={18} /> {t('adminOverview')}
          </button>
          <button 
            type="button"
            onClick={() => setActiveTab('staff_management')} 
            className={`tab-btn ${activeTab === 'staff_management' ? 'active' : ''}`}
          >
            <Shield size={18} /> {t('staffManagement')}
          </button>
          <button 
            type="button"
            onClick={() => setActiveTab('hospital_overview')} 
            className={`tab-btn ${activeTab === 'hospital_overview' ? 'active' : ''}`}
          >
            <Sliders size={18} /> {t('hospitalOverview')}
          </button>
          <button 
            type="button"
            onClick={() => { 
              setActiveTab('admin_leaves'); 
              if (typeof fetchLeaves === 'function') fetchLeaves(); 
            }} 
            className={`tab-btn ${activeTab === 'admin_leaves' ? 'active' : ''}`}
          >
            <Calendar size={18} /> {t('adminLeaves')}
          </button>
        </div>
      )}

      {/* ── TAB 1: Staff Allocation Tab ── */}
      {activeTab === 'staff_management' && (() => {
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
                    if (typeof setUpgradeSelectedPlan === 'function') setUpgradeSelectedPlan(plan === 'PRO' ? 'ENTERPRISE' : 'PRO');
                    if (typeof setShowUpgradeModal === 'function') setShowUpgradeModal(true);
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
                    if (typeof setUpgradeSelectedPlan === 'function') setUpgradeSelectedPlan(plan === 'PRO' ? 'ENTERPRISE' : 'PRO');
                    if (typeof setShowUpgradeModal === 'function') setShowUpgradeModal(true);
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
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
                <div className="form-group">
                  <label>Last Name</label>
                  <input type="text" className="form-control" value={staffLastName} onChange={e => setStaffLastName(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Email Address</label>
                  <input type="email" className="form-control" value={staffEmail} onChange={e => setStaffEmail(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Phone (For WhatsApp Dispatch)</label>
                  <input type="text" className="form-control" value={staffPhone} onChange={e => setStaffPhone(e.target.value)} required />
                </div>
              </div>

              {staffRole === 'DOCTOR' && (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
                    <div className="form-group">
                      <label>Department</label>
                      <select className="form-control" value={staffDeptId} onChange={e => setStaffDeptId(e.target.value)} required>
                        <option value="">Select Department...</option>
                        {departmentsList.map(d => (
                          <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group">
                      <label>License Number</label>
                      <input type="text" className="form-control" value={staffLicense} onChange={e => setStaffLicense(e.target.value)} />
                    </div>
                    <div className="form-group">
                      <label>OPD Consultation Fee (₹)</label>
                      <input type="number" className="form-control" value={staffOpdFees} onChange={e => setStaffOpdFees(parseInt(e.target.value) || 500)} required />
                    </div>
                    <div className="form-group">
                      <label>Slot Duration (mins)</label>
                      <input type="number" className="form-control" value={slotDurationMinutes} onChange={e => setSlotDurationMinutes(parseInt(e.target.value) || 30)} required style={{ borderRadius: '9px' }} />
                    </div>
                  </div>

                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>{t('lbl_sched_days')}</label>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {[
                        { id: 1, label: 'Mon' },
                        { id: 2, label: 'Tue' },
                        { id: 3, label: 'Wed' },
                        { id: 4, label: 'Thu' },
                        { id: 5, label: 'Fri' },
                        { id: 6, label: 'Sat' },
                        { id: 7, label: 'Sun' }
                      ].map(day => (
                        <label key={day.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: staffScheduleDays.includes(day.id) ? 'rgba(102,252,241,0.15)' : 'rgba(255,255,255,0.05)', border: staffScheduleDays.includes(day.id) ? '1px solid var(--color-primary)' : '1px solid rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', color: staffScheduleDays.includes(day.id) ? 'var(--color-primary)' : 'var(--text-muted)' }}>
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

                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: staffHasShift2 ? '1fr 1fr 1fr 1fr' : '1fr 1fr', gap: '15px' }}>
                      <div className="form-group" style={{ margin: 0 }}>
                        <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>🌅 Session 1 Start Time *</label>
                        <input type="time" className="form-control" value={staffStartTime} onChange={e => setStaffStartTime(e.target.value)} required />
                      </div>
                      <div className="form-group" style={{ margin: 0 }}>
                        <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>🌅 Session 1 End Time *</label>
                        <input type="time" className="form-control" value={staffEndTime} onChange={e => setStaffEndTime(e.target.value)} required />
                      </div>
                      {staffHasShift2 && (
                        <>
                          <div className="form-group animate-fade-in" style={{ margin: 0 }}>
                            <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>☀️ Session 2 Start Time</label>
                            <input type="time" className="form-control" value={staffStartTime2} onChange={e => setStaffStartTime2(e.target.value)} required />
                          </div>
                          <div className="form-group animate-fade-in" style={{ margin: 0 }}>
                            <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>☀️ Session 2 End Time</label>
                            <input type="time" className="form-control" value={staffEndTime2} onChange={e => setStaffEndTime2(e.target.value)} required />
                          </div>
                        </>
                      )}
                    </div>
                    <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px dashed rgba(255,255,255,0.08)' }}>
                      <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 600, color: 'var(--color-primary)' }}>
                        <input 
                          type="checkbox" 
                          checked={staffHasShift2} 
                          onChange={e => {
                            setStaffHasShift2(e.target.checked);
                            if (!e.target.checked) {
                              setStaffStartTime2('');
                              setStaffEndTime2('');
                            } else if (!staffStartTime2) {
                              setStaffStartTime2('14:00');
                              setStaffEndTime2('17:00');
                            }
                          }} 
                        />
                        <span>+ {staffHasShift2 ? '2nd Shift Active (Uncheck to remove)' : 'Enable 2nd Shift / Evening OPD (Optional)'}</span>
                      </label>
                    </div>
                  </div>
                </>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="submit" className="btn btn-primary" style={{ padding: '12px 24px', fontSize: '14px', fontWeight: 700 }}>
                  Allocate & Issue Credentials
                </button>
              </div>
            </form>

            {/* Current Staff List Allocation Table */}
            <div style={{ marginTop: '40px', paddingTop: '30px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              <h3 style={{ color: 'var(--text-main)', marginBottom: '15px' }}>Current Staff Allocation</h3>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
                {/* Doctors Section */}
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <h4 style={{ color: '#10b981', margin: 0, fontSize: '15px', fontWeight: 800 }}>
                      👨‍⚕️ Doctors ({hospitalStaff.doctors.length})
                    </h4>
                    <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>
                      Quota: {hospitalStaff.doctors.length} / {maxDocs === 999 ? 'Unlimited' : maxDocs}
                    </span>
                  </div>
                  {hospitalStaff.doctors.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '15px' }}>No doctors onboarded yet.</div>
                  ) : (
                    <div className="table-container">
                      <table className="custom-table" style={{ fontSize: '13px' }}>
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Department</th>
                            <th>Shift Timings</th>
                            <th>OPD Fee</th>
                            <th>Status</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {hospitalStaff.doctors.map(doc => (
                            <tr key={doc.id}>
                              <td>
                                <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{doc.username} • {doc.phone || 'N/A'}</div>
                              </td>
                              <td>{doc.department}</td>
                              <td>
                                <span style={{ background: '#EFF6FF', color: '#1E40AF', border: '1px solid #BFDBFE', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                                  {formatDoctorTimingsToEnglish(doc.timings) || 'Mon - Sat: 10:00 AM - 01:00 PM'}
                                </span>
                              </td>
                              <td style={{ fontWeight: 700 }}>₹{doc.opd_fees}</td>
                              <td>
                                <span style={{ background: '#DCFCE7', color: '#166534', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                                  Active
                                </span>
                              </td>
                              <td>
                                <div style={{ display: 'flex', gap: '6px' }}>
                                  <button
                                    type="button"
                                    onClick={() => handleOpenEditDoctorModal(doc)}
                                    style={{ padding: '5px 10px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }}
                                  >
                                    ✏️ Edit
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteStaff(doc.id)}
                                    style={{ padding: '5px 10px', background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }}
                                  >
                                    🗑️
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Receptionists Section */}
                <div className="glass-panel" style={{ padding: '20px' }}>
                  <h4 style={{ color: '#06b6d4', margin: '0 0 14px 0', fontSize: '15px', fontWeight: 800 }}>
                    🖥️ Receptionists ({hospitalStaff.receptionists.length})
                  </h4>
                  {hospitalStaff.receptionists.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '15px' }}>No receptionists onboarded yet.</div>
                  ) : (
                    <div className="table-container">
                      <table className="custom-table" style={{ fontSize: '13px' }}>
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {hospitalStaff.receptionists.map(rec => (
                            <tr key={rec.id}>
                              <td>
                                <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>{rec.first_name} {rec.last_name}</div>
                              </td>
                              <td><code style={{ color: '#6366f1' }}>{rec.username}</code></td>
                              <td>{rec.email}</td>
                              <td>{rec.phone || 'N/A'}</td>
                              <td>
                                <button
                                  type="button"
                                  onClick={() => handleDeleteStaff(rec.id)}
                                  style={{ padding: '5px 10px', background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }}
                                >
                                  🗑️ Delete
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── TAB 2: Hospital Analytics & Metrics Tab ── */}
      {activeTab === 'hospital_overview' && (
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
                  if (typeof fetchHospitalStats === 'function') fetchHospitalStats(e.target.value);
                }}
              />
              <button 
                type="button"
                className="btn btn-secondary" 
                style={{ padding: '5px 10px', fontSize: '11px', background: metricsDateFilter === new Date().toISOString().split('T')[0] ? '#10b981' : '' }}
                onClick={() => {
                  const todayStr = new Date().toISOString().split('T')[0];
                  setMetricsDateFilter(todayStr);
                  if (typeof fetchHospitalStats === 'function') fetchHospitalStats(todayStr);
                }}
              >
                Today
              </button>
              <button 
                type="button"
                className="btn btn-secondary" 
                style={{ padding: '5px 10px', fontSize: '11px' }}
                onClick={() => {
                  const yest = new Date();
                  yest.setDate(yest.getDate() - 1);
                  const yestStr = yest.toISOString().split('T')[0];
                  setMetricsDateFilter(yestStr);
                  if (typeof fetchHospitalStats === 'function') fetchHospitalStats(yestStr);
                }}
              >
                Yesterday
              </button>
              <button 
                type="button"
                className="btn btn-secondary" 
                style={{ padding: '5px 10px', fontSize: '11px', background: metricsDateFilter === '' ? '#3b82f6' : '' }}
                onClick={() => {
                  setMetricsDateFilter('');
                  if (typeof fetchHospitalStats === 'function') fetchHospitalStats('');
                }}
              >
                All Time
              </button>
            </div>
          </div>

          {/* 5 Per-Day KPI Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '24px' }}>
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
                              type="button"
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

      {/* ── TAB 3: Hospital Admin Leaves Management Tab ── */}
      {activeTab === 'admin_leaves' && (
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
                                  type="button"
                                  onClick={() => handleApproveLeave(leave.id)}
                                  style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid #10b981', color: '#34d399', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                >
                                  ✔️ Approve
                                </button>
                                <button 
                                  type="button"
                                  onClick={() => handleRejectLeave(leave.id)}
                                  style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid #ef4444', color: '#f87171', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}
                                >
                                  ❌ Reject
                                </button>
                              </>
                            )}
                            {leave.status === 'PENDING' && (
                              <button 
                                type="button"
                                onClick={() => handleDeleteLeave(leave.id)}
                                style={{ background: 'var(--bg-muted)', border: '1px solid rgba(255,255,255,0.2)', color: 'var(--text-secondary)', borderRadius: '6px', padding: '4px 10px', fontSize: '12px', cursor: 'pointer' }}
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

      {/* ── TAB 4: Hospital Admin Overview Tab (Executive Overview & Directory) ── */}
      {activeTab === 'admin_overview' && (() => {
        const staffDoctors = hospitalStaff.doctors.length > 0 ? hospitalStaff.doctors : (Array.isArray(doctorsList) ? doctorsList : []).map(d => ({ ...d, username: d.id, department: d.department_name }));
        const staffReceptionists = hospitalStaff.receptionists;
        const currentPlan = activeHospital?.subscription_plan || hospitalStats?.subscription_plan || 'PRO';
        const isEnterprise = currentPlan === 'ENTERPRISE';
        const maxDocs = activeHospital?.max_doctors || (isEnterprise ? 999 : (currentPlan === 'STARTER' ? 1 : 5));
        const quotaPct = isEnterprise ? 0 : Math.min(100, Math.round((staffDoctors.length / maxDocs) * 100));

        return (
          <div style={{ textAlign: 'left', animation: 'fadeIn 0.5s ease', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Urgent Expiry Alert Ribbon */}
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
                  type="button"
                  onClick={() => {
                    if (typeof setShowUpgradeModal === 'function') setShowUpgradeModal(true);
                  }}
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

            {/* Hard Expired Paywall Banner */}
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
                  type="button"
                  onClick={() => {
                    if (typeof setShowUpgradeModal === 'function') setShowUpgradeModal(true);
                  }}
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

            {/* Normal Executive Overview when NOT expired */}
            {!activeHospital?.is_expired && (
              <>
                {/* 1. Header Card */}
                <div style={{
                  background: '#FFFFFF', borderRadius: '20px', padding: '24px 28px',
                  border: '1.5px solid #DBEAFE', boxShadow: '0 4px 20px -2px rgba(15, 23, 42, 0.05)',
                  marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                      width: '56px', height: '56px', borderRadius: '16px',
                      background: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
                      border: '1px solid #BFDBFE', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '26px'
                    }}>
                      🏥
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <h2 style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                          {activeHospital?.name || 'AURA Partner Hospital'}
                        </h2>
                        <span style={{
                          background: isEnterprise ? '#FAF5FF' : '#EFF6FF',
                          color: isEnterprise ? '#7E22CE' : '#2563EB',
                          border: `1px solid ${isEnterprise ? '#E9D5FF' : '#BFDBFE'}`,
                          padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800
                        }}>
                          {isEnterprise ? '👑 ENTERPRISE 360' : (currentPlan === 'PRO' ? '⚡ PRO AI PLAN' : '⭐ STARTER TRIAL')}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px', fontWeight: 600 }}>
                        📍 {activeHospital?.address || 'India'} • 📞 Helpline: <strong style={{ color: '#0F172A' }}>{activeHospital?.helpline || activeHospital?.phone || 'AI Voice Line'}</strong> • WhatsApp: <strong style={{ color: '#10B981' }}>{activeHospital?.whatsapp_number || 'AI Automated'}</strong>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button 
                      type="button"
                      onClick={() => setEditHospitalProfileModalOpen(true)} 
                      className="btn btn-secondary" 
                      style={{ padding: '7px 12px', fontSize: '12px', borderRadius: '8px', fontWeight: 700 }}
                    >
                      ✏️ Profile
                    </button>
                    <button 
                      type="button"
                      onClick={() => setEditHospitalSettingsModalOpen(true)} 
                      className="btn btn-secondary" 
                      style={{ padding: '7px 12px', fontSize: '12px', borderRadius: '8px', fontWeight: 700 }}
                    >
                      ⚙️ Settings
                    </button>
                    <button 
                      type="button"
                      onClick={() => {
                        if (typeof setShowUpgradeModal === 'function') setShowUpgradeModal(true);
                      }} 
                      style={{
                        background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                        color: '#FFFFFF', border: 'none', borderRadius: '8px', padding: '8px 14px',
                        fontSize: '12px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)'
                      }}
                    >
                      ⚡ Plan Management
                    </button>
                  </div>
                </div>

                {/* 2. Key Metrics Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '24px' }}>
                  {/* Quota Gauge */}
                  <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '18px', border: '1.5px solid #DBEAFE', boxShadow: '0 2px 10px rgba(15,23,42,0.03)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>👨‍⚕️ Doctor Quota</span>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: quotaPct >= 100 ? '#DC2626' : '#2563EB' }}>
                        {staffDoctors.length} / {isEnterprise ? '∞' : maxDocs}
                      </span>
                    </div>
                    <div style={{ fontSize: '24px', fontWeight: 900, color: '#0F172A', marginTop: '6px' }}>
                      {staffDoctors.length} <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 600 }}>active doctor{staffDoctors.length !== 1 ? 's' : ''}</span>
                    </div>
                    <div style={{ background: '#F1F5F9', height: '6px', borderRadius: '6px', marginTop: '10px', overflow: 'hidden' }}>
                      <div style={{ background: quotaPct >= 100 ? '#DC2626' : '#2563EB', width: `${quotaPct}%`, height: '100%', borderRadius: '6px' }} />
                    </div>
                  </div>

                  {/* 24/7 AI Voice Line Status */}
                  <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '18px', border: '1.5px solid #DBEAFE', boxShadow: '0 2px 10px rgba(15,23,42,0.03)' }}>
                    <span style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>📞 AI Voice Line</span>
                    <div style={{ fontSize: '20px', fontWeight: 900, color: activeHospital?.ai_voice_enabled !== false ? '#166534' : '#991B1B', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>{activeHospital?.ai_voice_enabled !== false ? '🟢 ACTIVE' : '🔴 LOCKED'}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B', marginTop: '6px', fontWeight: 600 }}>
                      {activeHospital?.helpline ? `Line: ${activeHospital.helpline}` : 'Multi-Tenant Standard Line'}
                    </div>
                  </div>

                  {/* Completed Appointments */}
                  <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '18px', border: '1.5px solid #DBEAFE', boxShadow: '0 2px 10px rgba(15,23,42,0.03)' }}>
                    <span style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>✅ Completed Consultations</span>
                    <div style={{ fontSize: '24px', fontWeight: 900, color: '#0F172A', marginTop: '6px' }}>
                      {hospitalStats?.completed_bookings || 0}
                    </div>
                    <div style={{ fontSize: '11px', color: '#166534', marginTop: '6px', fontWeight: 600 }}>
                      Total Bookings: {hospitalStats?.total_bookings || 0}
                    </div>
                  </div>

                  {/* Total Revenue */}
                  <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '18px', border: '1.5px solid #DBEAFE', boxShadow: '0 2px 10px rgba(15,23,42,0.03)' }}>
                    <span style={{ fontSize: '11px', fontWeight: 800, color: '#64748B', textTransform: 'uppercase' }}>💰 Total OPD Collections</span>
                    <div style={{ fontSize: '24px', fontWeight: 900, color: '#166534', marginTop: '6px' }}>
                      ₹{(hospitalStats?.total_revenue || 0).toLocaleString()}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B', marginTop: '6px', fontWeight: 600 }}>
                      Razorpay & Cash Collections
                    </div>
                  </div>
                </div>

                {/* 3. Doctors Directory Table */}
                <div style={{ background: '#FFFFFF', borderRadius: '18px', border: '1.5px solid #DBEAFE', padding: '22px', marginBottom: '22px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                      👨‍⚕️ Doctors Directory & Shift Schedules
                    </h3>
                    <button
                      type="button"
                      onClick={() => setActiveTab('staff_management')}
                      style={{ background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', padding: '6px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}
                    >
                      + Add Doctor / Staff
                    </button>
                  </div>

                  {staffDoctors.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: '#64748B', fontSize: '13px' }}>
                      No doctors registered yet. Click "+ Add Doctor / Staff" to onboard your medical team.
                    </div>
                  ) : (
                    <div className="table-container">
                      <table className="custom-table" style={{ fontSize: '13px' }}>
                        <thead>
                          <tr>
                            <th>Doctor</th>
                            <th>Department</th>
                            <th>Shift Timings</th>
                            <th>OPD Fee</th>
                            <th>Slot</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {staffDoctors.map(doc => (
                            <tr key={doc.id}>
                              <td>
                                <div style={{ fontWeight: 800, color: '#0F172A' }}>Dr. {doc.first_name} {doc.last_name}</div>
                                <div style={{ fontSize: '11px', color: '#64748B' }}>U: <strong>{doc.username}</strong> • 📞 {doc.phone || 'N/A'}</div>
                              </td>
                              <td>{doc.department}</td>
                              <td>
                                <span style={{ background: '#EFF6FF', color: '#1E40AF', border: '1px solid #BFDBFE', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                                  {formatDoctorTimingsToEnglish(doc.timings) || 'Mon - Sat: 10:00 AM - 01:00 PM'}
                                </span>
                              </td>
                              <td style={{ fontWeight: 800 }}>₹{doc.opd_fees}</td>
                              <td>{doc.slot_duration_minutes || 30} mins</td>
                              <td>
                                <div style={{ display: 'flex', gap: '6px' }}>
                                  <button 
                                    type="button"
                                    onClick={() => handleOpenEditDoctorModal(doc)} 
                                    style={{ padding: '6px 10px', background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }} 
                                    title="Edit Doctor"
                                  >
                                    ✏️ Edit
                                  </button>
                                  <button 
                                    type="button"
                                    onClick={() => handleDeleteStaff(doc.id)} 
                                    style={{ padding: '6px 10px', background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }} 
                                    title="Delete Doctor"
                                  >
                                    🗑️
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* 4. Receptionists Directory Table */}
                <div style={{ background: '#FFFFFF', borderRadius: '18px', border: '1.5px solid #DBEAFE', padding: '22px' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', margin: '0 0 16px 0' }}>
                    🖥️ Receptionist Team ({staffReceptionists.length})
                  </h3>
                  {staffReceptionists.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#64748B', fontSize: '13px' }}>
                      No receptionists onboarded yet.
                    </div>
                  ) : (
                    <div className="table-container">
                      <table className="custom-table" style={{ fontSize: '13px' }}>
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {staffReceptionists.map(rec => (
                            <tr key={rec.id}>
                              <td>
                                <div style={{ fontWeight: 800, color: '#0F172A' }}>{rec.first_name} {rec.last_name}</div>
                              </td>
                              <td><code style={{ color: '#2563EB' }}>{rec.username}</code></td>
                              <td>{rec.email}</td>
                              <td>{rec.phone || 'N/A'}</td>
                              <td>
                                <button 
                                  type="button"
                                  onClick={() => handleDeleteStaff(rec.id)} 
                                  style={{ padding: '6px 10px', background: '#FEF2F2', color: '#DC2626', border: '1px solid #FECACA', borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 700 }} 
                                  title="Delete Account"
                                >
                                  🗑️ Delete
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        );
      })()}

      {/* ── 3 ADMIN MODALS ── */}

      {/* A. Edit Hospital Profile Modal */}
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

      {/* B. Edit Hospital Settings Modal */}
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

      {/* C. Edit Doctor Modal */}
      {editDoctorModalOpen && (
        <div className="modal-overlay" style={{ backdropFilter: 'blur(10px)', zIndex: 9999 }}>
          <div className="modal-content" style={{ maxWidth: '850px', width: '92%', maxHeight: '92vh', overflowY: 'auto', textAlign: 'left', background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '20px', padding: '24px', color: '#0F172A' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '12px' }}>
              <h3 style={{ color: 'var(--text-main)', margin: 0, fontWeight: 700, fontSize: '18px' }}>✏️ Edit Doctor Profile & OPD Schedule</h3>
              <button type="button" onClick={() => setEditDoctorModalOpen(false)} style={{ background: 'none', border: 'none', color: '#9ca3af', fontSize: '20px', cursor: 'pointer' }}>✕</button>
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
    </>
  );
}
