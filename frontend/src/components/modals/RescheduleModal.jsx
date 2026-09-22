import React from 'react';

export default function RescheduleModal({
  isOpen,
  onClose,
  appointment,
  rescheduleDate,
  onDateChange,
  allSlots = [],
  bookedSlots = [],
  selectedSlotTime,
  onSelectSlot,
  leavesList = [],
  rescheduleError,
  onConfirm,
  t
}) {
  if (!isOpen || !appointment) return null;

  return (
    <div className="modal-overlay" style={{ backdropFilter: 'blur(8px)', zIndex: 9999 }}>
      <div
        className="modal-content"
        style={{
          maxWidth: '560px',
          width: '92%',
          background: '#FFFFFF',
          borderRadius: '20px',
          padding: '24px',
          border: '1px solid #E2E8F0',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h3 style={{ color: '#0F172A', margin: 0, fontWeight: 800, fontSize: '18px' }}>
            🔄 Reschedule Appointment
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94A3B8',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '2px 6px'
            }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            background: '#F8FAFC',
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            padding: '12px 14px',
            marginBottom: '16px',
            fontSize: '12px',
            color: '#334155'
          }}
        >
          <div>👤 <strong>Patient:</strong> {appointment.patient_name}</div>
          <div style={{ marginTop: '3px' }}>
            👨‍⚕️ <strong>Doctor:</strong> {appointment.doctor_name} ({appointment.department_name})
          </div>
          <div style={{ marginTop: '3px', color: '#B45309', fontWeight: 600 }}>
            ℹ️ Authority: Allowed 1-Time only (Strictly within the next 2 days).
          </div>
        </div>

        {rescheduleError && (
          <div
            style={{
              color: '#DC2626',
              background: '#FEF2F2',
              border: '1px solid #FECACA',
              padding: '10px 14px',
              borderRadius: '10px',
              marginBottom: '14px',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            ⚠️ {rescheduleError}
          </div>
        )}

        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px', display: 'block' }}>
            📅 Select Date (Next 2 Days Only)
          </label>
          <input
            type="date"
            className="form-control"
            value={rescheduleDate}
            min={new Date().toISOString().split('T')[0]}
            max={new Date(Date.now() + 2 * 24 * 3600 * 1000).toISOString().split('T')[0]}
            onChange={(e) => onDateChange(e.target.value)}
            style={{
              padding: '10px 12px',
              fontSize: '13px',
              borderRadius: '10px',
              background: '#F8FAFC',
              border: '1.5px solid #CBD5E1',
              width: '100%'
            }}
          />
        </div>

        {rescheduleDate && (
          <div style={{ marginBottom: '20px' }}>
            <label style={{ fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '8px', display: 'block' }}>
              ⏰ Select Available Time Slot:
            </label>
            <div>
              {(() => {
                if (allSlots.length === 0) {
                  const onLeave = leavesList.find(
                    (l) =>
                      l.doctor_id === appointment.doctor_id &&
                      l.status === 'APPROVED' &&
                      new Date(l.start_date) <= new Date(rescheduleDate) &&
                      new Date(l.end_date) >= new Date(rescheduleDate)
                  );
                  if (onLeave) {
                    const sd = new Date(onLeave.start_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short' });
                    const ed = new Date(onLeave.end_date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short' });
                    return (
                      <div
                        style={{
                          textAlign: 'center',
                          padding: '15px',
                          color: '#DC2626',
                          background: '#FEF2F2',
                          borderRadius: '10px',
                          border: '1px solid #FECACA',
                          fontSize: '12px'
                        }}
                      >
                        <strong>{t('doc_on_leave_banner')}</strong><br />
                        <span style={{ marginTop: '4px', display: 'inline-block' }}>
                          Doctor is on approved leave from {sd} to {ed}.
                        </span>
                      </div>
                    );
                  }
                  return (
                    <div
                      style={{
                        textAlign: 'center',
                        padding: '15px',
                        color: '#64748B',
                        background: '#F8FAFC',
                        borderRadius: '10px',
                        border: '1px solid #E2E8F0',
                        fontSize: '12px',
                        fontStyle: 'italic'
                      }}
                    >
                      No active OPD schedule found for this doctor on selected date.
                    </div>
                  );
                }
                return (
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fill, minmax(95px, 1fr))',
                      gap: '8px',
                      maxHeight: '200px',
                      overflowY: 'auto',
                      padding: '4px'
                    }}
                  >
                    {allSlots.map((time) => {
                      const isBusy = bookedSlots.includes(time);
                      const isSelected = selectedSlotTime === time;
                      return (
                        <button
                          type="button"
                          key={time}
                          disabled={isBusy}
                          onClick={() => {
                            if (!isBusy) onSelectSlot(time);
                          }}
                          style={{
                            padding: '9px 6px',
                            borderRadius: '10px',
                            fontSize: '11px',
                            fontWeight: 700,
                            cursor: isBusy ? 'not-allowed' : 'pointer',
                            transition: 'all 0.15s ease',
                            border: isSelected
                              ? '2px solid #2563EB'
                              : isBusy
                              ? '1px solid #FECACA'
                              : '1.5px solid #CBD5E1',
                            background: isSelected
                              ? '#2563EB'
                              : isBusy
                              ? '#FEF2F2'
                              : '#FFFFFF',
                            color: isSelected
                              ? '#FFFFFF'
                              : isBusy
                              ? '#EF4444'
                              : '#1E293B',
                            boxShadow: isSelected ? '0 4px 10px rgba(37,99,235,0.25)' : 'none',
                            textAlign: 'center'
                          }}
                        >
                          {time}
                          {isBusy && (
                            <span style={{ display: 'block', fontSize: '8px', fontWeight: 600, color: '#EF4444' }}>
                              Booked
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        <div
          style={{
            display: 'flex',
            gap: '10px',
            justifyContent: 'flex-end',
            marginTop: '20px',
            borderTop: '1px solid #E2E8F0',
            paddingTop: '16px'
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              background: '#F1F5F9',
              border: '1px solid #CBD5E1',
              color: '#334155',
              borderRadius: '10px',
              padding: '9px 18px',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!rescheduleDate || !selectedSlotTime}
            onClick={onConfirm}
            style={{
              background:
                !rescheduleDate || !selectedSlotTime
                  ? '#94A3B8'
                  : 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
              border: 'none',
              color: '#FFFFFF',
              borderRadius: '10px',
              padding: '9px 20px',
              fontSize: '13px',
              fontWeight: 800,
              cursor: !rescheduleDate || !selectedSlotTime ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 12px rgba(37,99,235,0.25)'
            }}
          >
            Confirm Reschedule
          </button>
        </div>
      </div>
    </div>
  );
}
