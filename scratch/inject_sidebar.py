import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the dashboard tab container for Receptionist to introduce the Left Sidebar Layout
old_layout = '''        {/* DASHBOARD: shown when logged in */}
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
            <div style={{ flexGrow: 1 }}>'''

new_layout = '''        {/* DASHBOARD: shown when logged in */}
        {token && (
          <div style={{ flexGrow: 1, display: 'flex', flexDirection: userRole === 'RECEPTIONIST' ? 'row' : 'column' }}>
            
            {/* 📌 Left Vertical Sidebar for Receptionist Role */}
            {userRole === 'RECEPTIONIST' && (
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
                <button onClick={() => setActiveTab('patient_search')} className={`sidebar-btn ${activeTab === 'patient_search' ? 'active' : ''}`}>
                  <User size={18} /> 🔍 {t('patientSearch')}
                </button>
                <button onClick={() => { setActiveTab('receptionist_leaves'); fetchLeaves(); }} className={`sidebar-btn ${activeTab === 'receptionist_leaves' ? 'active' : ''}`}>
                  <Calendar size={18} /> {t('receptionistLeaves')}
                </button>
                
                <div style={{ marginTop: 'auto', background: 'var(--primary-soft)', border: '1px solid var(--primary-border)', borderRadius: '14px', padding: '14px', textAlign: 'center' }}>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: 'var(--primary)', marginBottom: '3px' }}>🟢 Voice AI System</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>Live Receptionist Active</div>
                </div>
              </aside>
            )}

            {/* Non-Receptionist Top Tabs */}
            {userRole !== 'RECEPTIONIST' && (
              <div className="tab-container">
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
            )}

            {/* Content viewports */}
            <div style={{ flexGrow: 1, padding: userRole === 'RECEPTIONIST' ? '24px' : '0' }}>'''

if old_layout in content:
    content = content.replace(old_layout, new_layout)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("App.jsx Left Sidebar layout replacement successful.")
else:
    print("WARNING: Target string not found in App.jsx.")
