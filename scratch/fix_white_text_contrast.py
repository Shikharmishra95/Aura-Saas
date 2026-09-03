import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace doctor roster timing text style (Line 2550)
old_roster_style = '''                              ) : (
                                <div style={{ color: 'rgba(255,255,255,0.5)', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                  <div>⏳ Timing: {isWorking ? timingStr.replace(/Timing:/gi, '').trim() : <span style={{ color: '#ef4444', fontWeight: 700 }}>Off Duty / Closed (छुट्टी)</span>}</div>
                                  <div>💰 OPD Fees: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{feesStr}</span></div>
                                  <div style={{ color: isWorking ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                                    Slots: {isWorking ? "72 slots free" : "0 slots free (Off-duty)"}
                                  </div>
                                </div>
                              )'''

new_roster_style = '''                              ) : (
                                <div style={{ color: '#334155', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
                                  <div style={{ color: '#0F172A', fontWeight: 600 }}>⏳ Timing: <span style={{ color: '#2563EB', fontWeight: 700 }}>{isWorking ? timingStr.replace(/Timing:/gi, '').trim() : <span style={{ color: '#DC2626', fontWeight: 700 }}>Off Duty / Closed (छुट्टी)</span>}</span></div>
                                  <div style={{ color: '#0F172A', fontWeight: 600 }}>💰 OPD Fees: <span style={{ color: '#059669', fontWeight: 700 }}>{feesStr}</span></div>
                                  <div style={{ color: isWorking ? '#166534' : '#DC2626', fontWeight: 700 }}>
                                    Slots: {isWorking ? "72 slots free" : "0 slots free (Off-duty)"}
                                  </div>
                                </div>
                              )'''

if old_roster_style in content:
    content = content.replace(old_roster_style, new_roster_style)
    print("Doctor timing & schedule text contrast updated.")

# Replace all translucent white text colors with dark slate theme colors
replacements = [
    ("color: 'rgba(255,255,255,0.7)'", "color: '#334155'"),
    ("color: 'rgba(255,255,255,0.6)'", "color: '#475569'"),
    ("color: 'rgba(255,255,255,0.5)'", "color: '#64748B'"),
    ("color: 'rgba(255,255,255,0.4)'", "color: '#64748B'"),
    ("color: 'rgba(255,255,255,0.3)'", "color: '#94A3B8'"),
    ("borderBottom: '1px solid rgba(255,255,255,0.05)'", "borderBottom: '1px solid #E2E8F0'"),
    ("border: '1px solid rgba(255,255,255,0.05)'", "border: '1px solid #E2E8F0'"),
    ("border: '1px solid rgba(255,255,255,0.06)'", "border: '1px solid #E2E8F0'"),
    ("borderTop: '1px solid rgba(255,255,255,0.05)'", "borderTop: '1px solid #E2E8F0'"),
    ("color: 'rgba(255,255,255,0.2)'", "color: '#94A3B8'"),
]

for old_str, new_str in replacements:
    content = content.replace(old_str, new_str)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx global high-contrast light theme text colors updated.")
