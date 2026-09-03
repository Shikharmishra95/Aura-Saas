import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Header Search Input and Dropdown Popup
old_header_search = '''        {/* Top Header Search Bar with Dropdown Popup */}
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
        )}'''

new_header_search = '''        {/* Top Header Search Bar with Dropdown Popup */}
        {token && userRole === 'RECEPTIONIST' && (
          <div style={{ position: 'relative', width: '400px' }}>
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
            {patientSearchQuery.trim().length > 1 && patientSearchResults && patientSearchResults.groups && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '6px',
                background: '#FFFFFF', border: '1.5px solid var(--border)', borderRadius: '14px',
                boxShadow: '0 8px 24px rgba(15, 23, 42, 0.15)', zIndex: 1000, maxHeight: '320px', overflowY: 'auto'
              }}>
                {patientSearchResults.groups.length === 0 ? (
                  <div style={{ padding: '14px', fontSize: '13px', color: '#64748B', textAlign: 'center' }}>
                    ❌ No patient record found matching "{patientSearchQuery}"
                  </div>
                ) : (
                  patientSearchResults.groups.map((group, gIdx) => (
                    <div key={gIdx} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <div style={{ background: '#F8FAFC', padding: '6px 14px', fontSize: '11px', fontWeight: 700, color: '#64748B' }}>
                        📞 Account: {group.phone_number}
                      </div>
                      {group.family_members.map(member => (
                        <div 
                          key={member.id} 
                          onClick={() => {
                            fetchPatientHistory(member.id);
                            setPatientSearchQuery('');
                            setPatientSearchResults(null);
                          }}
                          style={{
                            padding: '10px 14px', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            transition: 'background 0.2s'
                          }}
                          onMouseEnter={e => e.currentTarget.style.background = '#EFF6FF'}
                          onMouseLeave={e => e.currentTarget.style.background = '#FFFFFF'}
                        >
                          <div>
                            <div style={{ fontWeight: 700, fontSize: '13px', color: '#0F172A' }}>{member.name}</div>
                            <div style={{ fontSize: '11px', color: '#64748B' }}>{member.gender || 'Patient'} • Age {member.age || 'N/A'}</div>
                          </div>
                          <span style={{ fontSize: '11px', background: '#EFF6FF', color: '#2563EB', padding: '4px 10px', borderRadius: '6px', fontWeight: 700 }}>
                            View Profile →
                          </span>
                        </div>
                      ))}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}'''

if old_header_search in content:
    content = content.replace(old_header_search, new_header_search)
    print("Header search dropdown updated with handleSearchPatients and patientSearchResults.")

# 2. Remove duplicate Patient Search button from Left Vertical Sidebar
old_sidebar = '''                <button onClick={() => setActiveTab('patient_search')} className={`sidebar-btn ${activeTab === 'patient_search' ? 'active' : ''}`}>
                  <User size={18} /> 🔍 {t('patientSearch')}
                </button>'''

if old_sidebar in content:
    content = content.replace(old_sidebar, '')
    print("Removed duplicate Patient Search button from Left Sidebar.")

# 3. Update Slot Grid styling and rendering in New Booking
old_slot_item_render = '''                              let slotClass = 'available';
                              let slotStyle = { padding: '8px 4px', fontSize: '11px', textAlign: 'center', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.15s' };

                              if (isPast) {
                                slotClass = 'disabled-past';
                                slotStyle = { ...slotStyle, opacity: 0.35, cursor: 'not-allowed', background: '#FFFFFF', color: '#666', border: '1px dashed rgba(255,255,255,0.1)' };
                              } else if (isBusy) {
                                slotClass = 'busy';
                                slotStyle = { ...slotStyle, background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.5)', color: '#fca5a5', cursor: 'not-allowed' };
                              } else if (isSelected) {
                                slotClass = 'selected';
                                slotStyle = { ...slotStyle, background: 'linear-gradient(135deg, #10b981, #059669)', border: '1px solid #10b981', color: 'var(--text-main)', fontWeight: 'bold', boxShadow: '0 0 12px rgba(16, 185, 129, 0.5)' };
                              } else {
                                slotStyle = { ...slotStyle, background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#38bdf8' };
                              }'''

new_slot_item_render = '''                              let slotClass = 'available';
                              let slotStyle = { padding: '9px 6px', fontSize: '12px', textAlign: 'center', borderRadius: '10px', cursor: 'pointer', fontWeight: 600, transition: 'all 0.2s' };

                              if (isPast) {
                                slotClass = 'disabled-past';
                                slotStyle = { ...slotStyle, opacity: 0.5, cursor: 'not-allowed', background: '#F1F5F9', color: '#94A3B8', border: '1px dashed #CBD5E1' };
                              } else if (isBusy) {
                                slotClass = 'busy';
                                slotStyle = { ...slotStyle, background: '#FEE2E2', border: '1px solid #FECACA', color: '#991B1B', cursor: 'not-allowed' };
                              } else if (isSelected) {
                                slotClass = 'selected';
                                slotStyle = { ...slotStyle, background: '#2563EB', border: '1px solid #1D4ED8', color: '#FFFFFF', fontWeight: 800, boxShadow: '0 4px 12px rgba(37,99,235,0.3)' };
                              } else {
                                slotStyle = { ...slotStyle, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8' };
                              }'''

if old_slot_item_render in content:
    content = content.replace(old_slot_item_render, new_slot_item_render)
    print("Updated slot grid pill styles for high-contrast light mode.")

# Ensure slot container uses flex/grid with 4 columns
content = content.replace(
    '''<div className="slots-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px' }}>''',
    '''<div className="slots-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>'''
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx updated with header search fix, sidebar cleanup, and 4-column slot grid.")
