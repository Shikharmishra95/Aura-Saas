import React, { useState, useEffect, useCallback } from 'react';
import { Calendar, PlusCircle, RefreshCw } from 'lucide-react';
import { formatDoctorTimingsToEnglish, safeFormatDate, translateScheduleString } from '../../utils/formatters';

export default function ReceptionistDashboard({
  activeTab,
  setActiveTab,
  token,
  userRole,
  hospitalId,
  lang,
  t,
  API_BASE,
  activeHospital,
  hospitalsList,
  doctorsList,
  appointmentsList,
  leavesList,
  fetchLeaves,
  refreshTrigger,
  setRefreshTrigger,
  selectedScheduleDate,
  setSelectedScheduleDate,
  currentTime,
  onOpenPrescriptionModal,
  onOpenRescheduleModal,
  onOpenCancelModal,
  onOpenUpgradeModal,
  handleApproveLeave,
  handleRejectLeave,
  handleDeleteLeave,
  patientSearchQuery,
  setPatientSearchQuery,
  patientSearchResults,
  setPatientSearchResults,
  patientSearchLoading,
  patientSearchError,
  handleSearchPatients
}) {
  // Local state for Receptionist view
  const [receptionistTimeRange, setReceptionistTimeRange] = useState('today');

  // Booking Form State
  const [patientFirstName, setPatientFirstName] = useState('');
  const [patientLastName, setPatientLastName] = useState('');
  const [patientPhone, setPatientPhone] = useState('');
  const [patientGender, setPatientGender] = useState('Male');
  const [patientDob, setPatientDob] = useState('1995-01-01');
  const [bookingDoctorId, setBookingDoctorId] = useState('');
  const [bookingDate, setBookingDate] = useState(() => new Date().toLocaleDateString('en-CA'));
  const [bookingTime, setBookingTime] = useState('');
  const [bookingReason, setBookingReason] = useState('General Consultation');
  const [receptionistPaymentMode, setReceptionistPaymentMode] = useState('ONLINE');
  const [bookingSuccessMsg, setBookingSuccessMsg] = useState('');
  const [bookingErrorMsg, setBookingErrorMsg] = useState('');
  const [newBookingBookedSlots, setNewBookingBookedSlots] = useState([]);
  const [newBookingAllSlots, setNewBookingAllSlots] = useState([]);
  const [selectedNewBookingSlot, setSelectedNewBookingSlot] = useState('');

  const convertSlotTo24h = (slotStr) => {
    const timeClean = slotStr.replace(/(AM|PM)/i, '').trim();
    const isPm = slotStr.toLowerCase().includes('pm');
    let [hours, minutes] = timeClean.split(':').map(Number);
    if (isPm && hours !== 12) hours += 12;
    if (!isPm && hours === 12) hours = 0;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
  };

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
      console.error('Error fetching booked slots for new booking:', err);
    }
  }, [token, API_BASE]);

  useEffect(() => {
    if (bookingDoctorId && bookingDate) {
      handleNewBookingDateOrDoctorChange(bookingDoctorId, bookingDate);
    } else {
      setNewBookingBookedSlots([]);
      setNewBookingAllSlots([]);
    }
  }, [bookingDoctorId, bookingDate, refreshTrigger, handleNewBookingDateOrDoctorChange]);

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
      alert('Network error.');
    }
  };

  const handleBulkCancel = async (docId, dateStr) => {
    const reason = window.prompt('Reason for cancelling all appointments for this doctor today (e.g. Doctor Absent):', 'Doctor is unavailable today');
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
        alert('Failed to bulk cancel appointments.');
      }
    } catch (e) {
      alert('Network error.');
    }
  };

  return (
    <div style={{ display: 'flex', flexGrow: 1, width: '100%' }}>
      {/* 📌 Left Vertical Sidebar for Receptionist Role */}
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

      {/* Content viewports */}
      <div style={{ flexGrow: 1, padding: '24px', overflowY: 'auto' }}>
                  {activeTab === 'overview' && (
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
                              onClick={onOpenUpgradeModal}
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
                                                    onClick={() => onOpenPrescriptionModal(appt, true)}
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
                                                       onClick={() => onOpenRescheduleModal(appt)} 
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
                                                       onClick={() => onOpenPrescriptionModal(appt, false)}
                                                       style={{ padding: '6px 14px', fontSize: '12px', borderRadius: '8px', background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', border: 'none', color: '#FFFFFF', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)', transition: 'all 0.15s' }}
                                                     >
                                                       🩺 {lang === 'hi' ? 'पर्चा लिखें एवं पूरा करें →' : 'Complete & Add Prescription →'}
                                                     </button>
                                                   )}

                                                   {/* 3. Secondary Actions Row (Reschedule / Missed / Cancel) */}
                                                   <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                                     <button 
                                                       onClick={() => onOpenRescheduleModal(appt)} 
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
                                                       onClick={() => onOpenCancelModal(appt)}
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

              {activeTab === 'new_booking' && (
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

              {activeTab === 'patient_search' && (
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

              {activeTab === 'receptionist_leaves' && (
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
      </div>
    </div>
  );
}
