import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the Header layout
old_header = '''      {/* Header */}
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
          {token && userRole === 'RECEPTIONIST' && (
            <div style={{ position: 'relative', width: '240px' }}>
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
                  padding: '8px 12px 8px 32px', 
                  fontSize: '13px', 
                  borderRadius: '10px', 
                  border: '1px solid var(--border-input)', 
                  background: '#15181C', 
                  color: '#FFFFFF' 
                }} 
              />
              <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '13px', opacity: 0.6 }}>🔍</span>
            </div>
          )}
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
      </header>'''

new_header = '''      {/* Header */}
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

if old_header in content:
    content = content.replace(old_header, new_header)

# 2. Update 5 KPI Cards Section
old_kpi = '''                  {/* ── 4 Top KPI Metric Cards ── */}
                  <div className="kpi-grid">
                    <div className="kpi-card">
                      <div className="kpi-icon-wrapper" style={{ background: 'rgba(59,130,246,0.15)', color: '#3B82F6' }}>
                        <Calendar size={24} />
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Today Appointments</div>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                          {doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id)).length), 0)}
                        </div>
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-icon-wrapper" style={{ background: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}>
                        <Clock size={24} />
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Pending Collection</div>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                          {doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && a.payment_status === 'PENDING').length), 0)}
                        </div>
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-icon-wrapper" style={{ background: 'rgba(16,185,129,0.15)', color: '#10B981' }}>
                        <CheckCircle size={24} />
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Collected Today</div>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                          {doctorsList.reduce((acc, doc) => acc + (appointments.filter(a => String(a.doctor_id) === String(doc.id) && a.status === 'COMPLETED').length), 0)}
                        </div>
                      </div>
                    </div>
                    <div className="kpi-card">
                      <div className="kpi-icon-wrapper" style={{ background: 'rgba(139,92,246,0.15)', color: '#8B5CF6' }}>
                        <User size={24} />
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Doctors Online</div>
                        <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>
                          {doctorsList.filter(doc => {
                            const isDoctorOnLeave = doctorLeaves.some(l => {
                              if (String(l.doctor_id) !== String(doc.id) || l.status === 'REJECTED') return false;
                              const sd = new Date(l.start_date);
                              const ed = new Date(l.end_date);
                              const target = new Date(selectedScheduleDate);
                              return target >= sd && target <= ed;
                            });
                            return !isDoctorOnLeave;
                          }).length} / {doctorsList.length}
                        </div>
                      </div>
                    </div>
                  </div>'''

new_kpi = '''                  {/* ── 5 High-Contrast KPI Metric Cards ── */}
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

if old_kpi in content:
    content = content.replace(old_kpi, new_kpi)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx updated with high-contrast 5 KPI cards & header.")
