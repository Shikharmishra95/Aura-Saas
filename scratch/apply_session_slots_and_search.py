import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Header Search Dropdown to match backend JSON keys (group.primary_phone, group.members)
old_dropdown = '''            {/* Live Search Dropdown Popup */}
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
            )}'''

new_dropdown = '''            {/* Live Search Dropdown Popup */}
            {patientSearchQuery.trim().length > 1 && patientSearchResults && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '6px',
                background: '#FFFFFF', border: '1.5px solid var(--border)', borderRadius: '14px',
                boxShadow: '0 8px 24px rgba(15, 23, 42, 0.15)', zIndex: 1000, maxHeight: '320px', overflowY: 'auto'
              }}>
                {(!patientSearchResults.groups || patientSearchResults.groups.length === 0) ? (
                  <div style={{ padding: '14px', fontSize: '13px', color: '#64748B', textAlign: 'center' }}>
                    ❌ No patient record found matching "{patientSearchQuery}"
                  </div>
                ) : (
                  patientSearchResults.groups.map((group, gIdx) => (
                    <div key={gIdx} style={{ borderBottom: '1px solid #F1F5F9' }}>
                      <div style={{ background: '#F8FAFC', padding: '6px 14px', fontSize: '11px', fontWeight: 700, color: '#64748B' }}>
                        📞 Account Phone: {group.primary_phone || group.phone_number}
                      </div>
                      {(group.members || group.family_members || []).map(member => (
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
            )}'''

if old_dropdown in content:
    content = content.replace(old_dropdown, new_dropdown)
    print("Header dropdown mapping updated successfully.")

# 2. Update New Booking Time Slots Rendering (Grouped by Sessions in 4-Column Grids)
old_slots_block = '''                          <div className="slots-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                            {(() => {
                              if (newBookingAllSlots.length === 0) {
                                const onLeave = leavesList.find(l => l.doctor_id === bookingDoctorId && l.status === 'APPROVED' && new Date(l.start_date) <= new Date(bookingDate) && new Date(l.end_date) >= new Date(bookingDate));
                                if (onLeave) {
                                  const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  return (
                                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '15px', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                                      <strong style={{fontSize: '14px'}}>{t('doc_on_leave_banner')}</strong><br />
                                      <span style={{fontSize: '13px', marginTop: '4px', display: 'inline-block'}}>This doctor is on leave from {sd} to {ed}.</span>
                                    </div>
                                  );
                                }
                                return (
                                  <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '15px', color: '#ef4444', fontStyle: 'italic', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                                    Doctor is unavailable today (No active OPD schedule).
                                  </div>
                                );
                              }
                              return newBookingAllSlots.map(time => {
                              const slot24 = convertSlotTo24h(time);
                              const now = new Date();
                              // Convert local browser time to IST (UTC+5:30)
                              const istOffset = 5.5 * 60 * 60 * 1000;
                              const istDate = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
                              const todayStr = istDate.toISOString().split('T')[0];
                              const current24 = `${String(istDate.getHours()).padStart(2, '0')}:${String(istDate.getMinutes()).padStart(2, '0')}`;
                              
                              const isPast = (bookingDate === todayStr && slot24 <= current24);
                              const isBusy = newBookingBookedSlots.includes(time);
                              const isSelected = selectedNewBookingSlot === time;

                              let slotClass = 'available';
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
                              }

                              return (
                                <div
                                  key={time}
                                  className={`slot-item ${slotClass}`}
                                  style={slotStyle}
                                  onClick={() => {
                                    if (!isPast && !isBusy) {
                                      setSelectedNewBookingSlot(time);
                                      setBookingTime(slot24);
                                    }
                                  }}
                                >
                                  {time} {isPast ? '(Passed)' : ''}
                                </div>
                              );
                            })
                            })()}
                          </div>'''

new_slots_block = '''                          <div>
                            {(() => {
                              if (newBookingAllSlots.length === 0) {
                                const onLeave = leavesList.find(l => l.doctor_id === bookingDoctorId && l.status === 'APPROVED' && new Date(l.start_date) <= new Date(bookingDate) && new Date(l.end_date) >= new Date(bookingDate));
                                if (onLeave) {
                                  const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', {day: 'numeric', month: 'short'});
                                  return (
                                    <div style={{ textAlign: 'center', padding: '15px', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                                      <strong style={{fontSize: '14px'}}>{t('doc_on_leave_banner')}</strong><br />
                                      <span style={{fontSize: '13px', marginTop: '4px', display: 'inline-block'}}>This doctor is on leave from {sd} to {ed}.</span>
                                    </div>
                                  );
                                }
                                return (
                                  <div style={{ textAlign: 'center', padding: '15px', color: '#ef4444', fontStyle: 'italic', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                                    Doctor is unavailable today (No active OPD schedule).
                                  </div>
                                );
                              }

                              // Group slots into Morning, Afternoon, Evening sessions
                              const morningSlots = [];
                              const afternoonSlots = [];
                              const eveningSlots = [];

                              newBookingAllSlots.forEach(time => {
                                const s24 = convertSlotTo24h(time);
                                const hour = parseInt(s24.split(':')[0], 10);
                                if (hour < 13) {
                                  morningSlots.push(time);
                                } else if (hour >= 13 && hour < 17) {
                                  afternoonSlots.push(time);
                                } else {
                                  eveningSlots.push(time);
                                }
                              });

                              const renderSlotPill = (time) => {
                                const slot24 = convertSlotTo24h(time);
                                const now = new Date();
                                const istOffset = 5.5 * 60 * 60 * 1000;
                                const istDate = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
                                const todayStr = istDate.toISOString().split('T')[0];
                                const current24 = `${String(istDate.getHours()).padStart(2, '0')}:${String(istDate.getMinutes()).padStart(2, '0')}`;
                                
                                const isPast = (bookingDate === todayStr && slot24 <= current24);
                                const isBusy = newBookingBookedSlots.includes(time);
                                const isSelected = selectedNewBookingSlot === time;

                                let slotStyle = { padding: '9px 6px', fontSize: '12px', textAlign: 'center', borderRadius: '10px', cursor: 'pointer', fontWeight: 600, transition: 'all 0.2s' };

                                if (isPast) {
                                  slotStyle = { ...slotStyle, opacity: 0.5, cursor: 'not-allowed', background: '#F1F5F9', color: '#94A3B8', border: '1px dashed #CBD5E1' };
                                } else if (isBusy) {
                                  slotStyle = { ...slotStyle, background: '#FEE2E2', border: '1px solid #FECACA', color: '#991B1B', cursor: 'not-allowed' };
                                } else if (isSelected) {
                                  slotStyle = { ...slotStyle, background: '#2563EB', border: '1px solid #1D4ED8', color: '#FFFFFF', fontWeight: 800, boxShadow: '0 4px 12px rgba(37,99,235,0.3)' };
                                } else {
                                  slotStyle = { ...slotStyle, background: '#EFF6FF', border: '1px solid #BFDBFE', color: '#1D4ED8' };
                                }

                                return (
                                  <div
                                    key={time}
                                    style={slotStyle}
                                    onClick={() => {
                                      if (!isPast && !isBusy) {
                                        setSelectedNewBookingSlot(time);
                                        setBookingTime(slot24);
                                      }
                                    }}
                                  >
                                    {time} {isPast ? '(Passed)' : ''}
                                  </div>
                                );
                              };

                              return (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                  {morningSlots.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span>🌅</span> Morning Session (10:00 AM - 01:00 PM)
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                        {morningSlots.map(renderSlotPill)}
                                      </div>
                                    </div>
                                  )}

                                  {afternoonSlots.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span>☀️</span> Afternoon Session (01:00 PM - 05:00 PM)
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                        {afternoonSlots.map(renderSlotPill)}
                                      </div>
                                    </div>
                                  )}

                                  {eveningSlots.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span>🌙</span> Evening Session (05:00 PM - 08:00 PM)
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                                        {eveningSlots.map(renderSlotPill)}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })()}
                          </div>'''

if old_slots_block in content:
    content = content.replace(old_slots_block, new_slots_block)
    print("New Booking slots updated with Morning/Afternoon/Evening 4-column grids.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx updated successfully.")
