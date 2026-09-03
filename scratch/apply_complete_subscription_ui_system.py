import re

app_jsx_path = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(app_jsx_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Hospital Registration Form label from "Phone / Helpline *" to "Hospital Contact Phone *"
content = content.replace('Phone / Helpline *', 'Hospital Contact Phone *')

# 2. Update AI Active badge logic in Admin Overview banner
old_admin_banner_badge = '''<span className="role-tag">{activeHospital?.is_active ? '✓ ACTIVE' : 'INACTIVE'}</span>'''

# Search for AI Active badge in Admin Overview
old_ai_active_span = '''<span style={{color: '#166534', background: '#DCFCE7', padding: '2px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 800}}>✅ AI Active</span>'''

new_ai_active_span = '''{activeHospital?.ai_voice_enabled ? (
                        <span style={{color: '#166534', background: '#DCFCE7', border: '1px solid #BBF7D0', padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800}}>📞 AI Voice Line Active</span>
                      ) : (
                        <button 
                          onClick={() => alert("🔒 AI Voice Call Booking is disabled on the Starter Trial Plan. Click Upgrade Plan to unlock your AI Voice Helpline!")}
                          style={{color: '#92400E', background: '#FEF3C7', border: '1px solid #FDE68A', padding: '3px 10px', borderRadius: '20px', fontSize: '11px', fontWeight: 800, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px'}}
                        >
                          🔒 AI Line Locked (Upgrade Plan)
                        </button>
                      )}'''

if old_ai_active_span in content:
    content = content.replace(old_ai_active_span, new_ai_active_span)

# 3. Add Subscription Plan Pill Badge & Upgrade button to Admin Overview Banner
old_admin_title_row = '''<h2 style={{ color: '#0F172A', fontSize: '24px', fontWeight: 800, margin: 0 }}>
                            {activeHospital?.name || (hospitalsList || []).find(h => h.id === hospitalId)?.name || 'Hospital Workspace'}
                          </h2>'''

new_admin_title_row = '''<div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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
                            <button 
                              onClick={() => {
                                const nextPlan = activeHospital?.subscription_plan === 'STARTER' ? 'PRO' : 'ENTERPRISE';
                                handleUpgradePlan(hospitalId, nextPlan);
                              }}
                              style={{ background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)', color: '#FFF', border: 'none', padding: '5px 14px', borderRadius: '8px', fontSize: '12px', fontWeight: 800, cursor: 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.3)' }}
                            >
                              ⚡ Upgrade Plan
                            </button>
                          </div>'''

if old_admin_title_row in content:
    content = content.replace(old_admin_title_row, new_admin_title_row)

with open(app_jsx_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Applied complete Subscription UI System & lock badges to App.jsx.")
