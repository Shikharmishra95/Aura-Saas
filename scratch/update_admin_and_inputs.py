import re

filepath_app = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'
filepath_css = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.css'
filepath_index_css = r'c:\Users\shiva\Desktop\AAA\frontend\src\index.css'

# 1. Update App.jsx: Admin Overview Banner & Tables to Light Theme + Staff Management OPD Timings
with open(filepath_app, 'r', encoding='utf-8') as f:
    content_app = f.read()

# Update Hero Banner
old_admin_hero = '''                    {/* Compact Hero & Actions Bar */}
                    <div style={{
                      background: 'linear-gradient(to right, #0f172a, #1e1b4b)',
                      border: '1px solid rgba(139,92,246,0.2)',
                      borderRadius: '16px', padding: '16px 24px', marginBottom: '24px',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>🏥</div>
                        <div>
                          <div style={{ color: 'var(--text-main)', fontSize: '20px', fontWeight: 700 }}>{myHosp?.hospital_name || 'Hospital Dashboard'}</div>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px' }}>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>Code: <strong style={{color: 'var(--text-main)'}}>{hospitalId}</strong></span>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>•</span>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>User: <strong style={{color: 'var(--text-main)'}}>{activeHospital?.admin_username || 'Admin'}</strong></span>
                            <span style={{color: '#94a3b8', fontSize: '12px'}}>•</span>
                            {(()=>{
                              const activeHelpline = myHosp?.hospital_phone || activeHospital?.phone || activeHospital?.helpline || activeHospital?.settings?.twilio_helpline;
                              return activeHelpline ? (
                                <span style={{color: '#10b981', fontSize: '12px', fontWeight: 600}}>✅ AI Active</span>
                              ) : (
                                <span style={{color: '#f59e0b', fontSize: '12px', fontWeight: 600}}>⚠️ No AI</span>
                              );
                            })()}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button onClick={() => setEditHospitalProfileModalOpen(true)} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>✏️ Profile</button>
                        <button onClick={() => setEditHospitalSettingsModalOpen(true)} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>⚙️ Settings</button>
                        <button onClick={() => { setActiveTab('admin_leaves'); fetchLeaves(); }} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>📅 Leaves</button>
                        <button onClick={() => setActiveTab('hospital_overview')} style={{ padding: '8px 12px', fontSize: '12px', borderRadius: '8px', background: 'var(--bg-muted)', color: '#e2e8f0', border: '1px solid var(--border)', cursor: 'pointer' }}>📈 Metrics</button>
                        <button onClick={() => setActiveTab('staff_management')} style={{ padding: '8px 16px', fontSize: '12px', borderRadius: '8px', background: '#8b5cf6', color: 'var(--text-main)', border: 'none', fontWeight: 600, cursor: 'pointer' }}>➕ Add Staff</button>
                      </div>
                    </div>'''

new_admin_hero = '''                    {/* Compact Hero & Actions Bar (Clean Light SaaS Theme) */}
                    <div style={{
                      background: '#FFFFFF',
                      border: '1.5px solid #E2E8F0',
                      borderRadius: '20px', padding: '20px 24px', marginBottom: '24px',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px',
                      boxShadow: 'var(--shadow-md)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: '#EFF6FF', border: '1px solid #BFDBFE', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' }}>🏥</div>
                        <div>
                          <div style={{ color: '#0F172A', fontSize: '22px', fontWeight: 800 }}>{myHosp?.hospital_name || 'Hospital Dashboard'}</div>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px' }}>
                            <span style={{color: '#64748B', fontSize: '13px', fontWeight: 600}}>Code: <strong style={{color: '#0F172A'}}>{hospitalId}</strong></span>
                            <span style={{color: '#CBD5E1', fontSize: '13px'}}>•</span>
                            <span style={{color: '#64748B', fontSize: '13px', fontWeight: 600}}>User: <strong style={{color: '#0F172A'}}>{activeHospital?.admin_username || 'Admin'}</strong></span>
                            <span style={{color: '#CBD5E1', fontSize: '13px'}}>•</span>
                            {(()=>{
                              const activeHelpline = myHosp?.hospital_phone || activeHospital?.phone || activeHospital?.helpline || activeHospital?.settings?.twilio_helpline;
                              return activeHelpline ? (
                                <span style={{color: '#166534', background: '#DCFCE7', padding: '2px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 800}}>✅ AI Active</span>
                              ) : (
                                <span style={{color: '#92400E', background: '#FEF3C7', padding: '2px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 800}}>⚠️ No AI</span>
                              );
                            })()}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <button onClick={() => setEditHospitalProfileModalOpen(true)} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '13px', borderRadius: '8px', fontWeight: 600 }}>✏️ Profile</button>
                        <button onClick={() => setEditHospitalSettingsModalOpen(true)} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '13px', borderRadius: '8px', fontWeight: 600 }}>⚙️ Settings</button>
                        <button onClick={() => { setActiveTab('admin_leaves'); fetchLeaves(); }} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '13px', borderRadius: '8px', fontWeight: 600 }}>📅 Leaves</button>
                        <button onClick={() => setActiveTab('hospital_overview')} className="btn btn-secondary" style={{ padding: '8px 14px', fontSize: '13px', borderRadius: '8px', fontWeight: 600 }}>📈 Metrics</button>
                        <button onClick={() => setActiveTab('staff_management')} className="btn btn-primary" style={{ padding: '8px 18px', fontSize: '13px', borderRadius: '8px', fontWeight: 700 }}>➕ Add Staff</button>
                      </div>
                    </div>'''

if old_admin_hero in content_app:
    content_app = content_app.replace(old_admin_hero, new_admin_hero)
    print("Admin Hero Banner updated to Light Theme.")

# Replace dark navy Doctors Directory card & table styling
content_app = content_app.replace("background: '#1e293b'", "background: '#FFFFFF'")
content_app = content_app.replace("border: '1px solid #334155'", "border: '1.5px solid #E2E8F0'")
content_app = content_app.replace("color: '#f8fafc'", "color: '#0F172A'")
content_app = content_app.replace("color: '#cbd5e1'", "color: '#334155'")
content_app = content_app.replace("color: '#94a3b8'", "color: '#475569'")
content_app = content_app.replace("borderBottom: '1px solid #334155'", "borderBottom: '1px solid #E2E8F0'")

# Add Shift 1 and Shift 2 OPD Timings in Staff Management
old_schedule_checkboxes = '''                          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>{t('lbl_sched_days')}</label>
                            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                              {[
                                { id: 1, label: t('day_mon') },
                                { id: 2, label: t('day_tue') },
                                { id: 3, label: t('day_wed') },
                                { id: 4, label: t('day_thu') },
                                { id: 5, label: t('day_fri') },
                                { id: 6, label: t('day_sat') },
                                { id: 7, label: t('day_sun') }
                              ].map(day => (
                                <label key={day.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#FFFFFF', border: '1px solid var(--border)', padding: '8px 14px', borderRadius: '10px', cursor: 'pointer', fontSize: '13px', color: staffScheduleDays.includes(day.id) ? 'var(--color-primary)' : 'var(--text-muted)', borderColor: staffScheduleDays.includes(day.id) ? 'var(--color-primary)' : 'rgba(255,255,255,0.08)' }}>
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
                          </div>'''

new_schedule_checkboxes = '''                          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 700, color: '#0F172A' }}>{t('lbl_sched_days')}</label>
                            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                              {[
                                { id: 1, label: t('day_mon') },
                                { id: 2, label: t('day_tue') },
                                { id: 3, label: t('day_wed') },
                                { id: 4, label: t('day_thu') },
                                { id: 5, label: t('day_fri') },
                                { id: 6, label: t('day_sat') },
                                { id: 7, label: t('day_sun') }
                              ].map(day => (
                                <label key={day.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#FFFFFF', border: '1.5px solid #CBD5E1', padding: '8px 14px', borderRadius: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 600, color: staffScheduleDays.includes(day.id) ? '#2563EB' : '#475569', borderColor: staffScheduleDays.includes(day.id) ? '#2563EB' : '#CBD5E1' }}>
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

                          {/* OPD Shift Timings Builder (Shift 1 & Shift 2) */}
                          <div style={{ gridColumn: '1 / -1', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', background: '#F8FAFC', padding: '18px', borderRadius: '12px', border: '1.5px solid #CBD5E1', marginTop: '6px' }}>
                            <div>
                              <label style={{ fontWeight: 700, fontSize: '13px', color: '#0F172A', marginBottom: '6px', display: 'block' }}>
                                🌅 Shift 1 (Morning OPD Timings)
                              </label>
                              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                <input type="time" className="form-control" value={staffStartTime} onChange={e => setStaffStartTime(e.target.value)} style={{ borderRadius: '8px' }} />
                                <span style={{ fontWeight: 700, color: '#64748B' }}>to</span>
                                <input type="time" className="form-control" value={staffEndTime} onChange={e => setStaffEndTime(e.target.value)} style={{ borderRadius: '8px' }} />
                              </div>
                            </div>

                            <div>
                              <label style={{ fontWeight: 700, fontSize: '13px', color: '#0F172A', marginBottom: '6px', display: 'block' }}>
                                ☀️ Shift 2 (Evening OPD Timings)
                              </label>
                              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                <input type="time" className="form-control" value={staffStartTime2} onChange={e => setStaffStartTime2(e.target.value)} style={{ borderRadius: '8px' }} />
                                <span style={{ fontWeight: 700, color: '#64748B' }}>to</span>
                                <input type="time" className="form-control" value={staffEndTime2} onChange={e => setStaffEndTime2(e.target.value)} style={{ borderRadius: '8px' }} />
                              </div>
                            </div>
                          </div>'''

if old_schedule_checkboxes in content_app:
    content_app = content_app.replace(old_schedule_checkboxes, new_schedule_checkboxes)
    print("Staff Management OPD Shift Timings builder added.")

with open(filepath_app, 'w', encoding='utf-8') as f:
    f.write(content_app)

# 2. Update index.css and App.css for Boxy/Square Input Boxes
with open(filepath_index_css, 'r', encoding='utf-8') as f:
    content_index_css = f.read()

boxy_input_rules = '''
/* Global Boxy / Square Input Field Styling */
input[type="text"],
input[type="number"],
input[type="email"],
input[type="password"],
input[type="date"],
input[type="time"],
select,
textarea,
.form-control {
  border-radius: 8px !important;
  border: 1.5px solid #CBD5E1 !important;
  background-color: #FFFFFF !important;
  color: #0F172A !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  padding: 10px 14px !important;
  height: 42px !important;
  box-shadow: none !important;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out !important;
}

textarea.form-control {
  height: auto !important;
}

input[type="text"]:focus,
input[type="number"]:focus,
input[type="email"]:focus,
input[type="password"]:focus,
input[type="date"]:focus,
input[type="time"]:focus,
select:focus,
textarea:focus,
.form-control:focus {
  border-color: #2563EB !important;
  outline: none !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
}
'''

if "Global Boxy / Square Input Field Styling" not in content_index_css:
    content_index_css += "\n" + boxy_input_rules

with open(filepath_index_css, 'w', encoding='utf-8') as f:
    f.write(content_index_css)

print("Boxy / Square Input CSS rules updated in index.css.")
