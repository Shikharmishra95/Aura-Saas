import React from 'react';
import { LogOut } from 'lucide-react';

export default function Header({
  token,
  userRole,
  username,
  lang,
  toggleLanguage,
  logout,
  patientSearchQuery,
  setPatientSearchQuery,
  patientSearchResults,
  setPatientSearchResults,
  handleSearchPatients,
  setSelectedPatientRecord,
  activeHospital,
  onOpenProfile,
  t
}) {
  return (
    <header className="dashboard-header" style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '8px 24px',
      background: '#FFFFFF',
      borderBottom: '1px solid #E2E8F0',
      boxShadow: '0 2px 10px rgba(15, 23, 42, 0.04)',
      minHeight: '52px',
      boxSizing: 'border-box'
    }}>
      {/* App Logo & Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px',
          height: '32px',
          borderRadius: '9px',
          background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#FFFFFF',
          fontSize: '16px',
          fontWeight: 900,
          boxShadow: '0 2px 6px rgba(37,99,235,0.25)'
        }}>
          ⚡
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '16px', fontWeight: 900, color: '#0F172A', letterSpacing: '-0.3px' }}>
            AURA <span style={{ color: '#2563EB' }}>SaaS</span>
          </span>
          {activeHospital?.name && userRole !== 'SUPER_ADMIN' && (
            <span style={{
              fontSize: '11px',
              fontWeight: 800,
              color: '#1E40AF',
              background: '#EFF6FF',
              border: '1px solid #BFDBFE',
              padding: '2px 9px',
              borderRadius: '6px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              🏥 {activeHospital.name}
            </span>
          )}
          <span style={{ 
            fontSize: '10px', 
            fontWeight: 800, 
            color: '#64748B', 
            background: '#F1F5F9', 
            padding: '2px 8px', 
            borderRadius: '6px',
            textTransform: 'uppercase',
            letterSpacing: '0.4px'
          }}>
            {userRole === 'RECEPTIONIST' ? 'Receptionist' : userRole === 'DOCTOR' ? 'Doctor Workstation' : userRole === 'ADMIN' ? 'Hospital Admin' : userRole === 'SUPER_ADMIN' ? 'Super Admin' : 'Portal'}
          </span>
        </div>
      </div>

      {/* Top Header Search Bar (Receptionist and Doctor) */}
      {token && (userRole === 'RECEPTIONIST' || userRole === 'DOCTOR') && (
        <div style={{ position: 'relative', width: '380px' }}>
          <input 
            type="text" 
            value={patientSearchQuery}
            onChange={e => {
              const val = e.target.value;
              setPatientSearchQuery(val);
              if (val.trim().length > 1) {
                handleSearchPatients();
              } else {
                setPatientSearchResults(null);
              }
            }}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                e.preventDefault();
                if (patientSearchQuery.trim()) {
                  handleSearchPatients();
                }
              }
            }}
            placeholder="🔍 Search patient by name or phone..." 
            style={{ 
              width: '100%', 
              padding: '7px 12px 7px 34px', 
              fontSize: '12px', 
              borderRadius: '8px', 
              border: '1.5px solid #CBD5E1', 
              background: '#F8FAFC', 
              color: '#0F172A',
              fontWeight: 600
            }} 
          />
          <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '13px', opacity: 0.5 }}>🔍</span>

          {/* Live Search Dropdown Popup */}
          {patientSearchQuery.trim().length > 1 && patientSearchResults && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '6px',
              background: '#FFFFFF', border: '1.5px solid var(--border)', borderRadius: '12px',
              boxShadow: '0 8px 24px rgba(15, 23, 42, 0.15)', zIndex: 1000, maxHeight: '300px', overflowY: 'auto'
            }}>
              {(!patientSearchResults.groups || patientSearchResults.groups.length === 0) ? (
                <div style={{ padding: '12px', fontSize: '12px', color: '#64748B', textAlign: 'center' }}>
                  ❌ No patient record found matching "{patientSearchQuery}"
                </div>
              ) : (
                patientSearchResults.groups.map((group, gIdx) => {
                  const allMembers = group.members || group.family_members || [];
                  const uniqueMembers = [];
                  const seenNames = new Set();
                  allMembers.forEach(m => {
                    const key = (m.name || '').toLowerCase().trim();
                    if (!seenNames.has(key)) {
                      seenNames.add(key);
                      uniqueMembers.push(m);
                    }
                  });

                  return (
                    <div key={gIdx} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <div style={{ background: '#F8FAFC', padding: '5px 12px', fontSize: '10px', fontWeight: 700, color: '#64748B' }}>
                        📞 Account Phone: {group.primary_phone || group.phone_number}
                      </div>
                      {uniqueMembers.map(member => (
                        <div 
                          key={member.id} 
                          onClick={() => {
                            setSelectedPatientRecord(member);
                            setPatientSearchQuery('');
                            setPatientSearchResults(null);
                          }}
                          style={{
                            padding: '8px 12px', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            transition: 'background 0.15s'
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = '#EFF6FF'}
                          onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                        >
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '12px', color: '#0F172A' }}>{member.name}</div>
                            <div style={{ fontSize: '10px', color: '#64748B' }}>{member.gender || 'Patient'} • Age {member.age || 'N/A'}</div>
                          </div>
                          <span style={{ fontSize: '10px', background: '#EFF6FF', color: '#2563EB', padding: '3px 8px', borderRadius: '5px', fontWeight: 700 }}>
                            View Profile →
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}

      {/* Controls & User Profile Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <button 
          onClick={toggleLanguage} 
          style={{ 
            display: 'inline-flex', alignItems: 'center', gap: '5px', 
            padding: '4px 10px', fontSize: '11px', fontWeight: 800,
            borderRadius: '20px', border: '1px solid #CBD5E1',
            background: '#F8FAFC', color: '#1E40AF', cursor: 'pointer',
            boxShadow: '0 1px 3px rgba(15,23,42,0.05)',
            transition: 'all 0.15s'
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#93C5FD'; e.currentTarget.style.background = '#EFF6FF'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = '#CBD5E1'; e.currentTarget.style.background = '#F8FAFC'; }}
          title={lang === 'en' ? 'Switch to Hindi / हिंदी में बदलें' : 'Switch to English'}
        >
          <span style={{ fontSize: '12px' }}>🌐</span>
          <span>{lang === 'en' ? 'हिन्दी' : 'English'}</span>
          <span style={{ 
            background: '#2563EB', color: '#FFFFFF', borderRadius: '8px', 
            padding: '1px 5px', fontSize: '8px', fontWeight: 900, textTransform: 'uppercase' 
          }}>
            {lang === 'en' ? 'EN' : 'HI'}
          </span>
        </button>
        
        {token && (userRole === 'ADMIN' || userRole === 'RECEPTIONIST') && (() => {
          const isExpired = activeHospital?.subscription_status === 'EXPIRED' || activeHospital?.is_expired;
          return (
            <button 
              onClick={() => {
                if (isExpired) {
                  alert("⚠️ Patient Portal is temporarily paused because this hospital's subscription has expired.\n\nPlease renew the subscription via Razorpay on the dashboard to reactivate online booking.");
                  return;
                }
                const hospSlug = (activeHospital?.slug || activeHospital?.id || localStorage.getItem('hospital_id') || '').trim();
                const cleanSlug = hospSlug.replace(/^\/+|\/+$/g, '');
                const url = cleanSlug ? `${window.location.origin}/p/${cleanSlug}` : `${window.location.origin}/p/portal`;
                navigator.clipboard.writeText(url);
                alert("📋 Patient Portal Link copied to clipboard!\nShare this link with your patients to let them book appointments online:\n" + url);
              }}
              style={{
                background: isExpired ? '#FEF2F2' : '#EFF6FF',
                color: isExpired ? '#DC2626' : '#2563EB',
                border: isExpired ? '1px solid #FECACA' : '1px solid #BFDBFE',
                borderRadius: '7px', padding: '4px 10px', fontSize: '11px', fontWeight: 800,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px',
                transition: 'all 0.15s'
              }}
              title={isExpired ? "Patient Portal Paused (Subscription Expired)" : "Copy Patient Portal Booking Link to Share with Patients"}
            >
              {isExpired ? '🔒 Portal Paused' : '🔗 Patient Portal Link'}
            </button>
          );
        })()}

        {token && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '3px 8px 3px 10px', borderRadius: '8px' }}>
            <span style={{ 
              background: userRole === 'SUPER_ADMIN' ? '#EDE9FE' : userRole === 'ADMIN' ? '#DBEAFE' : '#DCFCE7', 
              color: userRole === 'SUPER_ADMIN' ? '#6D28D9' : userRole === 'ADMIN' ? '#1E40AF' : '#166534', 
              padding: '2px 7px', borderRadius: '5px', fontSize: '10px', fontWeight: 800 
            }}>
              {userRole === 'SUPER_ADMIN' ? 'Platform Owner' : userRole}
            </span>
            <button
              onClick={onOpenProfile}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: '#EFF6FF',
                color: '#1E40AF',
                border: '1px solid #BFDBFE',
                padding: '3px 8px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 800,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              title="View Profile & Change Password"
            >
              👤 {username}
            </button>
            <button 
              onClick={logout} 
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                background: '#FEF2F2',
                color: '#DC2626',
                border: '1px solid #FECACA',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 800,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                marginLeft: '4px'
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#DC2626'; e.currentTarget.style.color = '#FFFFFF'; e.currentTarget.style.borderColor = '#DC2626'; }}
              onMouseLeave={e => { e.currentTarget.style.background = '#FEF2F2'; e.currentTarget.style.color = '#DC2626'; e.currentTarget.style.borderColor = '#FECACA'; }}
              title="Sign out of account"
            >
              <LogOut size={13} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
