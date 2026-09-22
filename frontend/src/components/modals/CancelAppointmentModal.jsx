import React from 'react';

export default function CancelAppointmentModal({
  isOpen,
  onClose,
  isPaid = false,
  cancelReason,
  setCancelReason,
  onConfirm
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h3 style={{ color: 'var(--text-main)', marginBottom: '15px' }}>Cancel Appointment</h3>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '15px' }}>
          Are you sure you want to cancel?{' '}
          {isPaid && (
            <span style={{ color: '#f59e0b', fontWeight: 600 }}>
              Note: This is a PAID appointment. Refund will be initiated.
            </span>
          )}
        </p>

        <div className="form-group" style={{ marginBottom: '15px' }}>
          <label>Reason for Cancellation (for WhatsApp alert)</label>
          <textarea
            className="form-control"
            rows="3"
            placeholder="Reason for cancellation..."
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            required
          />
        </div>

        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Discard
          </button>
          <button type="button" onClick={onConfirm} className="btn btn-danger">
            Confirm Cancel & Refund
          </button>
        </div>
      </div>
    </div>
  );
}
