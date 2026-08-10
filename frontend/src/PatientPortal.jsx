import React, { useState, useEffect } from 'react';
import { Activity, Clock, Calendar, CheckCircle, Phone, User, FileText, ChevronRight, Download } from 'lucide-react';
import './PatientPortal.css'; // We'll create this or use App.css

const API_BASE = '/api/v1/patient';

const loadRazorpay = () => {
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

const TRANSLATIONS = {
  en: {
    welcome: "Welcome to",
    phoneLogin: "Enter Phone Number to login or register",
    sendOtp: "Send OTP",
    verifyOtp: "Verify OTP",
    upcomingApp: "Upcoming Appointments",
    historyApp: "Medical History",
    bookApp: "Book Appointment",
    noApp: "No upcoming appointments found.",
    opdFees: "OPD Fees",
    reason: "Reason",
    patientName: "Patient Name",
    patientAge: "Patient Age",
    step1: "Step 1: Choose Doctor & Department",
    step2: "Step 2: Select Date & Time Slot",
    step3: "Step 3: Tell Us Your Problem",
    step4: "Step 4: Payment",
    payOnline: "Pay Online",
    payReception: "Pay at Reception",
    downloadPresc: "Download Prescription",
    logout: "Logout",
    phone: "Phone Number",
    otp: "Enter 6-digit OTP",
    submitting: "Submitting...",
    enterDetails: "Enter Patient Details",
    searchDoc: "Search Doctors...",
    selectDoc: "Select Doctor",
    age: "Age",
    status: "Status"
  },
  hi: {
    welcome: "आपका स्वागत है",
    phoneLogin: "लॉगिन या पंजीकरण के लिए अपना फ़ोन नंबर दर्ज करें",
    sendOtp: "ओटीपी भेजें",
    verifyOtp: "ओटीपी सत्यापित करें",
    upcomingApp: "आगामी अपॉइंटमेंट्स",
    historyApp: "मेडिकल हिस्ट्री",
    bookApp: "अपॉइंटमेंट बुक करें",
    noApp: "कोई आगामी अपॉइंटमेंट नहीं मिला।",
    opdFees: "ओपीडी फीस",
    reason: "कारण",
    patientName: "मरीज का नाम",
    patientAge: "मरीज की उम्र",
    step1: "चरण 1: डॉक्टर और विभाग चुनें",
    step2: "चरण 2: तारीख और समय स्लॉट चुनें",
    step3: "चरण 3: अपनी समस्या बताएं",
    step4: "चरण 4: भुगतान",
    payOnline: "ऑनलाइन भुगतान करें",
    payReception: "काउंटर पर भुगतान करें",
    downloadPresc: "प्रिस्क्रिप्शन डाउनलोड करें",
    logout: "लॉगआउट",
    phone: "फ़ोन नंबर",
    otp: "6-अंकों का ओटीपी दर्ज करें",
    submitting: "जमा किया जा रहा है...",
    enterDetails: "मरीज का विवरण दर्ज करें",
    searchDoc: "डॉक्टर खोजें...",
    selectDoc: "डॉक्टर चुनें",
    age: "उम्र",
    status: "स्थिति"
  }
};

export default function PatientPortal({ slug, lang = 'en' }) {
  const t = (key) => TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key] || key;

  const [hospital, setHospital] = useState(null);
  const [token, setToken] = useState(localStorage.getItem(`patient_token_${slug}`) || '');
  const [patient, setPatient] = useState(() => {
    try {
      const raw = localStorage.getItem(`patient_data_${slug}`);
      if (!raw || raw === 'undefined') return null;
      return JSON.parse(raw);
    } catch(e) { return null; }
  });
  const [loading, setLoading] = useState(true);
  
  // Auth state
  const [name, setName] = useState('');
  const [age, setAge] = useState('');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [step, setStep] = useState('phone'); // phone, otp, dashboard
  const [authError, setAuthError] = useState('');
  const [isNewUser, setIsNewUser] = useState(false);

  // Dashboard state
  const [activeTab, setActiveTab] = useState('upcoming'); // upcoming, history, book
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  
  // Booking state
  const [bookStep, setBookStep] = useState(1); // 1: dept/doc, 2: slot, 3: reason, 4: payment
  const [selectedDept, setSelectedDept] = useState('');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [paymentModeSelection, setPaymentModeSelection] = useState('ONLINE');
  
  const getMinDate = () => new Date().toISOString().split('T')[0];
  const getMaxDate = () => {
    const d = new Date();
    d.setDate(d.getDate() + 2);
    return d.toISOString().split('T')[0];
  };

  const [selectedDate, setSelectedDate] = useState(getMinDate());
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [reason, setReason] = useState('');
  const [patientName, setPatientName] = useState('');
  const [patientAge, setPatientAge] = useState('');
  const [savedPatients, setSavedPatients] = useState([]);
  const [bookedAppointmentId, setBookedAppointmentId] = useState(null);
  const [viewingPrescription, setViewingPrescription] = useState(null);

  // Profile State
  const [profileData, setProfileData] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);

  const [editingProfile, setEditingProfile] = useState(false);
  const [editName, setEditName] = useState('');
  const [editGender, setEditGender] = useState('Male');
  const [editDob, setEditDob] = useState('');

  const safeJsonParse = (str, fallback = null) => {
    if (!str || str === 'undefined') return fallback;
    try {
      return JSON.parse(str);
    } catch (e) {
      return fallback;
    }
  };

  const fetchDoctors = async () => {
    if (!hospital || !hospital.id) return;
    try {
      const res = await fetch(`${API_BASE}/doctors?hospital_id=${hospital.id}`);
      if (res.ok) {
        const docs = await res.json();
        setDoctors(Array.isArray(docs) ? docs : []);
      }
    } catch (e) {
      console.error("Failed to fetch doctors", e);
    }
  };

  const fetchProfile = async () => {
    if (!token) return;
    setProfileLoading(true);
    try {
      const res = await fetch(`${API_BASE}/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProfileData(data);
        if (data.name) {
          const newName = data.name;
          setPatient(prev => ({ ...(prev || {}), name: newName }));
        }
      }
    } catch (e) {
      console.error("Failed to fetch profile", e);
    } finally {
      setProfileLoading(false);
    }
  };

  const fetchHospitalData = async () => {
    if (!slug) return;
    try {
      const res = await fetch(`${API_BASE}/hospital/${slug}`);
      if (res.ok) {
        setHospital(await res.json());
      } else {
        setHospital({ error: 'Hospital not found' });
      }
    } catch (e) {
      console.error("Failed to fetch hospital data", e);
      setHospital({ error: 'Failed to fetch hospital' });
    } finally {
      setLoading(false);
    }
  };

  const requestOTP = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, hospital_id: hospital?.id })
      });
      const data = await res.json();
      if (res.ok) {
        setIsNewUser(data.is_new_user);
        setStep('otp');
      } else {
        setAuthError(data.detail || 'Failed to send OTP');
      }
    } catch (e) {
      setAuthError('Network error');
    }
  };

  const verifyOTP = async (e) => {
    e.preventDefault();
    if (isNewUser && !name) {
      setAuthError('Full Name is required for new registration.');
      return;
    }
    if (isNewUser && (!age || parseInt(age) < 1 || parseInt(age) > 120)) {
      setAuthError('Please enter a valid age (1-120).');
      return;
    }
    
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, otp, hospital_id: hospital?.id, name: isNewUser ? name : null, age: isNewUser ? parseInt(age) : null })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem(`patient_token_${slug}`, data.access_token);
        localStorage.setItem(`patient_data_${slug}`, JSON.stringify(data.patient));
        setToken(data.access_token);
        setPatient(data.patient);
      } else {
        setAuthError(data.detail || 'Invalid OTP');
      }
    } catch (e) {
      setAuthError('Network error');
    }
  };

  const logout = () => {
    localStorage.removeItem(`patient_token_${slug}`);
    localStorage.removeItem(`patient_data_${slug}`);
    setToken('');
    setPatient(null);
    setStep('phone');
  };

  const handleSavePrimaryProfile = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: editName,
          gender: editGender,
          date_of_birth: editDob || null
        })
      });
      if (res.ok) {
        alert("Primary profile updated successfully!");
        setEditingProfile(false);
        fetchProfile();
      } else {
        alert("Failed to update profile.");
      }
    } catch (e) {
      alert("Network error.");
    }
  };



  useEffect(() => {
    setToken(localStorage.getItem(`patient_token_${slug}`) || '');
    setPatient(safeJsonParse(localStorage.getItem(`patient_data_${slug}`), null));
    setStep('phone');
    setName('');
    setPhone('');
    setOtp('');
    setIsNewUser(false);
    fetchHospitalData();
  }, [slug]);

  useEffect(() => {
    if (token) {
      setStep('dashboard');
      fetchDoctors();
      fetchProfile();
      fetchAppointments();
    }
  }, [token, hospital]);

  useEffect(() => {
    if (token) {
      fetchAppointments();
    }
  }, [token]);

  const fetchAppointments = async () => {
    try {
      const res = await fetch(`${API_BASE}/appointments`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const appts = await res.json();
        setAppointments(Array.isArray(appts) ? appts : []);
      }
    } catch (e) {}
  };

  const fetchSlots = async (docId, date) => {
    try {
      const res = await fetch(`${API_BASE}/doctors/${docId}/slots?date=${date}`);
      if (res.ok) {
        const data = await res.json();
        setSlots(data.slots || []);
      }
    } catch (e) {}
  };

  const handleViewPrescription = async (appointmentId) => {
    try {
      const res = await fetch(`${API_BASE}/appointments/${appointmentId}/prescription`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.has_prescription) {
          setViewingPrescription(data);
        } else {
          alert("No prescription available for this appointment yet.");
        }
      } else {
        alert("Failed to fetch prescription.");
      }
    } catch (e) {
      alert("Network error.");
    }
  };

  const handleBook = async (paymentMode = 'ONLINE') => {
    if (typeof paymentMode !== 'string') {
        paymentMode = 'ONLINE';
    }
    try {
      const datetimeStr = `${selectedDate}T${selectedSlot}:00`;
      const targetPatientId = patient?.id;
      
      let finalReason = reason;
      if (patientName) {
        finalReason = `For: ${patientName} (Age: ${patientAge}) | Reason: ${reason}`;
      }

      const res = await fetch(`${API_BASE}/appointments`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          hospital_id: hospital.id,
          doctor_id: selectedDoc.id,
          patient_id: targetPatientId,
          appointment_datetime: datetimeStr,
          reason: finalReason,
          payment_mode: paymentMode
        })
      });
      const data = await res.json();
      if (res.ok) {
        if (paymentModeSelection === 'ONLINE') {
            const resLoaded = await loadRazorpay();
            if (!resLoaded) {
                alert("Failed to load Razorpay SDK. Please check your connection.");
                return;
            }
            const options = {
                key: 'rzp_test_TDfSGFZwtVgpme',
                amount: (selectedDoc.opd_fees || 500) * 100, // in paise
                currency: 'INR',
                name: hospital.name,
                description: 'Consultation Fee',
                handler: async function (response) {
                    // Call backend to confirm payment
                    try {
                        const confirmRes = await fetch(`${API_BASE}/appointments/${data.appointment_id}/confirm-payment`, {
                            method: 'POST',
                            headers: { 
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${token}`
                            },
                            body: JSON.stringify({ payment_mode: 'ONLINE' })
                        });
                        if (confirmRes.ok) {
                            alert("Payment Successful! WhatsApp confirmation sent.");
                            setBookStep(1);
                            setActiveTab('upcoming');
                            fetchAppointments();
                        } else {
                            alert("Payment received, but confirmation failed. Please contact reception.");
                        }
                    } catch(e) {
                        alert("Network error confirming payment.");
                    }
                },
                prefill: {
                    name: patientName || patient?.name,
                    contact: patient?.phone
                },
                theme: {
                    color: '#0f3276'
                }
            };
            const rzp = new window.Razorpay(options);
            rzp.on('payment.failed', function (response){
                alert("Payment Failed: " + response.error.description);
            });
            rzp.open();
        } else {
            alert('Booking Confirmed! Please pay at the hospital counter. WhatsApp confirmation sent.');
            setBookStep(1);
            setActiveTab('upcoming');
            fetchAppointments();
        }
      } else {
        console.error("Booking Error:", data);
        alert(`Booking failed: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (e) {
      console.error(e);
      alert("Network error while booking");
    }
  };

  const confirmPayment = async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/appointments/${bookedAppointmentId}/confirm-payment`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ payment_mode: mode })
      });
      if (res.ok) {
        alert(mode === 'ONLINE' ? 'Payment Successful!' : 'Booking Confirmed! Please pay at the clinic.');
        setBookStep(1);
        setActiveTab('upcoming');
        fetchAppointments(); // Re-fetch to show new booking
      } else {
        fetchAppointments();
      }
    } catch(e) {}
  };

  if (loading) return <div className="p-loading">Loading...</div>;
  if (!hospital || hospital.error) return <div className="p-error">Hospital not found (404)</div>;

  return (
    <div className="patient-portal">
      {/* Dynamic Branding Header */}
      <header className="p-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="p-brand">
          <Activity size={24} className="p-icon" />
          <span>{hospital.name}</span>
        </div>

        {token && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>

            <button onClick={logout} className="p-logout">{t('logout')}</button>
          </div>
        )}
      </header>

      <main className="p-main">
        {!token ? (
          <div className="p-auth-container">
            <h2>{t('welcome')} {hospital.name}</h2>
            <p>{t('phoneLogin')}</p>
            
            {step === 'phone' && (
              <form onSubmit={requestOTP} className="p-form">
                <div className="p-input-group">
                  <label>{t('phone')}</label>
                  <input type="tel" required value={phone} onChange={e => setPhone(e.target.value)} placeholder="e.g. 9532399202" />
                </div>
                {authError && <div className="p-error-text">{authError}</div>}
                <button type="submit" className="p-btn p-btn-primary">{t('sendOtp')}</button>
                <div className="p-note">For demo MVP, use any registered phone and OTP: 1234</div>
              </form>
            )}

            {step === 'otp' && (
              <form onSubmit={verifyOTP} className="p-form">
                {isNewUser && (
                  <>
                    <div className="p-input-group">
                      <label>{t('name')}</label>
                      <input type="text" required={isNewUser} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Rahul Kumar" />
                    </div>
                    <div className="p-input-group">
                      <label>{t('age')}</label>
                      <input type="number" required={isNewUser} min="1" max="120" value={age} onChange={e => setAge(e.target.value)} placeholder="e.g. 28" />
                    </div>
                  </>
                )}
                <div className="p-input-group">
                  <label>Enter OTP sent to {phone}</label>
                  <input type="text" required value={otp} onChange={e => setOtp(e.target.value)} placeholder="1234" />
                </div>
                {authError && <div className="p-error-text">{authError}</div>}
                <button type="submit" className="p-btn p-btn-primary">{t('verifyOtp')}</button>
                <button type="button" onClick={() => setStep('phone')} className="p-btn p-btn-text">{t('cancel')}</button>
              </form>
            )}
          </div>
        ) : (
          <div className="p-dashboard">
            <div className="p-welcome" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3>Hello, {patient?.name} 👋</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#64748b' }}>
                  {lang === 'hi' ? 'अपने अपॉइंटमेंट और परिवार के रिकॉर्ड प्रबंधित करें।' : 'Manage your appointments and family records.'}
                </p>
              </div>
            </div>

            <div className="p-tabs">
              <button className={activeTab === 'upcoming' ? 'active' : ''} onClick={() => setActiveTab('upcoming')}>{t('upcomingApp')}</button>
              <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}>{t('historyApp')}</button>
              <button className={activeTab === 'book' ? 'active' : ''} onClick={() => {setActiveTab('book'); setBookStep(1);}}>{t('bookApp')}</button>
              <button className={activeTab === 'profile' ? 'active' : ''} onClick={() => {setActiveTab('profile'); fetchProfile();}}>{lang === 'hi' ? 'प्रोफाइल और परिवार' : 'Profile & Family'}</button>
            </div>

            <div className="p-tab-content">
              {activeTab === 'upcoming' && (
                <div className="p-list">
                  {appointments.filter(a => ['SCHEDULED', 'PENDING_PAYMENT', 'RESCHEDULED', 'CONFIRMED'].includes(a.status)).length === 0 ? (
                    <div className="p-empty">{t('noApp')}</div>
                  ) : (
                    appointments.filter(a => ['SCHEDULED', 'PENDING_PAYMENT', 'RESCHEDULED', 'CONFIRMED'].includes(a.status)).map(a => (
                      <div key={a.id} className="p-card">
                        <div className="p-card-header">
                          <div>
                            <strong>{a.doctor_name}</strong>
                            <div style={{fontSize: '11px', marginTop: '6px'}}>
                              <span style={{ padding: '3px 8px', borderRadius: '12px', fontWeight: 600, backgroundColor: a.payment_status?.includes('PAID') ? '#dcfce7' : (a.payment_status === 'CASH' ? '#ffedd5' : '#fef9c3'), color: a.payment_status?.includes('PAID') ? '#166534' : (a.payment_status === 'CASH' ? '#9a3412' : '#854d0e') }}>
                                Payment: {a.payment_status?.includes('PAID') ? 'PAID ONLINE' : (a.payment_status === 'CASH' ? 'PAID CASH' : 'PENDING')}
                              </span>
                            </div>
                          </div>
                          <span className="p-status">{a.status}</span>
                        </div>
                        <div className="p-card-body">
                          <div><User size={14}/> <strong>Patient:</strong> {a.patient_name || patient?.name}</div>
                          <div><Calendar size={14}/> {new Date(a.datetime).toLocaleDateString()}</div>
                          <div><Clock size={14}/> {new Date(a.datetime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                          <div><FileText size={14}/> {a.reason}</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'history' && (
                <div className="p-list">
                  {appointments.filter(a => ['COMPLETED', 'CANCELLED', 'MISSED'].includes(a.status)).length === 0 ? (
                    <div className="p-empty">No history records.</div>
                  ) : (
                    appointments.filter(a => ['COMPLETED', 'CANCELLED', 'MISSED'].includes(a.status)).map(a => (
                    <div key={a.id} className="p-card p-history-card">
                      <div className="p-card-header">
                        <div>
                          <strong>{a.doctor_name}</strong>
                          <div className="p-date">{new Date(a.datetime).toLocaleDateString()}</div>
                          <div style={{fontSize: '11px', marginTop: '6px'}}>
                            <span style={{ padding: '3px 8px', borderRadius: '12px', fontWeight: 600, backgroundColor: a.payment_status?.includes('PAID') ? '#dcfce7' : (a.payment_status === 'CASH' ? '#ffedd5' : '#fef9c3'), color: a.payment_status?.includes('PAID') ? '#166534' : (a.payment_status === 'CASH' ? '#9a3412' : '#854d0e') }}>
                              Payment: {a.payment_status?.includes('PAID') ? 'PAID ONLINE' : (a.payment_status === 'CASH' ? 'PAID CASH' : 'PENDING')}
                            </span>
                          </div>
                        </div>
                        <span className="p-status" style={{ color: a.status === 'MISSED' ? '#ef4444' : 'inherit' }}>{a.status}</span>
                      </div>
                      <div className="p-card-body" style={{ marginTop: '8px' }}>
                        <div><User size={14}/> <strong>Patient:</strong> {a.patient_name || patient?.name}</div>
                        <div><FileText size={14}/> {a.reason}</div>
                      </div>
                      <div className="p-card-actions" style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                        {['COMPLETED'].includes(a.status) && (
                          <button className="p-btn-small" onClick={() => handleViewPrescription(a.id)}>
                            <Download size={14}/> View Prescription
                          </button>
                        )}
                        {a.status === 'MISSED' && a.can_reschedule && (
                          <button className="p-btn-small" style={{ backgroundColor: '#2563eb', color: '#fff' }} onClick={() => { setActiveTab('book'); setBookStep(1); }}>
                            🔄 Reschedule (Available within 48h)
                          </button>
                        )}
                      </div>
                    </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'book' && (
                <div className="p-booking-flow">
                  {bookStep === 1 && (
                    <div className="p-step">
                      <h4>{t('step1')}</h4>
                      <div className="p-doc-list">
                        {doctors.map(d => (
                          <div key={d.id} className={`p-doc-item ${selectedDoc?.id === d.id ? 'selected' : ''}`} onClick={() => setSelectedDoc(d)}>
                            <strong>Dr. {d.name}</strong>
                            <p style={{ color: '#047857', fontWeight: 600, fontSize: '13px' }}>{d.department_name}</p>
                            <p style={{ fontSize: '12px', marginTop: '6px' }}>🕒 {d.schedule}</p>
                            <p style={{ fontWeight: 600, marginTop: '4px' }}>₹{d.opd_fees} Consultation</p>
                          </div>
                        ))}
                      </div>
                      <button 
                        disabled={!selectedDoc} 
                        onClick={() => { setBookStep(2); fetchSlots(selectedDoc.id, selectedDate); }} 
                        className="p-btn p-btn-primary"
                      >Next</button>
                    </div>
                  )}

                  {bookStep === 2 && (
                    <div className="p-step">
                      <h4>{t('step2')}</h4>
                      <input type="date" value={selectedDate} onChange={e => {setSelectedDate(e.target.value); fetchSlots(selectedDoc.id, e.target.value);}} className="p-input" min={getMinDate()} max={getMaxDate()} />
                      
                      <div className="p-slot-grid">
                        {slots.length === 0 ? <p>No slots available</p> : slots.map((s, idx) => {
                          const slotVal = s.value || s.time; // Use value if present (24h format), else fallback
                          return (
                            <button 
                              key={idx} 
                              disabled={s.is_booked}
                              className={`p-slot-btn ${selectedSlot === slotVal ? 'selected' : ''} ${s.is_booked ? 'booked' : ''}`} 
                              onClick={() => setSelectedSlot(slotVal)}
                            >
                              {s.time}
                            </button>
                          );
                        })}
                      </div>

                      <div className="p-btn-row">
                        <button onClick={() => setBookStep(1)} className="p-btn p-btn-text">Back</button>
                        <button disabled={!selectedSlot} onClick={() => setBookStep(3)} className="p-btn p-btn-primary">Next</button>
                      </div>
                    </div>
                  )}

                  {bookStep === 3 && (
                    <div className="p-step">
                      <h4>{t('step3')}</h4>
                      <div className="p-summary">
                        <p><strong>Doctor:</strong> {selectedDoc.name}</p>
                        <p><strong>Date:</strong> {selectedDate}</p>
                        <p><strong>Time:</strong> {selectedSlot}</p>
                        <p><strong>Fees:</strong> ₹{selectedDoc.opd_fees}</p>
                      </div>

                      <div className="p-patient-selection">
                        <label className="p-label-bold">Who is this appointment for?</label>
                        <div className="p-saved-patients">
                           <button 
                             className={`p-saved-btn ${!patientName ? 'selected' : ''}`}
                             onClick={() => { setPatientName(''); setPatientAge(''); }}
                           >
                             Myself ({patient?.name})
                           </button>
                           {savedPatients.map((p, idx) => (
                             <button 
                               key={idx}
                               className={`p-saved-btn ${patientName === p.name ? 'selected' : ''}`}
                               onClick={() => { setPatientName(p.name); setPatientAge(p.age); }}
                             >
                               {p.name}
                             </button>
                           ))}
                           <button 
                             className={`p-saved-btn ${patientName && !savedPatients.find(x => x.name === patientName) ? 'selected' : ''}`}
                             onClick={() => { setPatientName('New Patient'); setPatientAge(''); }}
                           >
                             + Add New
                           </button>
                        </div>
                        
                        {patientName && (
                          <div className="p-new-patient-fields">
                            <input 
                              type="text" 
                              placeholder="Patient Name" 
                              className="p-input" 
                              value={patientName === 'New Patient' ? '' : patientName} 
                              onChange={e => setPatientName(e.target.value)} 
                            />
                            <input 
                              type="number" 
                              placeholder="Age" 
                              className="p-input" 
                              value={patientAge} 
                              onChange={e => setPatientAge(e.target.value)} 
                            />
                          </div>
                        )}
                      </div>

                      <textarea placeholder="Any symptoms or reason for visit?" value={reason} onChange={e => setReason(e.target.value)} className="p-input p-textarea" style={{marginTop: '16px'}}></textarea>
                      
                      <div className="p-payment-selection" style={{ marginTop: '20px', background: '#f8fafc', padding: '16px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                        <div style={{ fontSize: '14px', fontWeight: '600', color: '#0f172a', marginBottom: '12px' }}>Payment Option</div>
                        <div style={{ display: 'flex', gap: '20px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '14px', color: '#334155' }}>
                                <input type="radio" name="payMode" value="ONLINE" checked={paymentModeSelection === 'ONLINE'} onChange={() => setPaymentModeSelection('ONLINE')} style={{ accentColor: '#0f3276' }} />
                                Pay Online Now
                            </label>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '14px', color: '#334155' }}>
                                <input type="radio" name="payMode" value="COUNTER" checked={paymentModeSelection === 'COUNTER'} onChange={() => setPaymentModeSelection('COUNTER')} style={{ accentColor: '#0f3276' }} />
                                Pay at Hospital
                            </label>
                        </div>
                      </div>

                      <div className="p-btn-row" style={{marginTop: '16px'}}>
                        <button onClick={() => setBookStep(2)} className="p-btn p-btn-text">Back</button>
                         <button onClick={handleBook} className="p-btn p-btn-primary">{t('confirm')}</button>
                      </div>
                    </div>
                  )}

                  {bookStep === 4 && (
                    <div className="p-step p-payment-step">
                       <CheckCircle size={48} color="#10b981" style={{margin: '0 auto 16px', display: 'block'}} />
                       <h4 style={{textAlign: 'center'}}>Booking Initiated!</h4>
                       <p style={{textAlign: 'center', color: '#64748b', marginBottom: '24px'}}>How would you like to pay the ₹{selectedDoc?.opd_fees} fee?</p>
                       
                       <div className="p-btn-col">
                         <button onClick={() => confirmPayment('ONLINE')} className="p-btn p-btn-primary">Pay Online Now</button>
                         <button onClick={() => confirmPayment('CASH')} className="p-btn p-btn-outline">Pay Cash at Hospital</button>
                       </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'profile' && (
                <div className="p-profile-section" style={{ padding: '16px' }}>
                  {profileLoading ? (
                    <div>Loading Profile...</div>
                  ) : !profileData ? (
                    <div>Unable to load profile data.</div>
                  ) : (
                    <div>
                      <div className="p-card" style={{ padding: '20px', marginBottom: '20px', background: '#ffffff', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                          <h4 style={{ margin: 0, color: '#0f172a' }}>👤 Primary Account Details</h4>
                          <button 
                            className="p-btn-small" 
                            onClick={() => {
                              setEditingProfile(true);
                              setEditName(profileData.name);
                              setEditGender(profileData.gender || 'Male');
                              setEditDob(profileData.date_of_birth || '');
                            }}
                          >
                            Edit Profile
                          </button>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '14px', color: '#334155' }}>
                          <div><strong>Name:</strong> {profileData.name}</div>
                          <div><strong>Phone:</strong> {profileData.phone}</div>
                          <div><strong>Gender:</strong> {profileData.gender}</div>
                          <div><strong>Date of Birth / Age:</strong> {profileData.date_of_birth || 'Not Specified'}</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Edit Profile Modal */}
      {editingProfile && (
        <div className="p-modal-overlay">
          <div className="p-modal" style={{ maxWidth: '450px', width: '90%' }}>
            <div className="p-modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#0f172a' }}>Edit Primary Profile</h3>
              <button onClick={() => setEditingProfile(false)} className="p-btn-close" style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#64748b' }}>&times;</button>
            </div>
            <form onSubmit={handleSavePrimaryProfile} style={{ padding: '16px 0' }}>
              <div className="p-input-group" style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>Full Name</label>
                <input type="text" required value={editName} onChange={e => setEditName(e.target.value)} className="p-input" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} />
              </div>
              <div className="p-input-group" style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>Gender</label>
                <select value={editGender} onChange={e => setEditGender(e.target.value)} className="p-input" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }}>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div className="p-input-group" style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>Date of Birth</label>
                <input type="date" value={editDob} onChange={e => setEditDob(e.target.value)} className="p-input" style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} />
              </div>
              <div className="p-btn-row" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" onClick={() => setEditingProfile(false)} className="p-btn p-btn-text">{t('cancel')}</button>
                 <button type="submit" className="p-btn p-btn-primary">{t('save')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Prescription Modal */}
      {viewingPrescription && (
        <div className="p-modal-overlay">
          <div className="p-modal" style={{ maxWidth: '600px', width: '90%' }}>
            <div className="p-modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#0f172a' }}>Prescription Details</h3>
              <button onClick={() => setViewingPrescription(null)} className="p-btn-close" style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: '#64748b' }}>&times;</button>
            </div>
            <div className="p-modal-body" style={{ padding: '16px 0' }}>
              <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#0f172a', fontSize: '14px' }}>Clinical Notes</h4>
                <p style={{ whiteSpace: 'pre-wrap', color: '#334155', margin: 0, fontSize: '14px' }}>{viewingPrescription.clinical_notes || "N/A"}</p>
              </div>
              
              <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#0f172a', fontSize: '14px' }}>Prescription</h4>
                <p style={{ whiteSpace: 'pre-wrap', color: '#334155', margin: 0, fontSize: '14px', fontFamily: 'monospace' }}>{viewingPrescription.prescription || "N/A"}</p>
              </div>

              {viewingPrescription.follow_up_date && (
                 <div style={{ padding: '12px 16px', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
                    <p style={{ margin: 0, color: '#1e3a8a', fontWeight: 600, fontSize: '14px' }}>Next Follow-up: {viewingPrescription.follow_up_date}</p>
                 </div>
              )}
            </div>
          </div>
        </div>
      )}


    </div>
  );
}
