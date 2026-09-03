import React, { useState } from 'react';
import { UserCheck, Clock, CheckCircle2, Search, FileText, Calendar as CalendarIcon, Pill, AlertCircle, Heart, ChevronLeft, ChevronRight, PlusCircle, Trash2 } from 'lucide-react';

export default function DoctorQueue({
  appointments,
  selectedAppointment,
  setSelectedAppointment,
  handleCompleteConsultation,
  selectedDate,
  setSelectedDate,
  activeTab,
  setActiveTab,
  leavesList = [],
  leaveStartDate,
  setLeaveStartDate,
  leaveEndDate,
  setLeaveEndDate,
  leaveReason,
  setLeaveReason,
  handleApplyLeave,
  handleDeleteLeave,
  leaveSuccess,
  leaveError,
  userId,
  hospitalName,
  doctorName,
  doctorSpecialty,
  doctorTimings,
  doctorOpdFees,
  logout,
  username,
  lang,
  toggleLanguage,
  t
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [globalSearchTerm, setGlobalSearchTerm] = useState('');
  const [showGlobalDropdown, setShowGlobalDropdown] = useState(false);
  const [historyModalAppt, setHistoryModalAppt] = useState(null);

  // Helper to format Slot Time cleanly
  const formatSlotTime = (appt) => {
    if (!appt) return 'N/A';
    if (appt.appointment_time && appt.appointment_time !== 'N/A') return appt.appointment_time;
    if (appt.slot_time && appt.slot_time !== 'N/A') return appt.slot_time;
    if (appt.appointment_datetime) {
      try {
        const d = new Date(appt.appointment_datetime);
        if (!isNaN(d.getTime())) {
          return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
        }
      } catch (e) {}
    }
    return '03:10 PM';
  };

  // Helper to format Patient ID cleanly
  const formatPatientId = (idStr) => {
    if (!idStr) return 'PAT-NEW';
    if (idStr.startsWith('PAT-')) return idStr;
    if (idStr.length > 12) {
      return `PAT-${idStr.substring(0, 8).toUpperCase()}`;
    }
    return idStr;
  };

  // Calendar State for Left Sidebar Widget
  const currentDateObj = selectedDate ? new Date(selectedDate) : new Date();
  const [calYear, setCalYear] = useState(currentDateObj.getFullYear());
  const [calMonth, setCalMonth] = useState(currentDateObj.getMonth());

  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

  const daysInMonth = getDaysInMonth(calYear, calMonth);
  const firstDay = getFirstDayOfMonth(calYear, calMonth);

  // Target date for Doctor Queue filtering (defaults to today's date)
  const targetDateStr = selectedDate || new Date().toISOString().split('T')[0];

  // Filter active non-cancelled appointments strictly for selected date
  const activeAppts = appointments.filter(a => {
    if (!a.appointment_datetime) return false;
    const aDate = a.appointment_datetime.split('T')[0];
    return aDate === targetDateStr && a.status !== 'CANCELLED';
  });

  // Local Search filtering for currently selected date
  const filteredAppts = activeAppts.filter(a => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const pName = (a.patient_name || '').toLowerCase();
    const pPhone = (a.patient_phone || '').toLowerCase();
    const pId = (a.patient_id || a.id || '').toLowerCase();
    return pName.includes(term) || pPhone.includes(term) || pId.includes(term);
  });

  // Global Search filtering across ALL DATES
  const allDatesSearchResults = (appointments || []).filter(a => {
    if (!globalSearchTerm.trim() || globalSearchTerm.trim().length < 2) return false;
    const term = globalSearchTerm.toLowerCase();
    const pName = (a.patient_name || '').toLowerCase();
    const pPhone = (a.patient_phone || '').toLowerCase();
    const pId = (a.patient_id || a.id || '').toLowerCase();
    const pReason = (a.reason || '').toLowerCase();
    return pName.includes(term) || pPhone.includes(term) || pId.includes(term) || pReason.includes(term);
  });

  // Doctor Performance Analytics Time Filter ('today', 'week', 'month', 'all')
  const [docAnalyticsRange, setDocAnalyticsRange] = useState('today');

  // Compute Doctor Analytics based on docAnalyticsRange
  const analyticsAppts = (appointments || []).filter(a => {
    if (!a.appointment_datetime) return false;
    const aDateStr = a.appointment_datetime.split('T')[0];
    const todayStr = new Date().toISOString().split('T')[0];
    if (docAnalyticsRange === 'today') {
      return aDateStr === (selectedDate || todayStr);
    }
    if (docAnalyticsRange === 'week') {
      const aTime = new Date(aDateStr).getTime();
      const nowTime = new Date(todayStr).getTime();
      const diffDays = (nowTime - aTime) / (1000 * 3600 * 24);
      return diffDays >= 0 && diffDays <= 7;
    }
    if (docAnalyticsRange === 'month') {
      const aD = new Date(aDateStr);
      const nowD = new Date();
      return aD.getMonth() === nowD.getMonth() && aD.getFullYear() === nowD.getFullYear();
    }
    return true; // 'all'
  });

  const docTotalBooked = analyticsAppts.length;
  const docCompleted = analyticsAppts.filter(a => a.status === 'COMPLETED' || a.status === 'CONSULTATION_FINISHED').length;
  const docMissed = analyticsAppts.filter(a => a.status === 'MISSED').length;
  const docWaiting = analyticsAppts.filter(a => a.status === 'CONFIRMED' || a.status === 'WAITING' || a.status === 'SCHEDULED' || !a.status).length;
  const docFee = Number(doctorOpdFees) || 400;
  const docRevenue = docCompleted * docFee;

  const waitingCount = activeAppts.filter(a => a.status === 'CONFIRMED' || a.status === 'WAITING' || a.status === 'SCHEDULED' || !a.status).length;
  const inConsultCount = activeAppts.filter(a => a.status === 'IN_CONSULTATION').length;
  const completedCount = activeAppts.filter(a => a.status === 'COMPLETED' || a.status === 'CONSULTATION_FINISHED').length;
  const missedCount = activeAppts.filter(a => a.status === 'MISSED').length;

  const handlePrevMonth = () => {
    if (calMonth === 0) {
      setCalMonth(11);
      setCalYear(calYear - 1);
    } else {
      setCalMonth(calMonth - 1);
    }
  };

  const handleNextMonth = () => {
    if (calMonth === 11) {
      setCalMonth(0);
      setCalYear(calYear + 1);
    } else {
      setCalMonth(calMonth + 1);
    }
  };

  const handleSelectCalDay = (dayNum) => {
    const m = (calMonth + 1).toString().padStart(2, '0');
    const d = dayNum.toString().padStart(2, '0');
    const newDateStr = `${calYear}-${m}-${d}`;
    setSelectedDate(newDateStr);
  };

  const currentTab = activeTab || 'appointments';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: '84vh', color: '#0F172A', textAlign: 'left', padding: '16px 0 0 0' }}>
      
      {/* ── SLEEK COMPACT DOCTOR & HOSPITAL EXECUTIVE BAR ── */}
      <div style={{
        background: 'linear-gradient(135deg, #0B132B 0%, #1C2541 45%, #1D4ED8 100%)',
        borderRadius: '16px',
        padding: '12px 20px',
        color: '#FFFFFF',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        boxShadow: '0 4px 20px rgba(15, 23, 42, 0.15)',
        border: '1.5px solid rgba(147, 197, 253, 0.25)',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #38BDF8 0%, #2563EB 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            boxShadow: '0 2px 10px rgba(56, 189, 248, 0.35)',
            flexShrink: 0
          }}>
            🩺
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{
                fontSize: '11px',
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#7DD3FC',
                border: '1px solid rgba(56, 189, 248, 0.35)',
                padding: '1px 8px',
                borderRadius: '6px',
                fontWeight: 800,
                letterSpacing: '0.3px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                🏥 {hospitalName || 'Rao Hospital'}
              </span>
              <span style={{
                fontSize: '10px',
                background: 'rgba(34, 197, 94, 0.18)',
                color: '#4ADE80',
                border: '1px solid rgba(74, 222, 128, 0.35)',
                padding: '1px 7px',
                borderRadius: '6px',
                fontWeight: 800,
                textTransform: 'uppercase'
              }}>
                ● Active OP Desk
              </span>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' }}>
              <h1 style={{ margin: 0, fontSize: '17px', fontWeight: 900, letterSpacing: '-0.3px', color: '#F8FAFC' }}>
                {doctorName ? (doctorName.startsWith('Dr.') ? doctorName : `Dr. ${doctorName}`) : 'Doctor Workstation'}
              </h1>
              <span style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600 }}>
                Specialty: <strong style={{ color: '#E2E8F0' }}>{doctorSpecialty || 'General OPD'}</strong> • OPD Fee: <strong style={{ color: '#38BDF8' }}>₹{doctorOpdFees || 400}</strong>
              </span>
            </div>
          </div>
        </div>

        {/* Right Controls: Timings, Language, Doctor Profile, Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {/* Doctor Working Days & Timings Sleek Glass Badge */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            borderRadius: '12px',
            padding: '7px 14px',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <div style={{ fontSize: '15px' }}>🗓️</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
              <div style={{ fontSize: '9px', color: '#93C5FD', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                OPD Hours
              </div>
              <div style={{ fontSize: '12px', fontWeight: 800, color: '#FFFFFF' }}>
                {doctorTimings || 'Mon – Sat: 10:00 AM – 01:00 PM'}
              </div>
            </div>
          </div>

          {/* Language Toggle Button */}
          {toggleLanguage && (
            <button
              onClick={toggleLanguage}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '10px',
                padding: '7px 12px',
                color: '#FFFFFF',
                fontSize: '12px',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s'
              }}
              title="Switch Language (Hindi / English)"
            >
              <span>🌐</span> {lang === 'hi' ? 'EN' : 'हिन्दी'}
            </button>
          )}

          {/* Doctor Profile Name Badge */}
          <div style={{
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid rgba(56, 189, 248, 0.35)',
            borderRadius: '10px',
            padding: '6px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ fontSize: '9px', fontWeight: 900, background: '#38BDF8', color: '#0F172A', padding: '2px 5px', borderRadius: '4px', textTransform: 'uppercase' }}>
              DOCTOR
            </span>
            <span style={{ fontSize: '12px', fontWeight: 800, color: '#E0F2FE' }}>
              {username || 'Dr. Account'}
            </span>
          </div>

          {/* Logout Button */}
          {logout && (
            <button
              onClick={logout}
              style={{
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.45)',
                color: '#FECACA',
                borderRadius: '10px',
                padding: '7px 14px',
                fontSize: '12px',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s',
                boxShadow: '0 2px 8px rgba(239, 68, 68, 0.2)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#EF4444';
                e.currentTarget.style.color = '#FFFFFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                e.currentTarget.style.color = '#FECACA';
              }}
            >
              <span>⎋</span> Logout
            </button>
          )}
        </div>
      </div>

      {/* ── DOCTOR PERFORMANCE & EARNINGS ANALYTICS BAR ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ fontSize: '13px', fontWeight: 900, color: '#0F172A', display: 'flex', alignItems: 'center', gap: '6px' }}>
            📊 DOCTOR CLINICAL & REVENUE ANALYTICS:
          </div>
          
          {/* Quick Date Filter Pills */}
          <div style={{ display: 'flex', gap: '6px', background: '#F1F5F9', padding: '3px', borderRadius: '10px', border: '1px solid #E2E8F0' }}>
            {[
              { id: 'today', label: 'Today' },
              { id: 'week', label: 'This Week' },
              { id: 'month', label: 'This Month' },
              { id: 'all', label: 'All Time' }
            ].map(pill => (
              <button
                key={pill.id}
                onClick={() => setDocAnalyticsRange(pill.id)}
                style={{
                  background: docAnalyticsRange === pill.id ? '#2563EB' : 'transparent',
                  color: docAnalyticsRange === pill.id ? '#FFFFFF' : '#475569',
                  border: 'none',
                  borderRadius: '7px',
                  padding: '4px 12px',
                  fontSize: '11px',
                  fontWeight: 800,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  boxShadow: docAnalyticsRange === pill.id ? '0 2px 6px rgba(37,99,235,0.25)' : 'none'
                }}
              >
                {pill.label}
              </button>
            ))}
          </div>
        </div>

        {/* 5 KPI Scorecards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px' }}>
          <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '14px 16px', border: '1.5px solid #E2E8F0', boxShadow: '0 2px 10px rgba(15,23,42,0.03)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: '#EFF6FF', color: '#2563EB', padding: '8px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CalendarIcon size={18} />
            </div>
            <div>
              <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 800, textTransform: 'uppercase' }}>Total Patients</div>
              <div style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A' }}>{docTotalBooked}</div>
            </div>
          </div>

          <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '14px 16px', border: '1.5px solid #E2E8F0', boxShadow: '0 2px 10px rgba(15,23,42,0.03)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: '#DCFCE7', color: '#166534', padding: '8px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <CheckCircle2 size={18} />
            </div>
            <div>
              <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 800, textTransform: 'uppercase' }}>Consulted</div>
              <div style={{ fontSize: '20px', fontWeight: 900, color: '#166534' }}>{docCompleted}</div>
            </div>
          </div>

          <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '14px 16px', border: '1.5px solid #E2E8F0', boxShadow: '0 2px 10px rgba(15,23,42,0.03)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: '#FEF3C7', color: '#D97706', padding: '8px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Clock size={18} />
            </div>
            <div>
              <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 800, textTransform: 'uppercase' }}>Waiting Queue</div>
              <div style={{ fontSize: '20px', fontWeight: 900, color: '#D97706' }}>{docWaiting}</div>
            </div>
          </div>

          <div style={{ background: '#FFFFFF', borderRadius: '16px', padding: '14px 16px', border: '1.5px solid #E2E8F0', boxShadow: '0 2px 10px rgba(15,23,42,0.03)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: '#FEE2E2', color: '#DC2626', padding: '8px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <AlertCircle size={18} />
            </div>
            <div>
              <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 800, textTransform: 'uppercase' }}>Missed / Cancelled</div>
              <div style={{ fontSize: '20px', fontWeight: 900, color: '#DC2626' }}>{docMissed}</div>
            </div>
          </div>

          <div style={{ background: 'linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)', borderRadius: '16px', padding: '14px 16px', border: '1.5px solid #86EFAC', boxShadow: '0 2px 10px rgba(22,101,52,0.06)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ background: '#166534', color: '#FFFFFF', padding: '8px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', fontWeight: 900 }}>
              ₹
            </div>
            <div>
              <div style={{ fontSize: '10px', color: '#166534', fontWeight: 800, textTransform: 'uppercase' }}>My Total Earnings</div>
              <div style={{ fontSize: '20px', fontWeight: 900, color: '#14532D' }}>₹{docRevenue.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── GLOBAL SEARCH BAR (ALL DATES PATIENT LOOKUP) ── */}
      <div style={{ position: 'relative', width: '100%' }}>
        <div style={{
          background: '#FFFFFF',
          borderRadius: '16px',
          border: '1.5px solid #CBD5E1',
          padding: '8px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          boxShadow: '0 4px 16px rgba(15,23,42,0.04)',
          transition: 'all 0.2s'
        }}>
          <div style={{ background: '#EFF6FF', color: '#2563EB', padding: '8px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Search size={18} />
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <input
              type="text"
              placeholder="🔍 Global Search: Search Patient across ALL Dates by Name, Phone (+91...), Patient ID, or Problem..."
              value={globalSearchTerm}
              onChange={e => {
                setGlobalSearchTerm(e.target.value);
                setShowGlobalDropdown(true);
              }}
              onFocus={() => setShowGlobalDropdown(true)}
              style={{
                width: '100%',
                border: 'none',
                outline: 'none',
                fontSize: '13px',
                fontWeight: 600,
                color: '#0F172A',
                background: 'transparent'
              }}
            />
          </div>
          {globalSearchTerm && (
            <button
              onClick={() => {
                setGlobalSearchTerm('');
                setShowGlobalDropdown(false);
              }}
              style={{
                background: '#F1F5F9',
                border: 'none',
                borderRadius: '8px',
                padding: '5px 10px',
                fontSize: '11px',
                fontWeight: 700,
                color: '#64748B',
                cursor: 'pointer'
              }}
            >
              ✕ Clear
            </button>
          )}
        </div>

        {/* Global Live Search Results Dropdown */}
        {showGlobalDropdown && globalSearchTerm.trim().length >= 2 && (
          <div style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            right: 0,
            background: '#FFFFFF',
            borderRadius: '16px',
            border: '1.5px solid #CBD5E1',
            boxShadow: '0 12px 32px rgba(15,23,42,0.15)',
            zIndex: 1000,
            maxHeight: '380px',
            overflowY: 'auto',
            padding: '12px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px 10px', borderBottom: '1px solid #F1F5F9', fontSize: '11px', fontWeight: 800, color: '#64748B' }}>
              <span>MATCHED PATIENT VISITS ACROSS ALL DATES ({allDatesSearchResults.length})</span>
              <span style={{ cursor: 'pointer', color: '#2563EB', fontWeight: 800 }} onClick={() => setShowGlobalDropdown(false)}>Close ✕</span>
            </div>

            {allDatesSearchResults.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748B', fontSize: '13px', fontWeight: 600 }}>
                ❌ No patient visits found matching "<strong>{globalSearchTerm}</strong>" across all dates.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                {allDatesSearchResults.map(appt => {
                  const apptDateStr = appt.appointment_datetime ? appt.appointment_datetime.split('T')[0] : '';
                  const apptDateObj = appt.appointment_datetime ? new Date(appt.appointment_datetime) : null;
                  const dateFormatted = apptDateObj && !isNaN(apptDateObj.getTime())
                    ? apptDateObj.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
                    : apptDateStr;

                  const isCompleted = appt.status === 'COMPLETED' || appt.status === 'CONSULTATION_FINISHED';
                  const isMissed = appt.status === 'MISSED';

                  return (
                    <div
                      key={appt.id}
                      onClick={() => {
                        if (apptDateStr) {
                          setSelectedDate(apptDateStr);
                        }
                        setSelectedAppointment(appt);
                        setShowGlobalDropdown(false);
                        if (isCompleted) {
                          setHistoryModalAppt(appt);
                        }
                      }}
                      style={{
                        padding: '12px 14px',
                        borderRadius: '12px',
                        border: '1.5px solid #E2E8F0',
                        background: '#F8FAFC',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.15s'
                      }}
                      onMouseEnter={e => { e.currentTarget.style.background = '#EFF6FF'; e.currentTarget.style.borderColor = '#93C5FD'; }}
                      onMouseLeave={e => { e.currentTarget.style.background = '#F8FAFC'; e.currentTarget.style.borderColor = '#E2E8F0'; }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '14px', fontWeight: 800, color: '#0F172A' }}>
                            👤 {appt.patient_name || 'Patient'}
                          </span>
                          {appt.patient_age && (
                            <span style={{ fontSize: '11px', color: '#64748B', background: '#E2E8F0', padding: '1px 6px', borderRadius: '6px' }}>
                              Age: {appt.patient_age}
                            </span>
                          )}
                          <span style={{ fontSize: '12px', color: '#2563EB', fontWeight: 700 }}>
                            📞 {appt.patient_phone || 'N/A'}
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>
                          Reason: <strong style={{ color: '#334155' }}>{appt.reason || 'General Consultation'}</strong>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        <span style={{
                          background: '#EFF6FF',
                          color: '#1D4ED8',
                          border: '1px solid #BFDBFE',
                          padding: '3px 8px',
                          borderRadius: '8px',
                          fontSize: '11px',
                          fontWeight: 800
                        }}>
                          📅 {dateFormatted} | ⏰ {formatSlotTime(appt)}
                        </span>
                        <span style={{
                          background: isCompleted ? '#DCFCE7' : isMissed ? '#FEE2E2' : '#FEF3C7',
                          color: isCompleted ? '#166534' : isMissed ? '#991B1B' : '#92400E',
                          padding: '2px 8px',
                          borderRadius: '6px',
                          fontSize: '10px',
                          fontWeight: 800
                        }}>
                          {isCompleted ? '✓ Completed' : isMissed ? '⚠️ Missed' : '⏳ Scheduled'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── PERSISTENT SIDEBAR LAYOUT ── */}
      <div style={{ display: 'grid', gridTemplateColumns: currentTab === 'doctor_leaves' ? '260px 1fr' : '260px 340px 1fr', gap: '20px', flex: 1 }}>
        
        {/* PERSISTENT LEFT SIDEBAR WIDGET WITH MINI-CALENDAR */}
        <div style={{ background: '#FFFFFF', borderRadius: '20px', border: '1.5px solid #E2E8F0', padding: '18px', display: 'flex', flexDirection: 'column', gap: '18px', boxShadow: '0 4px 16px rgba(15,23,42,0.03)' }}>
          
          {/* Navigation Tab Links */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              onClick={() => setActiveTab && setActiveTab('appointments')}
              style={{
                width: '100%',
                background: currentTab === 'appointments' ? '#EFF6FF' : '#F8FAFC',
                color: currentTab === 'appointments' ? '#2563EB' : '#475569',
                border: `1.5px solid ${currentTab === 'appointments' ? '#BFDBFE' : '#CBD5E1'}`,
                borderRadius: '12px', padding: '12px 14px', fontSize: '13px', fontWeight: 800,
                display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer',
                boxShadow: currentTab === 'appointments' ? '0 2px 8px rgba(37,99,235,0.1)' : 'none', transition: 'all 0.2s'
              }}
            >
              🏠 Patient Queue
            </button>

            <button
              onClick={() => setActiveTab && setActiveTab('doctor_leaves')}
              style={{
                width: '100%',
                background: currentTab === 'doctor_leaves' ? '#EFF6FF' : '#F8FAFC',
                color: currentTab === 'doctor_leaves' ? '#2563EB' : '#475569',
                border: `1.5px solid ${currentTab === 'doctor_leaves' ? '#BFDBFE' : '#CBD5E1'}`,
                borderRadius: '12px', padding: '12px 14px', fontSize: '13px', fontWeight: 800,
                display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer',
                boxShadow: currentTab === 'doctor_leaves' ? '0 2px 8px rgba(37,99,235,0.1)' : 'none', transition: 'all 0.2s'
              }}
            >
              🏖️ Apply Leave
            </button>
          </div>

          <div style={{ borderTop: '1px dashed #E2E8F0', paddingTop: '16px' }}>
            {/* MINI CALENDAR HEADER */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ fontSize: '13px', fontWeight: 800, color: '#0F172A' }}>
                {monthNames[calMonth]} {calYear}
              </span>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button onClick={handlePrevMonth} style={{ background: '#F1F5F9', border: 'none', borderRadius: '6px', padding: '4px', cursor: 'pointer', color: '#475569' }}><ChevronLeft size={16} /></button>
                <button onClick={handleNextMonth} style={{ background: '#F1F5F9', border: 'none', borderRadius: '6px', padding: '4px', cursor: 'pointer', color: '#475569' }}><ChevronRight size={16} /></button>
              </div>
            </div>

            {/* WEEKDAY HEADERS */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '2px', textAlign: 'center', fontSize: '10px', fontWeight: 800, color: '#64748B', marginBottom: '6px' }}>
              <span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span>
            </div>

            {/* MINI CALENDAR DAYS GRID */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', textAlign: 'center' }}>
              {Array.from({ length: firstDay }).map((_, i) => (
                <div key={`empty-${i}`} style={{ height: '28px' }} />
              ))}

              {Array.from({ length: daysInMonth }).map((_, i) => {
                const dayNum = i + 1;
                const m = (calMonth + 1).toString().padStart(2, '0');
                const d = dayNum.toString().padStart(2, '0');
                const dateStr = `${calYear}-${m}-${d}`;

                const isSelected = selectedDate === dateStr;

                return (
                  <button
                    key={dayNum}
                    onClick={() => {
                      handleSelectCalDay(dayNum);
                      if (currentTab !== 'appointments') setActiveTab('appointments');
                    }}
                    style={{
                      height: '28px', width: '28px', margin: '0 auto',
                      borderRadius: '50%', border: 'none',
                      background: isSelected ? '#2563EB' : 'transparent',
                      color: isSelected ? '#FFFFFF' : '#334155',
                      fontSize: '11px', fontWeight: isSelected ? 900 : 700,
                      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: isSelected ? '0 4px 10px rgba(37,99,235,0.35)' : 'none',
                      transition: 'all 0.15s'
                    }}
                  >
                    {dayNum}
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ marginTop: 'auto', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '12px', padding: '12px', fontSize: '11px', color: '#64748B', fontWeight: 600 }}>
            ℹ️ Selected Date: <strong style={{ color: '#2563EB' }}>{selectedDate || 'Today'}</strong>
          </div>

        </div>

        {/* VIEW A: PATIENT QUEUE WORKSTATION */}
        {currentTab === 'appointments' && (
          <>
            {/* COLUMN 2: VISITS QUEUE & SEARCH */}
            <div style={{ background: '#FFFFFF', borderRadius: '20px', border: '1.5px solid #E2E8F0', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px', boxShadow: '0 4px 16px rgba(15,23,42,0.03)' }}>
              
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <h2 style={{ fontSize: '16px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                  VISITS QUEUE ({selectedDate ? new Date(selectedDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase() : 'TODAY'})
                </h2>
              </div>

              {/* Search Box by Name, Phone, or Patient ID */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div style={{
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'center',
                  background: '#F8FAFC',
                  borderRadius: '12px',
                  border: searchTerm ? '1.5px solid #2563EB' : '1.5px solid #CBD5E1',
                  boxShadow: searchTerm ? '0 0 0 3px rgba(37,99,235,0.1)' : 'none',
                  transition: 'all 0.15s'
                }}>
                  <Search size={15} color={searchTerm ? "#2563EB" : "#64748B"} style={{ position: 'absolute', left: '12px' }} />
                  <input 
                    type="text" 
                    placeholder="Search in this date's queue..." 
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '9px 32px 9px 34px',
                      borderRadius: '12px',
                      border: 'none',
                      outline: 'none',
                      fontSize: '12px',
                      fontWeight: 600,
                      color: '#0F172A',
                      background: 'transparent'
                    }}
                  />
                  {searchTerm && (
                    <button
                      onClick={() => setSearchTerm('')}
                      style={{
                        position: 'absolute',
                        right: '10px',
                        background: 'transparent',
                        border: 'none',
                        color: '#94A3B8',
                        fontSize: '12px',
                        cursor: 'pointer',
                        padding: '2px 4px'
                      }}
                    >
                      ✕
                    </button>
                  )}
                </div>
                {searchTerm && (
                  <div style={{ fontSize: '10px', fontWeight: 700, color: '#2563EB', paddingLeft: '4px' }}>
                    🔍 Found {filteredAppts.length} of {activeAppts.length} visits for this date
                  </div>
                )}
              </div>

              {filteredAppts.length === 0 ? (
                <div style={{ padding: '30px', textAlign: 'center', color: '#64748B', background: '#F8FAFC', borderRadius: '12px', border: '1px dashed #CBD5E1', fontSize: '12px', fontWeight: 600 }}>
                  No appointments for {selectedDate || 'today'}.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '58vh' }}>
                  {filteredAppts.map(appt => {
                    const isSelected = selectedAppointment?.id === appt.id;
                    const isCompleted = appt.status === 'COMPLETED' || appt.status === 'CONSULTATION_FINISHED';
                    const isInConsult = appt.status === 'IN_CONSULTATION';
                    const isMissed = appt.status === 'MISSED';
                    const isCancelled = appt.status === 'CANCELLED';
                    const isRescheduled = appt.status === 'RESCHEDULED';

                    return (
                      <div 
                        key={appt.id}
                        onClick={() => {
                          setSelectedAppointment(appt);
                          if (isCompleted) {
                            setHistoryModalAppt(appt);
                          }
                        }}
                        style={{
                          background: isSelected ? '#EFF6FF' : '#FFFFFF',
                          border: `1.5px solid ${isSelected ? '#2563EB' : isCompleted ? '#BBF7D0' : isMissed ? '#FECACA' : isCancelled ? '#E2E8F0' : isInConsult ? '#FECACA' : '#DBEAFE'}`,
                          borderLeft: `4px solid ${isSelected ? '#2563EB' : isCompleted ? '#16A34A' : isMissed ? '#DC2626' : isCancelled ? '#94A3B8' : isInConsult ? '#DC2626' : '#3B82F6'}`,
                          borderRadius: '14px', padding: '14px', cursor: 'pointer',
                          transition: 'all 0.2s', boxShadow: isSelected ? '0 4px 14px rgba(37,99,235,0.12)' : '0 2px 6px rgba(15,23,42,0.03)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <div style={{ fontWeight: 800, fontSize: '14px', color: '#0F172A' }}>
                              {appt.patient_name || 'Patient'}
                            </div>
                            {appt.booked_by_name && appt.booked_by_name !== appt.patient_name && (
                              <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>
                                👤 Booked by: {appt.booked_by_name}
                              </div>
                            )}
                            <div style={{ fontSize: '11px', color: '#64748B', marginTop: '4px', fontWeight: 700, wordBreak: 'break-all' }}>
                              ID: <strong style={{ color: '#2563EB' }}>{formatPatientId(appt.patient_id || appt.id)}</strong> • 📞 {appt.patient_phone || 'N/A'}
                            </div>
                            <div style={{ fontSize: '11px', color: '#475569', marginTop: '3px', fontWeight: 700 }}>
                              Slot: <strong style={{ color: '#0F172A' }}>{formatSlotTime(appt)}</strong>
                            </div>
                          </div>
                          <span style={{ 
                            background: isCompleted ? '#DCFCE7' : isMissed ? '#FEE2E2' : isCancelled ? '#F1F5F9' : isRescheduled ? '#EFF6FF' : isInConsult ? '#FEE2E2' : '#FEF3C7',
                            color: isCompleted ? '#15803D' : isMissed ? '#DC2626' : isCancelled ? '#64748B' : isRescheduled ? '#2563EB' : isInConsult ? '#DC2626' : '#B45309',
                            border: `1px solid ${isCompleted ? '#86EFAC' : isMissed ? '#FECACA' : isCancelled ? '#CBD5E1' : isRescheduled ? '#BFDBFE' : isInConsult ? '#FECACA' : '#FDE68A'}`,
                            padding: '4px 8px', borderRadius: '8px', fontSize: '10px', fontWeight: 800
                          }}>
                            {isCompleted ? '✓ FINISHED' : isMissed ? '⚠️ MISSED' : isCancelled ? '❌ CANCELLED' : isRescheduled ? '🔄 RESCHEDULED' : isInConsult ? '🔴 IN CONSULT' : '🟡 WAITING'}
                          </span>
                        </div>

                        {/* Patient Mentioned Problem / Chief Complaint */}
                        <div style={{
                          marginTop: '8px',
                          padding: '6px 10px',
                          background: isSelected ? '#DBEAFE' : '#F8FAFC',
                          borderRadius: '8px',
                          border: `1px solid ${isSelected ? '#93C5FD' : '#E2E8F0'}`,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '11px'
                        }}>
                          <span style={{ fontWeight: 800, color: '#475569', whiteSpace: 'nowrap' }}>🩺 Problem:</span>
                          <span style={{ fontWeight: 700, color: '#1E40AF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {appt.reason || 'General Health Consultation'}
                          </span>
                        </div>

                        {isCompleted && (
                          <div style={{ marginTop: '8px', fontSize: '11px', color: '#2563EB', fontWeight: 800, textDecoration: 'underline', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <FileText size={12} /> View Prescription History
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* COLUMN 3: ACTIVE PATIENT EXAMINATION PANEL */}
            <div style={{ background: '#FFFFFF', borderRadius: '20px', border: '1.5px solid #E2E8F0', padding: '24px', display: 'flex', flexDirection: 'column', boxShadow: '0 4px 16px rgba(15,23,42,0.03)' }}>
              {!selectedAppointment ? (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748B', textAlign: 'center' }}>
                  <div style={{ fontSize: '48px', marginBottom: '12px' }}>🩺</div>
                  <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#0F172A', margin: 0 }}>Select a Patient from Queue</h3>
                  <p style={{ fontSize: '13px', color: '#64748B', marginTop: '4px', maxWidth: '380px', lineHeight: 1.5 }}>
                    Click any waiting patient card on the left to examine AI Voice Intake summary and finish consultation.
                  </p>
                </div>
              ) : (() => {
                const selectedIsCompleted = selectedAppointment.status === 'COMPLETED' || selectedAppointment.status === 'CONSULTATION_FINISHED';
                const selectedIsMissed = selectedAppointment.status === 'MISSED';
                const selectedIsCancelled = selectedAppointment.status === 'CANCELLED';

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between' }}>
                    <div>
                      {/* Patient Information Banner */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1.5px solid #F1F5F9', paddingBottom: '16px', marginBottom: '20px' }}>
                        <div>
                          <h2 style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                            CONSULTATION: {selectedAppointment.patient_name}
                          </h2>
                          {selectedAppointment.booked_by_name && selectedAppointment.booked_by_name !== selectedAppointment.patient_name && (
                            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 700, marginTop: '2px' }}>
                              👤 Booked by: <strong style={{ color: '#475569' }}>{selectedAppointment.booked_by_name}</strong> (Account Owner)
                            </div>
                          )}
                          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px', fontWeight: 600 }}>
                            Patient ID: <strong style={{ color: '#2563EB' }}>{formatPatientId(selectedAppointment.patient_id || selectedAppointment.id)}</strong> | 📞 {selectedAppointment.patient_phone} | Slot: <strong style={{ color: '#0F172A' }}>{formatSlotTime(selectedAppointment)}</strong>
                          </div>
                        </div>
                        <span style={{ 
                          background: selectedIsCompleted ? '#DCFCE7' : selectedIsMissed ? '#FEE2E2' : selectedIsCancelled ? '#F1F5F9' : '#FEF3C7',
                          color: selectedIsCompleted ? '#166534' : selectedIsMissed ? '#DC2626' : selectedIsCancelled ? '#64748B' : '#92400E',
                          border: `1px solid ${selectedIsCompleted ? '#86EFAC' : selectedIsMissed ? '#FECACA' : selectedIsCancelled ? '#CBD5E1' : '#FDE68A'}`,
                          padding: '6px 12px', borderRadius: '8px', fontSize: '11px', fontWeight: 800
                        }}>
                          {selectedAppointment.status || 'WAITING'}
                        </span>
                      </div>

                      {/* Missed or Cancelled Alert Banner */}
                      {(selectedIsMissed || selectedIsCancelled) && (
                        <div style={{ background: '#FEE2E2', border: '1.5px solid #FECACA', borderRadius: '14px', padding: '14px 16px', color: '#991B1B', fontSize: '13px', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '18px' }}>⚠️</span>
                          <div>
                            This appointment is marked as <strong>{selectedAppointment.status}</strong>. Consultation cannot be completed unless the patient reschedules or is checked in by receptionist.
                          </div>
                        </div>
                      )}

                      {/* 🤖 AI INTAKE SUMMARY CARD */}
                      <div style={{ background: 'linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 100%)', border: '1.5px solid #BFDBFE', borderRadius: '16px', padding: '18px', marginBottom: '20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#1E40AF', fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', marginBottom: '10px' }}>
                          🤖 AI VOICE INTAKE SUMMARY & CHIEF COMPLAINT
                        </div>

                        <div style={{ fontSize: '13px', color: '#0F172A', fontWeight: 600, lineHeight: 1.6, background: '#FFFFFF', padding: '14px', borderRadius: '12px', border: '1px solid #DBEAFE' }}>
                          {selectedAppointment.ai_intake_summary || selectedAppointment.notes || 'Patient reported symptoms during AI Voice call booking. No secondary complications logged.'}
                        </div>
                      </div>

                      <div style={{ background: '#F8FAFC', border: '1.5px solid #E2E8F0', borderRadius: '14px', padding: '14px', color: '#475569', fontSize: '12px', fontWeight: 600, lineHeight: 1.5 }}>
                        ℹ️ Examine patient physically, write prescription on physical slip, and click <strong>Finish Consultation</strong>. Receptionist will digitize prescription details & dispatch WhatsApp PDF receipt.
                      </div>
                    </div>

                    {/* SINGLE MAIN ACTION BUTTON: FINISH CONSULTATION */}
                    <div style={{ borderTop: '1.5px solid #F1F5F9', paddingTop: '18px', marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
                      <button 
                        onClick={() => handleCompleteConsultation(selectedAppointment.id)}
                        disabled={selectedIsCompleted || selectedIsMissed || selectedIsCancelled}
                        style={{
                          background: selectedIsCompleted ? '#CBD5E1' : (selectedIsMissed || selectedIsCancelled) ? '#F1F5F9' : 'linear-gradient(135deg, #059669 0%, #047857 100%)',
                          color: (selectedIsMissed || selectedIsCancelled) ? '#94A3B8' : selectedIsCompleted ? '#475569' : '#FFFFFF',
                          border: (selectedIsMissed || selectedIsCancelled) ? '1.5px solid #CBD5E1' : 'none',
                          borderRadius: '12px',
                          padding: '13px 28px', fontSize: '14px', fontWeight: 800,
                          cursor: (selectedIsCompleted || selectedIsMissed || selectedIsCancelled) ? 'not-allowed' : 'pointer',
                          boxShadow: (selectedIsCompleted || selectedIsMissed || selectedIsCancelled) ? 'none' : '0 4px 16px rgba(5,150,105,0.35)',
                          transition: 'all 0.2s'
                        }}
                      >
                        {selectedIsCompleted 
                          ? '✓ Consultation Finished & Sent to Receptionist' 
                          : (selectedIsMissed || selectedIsCancelled) 
                            ? `⚠️ Consultation Unavailable (Patient ${selectedAppointment.status})` 
                            : '✅ Finish Consultation & Send to Receptionist →'}
                      </button>
                    </div>

                  </div>
                );
              })()}
            </div>
          </>
        )}

        {/* VIEW B: APPLY LEAVE WORKSTATION (PERSISTENT SIDEBAR INTEGRATED) */}
        {currentTab === 'doctor_leaves' && (
          <div style={{ background: '#FFFFFF', borderRadius: '20px', border: '1.5px solid #E2E8F0', padding: '28px', display: 'flex', flexDirection: 'column', gap: '24px', boxShadow: '0 4px 16px rgba(15,23,42,0.03)' }}>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 900, color: '#0F172A', margin: 0 }}>🏖️ Apply Doctor Leave</h2>
              <p style={{ fontSize: '13px', color: '#64748B', margin: '4px 0 0 0', fontWeight: 600 }}>Submit leave applications to Hospital Administrator for approval.</p>
            </div>

            {leaveSuccess && <div style={{ color: '#166534', background: '#DCFCE7', padding: '12px 16px', borderRadius: '12px', fontSize: '13px', fontWeight: 700, border: '1px solid #BBF7D0' }}>✅ {leaveSuccess}</div>}
            {leaveError && <div style={{ color: '#DC2626', background: '#FEE2E2', padding: '12px 16px', borderRadius: '12px', fontSize: '13px', fontWeight: 700, border: '1px solid #FECACA' }}>⚠️ {leaveError}</div>}

            {/* Leave Application Form */}
            <form onSubmit={handleApplyLeave} style={{ background: '#F8FAFC', border: '1.5px solid #E2E8F0', borderRadius: '16px', padding: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr auto', gap: '14px', alignItems: 'end' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>Start Date *</label>
                <input type="date" value={leaveStartDate} onChange={e => setLeaveStartDate(e.target.value)} required style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 700 }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>End Date *</label>
                <input type="date" value={leaveEndDate} onChange={e => setLeaveEndDate(e.target.value)} required style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 700 }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#0F172A', marginBottom: '6px' }}>Reason for Leave</label>
                <input type="text" placeholder="e.g. Medical Conference / Personal Leave" value={leaveReason} onChange={e => setLeaveReason(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 600 }} />
              </div>
              <button type="submit" style={{ background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', color: '#FFFFFF', border: 'none', borderRadius: '10px', padding: '11px 20px', fontSize: '13px', fontWeight: 800, cursor: 'pointer', height: '42px' }}>
                + Submit Leave Request
              </button>
            </form>

            {/* My Leave Applications Table */}
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A', marginBottom: '14px' }}>📋 My Leave Applications</h3>
              <div style={{ borderRadius: '14px', border: '1.5px solid #E2E8F0', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ background: '#F8FAFC', borderBottom: '1.5px solid #E2E8F0', color: '#475569', textAlign: 'left' }}>
                      <th style={{ padding: '12px 16px', fontWeight: 800 }}>Start Date</th>
                      <th style={{ padding: '12px 16px', fontWeight: 800 }}>End Date</th>
                      <th style={{ padding: '12px 16px', fontWeight: 800 }}>Reason</th>
                      <th style={{ padding: '12px 16px', fontWeight: 800 }}>Status</th>
                      <th style={{ padding: '12px 16px', fontWeight: 800 }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leavesList.filter(l => l.doctor_id === userId).length === 0 ? (
                      <tr>
                        <td colSpan="5" style={{ padding: '24px', textAlign: 'center', color: '#64748B', fontWeight: 600 }}>No leave applications submitted yet.</td>
                      </tr>
                    ) : (
                      leavesList.filter(l => l.doctor_id === userId).map(leave => (
                        <tr key={leave.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                          <td style={{ padding: '12px 16px', fontWeight: 700 }}>{leave.start_date}</td>
                          <td style={{ padding: '12px 16px', fontWeight: 700 }}>{leave.end_date}</td>
                          <td style={{ padding: '12px 16px', color: '#334155' }}>{leave.reason || 'Personal'}</td>
                          <td style={{ padding: '12px 16px' }}>
                            <span style={{
                              padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 800,
                              background: leave.status === 'APPROVED' ? '#DCFCE7' : leave.status === 'REJECTED' ? '#FEE2E2' : '#FEF3C7',
                              color: leave.status === 'APPROVED' ? '#166534' : leave.status === 'REJECTED' ? '#DC2626' : '#92400E'
                            }}>
                              {leave.status}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {leave.status === 'PENDING' && (
                              <button onClick={() => handleDeleteLeave(leave.id)} style={{ background: '#FEE2E2', border: '1px solid #FECACA', color: '#DC2626', borderRadius: '6px', padding: '4px 10px', fontSize: '11px', fontWeight: 800, cursor: 'pointer' }}>
                                Cancel Request
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

      </div>

      {/* ── HISTORICAL COMPLETED PRESCRIPTION & DIAGNOSIS MODAL ── */}
      {historyModalAppt && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '20px' }}>
          <div className="animate-fade-scale" style={{ background: '#FFFFFF', borderRadius: '24px', width: '100%', maxWidth: '580px', padding: '28px', boxShadow: '0 20px 45px rgba(15, 23, 42, 0.25)', border: '1.5px solid #DBEAFE' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #F1F5F9', paddingBottom: '12px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '17px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                  📄 Medical Record & Completed Prescription
                </h3>
                <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 700, marginTop: '2px' }}>
                  {historyModalAppt.patient_name} (ID: {historyModalAppt.patient_id || historyModalAppt.id})
                </div>
              </div>
              <button onClick={() => setHistoryModalAppt(null)} style={{ background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: '#64748B', fontWeight: 800 }}>✕</button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ background: '#F8FAFC', padding: '12px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
                <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 800, textTransform: 'uppercase' }}>Clinical Notes / Observations</div>
                <div style={{ fontSize: '13px', color: '#0F172A', fontWeight: 600, marginTop: '4px' }}>
                  {historyModalAppt.clinical_notes || historyModalAppt.notes || 'No clinical notes recorded.'}
                </div>
              </div>

              <div style={{ background: '#EFF6FF', padding: '12px', borderRadius: '12px', border: '1px solid #BFDBFE' }}>
                <div style={{ fontSize: '11px', color: '#1E40AF', fontWeight: 800, textTransform: 'uppercase' }}>Prescription & Medicines List (Rx)</div>
                <div style={{ fontSize: '13px', color: '#0F172A', fontWeight: 600, marginTop: '4px', whiteSpace: 'pre-wrap' }}>
                  {historyModalAppt.prescription || 'No medicines logged yet.'}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#64748B', fontWeight: 600 }}>
                <span>Follow-up Date: <strong>{historyModalAppt.follow_up_date || 'None'}</strong></span>
                <span>Visit Status: <strong style={{ color: '#166534' }}>COMPLETED</strong></span>
              </div>
            </div>

            <button 
              onClick={() => setHistoryModalAppt(null)} 
              style={{ width: '100%', padding: '12px', borderRadius: '10px', background: '#2563EB', color: '#FFFFFF', border: 'none', fontWeight: 800, fontSize: '14px', marginTop: '18px', cursor: 'pointer' }}
            >
              Close History Record
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
