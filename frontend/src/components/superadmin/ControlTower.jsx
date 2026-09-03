import React, { useState, useEffect } from 'react';

const TRANSLATIONS = {
  en: {
    title: "AURA SaaS Control Tower",
    subtitle: "Enterprise Multi-Tenant Observability, Billing Lifecycle & SRE Radar",
    overviewTab: "Overview",
    hospitalsTab: "Hospitals Fleet",
    errorsTab: "Errors & Traces",
    healthTab: "Live Dependency Radar",
    totalHospitals: "TOTAL HOSPITALS",
    activeTenants: "Active Tenants",
    expiringSoon: "EXPIRING IN ≤ 7 DAYS",
    urgentRenewal: "Urgent Renewal Required",
    saasRevenue: "SAAS REVENUE (LTV)",
    collectedRazorpay: "Razorpay Cloud Collections",
    hospitalOpdVolume: "HOSPITAL OPD VOLUME",
    fromPaidAppts: "From OPD Appointments",
    activeIncidents: "ACTIVE INCIDENTS",
    errors24h: "Logged in last 24h",
    liveHealth: "Live External Dependency Health",
    fleetStatus: "Hospital Tenant Fleet Status",
    viewAllHospitals: "View All Hospitals →",
    hospitalCol: "Hospital Tenant",
    planCol: "Current Plan",
    expiryCol: "Expiry Timeline",
    doctorQuotaCol: "Doctor Capacity",
    patientsBookingsCol: "Patients & Bookings",
    saasPaidCol: "SaaS Revenue",
    healthCol: "Health Status",
    actionsCol: "Actions",
    auditBtn: "🔍 360° Audit",
    searchPlaceholder: "Search hospital by name, phone, or ID...",
    allPlans: "All Plans",
    daysLeft: "Days Left",
    expired: "EXPIRED",
    healthy: "HEALTHY",
    warning: "WARNING",
    degraded: "DEGRADED",
    refreshLogs: "🔄 Refresh Logs",
    timeCol: "Timestamp",
    serviceCol: "Subsystem",
    severityCol: "Severity",
    errorCodeCol: "Error Code & Message",
    tenantCol: "Hospital Tenant",
    correlationCol: "Correlation ID",
    modalTitle: "Hospital 360° Deep Telemetry",
    subHistoryTab: "💳 Financial & Subscription Ledger",
    doctorsTab: "👨‍⚕️ Doctors & OPD Quotas",
    voiceTab: "📞 AI Voice Telemetry",
    diagnosticsTab: "🛠️ Diagnostic Error Logs",
    currentPosture: "CURRENT SUBSCRIPTION POSTURE",
    immutableLedger: "📜 Immutable Financial Ledger (Append-Only)",
    noRecords: "No previous records found.",
    dateCol: "Date",
    eventCol: "Event",
    amountPaidCol: "Amount Paid",
    daysAddedCol: "Days Added",
    totalAppts: "TOTAL APPOINTMENTS",
    completed: "COMPLETED",
    missedCancelled: "MISSED / CANCELLED",
    registeredDoctors: "👨‍⚕️ Registered Doctors",
    totalCallsHandled: "TOTAL VOICE CALLS PROCESSED",
    recentVoiceSessions: "Recent Inbound Voice Sessions",
    duration: "Duration",
    intent: "Caller Intent",
    status: "Call Status",
    flawlessService: "✓ 100% Flawless Operation: Zero runtime errors logged for this hospital tenant.",
    closeAudit: "Close Audit Console",
    traceTitle: "🔗 End-to-End Correlation Trace",
    traceErrorEvents: "Error Events in this Trace",
    traceAuditEvents: "Security Audit Events",
    plansTab: "Plans & Pricing Config"
  },
  hi: {
    title: "ऑरा सास कंट्रोल टॉवर (AURA Control Tower)",
    subtitle: "मल्टी-टेनेंट लाइव ऑब्जर्वेबिलिटी, बिलिंग हिस्ट्री एवं SRE रडार",
    overviewTab: "डैशबोर्ड अवलोकन",
    hospitalsTab: "अस्पताल नेटवर्क",
    errorsTab: "त्रुटि और ट्रेस लॉग्स",
    healthTab: "सिस्टम हेल्थ रडार",
    plansTab: "प्लान्स व मूल्य निर्धारण",
    totalHospitals: "कुल अस्पताल (TOTAL HOSPITALS)",
    activeTenants: "सक्रिय अस्पताल",
    expiringSoon: "7 दिनों में समाप्त होने वाले",
    urgentRenewal: "तत्काल नवीनीकरण आवश्यक",
    saasRevenue: "कुल SaaS राजस्व (LTV)",
    collectedRazorpay: "Razorpay क्लाउड संग्रह",
    hospitalOpdVolume: "अस्पताल OPD वॉल्यूम",
    fromPaidAppts: "OPD परामर्श शुल्कों से",
    activeIncidents: "सक्रिय समस्याएँ (Incidents)",
    errors24h: "पिछले 24 घंटे की त्रुटियाँ",
    liveHealth: "लाइव बाहरी सेवा स्थिति (External Health)",
    fleetStatus: "अस्पताल नेटवर्क स्थिति (Fleet Status)",
    viewAllHospitals: "सभी अस्पताल देखें →",
    hospitalCol: "अस्पताल विवरण",
    planCol: "सक्रिय प्लान",
    expiryCol: "वैधता एवं बचे दिन",
    doctorQuotaCol: "डॉक्टर क्षमता (Quota)",
    patientsBookingsCol: "मरीज एवं बुकिंग्स",
    saasPaidCol: "SaaS भुगतान",
    healthCol: "सिस्टम हेल्थ",
    actionsCol: "कार्यवाही",
    auditBtn: "🔍 360° ऑडिट",
    searchPlaceholder: "नाम, फोन नंबर या आईडी द्वारा खोजें...",
    allPlans: "सभी प्लान्स",
    daysLeft: "दिन शेष",
    expired: "समाप्त (EXPIRED)",
    healthy: "उत्कृष्ट (HEALTHY)",
    warning: "चेतावनी (WARNING)",
    degraded: "धीमा (DEGRADED)",
    refreshLogs: "🔄 लॉग्स रीफ्रेश करें",
    timeCol: "समय",
    serviceCol: "सेवा",
    severityCol: "गंभीरता",
    errorCodeCol: "त्रुटि कोड और संदेश",
    tenantCol: "अस्पताल",
    correlationCol: "ट्रेस आईडी",
    modalTitle: "अस्पताल 360° सम्पूर्ण ऑडिट",
    subHistoryTab: "💳 सब्सक्रिप्शन एवं भुगतान इतिहास",
    doctorsTab: "👨‍⚕️ डॉक्टर एवं OPD कोटा",
    voiceTab: "📞 AI वॉइस टेलीमेट्री",
    diagnosticsTab: "🛠️ डायग्नोस्टिक्स एवं एरर लॉग्स",
    currentPosture: "वर्तमान सब्सक्रिप्शन स्थिति",
    immutableLedger: "📜 अपरिवर्तनीय सब्सक्रिप्शन व नवीनीकरण बहीखाता (Ledger)",
    noRecords: "कोई पुराना रिकॉर्ड नहीं मिला।",
    dateCol: "दिनांक",
    eventCol: "प्रकार",
    amountPaidCol: "भुगतान राशि",
    daysAddedCol: "जोड़े गए दिन",
    totalAppts: "कुल अपॉइंटमेंट्स",
    completed: "सफलतापूर्वक पूर्ण",
    missedCancelled: "छूटे / रद्द किए गए",
    registeredDoctors: "👨‍⚕️ पंजीकृत डॉक्टर्स",
    totalCallsHandled: "कुल AI कॉल्स संपन्न",
    recentVoiceSessions: "हालिया वॉइस कॉल्स रिकॉर्ड्स",
    duration: "अवधि",
    intent: "उद्देश्य",
    status: "स्थिति",
    flawlessService: "✓ त्रुटिरहित सेवा: इस अस्पताल में कोई समस्या दर्ज नहीं हुई!",
    closeAudit: "ऑडिट बंद करें",
    traceTitle: "🔗 अनुरोध सहसंबंध ट्रेस (Correlation Trace)",
    traceErrorEvents: "इस ट्रेस में त्रुटि घटनाएँ",
    traceAuditEvents: "इस ट्रेस में ऑडिट घटनाएँ"
  }
};

export default function ControlTower({ API_BASE = '/api/v1', token, lang = 'en' }) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.en;
  
  const [currentTab, setCurrentTab] = useState('overview');
  const [overviewData, setOverviewData] = useState(null);
  const [hospitalsList, setHospitalsList] = useState([]);
  const [healthData, setHealthData] = useState(null);
  const [errorLogs, setErrorLogs] = useState([]);
  const [plansList, setPlansList] = useState([]);
  const [editingPlan, setEditingPlan] = useState(null);
  const [isEditPlanModalOpen, setIsEditPlanModalOpen] = useState(false);
  const [planSaveLoading, setPlanSaveLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [planFilter, setPlanFilter] = useState('ALL');
  
  // Hospital 360 Individual Modal
  const [selectedHospital360, setSelectedHospital360] = useState(null);
  const [hosp360Data, setHosp360Data] = useState(null);
  const [hosp360Tab, setHosp360Tab] = useState('subscription');
  const [hosp360Loading, setHosp360Loading] = useState(false);

  // Correlation Trace Modal
  const [traceCorrelationId, setTraceCorrelationId] = useState(null);
  const [traceData, setTraceData] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);

  const effectiveToken = token || localStorage.getItem('jwt_token') || '';

  useEffect(() => {
    fetchGlobalData();
    const interval = setInterval(fetchGlobalData, 30000);
    return () => clearInterval(interval);
  }, [effectiveToken]);

  const fetchGlobalData = async () => {
    if (!effectiveToken) return;
    try {
      const headers = { Authorization: `Bearer ${effectiveToken}` };
      
      const [ovRes, hospRes, hlthRes, errRes, plansRes] = await Promise.all([
        fetch(`${API_BASE}/owner/overview`, { headers }),
        fetch(`${API_BASE}/owner/hospitals`, { headers }),
        fetch(`${API_BASE}/owner/health-radar`, { headers }),
        fetch(`${API_BASE}/owner/errors?limit=30`, { headers }),
        fetch(`${API_BASE}/plans`, { headers })
      ]);

      if (ovRes.ok) setOverviewData(await ovRes.json());
      if (hospRes.ok) setHospitalsList(await hospRes.json());
      if (hlthRes.ok) setHealthData(await hlthRes.json());
      if (errRes.ok) {
        const d = await errRes.json();
        setErrorLogs(d.errors || []);
      }
      if (plansRes.ok) {
        setPlansList(await plansRes.json());
      }
    } catch (e) {
      console.error('Failed to fetch Control Tower data:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchHospital360 = async (hospId) => {
    setHosp360Loading(true);
    setHosp360Tab('subscription');
    try {
      const res = await fetch(`${API_BASE}/owner/hospitals/${hospId}/360`, {
        headers: { Authorization: `Bearer ${effectiveToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHosp360Data(data);
      }
    } catch (e) {
      console.error('Failed to fetch 360 data:', e);
    } finally {
      setHosp360Loading(false);
    }
  };

  const fetchCorrelationTrace = async (corrId) => {
    setTraceCorrelationId(corrId);
    setTraceLoading(true);
    try {
      const res = await fetch(`${API_BASE}/owner/traces/${corrId}`, {
        headers: { Authorization: `Bearer ${effectiveToken}` }
      });
      if (res.ok) {
        setTraceData(await res.json());
      }
    } catch (e) {
      console.error('Failed to fetch trace:', e);
    } finally {
      setTraceLoading(false);
    }
  };

  const handleOpenEditPlan = (plan) => {
    setEditingPlan({
      ...plan,
      features_text: Array.isArray(plan.features) ? plan.features.join('\n') : ''
    });
    setIsEditPlanModalOpen(true);
  };

  const handleSavePlan = async (e) => {
    e.preventDefault();
    if (!editingPlan) return;
    setPlanSaveLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('price_inr', editingPlan.price_inr);
      formData.append('max_doctors', editingPlan.max_doctors);
      formData.append('duration_days', editingPlan.duration_days);
      formData.append('ai_voice_enabled', editingPlan.ai_voice_enabled ? '1' : '0');
      formData.append('description', editingPlan.description || '');
      
      const featuresArray = editingPlan.features_text
        ? editingPlan.features_text.split('\n').map(s => s.trim()).filter(Boolean)
        : (editingPlan.features || []);
      formData.append('features_json', JSON.stringify(featuresArray));

      const res = await fetch(`${API_BASE}/admin/plans/${editingPlan.plan_code}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          Authorization: `Bearer ${effectiveToken}`
        },
        body: formData
      });

      if (res.ok) {
        alert(`🎉 Plan ${editingPlan.plan_code} updated successfully!`);
        setIsEditPlanModalOpen(false);
        const pRes = await fetch(`${API_BASE}/plans`, { headers: { Authorization: `Bearer ${effectiveToken}` } });
        if (pRes.ok) setPlansList(await pRes.json());
      } else {
        const err = await res.json();
        alert(`Error updating plan: ${err.detail || 'Failed'}`);
      }
    } catch (e) {
      alert(`Network error: ${e.message}`);
    } finally {
      setPlanSaveLoading(false);
    }
  };

  const filteredHospitals = hospitalsList.filter(h => {
    const matchSearch = h.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.phone.toLowerCase().includes(searchTerm.toLowerCase()) ||
      h.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchPlan = planFilter === 'ALL' || h.subscription_plan === planFilter;
    return matchSearch && matchPlan;
  });

  return (
    <div style={{
      padding: '24px 32px', textAlign: 'left', minHeight: '85vh',
      background: '#F8FAFC', color: '#0F172A',
      fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif"
    }}>
      
      {/* ── TOP HERO COMMAND BAR (Clean Modern Light Theme) ── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '24px', flexWrap: 'wrap', gap: '16px',
        background: '#FFFFFF', padding: '18px 24px', borderRadius: '20px',
        border: '1.5px solid #DBEAFE',
        boxShadow: '0 4px 20px -2px rgba(37, 99, 235, 0.06)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '46px', height: '46px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 50%, #3B82F6 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.25)', color: '#FFFFFF', fontSize: '22px'
          }}>
            🛰️
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h1 style={{
                fontSize: '22px', fontWeight: 900, color: '#0F172A', margin: 0,
                letterSpacing: '-0.5px'
              }}>
                {t.title}
              </h1>
              <span style={{
                background: overviewData?.observability?.platform_health_status === 'HEALTHY' ? '#DCFCE7' : '#FEF2F2',
                color: overviewData?.observability?.platform_health_status === 'HEALTHY' ? '#15803D' : '#DC2626',
                border: `1.5px solid ${overviewData?.observability?.platform_health_status === 'HEALTHY' ? '#86EFAC' : '#F87171'}`,
                borderRadius: '20px', padding: '3px 12px', fontSize: '11px', fontWeight: 800,
                display: 'inline-flex', alignItems: 'center', gap: '6px'
              }}>
                <span className="live-indicator" style={{
                  width: '7px', height: '7px', borderRadius: '50%',
                  background: overviewData?.observability?.platform_health_status === 'HEALTHY' ? '#16A34A' : '#DC2626'
                }}></span>
                {t[overviewData?.observability?.platform_health_status?.toLowerCase()] || overviewData?.observability?.platform_health_status || t.healthy}
              </span>
            </div>
            <div style={{ color: '#64748B', fontSize: '12px', marginTop: '2px', fontWeight: 600 }}>
              {t.subtitle}
            </div>
          </div>
        </div>

        {/* Global Navigation Tabs */}
        <div style={{
          display: 'flex', gap: '6px', background: '#F1F5F9',
          padding: '5px', borderRadius: '16px', border: '1px solid #E2E8F0', flexWrap: 'wrap'
        }}>
          {[
            { id: 'overview', icon: '📊', label: t.overviewTab },
            { id: 'hospitals', icon: '🏥', label: `${t.hospitalsTab} (${hospitalsList.length})` },
            { id: 'plans', icon: '💎', label: `${t.plansTab} (${plansList.length || 3})` },
            { id: 'observability', icon: '🚨', label: `${t.errorsTab} (${errorLogs.length})` },
            { id: 'health', icon: '⚡', label: t.healthTab },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setCurrentTab(tab.id)}
              style={{
                padding: '8px 16px', borderRadius: '12px', fontSize: '12px', fontWeight: 800,
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                background: currentTab === tab.id ? 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)' : 'transparent',
                color: currentTab === tab.id ? '#FFFFFF' : '#475569',
                boxShadow: currentTab === tab.id ? '0 2px 10px rgba(37, 99, 235, 0.28)' : 'none',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
            >
              <span>{tab.icon}</span> {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── VIEW 1: EXECUTIVE OVERVIEW ── */}
      {currentTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
          
          {/* Top KPI Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            
            {/* Card 1: Hospitals */}
            <div className="luxury-card" style={{ padding: '22px', borderLeft: '4px solid #2563EB' }}>
              <div style={{ color: '#64748B', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px' }}>{t.totalHospitals}</div>
              <div style={{ fontSize: '32px', fontWeight: 900, color: '#0F172A', margin: '4px 0 2px 0', letterSpacing: '-0.5px' }}>
                {overviewData?.hospitals?.total || hospitalsList.length}
              </div>
              <div style={{ fontSize: '12px', color: '#15803D', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                <span>✓</span> {overviewData?.hospitals?.active || 0} {t.activeTenants}
              </div>
            </div>

            {/* Card 2: Expiring */}
            <div className="luxury-card" style={{ padding: '22px', borderLeft: '4px solid #F59E0B' }}>
              <div style={{ color: '#B45309', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px' }}>{t.expiringSoon}</div>
              <div style={{ fontSize: '32px', fontWeight: 900, color: '#B45309', margin: '4px 0 2px 0', letterSpacing: '-0.5px' }}>
                {overviewData?.hospitals?.expiring_soon || 0}
              </div>
              <div style={{ fontSize: '12px', color: '#D97706', fontWeight: 700 }}>
                ⚠️ {t.urgentRenewal}
              </div>
            </div>

            {/* Card 3: SaaS Revenue */}
            <div className="luxury-card" style={{ padding: '22px', borderLeft: '4px solid #10B981' }}>
              <div style={{ color: '#047857', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px' }}>{t.saasRevenue}</div>
              <div style={{ fontSize: '32px', fontWeight: 900, color: '#15803D', margin: '4px 0 2px 0', letterSpacing: '-0.5px' }}>
                ₹{(overviewData?.financials?.total_saas_revenue_inr || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '12px', color: '#059669', fontWeight: 700 }}>
                {t.collectedRazorpay}
              </div>
            </div>

            {/* Card 4: OPD Volume */}
            <div className="luxury-card" style={{ padding: '22px', borderLeft: '4px solid #3B82F6' }}>
              <div style={{ color: '#1D4ED8', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px' }}>{t.hospitalOpdVolume}</div>
              <div style={{ fontSize: '32px', fontWeight: 900, color: '#2563EB', margin: '4px 0 2px 0', letterSpacing: '-0.5px' }}>
                ₹{(overviewData?.financials?.total_hospital_opd_revenue_inr || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '12px', color: '#2563EB', fontWeight: 700 }}>
                {t.fromPaidAppts} ({overviewData?.operations?.completed_appointments || 0})
              </div>
            </div>

            {/* Card 5: Active Incidents */}
            <div className="luxury-card" style={{ padding: '22px', borderLeft: '4px solid #EF4444' }}>
              <div style={{ color: '#B91C1C', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.6px' }}>{t.activeIncidents}</div>
              <div style={{ fontSize: '32px', fontWeight: 900, color: '#DC2626', margin: '4px 0 2px 0', letterSpacing: '-0.5px' }}>
                {overviewData?.observability?.active_incidents || 0}
              </div>
              <div style={{ fontSize: '12px', color: '#DC2626', fontWeight: 700 }}>
                {overviewData?.observability?.errors_last_24h || 0} {t.errors24h}
              </div>
            </div>
          </div>

          {/* Dependency Status Pills Radar */}
          {healthData && (
            <div className="luxury-card" style={{ padding: '18px 24px' }}>
              <div style={{ fontSize: '13px', fontWeight: 800, color: '#334155', marginBottom: '12px' }}>
                ⚡ {t.liveHealth}
              </div>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {Object.entries(healthData.components || {}).map(([key, comp]) => (
                  <div key={key} style={{
                    display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', borderRadius: '12px',
                    background: comp.status === 'HEALTHY' ? '#F0FDF4' : '#FEF2F2',
                    border: `1.5px solid ${comp.status === 'HEALTHY' ? '#86EFAC' : '#F87171'}`
                  }}>
                    <span style={{ fontSize: '10px' }}>{comp.status === 'HEALTHY' ? '🟢' : '🔴'}</span>
                    <span style={{ fontSize: '12px', fontWeight: 800, color: '#0F172A' }}>{comp.name}:</span>
                    <span style={{ fontSize: '12px', fontWeight: 800, color: comp.status === 'HEALTHY' ? '#15803D' : '#DC2626' }}>
                      {comp.status} {comp.latency_ms ? `(${comp.latency_ms}ms)` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick Hospitals Snapshot Table */}
          <div className="luxury-card" style={{ padding: '24px', overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 900, color: '#0F172A', margin: 0 }}>🏥 {t.fleetStatus}</h3>
              <button onClick={() => setCurrentTab('hospitals')} style={{
                background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE',
                borderRadius: '10px', padding: '6px 14px', fontSize: '12px', fontWeight: 800, cursor: 'pointer',
                transition: 'all 0.15s'
              }}>
                {t.viewAllHospitals}
              </button>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
                <thead style={{ background: '#F8FAFC', borderBottom: '2px solid #DBEAFE' }}>
                  <tr>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.hospitalCol}</th>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.planCol}</th>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.expiryCol}</th>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.doctorQuotaCol}</th>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.saasPaidCol}</th>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.healthCol}</th>
                    <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.actionsCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {hospitalsList.slice(0, 5).map(h => (
                    <tr key={h.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '14px' }}>
                        <div style={{ fontWeight: 800, color: '#0F172A', fontSize: '14px' }}>{h.name}</div>
                        <div style={{ fontSize: '11px', color: '#64748B', fontFamily: 'monospace' }}>ID: {h.id}</div>
                      </td>
                      <td style={{ padding: '14px' }}>
                        <span style={{
                          background: h.subscription_plan === 'ENTERPRISE' ? '#F3E8FF' : (h.subscription_plan === 'PRO' ? '#EFF6FF' : '#F1F5F9'),
                          color: h.subscription_plan === 'ENTERPRISE' ? '#7E22CE' : (h.subscription_plan === 'PRO' ? '#2563EB' : '#475569'),
                          border: `1px solid ${h.subscription_plan === 'ENTERPRISE' ? '#C084FC' : (h.subscription_plan === 'PRO' ? '#93C5FD' : '#CBD5E1')}`,
                          padding: '3px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800
                        }}>
                          {h.subscription_plan}
                        </span>
                      </td>
                      <td style={{ padding: '14px' }}>
                        <span style={{
                          color: h.days_left <= 7 ? '#DC2626' : '#15803D',
                          fontWeight: 800, fontSize: '12px',
                          background: h.days_left <= 7 ? '#FEF2F2' : '#F0FDF4',
                          padding: '3px 8px', borderRadius: '6px', border: `1px solid ${h.days_left <= 7 ? '#F87171' : '#86EFAC'}`
                        }}>
                          {h.days_left <= 0 ? t.expired : `${h.days_left} ${t.daysLeft}`}
                        </span>
                      </td>
                      <td style={{ padding: '14px', fontWeight: 700, color: '#334155' }}>
                        {h.active_doctors} / {h.max_doctors} ({h.doctor_quota_used_pct}%)
                      </td>
                      <td style={{ padding: '14px', fontWeight: 900, color: '#15803D', fontSize: '14px' }}>
                        ₹{h.total_saas_revenue_inr.toLocaleString()}
                      </td>
                      <td style={{ padding: '14px' }}>
                        <span style={{ color: h.health_status === 'HEALTHY' ? '#15803D' : '#DC2626', fontWeight: 800 }}>
                          ● {t[h.health_status.toLowerCase()] || h.health_status}
                        </span>
                      </td>
                      <td style={{ padding: '14px' }}>
                        <button
                          onClick={() => { setSelectedHospital360(h.id); fetchHospital360(h.id); }}
                          style={{
                            background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                            color: '#FFFFFF', border: 'none', borderRadius: '10px', padding: '6px 14px',
                            fontSize: '12px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)',
                            transition: 'all 0.15s'
                          }}
                        >
                          {t.auditBtn}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── VIEW 2: HOSPITALS MASTER CONTROL (ALL IN ONE) ── */}
      {currentTab === 'hospitals' && (
        <div className="luxury-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: 0 }}>🏥 {t.hospitalsTab}</h2>
              <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px', fontWeight: 600 }}>{t.subtitle}</div>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="text"
                placeholder={t.searchPlaceholder}
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                style={{
                  padding: '10px 14px', borderRadius: '12px',
                  background: '#FFFFFF', border: '1.5px solid #CBD5E1',
                  color: '#0F172A', fontSize: '13px', width: '280px'
                }}
              />

              <select
                value={planFilter}
                onChange={e => setPlanFilter(e.target.value)}
                style={{
                  padding: '10px 14px', borderRadius: '12px',
                  background: '#FFFFFF', border: '1.5px solid #CBD5E1',
                  color: '#0F172A', fontSize: '13px', fontWeight: 700
                }}
              >
                <option value="ALL">{t.allPlans}</option>
                <option value="STARTER">Starter</option>
                <option value="PRO">Pro AI</option>
                <option value="ENTERPRISE">Enterprise</option>
              </select>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
              <thead style={{ background: '#F8FAFC', borderBottom: '2px solid #DBEAFE' }}>
                <tr>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.hospitalCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.planCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.expiryCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.doctorQuotaCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.patientsBookingsCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.saasPaidCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.healthCol}</th>
                  <th style={{ padding: '12px 14px', color: '#475569', fontWeight: 800 }}>{t.actionsCol}</th>
                </tr>
              </thead>
              <tbody>
                {filteredHospitals.map(h => (
                  <tr key={h.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                    <td style={{ padding: '14px' }}>
                      <div style={{ fontWeight: 800, color: '#0F172A', fontSize: '14px' }}>{h.name}</div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>📱 {h.phone} | 🆔 {h.id}</div>
                    </td>
                    <td style={{ padding: '14px' }}>
                      <span style={{
                        background: h.subscription_plan === 'ENTERPRISE' ? '#F3E8FF' : (h.subscription_plan === 'PRO' ? '#EFF6FF' : '#F1F5F9'),
                        color: h.subscription_plan === 'ENTERPRISE' ? '#7E22CE' : (h.subscription_plan === 'PRO' ? '#2563EB' : '#475569'),
                        border: `1px solid ${h.subscription_plan === 'ENTERPRISE' ? '#C084FC' : (h.subscription_plan === 'PRO' ? '#93C5FD' : '#CBD5E1')}`,
                        padding: '4px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 800
                      }}>
                        {h.subscription_plan}
                      </span>
                    </td>
                    <td style={{ padding: '14px' }}>
                      <span style={{
                        color: h.days_left <= 7 ? '#DC2626' : '#15803D',
                        fontWeight: 800, fontSize: '12px',
                        background: h.days_left <= 7 ? '#FEF2F2' : '#F0FDF4',
                        padding: '3px 10px', borderRadius: '6px', border: `1px solid ${h.days_left <= 7 ? '#F87171' : '#86EFAC'}`
                      }}>
                        {h.days_left <= 0 ? t.expired : `⏳ ${h.days_left} ${t.daysLeft}`}
                      </span>
                    </td>
                    <td style={{ padding: '14px' }}>
                      <div style={{ fontWeight: 800, color: '#0F172A' }}>{h.active_doctors} / {h.max_doctors} Doctors</div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>Quota: {h.doctor_quota_used_pct}%</div>
                    </td>
                    <td style={{ padding: '14px', fontWeight: 700, color: '#334155' }}>
                      {h.total_patients} Patients • {h.total_appointments} Bookings
                    </td>
                    <td style={{ padding: '14px', fontWeight: 900, color: '#15803D', fontSize: '14px' }}>
                      ₹{h.total_saas_revenue_inr.toLocaleString()}
                    </td>
                    <td style={{ padding: '14px' }}>
                      <div style={{ color: h.health_status === 'HEALTHY' ? '#15803D' : '#DC2626', fontWeight: 800, fontSize: '12px' }}>
                        ● {t[h.health_status.toLowerCase()] || h.health_status}
                      </div>
                      <div style={{ fontSize: '10px', color: '#64748B' }}>{h.error_count} errors</div>
                    </td>
                    <td style={{ padding: '14px' }}>
                      <button
                        onClick={() => { setSelectedHospital360(h.id); fetchHospital360(h.id); }}
                        style={{
                          background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                          color: '#FFFFFF', border: 'none', borderRadius: '10px', padding: '8px 16px',
                          fontSize: '12px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)',
                          transition: 'all 0.15s'
                        }}
                      >
                        {t.auditBtn}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── VIEW 3: OBSERVABILITY & ERROR STREAM ── */}
      {currentTab === 'observability' && (
        <div className="luxury-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: 0 }}>🚨 {t.errorsTab}</h2>
              <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px', fontWeight: 600 }}>{t.subtitle}</div>
            </div>
            <button onClick={fetchGlobalData} style={{
              background: '#EFF6FF', border: '1px solid #BFDBFE',
              color: '#2563EB', padding: '6px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: 800, cursor: 'pointer'
            }}>
              {t.refreshLogs}
            </button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
              <thead style={{ background: '#F8FAFC', borderBottom: '2px solid #DBEAFE' }}>
                <tr>
                  <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.timeCol}</th>
                  <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.serviceCol}</th>
                  <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.severityCol}</th>
                  <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.errorCodeCol}</th>
                  <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.tenantCol}</th>
                  <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.correlationCol}</th>
                </tr>
              </thead>
              <tbody>
                {errorLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: '#15803D', fontWeight: 700 }}>
                      ✓ {t.flawlessService}
                    </td>
                  </tr>
                ) : (
                  errorLogs.map(err => (
                    <tr key={err.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <td style={{ padding: '10px 12px', color: '#64748B', whiteSpace: 'nowrap' }}>
                        {new Date(err.occurred_at).toLocaleTimeString()}
                      </td>
                      <td style={{ padding: '10px 12px', fontWeight: 800, color: '#2563EB' }}>
                        {err.service_name}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{
                          background: err.severity === 'CRITICAL' ? '#FEE2E2' : '#FEF3C7',
                          color: err.severity === 'CRITICAL' ? '#991B1B' : '#B45309',
                          padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 800
                        }}>
                          {err.severity}
                        </span>
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        <div style={{ fontWeight: 800, color: '#0F172A' }}>{err.error_code}</div>
                        <div style={{ color: '#475569', fontSize: '11px' }}>{err.error_message}</div>
                      </td>
                      <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#64748B' }}>
                        {err.hospital_id || 'SYSTEM'}
                      </td>
                      <td style={{ padding: '10px 12px' }}>
                        {err.correlation_id ? (
                          <button
                            onClick={() => fetchCorrelationTrace(err.correlation_id)}
                            style={{
                              background: '#EFF6FF', border: '1px solid #BFDBFE',
                              color: '#2563EB', padding: '3px 8px', borderRadius: '6px', fontSize: '11px',
                              cursor: 'pointer', fontFamily: 'monospace', fontWeight: 700
                            }}
                          >
                            🔗 {err.correlation_id.substring(0, 8)}...
                          </button>
                        ) : 'N/A'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── VIEW 4: SUBSCRIPTION PLANS & PRICING CONFIG (SUPER ADMIN DYNAMIC CONFIG) ── */}
      {currentTab === 'plans' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
          
          {/* Header Card */}
          <div className="luxury-card" style={{ padding: '24px', background: '#FFFFFF', border: '1.5px solid #DBEAFE' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>💎</span> SaaS Subscription Plans, Pricing & Doctor Quotas
                </h2>
                <div style={{ fontSize: '12px', color: '#64748B', marginTop: '4px', fontWeight: 600 }}>
                  Configure tier prices, doctor capacities, trial durations, and capabilities. Changes instantly apply across all tenant hospitals.
                </div>
              </div>
              <button
                onClick={async () => {
                  const pRes = await fetch(`${API_BASE}/plans`, { headers: { Authorization: `Bearer ${effectiveToken}` } });
                  if (pRes.ok) setPlansList(await pRes.json());
                }}
                style={{
                  background: '#EFF6FF', border: '1px solid #BFDBFE',
                  color: '#2563EB', padding: '6px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: 800, cursor: 'pointer'
                }}
              >
                🔄 Refresh Plans
              </button>
            </div>
          </div>

          {/* Plan Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
            {plansList.map(plan => {
              const isEnterprise = plan.plan_code === 'ENTERPRISE';
              const isPro = plan.plan_code === 'PRO';
              const isStarter = plan.plan_code === 'STARTER';

              const accentColor = isEnterprise ? '#7E22CE' : (isPro ? '#2563EB' : '#D97706');
              const bgGradient = isEnterprise ? '#FAF5FF' : (isPro ? '#EFF6FF' : '#FFFBEB');
              const borderCol = isEnterprise ? '#C084FC' : (isPro ? '#93C5FD' : '#FDE68A');

              return (
                <div
                  key={plan.plan_code}
                  className="luxury-card"
                  style={{
                    padding: '24px', background: '#FFFFFF', border: `2px solid ${borderCol}`,
                    display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                    boxShadow: '0 8px 24px -4px rgba(15, 23, 42, 0.06)'
                  }}
                >
                  <div>
                    {/* Top Row: Code & Cycle */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <span style={{
                        background: bgGradient, color: accentColor,
                        padding: '4px 12px', borderRadius: '8px', fontSize: '11px', fontWeight: 900,
                        border: `1px solid ${borderCol}`
                      }}>
                        {isEnterprise ? '👑 ENTERPRISE 360' : (isPro ? '⚡ PRO AI' : '⭐ STARTER TRIAL')}
                      </span>
                      <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 700 }}>
                        {plan.duration_days} Days ({plan.billing_cycle})
                      </span>
                    </div>

                    <h3 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: '0 0 6px 0' }}>
                      {plan.display_name}
                    </h3>
                    <p style={{ fontSize: '12px', color: '#64748B', margin: '0 0 16px 0', lineHeight: 1.4, minHeight: '34px' }}>
                      {plan.description}
                    </p>

                    {/* Pricing Display */}
                    <div style={{
                      background: '#F8FAFC', padding: '12px 16px', borderRadius: '12px',
                      border: '1px solid #E2E8F0', marginBottom: '16px', display: 'flex', alignItems: 'baseline', gap: '6px'
                    }}>
                      <span style={{ fontSize: '26px', fontWeight: 900, color: '#0F172A' }}>
                        ₹{plan.price_inr.toLocaleString('en-IN')}
                      </span>
                      <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 700 }}>
                        {isStarter ? '(Post-Trial / mo)' : (isEnterprise ? '/ year' : '/ month')}
                      </span>
                    </div>

                    {/* Quota Highlights */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '18px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', borderBottom: '1px solid #F1F5F9', paddingBottom: '6px' }}>
                        <span style={{ color: '#64748B', fontWeight: 600 }}>👨‍⚕️ Max Doctors Quota:</span>
                        <strong style={{ color: '#0F172A' }}>{plan.max_doctors >= 999 ? 'Unlimited (999)' : `${plan.max_doctors} Doctor(s)`}</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', borderBottom: '1px solid #F1F5F9', paddingBottom: '6px' }}>
                        <span style={{ color: '#64748B', fontWeight: 600 }}>📞 AI Voice Receptionist:</span>
                        <strong style={{ color: plan.ai_voice_enabled ? '#15803D' : '#991B1B' }}>
                          {plan.ai_voice_enabled ? '✅ Active 24/7' : '❌ Locked'}
                        </strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', paddingBottom: '6px' }}>
                        <span style={{ color: '#64748B', fontWeight: 600 }}>💬 WhatsApp Automation:</span>
                        <strong style={{ color: '#15803D' }}>✅ Enabled</strong>
                      </div>
                    </div>

                    {/* Features List */}
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 800, color: '#475569', textTransform: 'uppercase', marginBottom: '6px' }}>
                        Included Features:
                      </div>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {(plan.features || []).map((f, i) => (
                          <li key={i} style={{ fontSize: '12px', color: '#334155', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ color: accentColor, fontWeight: 800 }}>✓</span> {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Edit Plan Button */}
                  <button
                    onClick={() => handleOpenEditPlan(plan)}
                    style={{
                      width: '100%', padding: '10px', borderRadius: '10px',
                      background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                      color: '#FFFFFF', border: 'none', fontWeight: 800, fontSize: '12px',
                      cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.25)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px'
                    }}
                  >
                    ✏️ Edit Plan Pricing & Quotas
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── VIEW 5: SYSTEM HEALTH RADAR ── */}
      {currentTab === 'health' && healthData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="luxury-card" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: '0 0 16px 0' }}>⚡ {t.healthTab}</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              {Object.entries(healthData.components || {}).map(([key, comp]) => (
                <div key={key} style={{
                  padding: '20px', borderRadius: '16px',
                  background: comp.status === 'HEALTHY' ? '#F0FDF4' : '#FEF2F2',
                  border: `1.5px solid ${comp.status === 'HEALTHY' ? '#86EFAC' : '#F87171'}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>{comp.name}</span>
                    <span style={{
                      background: comp.status === 'HEALTHY' ? '#DCFCE7' : '#FEE2E2',
                      color: comp.status === 'HEALTHY' ? '#15803D' : '#991B1B',
                      padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 800
                    }}>
                      ● {t[comp.status.toLowerCase()] || comp.status}
                    </span>
                  </div>
                  <div style={{ color: '#64748B', fontSize: '12px', marginTop: '8px' }}>Provider: <strong>{comp.provider}</strong></div>
                  {comp.latency_ms !== undefined && (
                    <div style={{ color: '#15803D', fontSize: '12px', fontWeight: 700, marginTop: '4px' }}>
                      Latency: <strong>{comp.latency_ms} ms</strong>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: EDIT PLAN PRICING & QUOTA (SUPER ADMIN) ── */}
      {isEditPlanModalOpen && editingPlan && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1300, padding: '20px'
        }}>
          <div className="animate-modal-pop" style={{
            background: '#FFFFFF', borderRadius: '24px', width: '100%', maxWidth: '580px',
            padding: '28px', boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.3)',
            border: '1.5px solid #DBEAFE', textAlign: 'left'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #E2E8F0', paddingBottom: '14px', marginBottom: '18px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                  ✏️ Edit Plan: {editingPlan.plan_code}
                </h3>
                <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 600, marginTop: '2px' }}>
                  Update live pricing, doctor limits, and duration for this tier
                </div>
              </div>
              <button
                onClick={() => setIsEditPlanModalOpen(false)}
                style={{ background: '#F1F5F9', border: 'none', width: '32px', height: '32px', borderRadius: '50%', fontSize: '16px', cursor: 'pointer', color: '#64748B', fontWeight: 800 }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSavePlan} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#475569', marginBottom: '4px' }}>
                    💰 Price in INR (₹)
                  </label>
                  <input
                    type="number"
                    value={editingPlan.price_inr}
                    onChange={e => setEditingPlan({ ...editingPlan, price_inr: parseFloat(e.target.value) || 0 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 700 }}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#475569', marginBottom: '4px' }}>
                    👨‍⚕️ Max Doctors Quota
                  </label>
                  <input
                    type="number"
                    value={editingPlan.max_doctors}
                    onChange={e => setEditingPlan({ ...editingPlan, max_doctors: parseInt(e.target.value) || 1 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 700 }}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#475569', marginBottom: '4px' }}>
                    ⏳ Duration Days
                  </label>
                  <input
                    type="number"
                    value={editingPlan.duration_days}
                    onChange={e => setEditingPlan({ ...editingPlan, duration_days: parseInt(e.target.value) || 30 })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 700 }}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#475569', marginBottom: '4px' }}>
                    📞 AI Voice Helpline
                  </label>
                  <select
                    value={editingPlan.ai_voice_enabled ? '1' : '0'}
                    onChange={e => setEditingPlan({ ...editingPlan, ai_voice_enabled: e.target.value === '1' })}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px', fontWeight: 700 }}
                  >
                    <option value="1">✅ Enabled (Voice AI Receptionist)</option>
                    <option value="0">❌ Disabled (Manual Front Desk Only)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#475569', marginBottom: '4px' }}>
                  📝 Plan Description
                </label>
                <input
                  type="text"
                  value={editingPlan.description || ''}
                  onChange={e => setEditingPlan({ ...editingPlan, description: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 800, color: '#475569', marginBottom: '4px' }}>
                  📋 Feature Bullets (One per line)
                </label>
                <textarea
                  rows={4}
                  value={editingPlan.features_text || ''}
                  onChange={e => setEditingPlan({ ...editingPlan, features_text: e.target.value })}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '10px', border: '1.5px solid #CBD5E1', fontSize: '12px', fontFamily: 'monospace' }}
                  placeholder="Enter features, each on a new line..."
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsEditPlanModalOpen(false)}
                  style={{ padding: '10px 18px', borderRadius: '10px', border: '1px solid #CBD5E1', background: '#FFFFFF', color: '#475569', fontWeight: 700, fontSize: '13px', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={planSaveLoading}
                  style={{
                    padding: '10px 22px', borderRadius: '10px', border: 'none',
                    background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                    color: '#FFFFFF', fontWeight: 800, fontSize: '13px', cursor: 'pointer',
                    boxShadow: '0 2px 10px rgba(37, 99, 235, 0.3)'
                  }}
                >
                  {planSaveLoading ? 'Saving...' : '💾 Save Plan Configuration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: INDIVIDUAL HOSPITAL 360° AUDIT (INDIVIDUALLY ALL HOSPITALS) ── */}
      {selectedHospital360 && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1200, padding: '20px'
        }}>
          <div className="animate-modal-pop" style={{
            background: '#FFFFFF', borderRadius: '24px', width: '100%', maxWidth: '920px',
            maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
            boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.3)', border: '1.5px solid #DBEAFE'
          }}>
            
            {/* Modal Header */}
            <div style={{
              padding: '20px 28px', borderBottom: '1px solid #E2E8F0',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              background: '#F8FAFC'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '22px' }}>🏥</span>
                  <h3 style={{ fontSize: '18px', fontWeight: 900, color: '#0F172A', margin: 0 }}>
                    {hosp360Data?.profile?.name || t.modalTitle}
                  </h3>
                  <span style={{
                    background: '#EFF6FF', color: '#2563EB', border: '1px solid #BFDBFE',
                    padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 800
                  }}>
                    {hosp360Data?.profile?.subscription_plan}
                  </span>
                </div>
                <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>
                  Tenant ID: <strong style={{ fontFamily: 'monospace', color: '#0F172A' }}>{selectedHospital360}</strong> | Joined: {hosp360Data?.profile?.joined_date ? new Date(hosp360Data.profile.joined_date).toLocaleDateString() : 'N/A'}
                </div>
              </div>
              <button onClick={() => { setSelectedHospital360(null); setHosp360Data(null); }} style={{
                background: '#F1F5F9', border: 'none', borderRadius: '50%',
                width: '32px', height: '32px', fontSize: '16px', cursor: 'pointer', color: '#64748B',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>✕</button>
            </div>

            {/* Modal Tabs */}
            <div style={{ display: 'flex', gap: '4px', padding: '10px 28px', background: '#FFFFFF', borderBottom: '1px solid #E2E8F0' }}>
              {[
                { id: 'subscription', label: t.subHistoryTab },
                { id: 'operations', label: t.doctorsTab },
                { id: 'voice', label: t.voiceTab },
                { id: 'diagnostics', label: t.diagnosticsTab },
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setHosp360Tab(tab.id)}
                  style={{
                    padding: '8px 16px', borderRadius: '10px', border: 'none', cursor: 'pointer', fontSize: '12px', fontWeight: 800,
                    background: hosp360Tab === tab.id ? '#EFF6FF' : 'transparent',
                    color: hosp360Tab === tab.id ? '#2563EB' : '#64748B',
                    borderBottom: hosp360Tab === tab.id ? '2px solid #2563EB' : 'none',
                    transition: 'all 0.15s'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Modal Body */}
            <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>
              {hosp360Loading ? (
                <div style={{ padding: '40px', textAlign: 'center', color: '#64748B', fontWeight: 700 }}>Loading 360° telemetry data...</div>
              ) : (
                <>
                  {/* TAB 1: SUBSCRIPTION HISTORY LEDGER */}
                  {hosp360Tab === 'subscription' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div style={{
                        background: '#F0FDF4',
                        border: '1.5px solid #86EFAC', borderRadius: '16px', padding: '18px',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                      }}>
                        <div>
                          <div style={{ fontSize: '11px', color: '#15803D', fontWeight: 800, textTransform: 'uppercase' }}>{t.currentPosture}</div>
                          <div style={{ fontSize: '22px', fontWeight: 900, color: '#0F172A', marginTop: '2px' }}>
                            {hosp360Data?.profile?.subscription_plan} Plan ({hosp360Data?.profile?.plan_status})
                          </div>
                          <div style={{ fontSize: '12px', color: '#475569', marginTop: '2px' }}>
                            Expires: <strong style={{ color: '#0F172A' }}>{hosp360Data?.profile?.plan_expires_at ? new Date(hosp360Data.profile.plan_expires_at).toLocaleDateString() : 'N/A'}</strong> ({hosp360Data?.profile?.days_left} {t.daysLeft})
                          </div>
                        </div>
                      </div>

                      <h4 style={{ fontSize: '14px', fontWeight: 900, color: '#0F172A', margin: '8px 0 0 0' }}>{t.immutableLedger}</h4>
                      
                      {(hosp360Data?.subscription_history || []).length === 0 ? (
                        <div style={{ color: '#64748B', fontSize: '13px', padding: '16px' }}>{t.noRecords}</div>
                      ) : (
                        <div style={{ border: '1px solid #E2E8F0', borderRadius: '14px', overflow: 'hidden' }}>
                          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                            <thead style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                              <tr>
                                <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.dateCol}</th>
                                <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.eventCol}</th>
                                <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.planCol}</th>
                                <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.amountPaidCol}</th>
                                <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.daysAddedCol}</th>
                                <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.expiryCol}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {hosp360Data.subscription_history.map(s => (
                                <tr key={s.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                                  <td style={{ padding: '12px', color: '#64748B' }}>{new Date(s.created_at).toLocaleDateString()}</td>
                                  <td style={{ padding: '12px', fontWeight: 800, color: '#2563EB' }}>{s.event_type}</td>
                                  <td style={{ padding: '12px', fontWeight: 800, color: '#0F172A' }}>{s.plan_name}</td>
                                  <td style={{ padding: '12px', fontWeight: 900, color: '#15803D' }}>₹{s.amount_paid.toLocaleString()}</td>
                                  <td style={{ padding: '12px', fontWeight: 800, color: '#334155' }}>+{s.duration_days_added} Days</td>
                                  <td style={{ padding: '12px', color: '#64748B' }}>
                                    {s.plan_expires_at ? new Date(s.plan_expires_at).toLocaleDateString() : 'N/A'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}

                  {/* TAB 2: OPERATIONS & DOCTORS */}
                  {hosp360Tab === 'operations' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                        <div style={{ background: '#F8FAFC', padding: '16px', borderRadius: '14px', border: '1px solid #E2E8F0' }}>
                          <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 800 }}>{t.totalAppts}</div>
                          <div style={{ fontSize: '24px', fontWeight: 900, color: '#0F172A' }}>{hosp360Data?.operations_funnel?.total_appointments || 0}</div>
                        </div>
                        <div style={{ background: '#F0FDF4', padding: '16px', borderRadius: '14px', border: '1.5px solid #86EFAC' }}>
                          <div style={{ fontSize: '11px', color: '#15803D', fontWeight: 800 }}>{t.completed}</div>
                          <div style={{ fontSize: '24px', fontWeight: 900, color: '#15803D' }}>{hosp360Data?.operations_funnel?.completed || 0} ({hosp360Data?.operations_funnel?.completion_rate_pct}%)</div>
                        </div>
                        <div style={{ background: '#FEF2F2', padding: '16px', borderRadius: '14px', border: '1.5px solid #F87171' }}>
                          <div style={{ fontSize: '11px', color: '#DC2626', fontWeight: 800 }}>{t.missedCancelled}</div>
                          <div style={{ fontSize: '24px', fontWeight: 900, color: '#DC2626' }}>{(hosp360Data?.operations_funnel?.missed || 0) + (hosp360Data?.operations_funnel?.cancelled || 0)}</div>
                        </div>
                      </div>

                      <h4 style={{ fontSize: '14px', fontWeight: 900, color: '#0F172A', margin: '8px 0 0 0' }}>{t.registeredDoctors} ({hosp360Data?.doctors?.length || 0} / {hosp360Data?.profile?.max_doctors || 1})</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        {(hosp360Data?.doctors || []).map(doc => (
                          <div key={doc.id} style={{ padding: '14px', borderRadius: '12px', border: '1px solid #E2E8F0', background: '#FFFFFF' }}>
                            <div style={{ fontWeight: 800, color: '#0F172A' }}>{doc.name}</div>
                            <div style={{ fontSize: '11px', color: '#64748B', marginTop: '2px' }}>OPD Fee: <strong style={{ color: '#15803D' }}>₹{doc.opd_fees}</strong> | License: {doc.license_number || 'N/A'}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* TAB 3: AI VOICE TELEMETRY */}
                  {hosp360Tab === 'voice' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div style={{ background: '#EFF6FF', border: '1.5px solid #93C5FD', borderRadius: '16px', padding: '18px' }}>
                        <div style={{ fontSize: '11px', color: '#1E40AF', fontWeight: 800 }}>{t.totalCallsHandled}</div>
                        <div style={{ fontSize: '26px', fontWeight: 900, color: '#1E40AF' }}>{hosp360Data?.ai_voice_telemetry?.total_calls_handled || 0} Calls</div>
                      </div>

                      <h4 style={{ fontSize: '14px', fontWeight: 900, color: '#0F172A', margin: '8px 0 0 0' }}>{t.recentVoiceSessions}</h4>
                      <div style={{ border: '1px solid #E2E8F0', borderRadius: '14px', overflow: 'hidden' }}>
                        <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                          <thead style={{ background: '#F8FAFC', borderBottom: '1px solid #E2E8F0' }}>
                            <tr>
                              <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.timeCol}</th>
                              <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>Caller</th>
                              <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.duration}</th>
                              <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.intent}</th>
                              <th style={{ padding: '10px 12px', color: '#475569', fontWeight: 800 }}>{t.status}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(hosp360Data?.ai_voice_telemetry?.recent_calls || []).map(c => (
                              <tr key={c.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                                <td style={{ padding: '10px 12px', color: '#64748B' }}>{c.created_at ? new Date(c.created_at).toLocaleTimeString() : 'N/A'}</td>
                                <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#0F172A' }}>{c.caller_number}</td>
                                <td style={{ padding: '10px 12px', fontWeight: 700, color: '#2563EB' }}>{c.call_duration}s</td>
                                <td style={{ padding: '10px 12px', color: '#334155' }}>{c.intent}</td>
                                <td style={{ padding: '10px 12px', fontWeight: 800, color: '#15803D' }}>{c.status}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* TAB 4: DIAGNOSTICS */}
                  {hosp360Tab === 'diagnostics' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <h4 style={{ fontSize: '14px', fontWeight: 900, color: '#0F172A', margin: 0 }}>{t.diagnosticsTab}</h4>
                      {(hosp360Data?.recent_errors || []).length === 0 ? (
                        <div style={{
                          color: '#15803D', background: '#F0FDF4', padding: '18px',
                          borderRadius: '14px', fontSize: '13px', fontWeight: 700, border: '1.5px solid #86EFAC'
                        }}>
                          {t.flawlessService}
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {hosp360Data.recent_errors.map(err => (
                            <div key={err.id} style={{
                              padding: '14px', borderRadius: '12px',
                              border: '1.5px solid #FECACA', background: '#FEF2F2'
                            }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ fontWeight: 800, color: '#DC2626', fontSize: '12px' }}>{err.service_name} • {err.error_code}</span>
                                <span style={{ fontSize: '11px', color: '#64748B' }}>{new Date(err.occurred_at).toLocaleString()}</span>
                              </div>
                              <div style={{ fontSize: '12px', color: '#475569', marginTop: '4px' }}>{err.error_message}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div style={{ padding: '16px 28px', borderTop: '1px solid #E2E8F0', background: '#F8FAFC', textAlign: 'right' }}>
              <button
                onClick={() => { setSelectedHospital360(null); setHosp360Data(null); }}
                style={{
                  background: '#FFFFFF', border: '1.5px solid #CBD5E1',
                  padding: '8px 20px', borderRadius: '10px', fontWeight: 700, fontSize: '13px', color: '#334155', cursor: 'pointer'
                }}
              >
                {t.closeAudit}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: CORRELATION TRACE LOOKUP ── */}
      {traceCorrelationId && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 1300, padding: '20px'
        }}>
          <div style={{
            background: '#FFFFFF', borderRadius: '22px', width: '100%', maxWidth: '700px',
            maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
            padding: '24px', border: '1.5px solid #DBEAFE',
            boxShadow: '0 25px 60px -15px rgba(15, 23, 42, 0.3)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #E2E8F0', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 900, color: '#0F172A', margin: 0 }}>{t.traceTitle}</h3>
                <div style={{ fontSize: '11px', color: '#64748B', fontFamily: 'monospace' }}>Correlation ID: {traceCorrelationId}</div>
              </div>
              <button onClick={() => { setTraceCorrelationId(null); setTraceData(null); }} style={{
                background: '#F1F5F9', border: 'none', borderRadius: '50%',
                width: '30px', height: '30px', fontSize: '16px', cursor: 'pointer', color: '#64748B'
              }}>✕</button>
            </div>

            <div style={{ padding: '16px 0', overflowY: 'auto', flex: 1 }}>
              {traceLoading ? (
                <div style={{ color: '#64748B' }}>Loading correlation trace...</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#0F172A' }}>{t.traceErrorEvents} ({traceData?.error_logs_count || 0})</div>
                  {(traceData?.error_events || []).map(e => (
                    <div key={e.id} style={{
                      padding: '12px', borderRadius: '10px',
                      background: '#FEF2F2', border: '1.5px solid #FECACA', fontSize: '11px'
                    }}>
                      <div style={{ fontWeight: 800, color: '#DC2626' }}>{e.service_name} • {e.error_code}</div>
                      <div style={{ color: '#475569', marginTop: '2px' }}>{e.error_message}</div>
                    </div>
                  ))}

                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#0F172A', marginTop: '10px' }}>{t.traceAuditEvents} ({traceData?.audit_logs_count || 0})</div>
                  {(traceData?.audit_events || []).map(a => (
                    <div key={a.id} style={{
                      padding: '12px', borderRadius: '10px',
                      background: '#F0FDF4', border: '1.5px solid #86EFAC', fontSize: '11px'
                    }}>
                      <div style={{ fontWeight: 800, color: '#15803D' }}>{a.actor} ({a.action}) on {a.resource_type}</div>
                      <div style={{ color: '#475569', marginTop: '2px' }}>Status: {a.status}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
