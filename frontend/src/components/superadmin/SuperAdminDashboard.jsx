import React, { useState } from 'react';
import ControlTower from './ControlTower';

export default function SuperAdminDashboard({
  API_BASE,
  token,
  lang = 'en',
  hospitalsList = [],
  fetchHospitals,
  handleToggleHospitalStatus,
  handleDeleteHospital,
  handleSaveTwilioConfig,
  twilioHelplines = {},
  setTwilioHelplines,
  twilioWhatsappNumbers = {},
  setTwilioWhatsappNumbers,
  twilioAccountSids = {},
  setTwilioAccountSids,
  twilioAuthTokens = {},
  setTwilioAuthTokens,
  showTwilioTokens = {},
  setShowTwilioTokens,
  fetchHospitalStaff,
  hospitalStaff = { doctors: [], receptionists: [] },
  setHospitalStaff,
  hospitalStaffLoading = false,
}) {
  const [selectedHospital, setSelectedHospital] = useState(null); // null = list view, hosp obj = detail view
  const [superAdminView, setSuperAdminView] = useState('control_tower'); // 'control_tower' | 'hospitals' | 'owners'
  const [expandedStaffCard, setExpandedStaffCard] = useState(null);

  // Platform Owners Registration state
  const [newOwnerUsername, setNewOwnerUsername] = useState('');
  const [newOwnerEmail, setNewOwnerEmail] = useState('');
  const [newOwnerPassword, setNewOwnerPassword] = useState('');
  const [newOwnerSuccess, setNewOwnerSuccess] = useState('');
  const [newOwnerError, setNewOwnerError] = useState('');

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

  const getWebhookUrl = (hospId) => {
    const domain = window.location.origin.includes('localhost')
      ? 'https://aura-saas-api.herokuapp.com'
      : window.location.origin;
    return `${domain}/api/v1/voice/inbound?hospital_id=${hospId}`;
  };

  return (
    <div style={{ display: 'flex', gap: '0', minHeight: '80vh', textAlign: 'left' }}>
      {/* LEFT SIDEBAR (Luxury Enterprise Light Theme) */}
      <div
        style={{
          width: '240px',
          flexShrink: 0,
          background: '#FFFFFF',
          borderRight: '1.5px solid #DBEAFE',
          padding: '24px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          boxShadow: '2px 0 12px rgba(15, 23, 42, 0.02)'
        }}
      >
        {/* Brand */}
        <div style={{ marginBottom: '18px', padding: '0 8px' }}>
          <div style={{ color: '#0F172A', fontWeight: 900, fontSize: '15px', letterSpacing: '-0.3px' }}>
            Platform Control
          </div>
          <div style={{ color: '#64748B', fontSize: '12px', fontWeight: 600 }}>
            AURA SaaS — Owner Panel
          </div>
        </div>

        {/* Nav Items */}
        {[
          { id: 'control_tower', icon: '🛰️', label: 'Control Tower', count: 'LIVE' },
          { id: 'hospitals', icon: '🏥', label: 'Hospitals & Config', count: hospitalsList.length },
          { id: 'owners', icon: '🔐', label: 'Platform Owners', count: null },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => {
              setSuperAdminView(item.id);
              setSelectedHospital(null);
            }}
            style={{
              background:
                superAdminView === item.id
                  ? 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)'
                  : '#F8FAFC',
              border: `1.5px solid ${superAdminView === item.id ? '#1D4ED8' : '#E2E8F0'}`,
              borderRadius: '12px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              color: superAdminView === item.id ? '#FFFFFF' : '#334155',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 800,
              textAlign: 'left',
              width: '100%',
              boxShadow: superAdminView === item.id ? '0 4px 14px rgba(37, 99, 235, 0.28)' : 'none',
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            <span style={{ fontSize: '16px' }}>{item.icon}</span>
            <span style={{ flex: 1 }}>{item.label}</span>
            {item.count !== null && (
              <span
                style={{
                  background: superAdminView === item.id ? 'rgba(255,255,255,0.25)' : '#DBEAFE',
                  color: superAdminView === item.id ? '#FFFFFF' : '#1E40AF',
                  borderRadius: '20px',
                  padding: '2px 8px',
                  fontSize: '11px',
                  fontWeight: 900
                }}
              >
                {item.count}
              </span>
            )}
          </button>
        ))}

        <div style={{ borderTop: '1px solid #E2E8F0', margin: '14px 0 8px 0' }} />
        <div
          style={{
            color: '#475569',
            fontSize: '11px',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.6px',
            padding: '0 8px',
            marginBottom: '4px'
          }}
        >
          Platform Stats
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {[
            { label: 'Total Hospitals', value: hospitalsList.length, color: '#2563EB', bg: '#EFF6FF', border: '#DBEAFE' },
            { label: 'Active Tenants', value: hospitalsList.filter((h) => h.is_active).length, color: '#166534', bg: '#F0FDF4', border: '#DCFCE7' },
            { label: 'AI Voice Lines', value: hospitalsList.filter((h) => h.helpline).length, color: '#D97706', bg: '#FEF3C7', border: '#FDE68A' },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                padding: '8px 12px',
                borderRadius: '10px',
                background: stat.bg,
                border: `1px solid ${stat.border}`,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <span style={{ color: '#334155', fontSize: '12px', fontWeight: 700 }}>{stat.label}</span>
              <span style={{ color: stat.color, fontWeight: 900, fontSize: '13px' }}>{stat.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div style={{ flex: 1, padding: '0', overflow: 'auto' }}>
        {/* VIEW: CONTROL TOWER */}
        {superAdminView === 'control_tower' && (
          <ControlTower API_BASE={API_BASE} token={token} lang={lang} />
        )}

        {/* VIEW: HOSPITALS LIST */}
        {superAdminView === 'hospitals' && !selectedHospital && (
          <div style={{ padding: '24px 28px' }}>
            <div style={{ marginBottom: '20px' }}>
              <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>
                🏥 Registered Hospitals
              </h2>
              <p style={{ color: '#64748B', fontSize: '13px', margin: '4px 0 0 0' }}>
                Click a hospital to view details, configure Twilio, and see staff.
              </p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {hospitalsList.map((hosp, idx) => {
                const colors = ['#8b5cf6', '#06b6d4', '#f59e0b', '#10b981', '#ec4899'];
                const c = colors[idx % colors.length];
                const isProOrEnt =
                  hosp.subscription_plan === 'PRO' ||
                  hosp.subscription_plan === 'ENTERPRISE' ||
                  hosp.ai_voice_enabled === true;
                return (
                  <div
                    key={hosp.id}
                    onClick={() => {
                      setSelectedHospital(hosp);
                      if (typeof fetchHospitalStaff === 'function') {
                        fetchHospitalStaff(hosp.id);
                      }
                    }}
                    style={{
                      background: `rgba(${
                        c === '#8b5cf6'
                          ? '139,92,246'
                          : c === '#06b6d4'
                          ? '6,182,212'
                          : c === '#f59e0b'
                          ? '245,158,11'
                          : c === '#10b981'
                          ? '16,185,129'
                          : '236,72,153'
                      },0.06)`,
                      border: `1px solid ${c}33`,
                      borderRadius: '14px',
                      padding: '18px 22px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = c)}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = `${c}33`)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <div
                        style={{
                          width: '46px',
                          height: '46px',
                          borderRadius: '14px',
                          background: `${c}22`,
                          border: `1px solid ${c}44`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '20px'
                        }}
                      >
                        🏥
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '15px' }}>
                          {hosp.name}
                        </div>
                        <div
                          style={{
                            color: '#475569',
                            fontSize: '11px',
                            marginTop: '3px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '2px'
                          }}
                        >
                          <div>
                            📞 <strong>Contact Phone:</strong> {hosp.phone || 'N/A'}{' '}
                            {hosp.helpline ? `| 📱 AI Helpline: ${hosp.helpline}` : ''} | 📧{' '}
                            <strong>Admin Email:</strong> {hosp.email || 'N/A'}
                          </div>
                          <div>
                            👤 <strong>Username:</strong> {hosp.admin_username || 'N/A'} | 🔑{' '}
                            <strong>Password:</strong> {hosp.admin_password || 'N/A'}
                          </div>
                          <div>
                            📍 <strong>Address:</strong> {hosp.address || 'N/A'} | 🆔{' '}
                            <strong>Hospital ID:</strong> {hosp.id}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span
                        style={{
                          background: hosp.is_active ? '#DCFCE7' : '#FEE2E2',
                          color: hosp.is_active ? '#166534' : '#991B1B',
                          border: `1px solid ${hosp.is_active ? '#BBF7D0' : '#FECACA'}`,
                          borderRadius: '20px',
                          padding: '3px 12px',
                          fontSize: '11px',
                          fontWeight: 800
                        }}
                      >
                        {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                      </span>
                      <span
                        style={{
                          background: !isProOrEnt ? '#F3F4F6' : hosp.helpline ? '#FEF3C7' : '#EFF6FF',
                          color: !isProOrEnt ? '#6B7280' : hosp.helpline ? '#B45309' : '#1E40AF',
                          border: `1px solid ${
                            !isProOrEnt ? '#E5E7EB' : hosp.helpline ? '#FDE68A' : '#DBEAFE'
                          }`,
                          borderRadius: '20px',
                          padding: '3px 12px',
                          fontSize: '11px',
                          fontWeight: 800
                        }}
                      >
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
                          borderRadius: '8px',
                          padding: '5px 10px',
                          fontSize: '12px',
                          fontWeight: 800,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
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
                          background: '#FEE2E2',
                          color: '#DC2626',
                          border: '1px solid #FECACA',
                          borderRadius: '8px',
                          padding: '5px 10px',
                          fontSize: '12px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
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

        {/* VIEW: HOSPITAL DETAIL (after clicking a hospital) */}
        {superAdminView === 'hospitals' && selectedHospital && (() => {
          const hosp = selectedHospital;
          const isStarter = hosp.subscription_plan === 'STARTER' || hosp.ai_voice_enabled === false;
          const webhook = getWebhookUrl(hosp.id);

          // Calculate 48-Hour SLA Remaining Time
          const createdDate = hosp.created_at ? new Date(hosp.created_at) : new Date();
          const slaDeadline = new Date(createdDate.getTime() + 48 * 60 * 60 * 1000);
          const now = new Date();
          const diffMs = slaDeadline.getTime() - now.getTime();
          const hoursLeft = Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60)));
          const slaStatusBadge =
            hoursLeft > 0
              ? `⏳ Pending AI Line Assignment (${hoursLeft} Hours Left in 48h SLA)`
              : `⚠️ AI Line Assignment Overdue (48h SLA Exceeded)`;

          return (
            <div style={{ padding: '24px 28px' }}>
              {/* Back button + title */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  marginBottom: '22px',
                  flexWrap: 'wrap'
                }}
              >
                <button
                  onClick={() => {
                    setSelectedHospital(null);
                    if (typeof setHospitalStaff === 'function') {
                      setHospitalStaff({ doctors: [], receptionists: [] });
                    }
                  }}
                  style={{
                    background: '#F1F5F9',
                    border: '1px solid #CBD5E1',
                    borderRadius: '8px',
                    padding: '6px 14px',
                    color: '#334155',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: 700
                  }}
                >
                  ← Back
                </button>
                <div>
                  <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>
                    {hosp.name}
                  </h2>
                  <div style={{ color: '#64748B', fontSize: '12px' }}>{hosp.address || 'Address not set'}</div>
                </div>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    onClick={() => {
                      const cleanSlug = (hosp.slug || hosp.id).replace(/^\/+|\/+$/g, '');
                      const url = `${window.location.origin}/p/${cleanSlug}`;
                      navigator.clipboard.writeText(url);
                      alert(`📋 Patient Portal Link copied for ${hosp.name}!\n\n${url}`);
                    }}
                    style={{
                      background: '#EFF6FF',
                      border: '1px solid #BFDBFE',
                      color: '#2563EB',
                      borderRadius: '20px',
                      padding: '6px 14px',
                      fontSize: '12px',
                      fontWeight: 800,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px'
                    }}
                    title="Copy Patient Portal Link for this Hospital"
                  >
                    🔗 Patient Portal Link
                  </button>
                  <button
                    onClick={() => handleToggleHospitalStatus(hosp.id)}
                    style={{
                      background: hosp.is_active ? '#FEF3C7' : '#DCFCE7',
                      border: `1px solid ${hosp.is_active ? '#FDE68A' : '#BBF7D0'}`,
                      color: hosp.is_active ? '#92400E' : '#166534',
                      borderRadius: '20px',
                      padding: '6px 16px',
                      fontSize: '12px',
                      fontWeight: 800,
                      cursor: 'pointer'
                    }}
                  >
                    ⚡ {hosp.is_active ? 'Deactivate Hospital' : 'Activate Hospital'}
                  </button>
                  <span
                    style={{
                      background: hosp.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                      color: hosp.is_active ? '#10b981' : '#ef4444',
                      border: `1px solid ${hosp.is_active ? '#10b98150' : '#ef444450'}`,
                      borderRadius: '20px',
                      padding: '4px 14px',
                      fontSize: '12px',
                      fontWeight: 700
                    }}
                  >
                    {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                  </span>
                  <button
                    onClick={() => handleDeleteHospital(hosp.id)}
                    style={{
                      background: '#FEE2E2',
                      border: '1px solid #FECACA',
                      color: '#DC2626',
                      borderRadius: '20px',
                      padding: '6px 16px',
                      fontSize: '12px',
                      fontWeight: 800,
                      cursor: 'pointer'
                    }}
                  >
                    🗑️ Delete Hospital
                  </button>
                </div>
              </div>

              {/* Info pills */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '12px',
                  marginBottom: '20px'
                }}
              >
                {[
                  { icon: '🪪', label: 'Hospital ID', value: hosp.id, color: '#8b5cf6' },
                  { icon: '📞', label: 'Contact Phone', value: hosp.phone || 'Not set', color: '#06b6d4' },
                  {
                    icon: '💳',
                    label: 'Plan & AI Voice',
                    value: isStarter
                      ? 'Starter (AI Locked)'
                      : hosp.helpline
                      ? `Pro/Ent (${hosp.helpline})`
                      : `Pro/Ent (${hoursLeft}h SLA)`,
                    color: isStarter ? '#d97706' : hosp.helpline ? '#10b981' : '#f59e0b'
                  },
                  { icon: '✉️', label: 'Email', value: hosp.email || 'Not set', color: '#f59e0b' },
                  { icon: '👤', label: 'Admin Username', value: hosp.admin_username || 'N/A', color: '#10b981' },
                  { icon: '🔑', label: 'Admin Password', value: hosp.admin_password || 'N/A', color: '#ec4899' },
                ].map((pill) => (
                  <div
                    key={pill.label}
                    style={{
                      background: '#FFFFFF',
                      border: '1px solid var(--border)',
                      borderRadius: '12px',
                      padding: '12px 16px'
                    }}
                  >
                    <div
                      style={{
                        color: '#64748B',
                        fontSize: '10px',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        marginBottom: '5px'
                      }}
                    >
                      {pill.icon} {pill.label}
                    </div>
                    <div
                      style={{
                        color: pill.color,
                        fontSize: '13px',
                        fontWeight: 700,
                        fontFamily: 'monospace',
                        wordBreak: 'break-all'
                      }}
                    >
                      {pill.value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Twilio & WhatsApp Config */}
              <div
                style={{
                  background: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '14px',
                  padding: '18px',
                  marginBottom: '20px'
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: '14px',
                    flexWrap: 'wrap',
                    gap: '8px'
                  }}
                >
                  <div
                    style={{
                      color: '#0F172A',
                      fontWeight: 800,
                      fontSize: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <span>📡</span>
                    <span>Twilio AI Helpline & WhatsApp Integration</span>
                  </div>
                  {isStarter ? (
                    <span
                      style={{
                        background: '#FEF3C7',
                        color: '#92400E',
                        border: '1px solid #FDE68A',
                        padding: '3px 10px',
                        borderRadius: '20px',
                        fontSize: '11px',
                        fontWeight: 800
                      }}
                    >
                      🔒 AI Voice Locked (Starter Free Trial)
                    </span>
                  ) : hosp.helpline ? (
                    <span
                      style={{
                        background: '#DCFCE7',
                        color: '#166534',
                        border: '1px solid #BBF7D0',
                        padding: '3px 10px',
                        borderRadius: '20px',
                        fontSize: '11px',
                        fontWeight: 800
                      }}
                    >
                      🟢 AI Voice Line Active: {hosp.helpline}
                    </span>
                  ) : (
                    <span
                      style={{
                        background: '#FEF3C7',
                        color: '#B45309',
                        border: '1px solid #FDE68A',
                        padding: '3px 10px',
                        borderRadius: '20px',
                        fontSize: '11px',
                        fontWeight: 800
                      }}
                    >
                      {slaStatusBadge}
                    </span>
                  )}
                </div>

                {isStarter ? (
                  <div
                    style={{
                      background: '#FFFBEB',
                      border: '1.5px solid #FDE68A',
                      borderRadius: '10px',
                      padding: '12px 16px',
                      color: '#92400E',
                      fontSize: '12px',
                      fontWeight: 700,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    <span>ℹ️</span>
                    <span>
                      This hospital is on the <strong>Starter Plan (15-Day Free Trial)</strong>. AI Voice helpline is locked for this tier. When the hospital upgrades to <strong>Pro AI</strong> or <strong>Enterprise</strong>, you can assign a dedicated Twilio AI helpline number here.
                    </span>
                  </div>
                ) : (
                  <>
                    {/* autoComplete=off form wrapper with hidden dummy fields to absorb Chrome autofill */}
                    <form autoComplete="off" onSubmit={(e) => e.preventDefault()} style={{ margin: 0 }}>
                      <input type="text" style={{ display: 'none' }} autoComplete="username" tabIndex={-1} readOnly />
                      <input type="password" style={{ display: 'none' }} autoComplete="current-password" tabIndex={-1} readOnly />
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '1fr 1fr 1fr 1fr auto',
                          gap: '10px',
                          alignItems: 'end',
                          marginBottom: '14px'
                        }}
                      >
                        <div className="form-group" style={{ margin: 0 }}>
                          <label
                            style={{
                              fontSize: '10px',
                              color: '#64748B',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                              marginBottom: '5px',
                              display: 'block'
                            }}
                          >
                            Helpline Number
                          </label>
                          <input
                            type="text"
                            className="form-control"
                            autoComplete="off"
                            name="twilio_helpline_x"
                            style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                            placeholder="+91XXXXXXXXXX"
                            value={
                              twilioHelplines[hosp.id] !== undefined
                                ? twilioHelplines[hosp.id]
                                : hosp.helpline || ''
                            }
                            onChange={(e) =>
                              setTwilioHelplines((p) => ({ ...p, [hosp.id]: e.target.value }))
                            }
                          />
                        </div>
                        <div className="form-group" style={{ margin: 0 }}>
                          <label
                            style={{
                              fontSize: '10px',
                              color: '#64748B',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                              marginBottom: '5px',
                              display: 'block'
                            }}
                          >
                            WhatsApp Number (Master Line)
                          </label>
                          <input
                            type="text"
                            className="form-control"
                            autoComplete="off"
                            name="twilio_whatsapp_x"
                            style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                            placeholder="whatsapp:+1415..."
                            value={
                              twilioWhatsappNumbers[hosp.id] !== undefined
                                ? twilioWhatsappNumbers[hosp.id]
                                : hosp.whatsapp_number || 'whatsapp:+14155238886'
                            }
                            onChange={(e) =>
                              setTwilioWhatsappNumbers((p) => ({ ...p, [hosp.id]: e.target.value }))
                            }
                          />
                        </div>
                        <div className="form-group" style={{ margin: 0 }}>
                          <label
                            style={{
                              fontSize: '10px',
                              color: '#64748B',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                              marginBottom: '5px',
                              display: 'block'
                            }}
                          >
                            Account SID
                          </label>
                          <input
                            type="text"
                            className="form-control"
                            autoComplete="off"
                            name="twilio_sid_x"
                            style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)' }}
                            placeholder="ACxxxxxxxx..."
                            value={
                              twilioAccountSids[hosp.id] !== undefined
                                ? twilioAccountSids[hosp.id]
                                : hosp.twilio_account_sid || ''
                            }
                            onChange={(e) =>
                              setTwilioAccountSids((p) => ({ ...p, [hosp.id]: e.target.value }))
                            }
                          />
                        </div>
                        <div className="form-group" style={{ margin: 0 }}>
                          <label
                            style={{
                              fontSize: '10px',
                              color: '#64748B',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                              marginBottom: '5px',
                              display: 'block'
                            }}
                          >
                            Auth Token
                            <button
                              type="button"
                              onClick={() =>
                                setShowTwilioTokens((p) => ({ ...p, [hosp.id]: !p[hosp.id] }))
                              }
                              style={{
                                marginLeft: '6px',
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '10px',
                                color: '#94a3b8',
                                fontWeight: 600,
                                padding: 0
                              }}
                            >
                              {showTwilioTokens?.[hosp.id] ? '🙈 Hide' : '👁 Show'}
                            </button>
                          </label>
                          <input
                            type="text"
                            className="form-control"
                            autoComplete="off"
                            name="twilio_token_x"
                            style={{
                              padding: '8px 12px',
                              fontSize: '12px',
                              borderRadius: '8px',
                              background: 'var(--bg-muted)',
                              WebkitTextSecurity: showTwilioTokens?.[hosp.id] ? 'none' : 'disc'
                            }}
                            placeholder="Enter Auth Token"
                            value={
                              twilioAuthTokens[hosp.id] !== undefined
                                ? twilioAuthTokens[hosp.id]
                                : hosp.twilio_auth_token || ''
                            }
                            onChange={(e) =>
                              setTwilioAuthTokens((p) => ({ ...p, [hosp.id]: e.target.value }))
                            }
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => handleSaveTwilioConfig(hosp.id)}
                          style={{
                            background: 'linear-gradient(135deg, #fb923c, #f59e0b)',
                            border: 'none',
                            borderRadius: '10px',
                            padding: '10px 18px',
                            color: '#1a1a1a',
                            fontWeight: 700,
                            fontSize: '12px',
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                            height: '36px'
                          }}
                        >
                          💾 Save & Inject
                        </button>
                      </div>
                    </form>

                    {/* Webhook URLs Grid */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '10px',
                        marginTop: '10px',
                        paddingTop: '10px',
                        borderTop: '1px solid #E2E8F0'
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: '10px',
                            color: '#0284C7',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            marginBottom: '4px'
                          }}
                        >
                          📞 Twilio Voice Webhook URL
                        </div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <input
                            type="text"
                            readOnly
                            className="form-control"
                            style={{
                              fontSize: '11px',
                              padding: '5px 8px',
                              background: '#F8FAFC',
                              fontFamily: 'monospace',
                              color: '#475569'
                            }}
                            value={`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/voice/inbound?hospital_id=${hosp.id}`}
                          />
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => {
                              navigator.clipboard.writeText(
                                `https://grape-fifty-unfitted.ngrok-free.dev/api/v1/voice/inbound?hospital_id=${hosp.id}`
                              );
                              alert('Voice Webhook copied!');
                            }}
                          >
                            Copy
                          </button>
                        </div>
                      </div>
                      <div>
                        <div
                          style={{
                            fontSize: '10px',
                            color: '#2563EB',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            marginBottom: '4px'
                          }}
                        >
                          💬 WhatsApp Webhook URL
                        </div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <input
                            type="text"
                            readOnly
                            className="form-control"
                            style={{
                              fontSize: '11px',
                              padding: '5px 8px',
                              background: '#F8FAFC',
                              fontFamily: 'monospace',
                              color: '#475569'
                            }}
                            value={`https://grape-fifty-unfitted.ngrok-free.dev/api/v1/whatsapp/webhook?hospital_id=${hosp.id}`}
                          />
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => {
                              navigator.clipboard.writeText(
                                `https://grape-fifty-unfitted.ngrok-free.dev/api/v1/whatsapp/webhook?hospital_id=${hosp.id}`
                              );
                              alert('WhatsApp Webhook copied!');
                            }}
                          >
                            Copy
                          </button>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Staff Section: Doctors + Receptionists */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '18px' }}>
                {/* Doctors */}
                <div
                  style={{
                    background: 'rgba(16,185,129,0.04)',
                    border: '1px solid rgba(16,185,129,0.2)',
                    borderRadius: '16px',
                    padding: '18px'
                  }}
                >
                  <div
                    style={{
                      color: '#10b981',
                      fontWeight: 800,
                      fontSize: '14px',
                      marginBottom: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    👨‍⚕️ Doctors
                    <span
                      style={{
                        background: 'rgba(16,185,129,0.2)',
                        color: '#10b981',
                        borderRadius: '20px',
                        padding: '1px 8px',
                        fontSize: '11px'
                      }}
                    >
                      {hospitalStaff.doctors.length}
                    </span>
                  </div>
                  {hospitalStaffLoading ? (
                    <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
                      Loading...
                    </div>
                  ) : hospitalStaff.doctors.length === 0 ? (
                    <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
                      No doctors registered
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {hospitalStaff.doctors.map((doc) => (
                        <div
                          key={doc.id}
                          onClick={() => setExpandedStaffCard(expandedStaffCard === doc.id ? null : doc.id)}
                          style={{
                            background: '#FFFFFF',
                            border: `1px solid ${
                              expandedStaffCard === doc.id ? 'rgba(16,185,129,0.5)' : 'rgba(255,255,255,0.08)'
                            }`,
                            borderRadius: '10px',
                            padding: '12px',
                            cursor: 'pointer',
                            transition: 'all 0.15s'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '13px' }}>
                                Dr. {doc.first_name} {doc.last_name}
                              </div>
                              <div style={{ color: '#10b981', fontSize: '11px', marginTop: '1px' }}>
                                {doc.department}
                              </div>
                            </div>
                            <span style={{ color: '#94A3B8', fontSize: '14px' }}>
                              {expandedStaffCard === doc.id ? '▲' : '▼'}
                            </span>
                          </div>
                          {expandedStaffCard === doc.id && (
                            <div
                              style={{
                                marginTop: '10px',
                                borderTop: '1px solid rgba(255,255,255,0.08)',
                                paddingTop: '10px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '5px'
                              }}
                            >
                              {[
                                { label: '🔑 Username', value: doc.username },
                                { label: '✉️ Email', value: doc.email },
                                { label: '📞 Phone', value: doc.phone || 'N/A' },
                                { label: '📋 License', value: doc.license_number || 'N/A' },
                                { label: '💰 OPD Fee', value: `₹${doc.opd_fees}` },
                              ].map((info) => (
                                <div key={info.label} style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                                  <span style={{ color: '#64748B', minWidth: '90px' }}>{info.label}:</span>
                                  <span
                                    style={{
                                      color: 'var(--text-main)',
                                      fontWeight: 600,
                                      wordBreak: 'break-all'
                                    }}
                                  >
                                    {info.value}
                                  </span>
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
                <div
                  style={{
                    background: 'rgba(6,182,212,0.04)',
                    border: '1px solid rgba(6,182,212,0.2)',
                    borderRadius: '16px',
                    padding: '18px'
                  }}
                >
                  <div
                    style={{
                      color: '#06b6d4',
                      fontWeight: 800,
                      fontSize: '14px',
                      marginBottom: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    🖥️ Receptionists
                    <span
                      style={{
                        background: 'rgba(6,182,212,0.2)',
                        color: '#06b6d4',
                        borderRadius: '20px',
                        padding: '1px 8px',
                        fontSize: '11px'
                      }}
                    >
                      {hospitalStaff.receptionists.length}
                    </span>
                  </div>
                  {hospitalStaffLoading ? (
                    <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
                      Loading...
                    </div>
                  ) : hospitalStaff.receptionists.length === 0 ? (
                    <div style={{ color: '#94A3B8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
                      No receptionists registered
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {hospitalStaff.receptionists.map((rec) => (
                        <div
                          key={rec.id}
                          onClick={() => setExpandedStaffCard(expandedStaffCard === rec.id ? null : rec.id)}
                          style={{
                            background: '#FFFFFF',
                            border: `1px solid ${
                              expandedStaffCard === rec.id ? 'rgba(6,182,212,0.5)' : 'rgba(255,255,255,0.08)'
                            }`,
                            borderRadius: '10px',
                            padding: '12px',
                            cursor: 'pointer',
                            transition: 'all 0.15s'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <div style={{ color: 'var(--text-main)', fontWeight: 700, fontSize: '13px' }}>
                                {rec.first_name} {rec.last_name}
                              </div>
                              <div style={{ color: '#06b6d4', fontSize: '11px', marginTop: '1px' }}>
                                Receptionist
                              </div>
                            </div>
                            <span style={{ color: '#94A3B8', fontSize: '14px' }}>
                              {expandedStaffCard === rec.id ? '▲' : '▼'}
                            </span>
                          </div>
                          {expandedStaffCard === rec.id && (
                            <div
                              style={{
                                marginTop: '10px',
                                borderTop: '1px solid rgba(255,255,255,0.08)',
                                paddingTop: '10px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '5px'
                              }}
                            >
                              {[
                                { label: '🔑 Username', value: rec.username },
                                { label: '✉️ Email', value: rec.email },
                              ].map((info) => (
                                <div key={info.label} style={{ display: 'flex', gap: '8px', fontSize: '11px' }}>
                                  <span style={{ color: '#64748B', minWidth: '90px' }}>{info.label}:</span>
                                  <span
                                    style={{
                                      color: 'var(--text-main)',
                                      fontWeight: 600,
                                      wordBreak: 'break-all'
                                    }}
                                  >
                                    {info.value}
                                  </span>
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

        {/* VIEW: PLATFORM OWNERS MANAGEMENT */}
        {superAdminView === 'owners' && (
          <div>
            <div style={{ marginBottom: '22px' }}>
              <h2 style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 800, margin: 0 }}>
                🔐 Platform Owner Accounts
              </h2>
              <p style={{ color: '#64748B', fontSize: '13px', margin: '4px 0 0 0' }}>
                Register new Platform Owner (SUPER_ADMIN) logins for this platform.
              </p>
            </div>

            {newOwnerSuccess && (
              <div
                style={{
                  color: '#34d399',
                  fontSize: '13px',
                  background: 'rgba(52,211,153,0.1)',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  marginBottom: '18px',
                  border: '1px solid rgba(52,211,153,0.2)'
                }}
              >
                ✅ {newOwnerSuccess}
              </div>
            )}
            {newOwnerError && (
              <div
                style={{
                  color: '#f87171',
                  fontSize: '13px',
                  background: 'rgba(239,68,68,0.1)',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  marginBottom: '18px',
                  border: '1px solid rgba(239,68,68,0.2)'
                }}
              >
                ⚠️ {newOwnerError}
              </div>
            )}

            <div
              style={{
                background: 'rgba(139,92,246,0.06)',
                border: '1px solid rgba(139,92,246,0.2)',
                borderRadius: '18px',
                padding: '24px',
                marginBottom: '24px'
              }}
            >
              <div style={{ color: '#c4b5fd', fontWeight: 700, fontSize: '14px', marginBottom: '6px' }}>
                ➕ Register New Platform Owner
              </div>
              <div style={{ color: '#64748B', fontSize: '12px', marginBottom: '18px' }}>
                This creates a new database-backed SUPER_ADMIN account. The new owner can log in from Platform Owner tab and manage all hospitals.
              </div>
              <form onSubmit={handleRegisterSuperAdmin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label
                      style={{
                        fontSize: '11px',
                        color: '#64748B',
                        fontWeight: 700,
                        marginBottom: '6px',
                        display: 'block',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}
                    >
                      Username *
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      required
                      style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                      placeholder="e.g. admin_shiva"
                      value={newOwnerUsername}
                      onChange={(e) => setNewOwnerUsername(e.target.value)}
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label
                      style={{
                        fontSize: '11px',
                        color: '#64748B',
                        fontWeight: 700,
                        marginBottom: '6px',
                        display: 'block',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}
                    >
                      Email *
                    </label>
                    <input
                      type="email"
                      className="form-control"
                      required
                      style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                      placeholder="e.g. admin@gmail.com"
                      value={newOwnerEmail}
                      onChange={(e) => setNewOwnerEmail(e.target.value)}
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label
                      style={{
                        fontSize: '11px',
                        color: '#64748B',
                        fontWeight: 700,
                        marginBottom: '6px',
                        display: 'block',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}
                    >
                      Password *
                    </label>
                    <input
                      type="password"
                      className="form-control"
                      required
                      style={{ padding: '10px 14px', fontSize: '13px', borderRadius: '10px', background: 'var(--bg-muted)' }}
                      placeholder="••••••••"
                      value={newOwnerPassword}
                      onChange={(e) => setNewOwnerPassword(e.target.value)}
                    />
                  </div>
                </div>
                <div>
                  <button
                    type="submit"
                    style={{
                      background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
                      border: 'none',
                      borderRadius: '10px',
                      padding: '12px 28px',
                      color: 'var(--text-main)',
                      fontWeight: 800,
                      fontSize: '14px',
                      cursor: 'pointer'
                    }}
                  >
                    ➕ Create Platform Owner Account
                  </button>
                </div>
              </form>
            </div>

            {/* Setup Guide */}
            <div
              style={{
                background: 'rgba(251,146,60,0.06)',
                border: '1px solid rgba(251,146,60,0.2)',
                borderRadius: '14px',
                padding: '18px 22px'
              }}
            >
              <div style={{ color: '#fb923c', fontWeight: 700, fontSize: '13px', marginBottom: '10px' }}>
                📋 Setup Guide — How to Activate AI Helpline
              </div>
              <ol style={{ color: '#475569', fontSize: '12px', paddingLeft: '16px', lineHeight: '1.9', margin: 0 }}>
                <li>
                  Buy a Twilio number → go to <strong style={{ color: 'var(--text-main)' }}>console.twilio.com</strong>
                </li>
                <li>
                  Go to Hospitals → click your hospital → enter Helpline, SID, Token → click{' '}
                  <strong style={{ color: '#fb923c' }}>Save & Inject</strong>
                </li>
                <li>
                  Copy the Webhook URL → paste in Twilio Console under{' '}
                  <strong style={{ color: 'var(--text-main)' }}>"A call comes in"</strong>
                </li>
                <li>Test by calling the Twilio number — AI receptionist will answer!</li>
              </ol>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
