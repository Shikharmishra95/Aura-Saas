import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add state variables for Subscription System
state_marker = "  const [showRegisterHospital, setShowRegisterHospital] = useState(false);"
new_states = state_marker + '''
  const [selectedPlan, setSelectedPlan] = useState('STARTER');
  const [showCheckoutModal, setShowCheckoutModal] = useState(false);
  const [upgradingHospId, setUpgradingHospId] = useState(null);
  const [demoCardNum, setDemoCardNum] = useState('4111 2222 3333 4444');
  const [demoCvv, setDemoCvv] = useState('123');
  const [demoExpiry, setDemoExpiry] = useState('12/28');
  const [paymentSuccessMsg, setPaymentSuccessMsg] = useState('');
'''

if 'const [selectedPlan, setSelectedPlan]' not in content:
    content = content.replace(state_marker, new_states)

# 2. Append plan_name in handleRegisterHospital
old_reg_fetch = "formData.append('admin_password', hospAdminPassword);"
new_reg_fetch = "formData.append('admin_password', hospAdminPassword);\n      formData.append('plan_name', selectedPlan);"

if old_reg_fetch in content and "formData.append('plan_name'" not in content:
    content = content.replace(old_reg_fetch, new_reg_fetch)

# 3. Add Upgrade Plan Handler
upgrade_handler = '''
  // Upgrade Hospital Subscription Plan (Demo Payment)
  const handleUpgradePlan = async (hospId, targetPlan) => {
    try {
      const formData = new URLSearchParams();
      formData.append('plan_name', targetPlan);
      const res = await fetch(`${API_BASE}/hospitals/${hospId}/upgrade-plan`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}` 
        },
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        alert(data.message);
        setShowCheckoutModal(false);
        setUpgradingHospId(null);
        fetchHospitals(); // refresh list
      } else {
        alert(data.detail || 'Plan upgrade failed');
      }
    } catch (e) {
      console.error(e);
      alert('Network error: ' + e.message);
    }
  };
'''

if 'const handleUpgradePlan' not in content:
    content = content.replace('  // Delete/Deboard Hospital', upgrade_handler + '\n  // Delete/Deboard Hospital')

# 4. Insert 3-Plan Selection Cards into Hospital Registration Form
plan_cards_html = '''
                    {/* SaaS 3-Plan Selection Cards */}
                    <div style={{ marginBottom: '14px' }}>
                      <label style={{ fontSize: '12px', color: '#0F172A', fontWeight: 800, marginBottom: '8px', display: 'block' }}>Select Subscription Plan *</label>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                        {[
                          { id: 'STARTER', title: '🥉 Starter', price: 'Free', docs: 'Max 1 Doctor', ai: '📵 No AI Line', color: '#64748B' },
                          { id: 'PRO', title: '🥈 Pro AI', price: '₹2,999/mo', docs: 'Max 5 Doctors', ai: '📞 AI Call Bot', color: '#2563EB', popular: True },
                          { id: 'ENTERPRISE', title: '🥇 Enterprise', price: '₹29,999/yr', docs: 'Unlimited Docs', ai: '⚡ Priority AI', color: '#8B5CF6' }
                        ].map(p => (
                          <div 
                            key={p.id}
                            onClick={() => setSelectedPlan(p.id)}
                            style={{
                              border: `2px solid ${selectedPlan === p.id ? p.color : '#CBD5E1'}`,
                              background: selectedPlan === p.id ? `${p.color}10` : '#FFFFFF',
                              borderRadius: '12px', padding: '10px', cursor: 'pointer', textAlign: 'center',
                              position: 'relative', transition: 'all 0.15s'
                            }}
                          >
                            {p.popular && <span style={{ position: 'absolute', top: '-8px', right: '10px', background: '#2563EB', color: '#FFF', fontSize: '9px', fontWeight: 800, padding: '1px 6px', borderRadius: '10px' }}>POPULAR</span>}
                            <div style={{ fontWeight: 800, fontSize: '13px', color: '#0F172A' }}>{p.title}</div>
                            <div style={{ fontWeight: 800, fontSize: '14px', color: p.color, margin: '2px 0' }}>{p.price}</div>
                            <div style={{ fontSize: '10px', color: '#475569', fontWeight: 700 }}>{p.docs}</div>
                            <div style={{ fontSize: '10px', color: '#64748B', marginTop: '2px' }}>{p.ai}</div>
                          </div>
                        ))}
                      </div>
                    </div>
'''

old_pass_input = '<div className="form-group"><label style={{ fontSize: \'12px\', color: \'var(--text-muted)\', marginBottom: \'5px\', display: \'block\' }}>Admin Password *</label><input type="password" className="form-control" value={hospAdminPassword} onChange={e => setHospAdminPassword(e.target.value)} placeholder="••••••••" required style={{ borderRadius: \'9px\' }} /></div>'

if old_pass_input in content and 'Select Subscription Plan' not in content:
    content = content.replace(old_pass_input, old_pass_input + '\n' + plan_cards_html)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Subscription plan selector & upgrade state integrated into App.jsx.")
