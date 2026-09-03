import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the Header to include Search Bar with Quick Dropdown Popup
old_header = '''      {/* Header */}
      <header className="dashboard-header">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'var(--primary-soft)', border: '1px solid var(--primary-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={22} style={{ color: 'var(--primary)' }} />
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', lineHeight: 1.1 }}>AURA <span style={{ color: 'var(--primary)' }}>SaaS</span></div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>Receptionist Workspace</div>
          </div>
          {userRole === 'ADMIN' && activeHospital?.slug && (
            <a 
              href={`/p/${activeHospital.slug}`} 
              target="_blank" 
              rel="noreferrer" 
              style={{ marginLeft: '12px', fontSize: '12px', color: 'var(--primary)', textDecoration: 'none', background: 'var(--primary-soft)', padding: '4px 10px', borderRadius: '6px', fontWeight: 600, border: '1px solid var(--primary-border)' }}
            >
              🔗 Patient Portal
            </a>
          )}
        </div>
        
        {token && userRole === 'RECEPTIONIST' && (
          <div style={{ position: 'relative', width: '280px', margin: '0 auto' }}>
            <input 
              type="text" 
              value={patientSearchQuery}
              onChange={e => {
                setPatientSearchQuery(e.target.value);
                if (e.target.value && activeTab !== 'patient_search') {
                  setActiveTab('patient_search');
                }
              }}
              placeholder="Search patient or phone..." 
              style={{ 
                width: '100%', 
                padding: '9px 12px 9px 34px', 
                fontSize: '13px', 
                borderRadius: '10px', 
                border: '1.5px solid var(--border-input)', 
                background: '#FFFFFF', 
                color: '#0F172A' 
              }} 
            />
            <span style={{ position: 'absolute', left: '11px', top: '50%', transform: 'translateY(-50%)', fontSize: '13px', opacity: 0.6 }}>🔍</span>
          </div>
        )}

        <div className="header-controls" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
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
              border: '1.5px solid var(--border-input)',
              background: '#FFFFFF',
              color: '#0F172A',
              cursor: 'pointer'
            }}
          >
            <span>🌐</span>
            <span>{lang === 'en' ? 'हिंदी' : 'English'}</span>
          </button>
          
          {token && (
            <div className="user-badge">
              <span className="role-tag">{userRole === 'SUPER_ADMIN' ? 'Platform Owner' : userRole}</span>
              <span style={{ fontWeight: 700, color: '#0F172A' }}>{username}</span>
              <button onClick={logout} className="btn btn-secondary" style={{ padding: '6px 10px', fontSize: '13px', height: '32px' }} title="Logout">
                <LogOut size={14} />
              </button>
            </div>
          )}
        </div>
      </header>'''

new_header = '''      {/* Header */}
      <header className="dashboard-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 28px', background: '#FFFFFF', borderBottom: '1.5px solid var(--border)', position: 'sticky', top: 0, zIndex: 100 }}>
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'var(--primary-soft)', border: '1px solid var(--primary-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={22} style={{ color: 'var(--primary)' }} />
          </div>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#0F172A', lineHeight: 1.1 }}>AURA <span style={{ color: 'var(--primary)' }}>SaaS</span></div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>Receptionist Workspace</div>
          </div>
        </div>
        
        {/* Top Header Search Bar with Dropdown Popup */}
        {token && userRole === 'RECEPTIONIST' && (
          <div style={{ position: 'relative', width: '380px' }}>
            <input 
              type="text" 
              value={patientSearchQuery}
              onChange={e => {
                setPatientSearchQuery(e.target.value);
                if (e.target.value.trim().length > 1) {
                  handlePatientSearch();
                }
              }}
              placeholder="🔍 Search patient by name or phone..." 
              style={{ 
                width: '100%', 
                padding: '9px 14px 9px 36px', 
                fontSize: '13px', 
                borderRadius: '10px', 
                border: '1.5px solid var(--border-input)', 
                background: '#F8FAFC', 
                color: '#0F172A',
                fontWeight: 600
              }} 
            />
            <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', fontSize: '13px', opacity: 0.5 }}>🔍</span>

            {/* Live Search Dropdown Popup */}
            {patientSearchQuery.trim().length > 1 && searchResults.length > 0 && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '6px',
                background: '#FFFFFF', border: '1.5px solid var(--border)', borderRadius: '14px',
                boxShadow: '0 8px 24px rgba(15, 23, 42, 0.15)', zIndex: 1000, maxHeight: '280px', overflowY: 'auto'
              }}>
                {searchResults.map(pt => (
                  <div 
                    key={pt.id} 
                    onClick={() => {
                      fetchPatientHistory(pt.id);
                      setPatientSearchQuery('');
                    }}
                    style={{
                      padding: '12px 16px', borderBottom: '1px solid #F1F5F9', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#EFF6FF'}
                    onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '13px', color: '#0F172A' }}>{pt.patient_name || pt.name}</div>
                      <div style={{ fontSize: '11px', color: '#64748B' }}>📞 {pt.phone_number || pt.phone}</div>
                    </div>
                    <span style={{ fontSize: '11px', background: '#EFF6FF', color: '#2563EB', padding: '4px 10px', borderRadius: '6px', fontWeight: 700 }}>View Account →</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="header-controls" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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
              border: '1.5px solid var(--border-input)',
              background: '#FFFFFF',
              color: '#0F172A',
              cursor: 'pointer'
            }}
          >
            <span>🌐</span>
            <span>{lang === 'en' ? 'हिंदी' : 'English'}</span>
          </button>
          
          {token && (
            <div className="user-badge">
              <span className="role-tag">{userRole === 'SUPER_ADMIN' ? 'Platform Owner' : userRole}</span>
              <span style={{ fontWeight: 700, color: '#0F172A' }}>{username}</span>
              <button onClick={logout} className="btn btn-secondary" style={{ padding: '6px 10px', fontSize: '13px', height: '32px' }} title="Logout">
                <LogOut size={14} />
              </button>
            </div>
          )}
        </div>
      </header>'''

if old_header in content:
    content = content.replace(old_header, new_header)

# 2. Unified Balaji Hospital Card with KPI metrics inside (matching Screenshot 3)
old_banner_and_kpi = '''                  {/* ── Receptionist Portal Header Banner ── */}
                  <div style={{
                    background: '#FFFFFF',
                    borderRadius: '20px', padding: '20px 24px', marginBottom: '20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
                    boxShadow: 'var(--shadow-sm)', border: '1.5px solid var(--border)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                      <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'var(--primary-soft)', border: '1px solid var(--primary-border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' }}>
                        🏨
                      </div>
                      <div>
                        <h2 style={{ color: '#0F172A', fontSize: '22px', fontWeight: 800, margin: 0 }}>
                          {activeHospital?.name || hospitalsList.find(h => h.id === hospitalId)?.name || 'CP Tiwari Hospital'}
                        </h2>
                        <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '2px 0 0 0', fontWeight: 600 }}>
                          {t('recep_dashboard_sub')}
                        </p>
                      </div>
                    </div>
                    {/* Live Clock Card */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ background: '#F8FAFC', border: '1.5px solid var(--border-input)', borderRadius: '12px', padding: '9px 18px', color: '#0F172A', fontSize: '16px', fontWeight: 800, fontFamily: 'monospace', minWidth: '120px', textAlign: 'center' }}>
                        ⏱️ {currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </div>
                      <button onClick={() => setRefreshTrigger(p => p+1)} className="btn btn-primary" style={{ padding: '8px 16px', fontSize: '13px', height: '42px' }}>
                        <RefreshCw size={14} style={{ marginRight: '6px' }} /> Sync Live
                      </button>
                    </div>
                  </div>

                  {/* ── 5 High-Contrast KPI Metric Cards ── */}
                  <div className="kpi-grid-5">
                    <div className="kpi-card-light" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
                      <div className="kpi-header-row">
                        <span style={{ fontSize: '18px' }}>📅</span>
                        <span className="kpi-pill" style={{ background: '#DBEAFE', color: '#1E40AF' }}>Today</span>
                      </div>
                      <div>
                        <div className="kpi-value">{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id)).length), 0)}</div>
                        <div className="kpi-title" style={{ color: '#1E3A8A' }}>Appointments</div>
                      </div>
                    </div>

                    <div className="kpi-card-light" style={{ background: '#FEF3C7', border: '1px solid #FDE68A' }}>
                      <div className="kpi-header-row">
                        <span style={{ fontSize: '18px' }}>💰</span>
                        <span className="kpi-pill" style={{ background: '#FDE68A', color: '#92400E' }}>Pending</span>
                      </div>
                      <div>
                        <div className="kpi-value">₹{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && a.payment_status === 'PENDING').length * (doc.opd_fees || 500)), 0)}</div>
                        <div className="kpi-title" style={{ color: '#78350F' }}>Collection Due</div>
                      </div>
                    </div>

                    <div className="kpi-card-light" style={{ background: '#DCFCE7', border: '1px solid #BBF7D0' }}>
                      <div className="kpi-header-row">
                        <span style={{ fontSize: '18px' }}>✅</span>
                        <span className="kpi-pill" style={{ background: '#BBF7D0', color: '#166534' }}>Paid</span>
                      </div>
                      <div>
                        <div className="kpi-value">₹{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && a.status === 'COMPLETED').length * (doc.opd_fees || 500)), 0)}</div>
                        <div className="kpi-title" style={{ color: '#14532D' }}>Collected Today</div>
                      </div>
                    </div>

                    <div className="kpi-card-light" style={{ background: '#F3E8FF', border: '1px solid #E9D5FF' }}>
                      <div className="kpi-header-row">
                        <span style={{ fontSize: '18px' }}>🩺</span>
                        <span className="kpi-pill" style={{ background: '#E9D5FF', color: '#6B21A8' }}>Live</span>
                      </div>
                      <div>
                        <div className="kpi-value">{doctorsList.filter(doc => {
                          const isDoctorOnLeave = doctorLeaves.some(l => {
                            if (String(l.doctor_id) !== String(doc.id) || l.status === 'REJECTED') return false;
                            const sd = new Date(l.start_date);
                            const ed = new Date(l.end_date);
                            const target = new Date(selectedScheduleDate);
                            return target >= sd && target <= ed;
                          });
                          return !isDoctorOnLeave;
                        }).length} / {doctorsList.length}</div>
                        <div className="kpi-title" style={{ color: '#581C87' }}>Doctors Online</div>
                      </div>
                    </div>

                    <div className="kpi-card-light" style={{ background: '#FEE2E2', border: '1px solid #FECACA' }}>
                      <div className="kpi-header-row">
                        <span style={{ fontSize: '18px' }}>❌</span>
                        <span className="kpi-pill" style={{ background: '#FECACA', color: '#991B1B' }}>Missed</span>
                      </div>
                      <div>
                        <div className="kpi-value">{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && (a.status === 'CANCELLED' || a.status === 'MISSED')).length), 0)}</div>
                        <div className="kpi-title" style={{ color: '#7F1D1D' }}>Missed / Cancelled</div>
                      </div>
                    </div>
                  </div>'''

new_banner_and_kpi = '''                  {/* ── UNIFIED BALAJI HOSPITAL CARD WITH KPI METRICS INSIDE (MATCHING SCREENSHOT 3) ── */}
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
                          <h2 style={{ color: '#0F172A', fontSize: '24px', fontWeight: 800, margin: 0 }}>
                            {activeHospital?.name || hospitalsList.find(h => h.id === hospitalId)?.name || 'CP Tiwari Hospital'}
                          </h2>
                          <p style={{ color: 'var(--text-muted)', fontSize: '13px', margin: '3px 0 0 0', fontWeight: 600 }}>
                            AI Voice Booking System • Live Receptionist
                          </p>
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

                    {/* 5 KPI Metric Cards Embedded Inside Hospital Card */}
                    <div className="kpi-grid-5">
                      <div className="kpi-card-light" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>📅</span>
                          <span className="kpi-pill" style={{ background: '#DBEAFE', color: '#1E40AF' }}>Today</span>
                        </div>
                        <div>
                          <div className="kpi-value">{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id)).length), 0)}</div>
                          <div className="kpi-title" style={{ color: '#1E3A8A' }}>Appointments</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#FEF3C7', border: '1px solid #FDE68A' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>💰</span>
                          <span className="kpi-pill" style={{ background: '#FDE68A', color: '#92400E' }}>Pending</span>
                        </div>
                        <div>
                          <div className="kpi-value">₹{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && a.payment_status === 'PENDING').length * (doc.opd_fees || 500)), 0)}</div>
                          <div className="kpi-title" style={{ color: '#78350F' }}>Collection Due</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#DCFCE7', border: '1px solid #BBF7D0' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>✅</span>
                          <span className="kpi-pill" style={{ background: '#BBF7D0', color: '#166534' }}>Paid</span>
                        </div>
                        <div>
                          <div className="kpi-value">₹{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && a.status === 'COMPLETED').length * (doc.opd_fees || 500)), 0)}</div>
                          <div className="kpi-title" style={{ color: '#14532D' }}>Collected Today</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#F3E8FF', border: '1px solid #E9D5FF' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>🩺</span>
                          <span className="kpi-pill" style={{ background: '#E9D5FF', color: '#6B21A8' }}>Live</span>
                        </div>
                        <div>
                          <div className="kpi-value">{doctorsList.filter(doc => {
                            const isDoctorOnLeave = doctorLeaves.some(l => {
                              if (String(l.doctor_id) !== String(doc.id) || l.status === 'REJECTED') return false;
                              const sd = new Date(l.start_date);
                              const ed = new Date(l.end_date);
                              const target = new Date(selectedScheduleDate);
                              return target >= sd && target <= ed;
                            });
                            return !isDoctorOnLeave;
                          }).length} / {doctorsList.length}</div>
                          <div className="kpi-title" style={{ color: '#581C87' }}>Doctors Online</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#FEE2E2', border: '1px solid #FECACA' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>❌</span>
                          <span className="kpi-pill" style={{ background: '#FECACA', color: '#991B1B' }}>Missed</span>
                        </div>
                        <div>
                          <div className="kpi-value">{doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && (a.status === 'CANCELLED' || a.status === 'MISSED')).length), 0)}</div>
                          <div className="kpi-title" style={{ color: '#7F1D1D' }}>Missed / Cancelled</div>
                        </div>
                      </div>
                    </div>
                  </div>'''

if old_banner_and_kpi in content:
    content = content.replace(old_banner_and_kpi, new_banner_and_kpi)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx Header search bar and Unified Hospital Card updated successfully.")
