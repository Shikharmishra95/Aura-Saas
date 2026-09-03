import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Super Admin Console Left Sidebar & Hospitals List styling
old_super_sidebar = '''                  {/* LEFT SIDEBAR */}
                  <div style={{
                    width: '220px', flexShrink: 0,
                    background: '#FFFFFF',
                    borderRight: '1px solid rgba(255,255,255,0.07)',
                    padding: '24px 14px',
                    display: 'flex', flexDirection: 'column', gap: '8px'
                  }}>
                    {/* Brand */}
                    <div style={{ marginBottom: '20px', padding: '0 6px' }}>
                      <div style={{ color: 'var(--text-main)', fontWeight: 800, fontSize: '14px' }}>Platform Control</div>
                      <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '11px' }}>AURA SaaS — Owner Panel</div>
                    </div>

                    {/* Nav Items */}
                    {[
                      { id: 'hospitals', icon: '🏥', label: 'Hospitals', count: hospitalsList.length },
                      { id: 'owners', icon: '🔐', label: 'Platform Owners', count: null },
                    ].map(item => (
                      <button key={item.id} onClick={() => { setSuperAdminView(item.id); setSelectedHospital(null); }}
                        style={{
                          background: superAdminView === item.id ? 'rgba(139,92,246,0.18)' : 'transparent',
                          border: `1px solid ${superAdminView === item.id ? 'rgba(139,92,246,0.5)' : 'transparent'}`,
                          borderRadius: '10px', padding: '10px 12px',
                          display: 'flex', alignItems: 'center', gap: '10px',
                          color: superAdminView === item.id ? '#c4b5fd' : 'rgba(255,255,255,0.5)',
                          cursor: 'pointer', fontSize: '13px', fontWeight: 600,
                          textAlign: 'left', width: '100%', transition: 'all 0.15s'
                        }}>
                        <span style={{ fontSize: '16px' }}>{item.icon}</span>
                        <span style={{ flex: 1 }}>{item.label}</span>
                        {item.count !== null && <span style={{ background: 'rgba(139,92,246,0.3)', color: '#c4b5fd', borderRadius: '20px', padding: '1px 7px', fontSize: '10px', fontWeight: 700 }}>{item.count}</span>}
                      </button>
                    ))}

                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', margin: '12px 0' }} />
                    <div style={{ color: 'rgba(255,255,255,0.25)', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', padding: '0 6px' }}>Platform Stats</div>
                    {[
                      { label: 'Total Hospitals', value: hospitalsList.length, color: '#8b5cf6' },
                      { label: 'Active', value: hospitalsList.filter(h => h.is_active).length, color: '#10b981' },
                      { label: 'AI Lines', value: hospitalsList.filter(h => h.helpline).length, color: '#f59e0b' },
                    ].map(stat => (
                      <div key={stat.label} style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: '#64748B', fontSize: '11px' }}>{stat.label}</span>
                        <span style={{ color: stat.color, fontWeight: 800, fontSize: '13px' }}>{stat.value}</span>
                      </div>
                    ))}
                  </div>'''

new_super_sidebar = '''                  {/* LEFT SIDEBAR (High-Contrast Light Theme) */}
                  <div style={{
                    width: '230px', flexShrink: 0,
                    background: '#FFFFFF',
                    borderRight: '1.5px solid #DBEAFE',
                    padding: '24px 14px',
                    display: 'flex', flexDirection: 'column', gap: '8px'
                  }}>
                    {/* Brand */}
                    <div style={{ marginBottom: '20px', padding: '0 6px' }}>
                      <div style={{ color: '#0F172A', fontWeight: 800, fontSize: '15px' }}>Platform Control</div>
                      <div style={{ color: '#64748B', fontSize: '12px', fontWeight: 600 }}>AURA SaaS — Owner Panel</div>
                    </div>

                    {/* Nav Items */}
                    {[
                      { id: 'hospitals', icon: '🏥', label: 'Hospitals', count: hospitalsList.length },
                      { id: 'owners', icon: '🔐', label: 'Platform Owners', count: null },
                    ].map(item => (
                      <button key={item.id} onClick={() => { setSuperAdminView(item.id); setSelectedHospital(null); }}
                        style={{
                          background: superAdminView === item.id ? '#2563EB' : '#F8FAFC',
                          border: `1.5px solid ${superAdminView === item.id ? '#2563EB' : '#CBD5E1'}`,
                          borderRadius: '10px', padding: '10px 12px',
                          display: 'flex', alignItems: 'center', gap: '10px',
                          color: superAdminView === item.id ? '#FFFFFF' : '#334155',
                          cursor: 'pointer', fontSize: '13px', fontWeight: 700,
                          textAlign: 'left', width: '100%', transition: 'all 0.15s'
                        }}>
                        <span style={{ fontSize: '16px' }}>{item.icon}</span>
                        <span style={{ flex: 1 }}>{item.label}</span>
                        {item.count !== null && <span style={{ background: superAdminView === item.id ? 'rgba(255,255,255,0.25)' : '#DBEAFE', color: superAdminView === item.id ? '#FFFFFF' : '#1E40AF', borderRadius: '20px', padding: '1px 8px', fontSize: '11px', fontWeight: 800 }}>{item.count}</span>}
                      </button>
                    ))}

                    <div style={{ borderTop: '1px solid #E2E8F0', margin: '12px 0' }} />
                    <div style={{ color: '#475569', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px', padding: '0 6px' }}>Platform Stats</div>
                    {[
                      { label: 'Total Hospitals', value: hospitalsList.length, color: '#2563EB' },
                      { label: 'Active', value: hospitalsList.filter(h => h.is_active).length, color: '#166534' },
                      { label: 'AI Lines', value: hospitalsList.filter(h => h.helpline).length, color: '#D97706' },
                    ].map(stat => (
                      <div key={stat.label} style={{ padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: '#475569', fontSize: '12px', fontWeight: 600 }}>{stat.label}</span>
                        <span style={{ color: stat.color, fontWeight: 800, fontSize: '14px' }}>{stat.value}</span>
                      </div>
                    ))}
                  </div>'''

if old_super_sidebar in content:
    content = content.replace(old_super_sidebar, new_super_sidebar)

# 2. Add Delete Hospital Button on each hospital card on the Hospitals List view
old_card_view = '''                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ background: hosp.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: hosp.is_active ? '#10b981' : '#ef4444', border: `1px solid ${hosp.is_active ? '#10b98150' : '#ef444450'}`, borderRadius: '20px', padding: '3px 12px', fontSize: '11px', fontWeight: 700 }}>
                                    {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                                  </span>
                                  <span style={{ color: hosp.helpline ? '#f59e0b' : 'rgba(255,255,255,0.2)', fontSize: '11px', fontWeight: 600 }}>
                                    {hosp.helpline ? '📞 AI Active' : '📵 No AI Line'}
                                  </span>
                                  <span style={{ color: c, fontSize: '20px' }}>›</span>
                                </div>'''

new_card_view = '''                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                  <span style={{ background: hosp.is_active ? '#DCFCE7' : '#FEE2E2', color: hosp.is_active ? '#166534' : '#991B1B', border: `1px solid ${hosp.is_active ? '#BBF7D0' : '#FECACA'}`, borderRadius: '20px', padding: '3px 12px', fontSize: '11px', fontWeight: 800 }}>
                                    {hosp.is_active ? '✓ ACTIVE' : '✗ INACTIVE'}
                                  </span>
                                  <span style={{ color: hosp.helpline ? '#D97706' : '#64748B', fontSize: '11px', fontWeight: 700 }}>
                                    {hosp.helpline ? '📞 AI Active' : '📵 No AI Line'}
                                  </span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeleteHospital(hosp.id);
                                    }}
                                    style={{
                                      background: '#FEE2E2', color: '#DC2626', border: '1px solid #FECACA',
                                      borderRadius: '8px', padding: '5px 10px', fontSize: '12px', fontWeight: 700,
                                      cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px'
                                    }}
                                    title="Delete Hospital Tenant"
                                  >
                                    🗑️ Delete
                                  </button>
                                  <span style={{ color: '#2563EB', fontSize: '20px', fontWeight: 800 }}>›</span>
                                </div>'''

if old_card_view in content:
    content = content.replace(old_card_view, new_card_view)
    print("Hospital Delete button added to hospital cards list.")

# 3. Update Edit Doctor Modal background from dark #111827 to Light Theme #FFFFFF
old_edit_doc_modal = "background: '#111827', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '20px', padding: '24px'"
new_edit_doc_modal = "background: '#FFFFFF', border: '1.5px solid #CBD5E1', borderRadius: '20px', padding: '24px', color: '#0F172A'"

if old_edit_doc_modal in content:
    content = content.replace(old_edit_doc_modal, new_edit_doc_modal)
    print("Edit Doctor Modal updated to Light Theme.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx updated with Hospital Delete button & High Contrast Light Theme text.")
