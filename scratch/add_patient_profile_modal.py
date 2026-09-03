import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Declare state for selectedPatientRecord
if "const [selectedPatientRecord, setSelectedPatientRecord] = useState(null);" not in content:
    content = content.replace(
        "const [selectedNewBookingSlot, setSelectedNewBookingSlot] = useState('');",
        "const [selectedNewBookingSlot, setSelectedNewBookingSlot] = useState('');\n  const [selectedPatientRecord, setSelectedPatientRecord] = useState(null);"
    )
    print("Added selectedPatientRecord state.")

# 2. Update Header Search Dropdown to deduplicate unique members & click set selectedPatientRecord
old_dropdown_block = '''            {/* Live Search Dropdown Popup */}
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

new_dropdown_block = '''            {/* Live Search Dropdown Popup */}
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
                  patientSearchResults.groups.map((group, gIdx) => {
                    const allMembers = group.members || group.family_members || [];
                    const uniqueMembers = [];
                    const seenNames = new Set();
                    allMembers.forEach(m => {
                      const key = (m.name || '').toLowerCase().trim();
                      if (!seenNames.has(key)) {
                        seenNames.add(key);
                        uniqueMembers.push(m);
                      }
                    });

                    return (
                      <div key={gIdx} style={{ borderBottom: '1px solid #F1F5F9' }}>
                        <div style={{ background: '#F8FAFC', padding: '6px 14px', fontSize: '11px', fontWeight: 700, color: '#64748B' }}>
                          📞 Account Phone: {group.primary_phone || group.phone_number}
                        </div>
                        {uniqueMembers.map(member => (
                          <div 
                            key={member.id} 
                            onClick={() => {
                              setSelectedPatientRecord(member);
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
                              View Profile & Appointments →
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  })
                )}
              </div>
            )}'''

if old_dropdown_block in content:
    content = content.replace(old_dropdown_block, new_dropdown_block)
    print("Deduplicated Header dropdown mapping updated.")

# 3. Add Patient Profile & Appointments History Modal rendering
patient_modal_markup = '''      {/* D. Patient Profile & Appointments History Modal */}
      {selectedPatientRecord && (
        <div className="modal-backdrop" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100, padding: '20px' }}>
          <div className="modal-content" style={{ background: '#FFFFFF', borderRadius: '24px', width: '100%', maxWidth: '780px', maxHeight: '90vh', overflowY: 'auto', padding: '28px', boxShadow: '0 20px 45px rgba(15, 23, 42, 0.25)', border: '1.5px solid var(--border)', textAlign: 'left' }}>
            
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1.5px solid #F1F5F9', paddingBottom: '16px', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: '#EFF6FF', border: '1px solid #BFDBFE', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px' }}>
                  👤
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', margin: 0 }}>
                      {selectedPatientRecord.name}
                    </h2>
                    {selectedPatientRecord.is_primary && (
                      <span style={{ background: '#DCFCE7', color: '#166534', border: '1px solid #BBF7D0', padding: '2px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                        Primary Patient
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '13px', color: '#64748B', marginTop: '2px', fontWeight: 600 }}>
                    📞 {selectedPatientRecord.phone} • Gender: {selectedPatientRecord.gender || 'N/A'} • Age: {selectedPatientRecord.age || 'N/A'}
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedPatientRecord(null)}
                style={{ background: '#F1F5F9', border: 'none', width: '36px', height: '36px', borderRadius: '10px', fontSize: '18px', color: '#64748B', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                ✕
              </button>
            </div>

            {/* 1. Upcoming & Confirmed Appointments Section */}
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📅</span> Confirmed & Upcoming Appointments ({selectedPatientRecord.upcoming_appointments?.length || 0})
              </h3>
              
              {(!selectedPatientRecord.upcoming_appointments || selectedPatientRecord.upcoming_appointments.length === 0) ? (
                <div style={{ padding: '16px', background: '#F8FAFC', borderRadius: '12px', color: '#64748B', fontSize: '13px', textAlign: 'center', border: '1px solid #E2E8F0' }}>
                  No upcoming appointments scheduled for this patient.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedPatientRecord.upcoming_appointments.map(appt => (
                    <div key={appt.appointment_id} style={{ background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '14px', padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '14px', color: '#1E3A8A' }}>
                          🩺 {appt.doctor_name}
                        </div>
                        <div style={{ fontSize: '13px', color: '#1E40AF', marginTop: '2px', fontWeight: 600 }}>
                          ⏱️ Date & Time: <strong>{appt.datetime_display}</strong>
                        </div>
                        <div style={{ fontSize: '12px', color: '#475569', marginTop: '2px' }}>
                          Reason: {appt.reason}
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ background: '#DBEAFE', color: '#1E40AF', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 800 }}>
                          {appt.status || 'CONFIRMED'}
                        </span>
                        <span style={{ background: appt.payment_status === 'PAID' ? '#DCFCE7' : '#FEF3C7', color: appt.payment_status === 'PAID' ? '#166534' : '#92400E', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 800 }}>
                          {appt.payment_status === 'PAID' ? '💰 PAID' : '⏳ PENDING'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 2. Past History & Completed Appointments Section */}
            <div>
              <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#0F172A', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📜</span> Past Consultation History & Prescriptions ({selectedPatientRecord.history_appointments?.length || 0})
              </h3>
              
              {(!selectedPatientRecord.history_appointments || selectedPatientRecord.history_appointments.length === 0) ? (
                <div style={{ padding: '16px', background: '#F8FAFC', borderRadius: '12px', color: '#64748B', fontSize: '13px', textAlign: 'center', border: '1px solid #E2E8F0' }}>
                  No past appointment history found.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedPatientRecord.history_appointments.map(appt => (
                    <div key={appt.appointment_id} style={{ background: '#FFFFFF', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '14px 18px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: appt.has_prescription ? '10px' : '0' }}>
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '14px', color: '#0F172A' }}>
                            🩺 {appt.doctor_name}
                          </div>
                          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                            📅 {appt.datetime_display} • Reason: {appt.reason}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ background: '#F1F5F9', color: '#334155', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                            {appt.status}
                          </span>
                          <span style={{ background: appt.payment_status === 'PAID' ? '#DCFCE7' : '#FEE2E2', color: appt.payment_status === 'PAID' ? '#166534' : '#991B1B', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700 }}>
                            {appt.payment_status}
                          </span>
                        </div>
                      </div>

                      {/* Prescription details if available */}
                      {appt.has_prescription && appt.prescription && (
                        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '10px', padding: '12px', marginTop: '8px', fontSize: '12px' }}>
                          <div style={{ fontWeight: 700, color: '#2563EB', marginBottom: '4px' }}>📋 Prescription & Clinical Notes:</div>
                          {appt.prescription.clinical_notes && <div><strong>Notes:</strong> {appt.prescription.clinical_notes}</div>}
                          {appt.prescription.prescription && <div style={{ marginTop: '2px' }}><strong>Medicines:</strong> {appt.prescription.prescription}</div>}
                          {appt.prescription.follow_up_date && <div style={{ marginTop: '2px', color: '#059669', fontWeight: 600 }}>🗓️ Follow-up Date: {appt.prescription.follow_up_date}</div>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ textAlign: 'right', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #F1F5F9' }}>
              <button onClick={() => setSelectedPatientRecord(null)} className="btn btn-secondary" style={{ padding: '8px 20px', fontSize: '13px', borderRadius: '10px', fontWeight: 700 }}>
                Close Modal
              </button>
            </div>
          </div>
        </div>
      )}'''

# Inject modal before Footer
if "/* Footer */" in content:
    content = content.replace("/* Footer */", patient_modal_markup + "\n\n      /* Footer */")
    print("Injected Patient Profile & Appointments History Modal.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx updated successfully.")
