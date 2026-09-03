import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace unsafe doctorsList and appointmentsList and doctorLeaves calls with safe array fallbacks
old_kpi_section = '''                    {/* 5 KPI Metric Cards Embedded Inside Hospital Card */}
                    <div className="kpi-grid-5">
                      <div className="kpi-card-light" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>📅</span>
                          <span className="kpi-pill" style={{ background: '#DBEAFE', color: '#1E40AF' }}>Today</span>
                        </div>
                        <div>
                          <div className="kpi-value">{doctorsList.reduce((acc, doc) => acc + (appointmentsList.filter(a => String(a.doctor_id) === String(doc.id)).length), 0)}</div>
                          <div className="kpi-title" style={{ color: '#1E3A8A' }}>Appointments</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#FEF3C7', border: '1px solid #FDE68A' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>💰</span>
                          <span className="kpi-pill" style={{ background: '#FDE68A', color: '#92400E' }}>Pending</span>
                        </div>
                        <div>
                          <div className="kpi-value">₹{doctorsList.reduce((acc, doc) => acc + (appointmentsList.filter(a => String(a.doctor_id) === String(doc.id) && a.payment_status === 'PENDING').length * (doc.opd_fees || 500)), 0)}</div>
                          <div className="kpi-title" style={{ color: '#78350F' }}>Collection Due</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#DCFCE7', border: '1px solid #BBF7D0' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>✅</span>
                          <span className="kpi-pill" style={{ background: '#BBF7D0', color: '#166534' }}>Paid</span>
                        </div>
                        <div>
                          <div className="kpi-value">₹{doctorsList.reduce((acc, doc) => acc + (appointmentsList.filter(a => String(a.doctor_id) === String(doc.id) && a.status === 'COMPLETED').length * (doc.opd_fees || 500)), 0)}</div>
                          <div className="kpi-title" style={{ color: '#14532D' }}>Collected Today</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#F3E8FF', border: '1px solid #E9D5FF' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>🩺</span>
                          <span className="kpi-pill" style={{ background: '#E9D5FF', color: '#6B21A8' }}>Live</span>
                        </div>
                        <div>
                          <div className="kpi-value">{(doctorsList || []).filter(doc => {
                            const isDoctorOnLeave = (doctorLeaves || []).some(l => {
                              if (String(l.doctor_id) !== String(doc.id) || l.status === 'REJECTED') return false;
                              const sd = new Date(l.start_date);
                              const ed = new Date(l.end_date);
                              const target = new Date(selectedScheduleDate);
                              return target >= sd && target <= ed;
                            });
                            return !isDoctorOnLeave;
                          }).length} / {(doctorsList || []).length}</div>
                          <div className="kpi-title" style={{ color: '#581C87' }}>Doctors Online</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#FEE2E2', border: '1px solid #FECACA' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>❌</span>
                          <span className="kpi-pill" style={{ background: '#FECACA', color: '#991B1B' }}>Missed</span>
                        </div>
                        <div>
                          <div className="kpi-value">{(doctorsList || []).reduce((acc, doc) => acc + ((appointmentsList || []).filter(a => String(a.doctor_id) === String(doc.id) && (a.status === 'CANCELLED' || a.status === 'MISSED')).length), 0)}</div>
                          <div className="kpi-title" style={{ color: '#7F1D1D' }}>Missed / Cancelled</div>
                        </div>
                      </div>
                    </div>'''

new_kpi_section = '''                    {/* 5 KPI Metric Cards Embedded Inside Hospital Card */}
                    <div className="kpi-grid-5">
                      <div className="kpi-card-light" style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>📅</span>
                          <span className="kpi-pill" style={{ background: '#DBEAFE', color: '#1E40AF' }}>Today</span>
                        </div>
                        <div>
                          <div className="kpi-value">{(doctorsList || []).reduce((acc, doc) => acc + ((appointmentsList || []).filter(a => String(a.doctor_id) === String(doc.id)).length), 0)}</div>
                          <div className="kpi-title" style={{ color: '#1E3A8A' }}>Appointments</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#FEF3C7', border: '1px solid #FDE68A' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>💰</span>
                          <span className="kpi-pill" style={{ background: '#FDE68A', color: '#92400E' }}>Pending</span>
                        </div>
                        <div>
                          <div className="kpi-value">₹{(doctorsList || []).reduce((acc, doc) => acc + ((appointmentsList || []).filter(a => String(a.doctor_id) === String(doc.id) && a.payment_status === 'PENDING').length * (doc.opd_fees || 500)), 0)}</div>
                          <div className="kpi-title" style={{ color: '#78350F' }}>Collection Due</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#DCFCE7', border: '1px solid #BBF7D0' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>✅</span>
                          <span className="kpi-pill" style={{ background: '#BBF7D0', color: '#166534' }}>Paid</span>
                        </div>
                        <div>
                          <div className="kpi-value">₹{(doctorsList || []).reduce((acc, doc) => acc + ((appointmentsList || []).filter(a => String(a.doctor_id) === String(doc.id) && a.status === 'COMPLETED').length * (doc.opd_fees || 500)), 0)}</div>
                          <div className="kpi-title" style={{ color: '#14532D' }}>Collected Today</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#F3E8FF', border: '1px solid #E9D5FF' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>🩺</span>
                          <span className="kpi-pill" style={{ background: '#E9D5FF', color: '#6B21A8' }}>Live</span>
                        </div>
                        <div>
                          <div className="kpi-value">{(doctorsList || []).filter(doc => {
                            const isDoctorOnLeave = (doctorLeaves || []).some(l => {
                              if (String(l.doctor_id) !== String(doc.id) || l.status === 'REJECTED') return false;
                              const sd = new Date(l.start_date);
                              const ed = new Date(l.end_date);
                              const target = new Date(selectedScheduleDate);
                              return target >= sd && target <= ed;
                            });
                            return !isDoctorOnLeave;
                          }).length} / {(doctorsList || []).length}</div>
                          <div className="kpi-title" style={{ color: '#581C87' }}>Doctors Online</div>
                        </div>
                      </div>

                      <div className="kpi-card-light" style={{ background: '#FEE2E2', border: '1px solid #FECACA' }}>
                        <div className="kpi-header-row">
                          <span style={{ fontSize: '18px' }}>❌</span>
                          <span className="kpi-pill" style={{ background: '#FECACA', color: '#991B1B' }}>Missed</span>
                        </div>
                        <div>
                          <div className="kpi-value">{(doctorsList || []).reduce((acc, doc) => acc + ((appointmentsList || []).filter(a => String(a.doctor_id) === String(doc.id) && (a.status === 'CANCELLED' || a.status === 'MISSED')).length), 0)}</div>
                          <div className="kpi-title" style={{ color: '#7F1D1D' }}>Missed / Cancelled</div>
                        </div>
                      </div>
                    </div>'''

if old_kpi_section in content:
    content = content.replace(old_kpi_section, new_kpi_section)
    print("Safeguarded KPI metric card array references successfully.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
