import React from 'react';

export default function PrescriptionModal({
  isOpen,
  onClose,
  appointment,
  isViewMode = false,
  prescNotes,
  setPrescNotes,
  prescMedicines,
  setPrescMedicines,
  prescFollowUp,
  setPrescFollowUp,
  onComplete,
  t
}) {
  if (!isOpen || !appointment) return null;

  const diagnosisTemplates = [
    { notes: "", prescription: "" },
    {
      notes: "Patient complained of mild viral fever, headache and body ache for 2 days. Chest clear. Advised hydration.",
      prescription: "1. Tab Paracetamol 650mg - 1 Tab twice daily after meals - 3 Days\n2. Tab Pantocid 40mg - 1 Tab once daily before breakfast - 3 Days\n3. Drink plenty of warm water and take complete rest."
    },
    {
      notes: "Sore throat, dry cough, mild nasal congestion. No difficulty breathing.",
      prescription: "1. Tab Cetirizine 10mg - 1 Tab once daily at bedtime - 5 Days\n2. Syrup Alex Cough Syrup - 5ml thrice daily - 5 Days\n3. Tab Vitamin C 500mg - 1 Tab daily - 10 Days\n4. Steam inhalation twice daily."
    },
    {
      notes: "Epigastric burning sensation, bloating after meals. Advised light non-spicy meals.",
      prescription: "1. Cap Pantoprazole 40mg + Domperidone 30mg - 1 Cap empty stomach in morning - 5 Days\n2. Syrup Digene - 10ml twice daily after meals - 5 Days\n3. Avoid tea, coffee and oily foods."
    },
    {
      notes: "Watery stools 4-5 times, mild abdominal cramp, dehydration symptoms.",
      prescription: "1. Tab Ofloxacin 200mg + Ornidazole 500mg - 1 Tab twice daily after meals - 5 Days\n2. ORS Solution - 1 sachet dissolved in 1L water, sip throughout the day - 3 Days\n3. Tab Loperamide 2mg - 1 Tab only if loose motion persists - SOS"
    }
  ];

  const handleTemplateChange = (e) => {
    const idx = e.target.selectedIndex;
    if (idx > 0) {
      const tmpl = diagnosisTemplates[idx];
      setPrescNotes(tmpl.notes);
      setPrescMedicines(tmpl.prescription);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '600px' }}>
        <h3 style={{ color: 'var(--text-main)', marginBottom: '15px' }}>
          {isViewMode
            ? `Consultation Details: ${appointment.patient_name}`
            : `Prescribe & Complete Consultation: ${appointment.patient_name}`}
        </h3>

        {isViewMode && appointment.consultation_completed_at && (
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '15px' }}>
            Completed on: {new Date(appointment.consultation_completed_at).toLocaleString('hi-IN')}
          </div>
        )}

        <form
          onSubmit={(e) => onComplete(e, appointment.id, prescNotes, prescMedicines, prescFollowUp)}
          style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}
        >
          {!isViewMode && (
            <div
              className="form-group"
              style={{
                background: 'rgba(102,252,241,0.04)',
                border: '1px solid rgba(102,252,241,0.15)',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '5px'
              }}
            >
              <label
                style={{
                  fontWeight: 700,
                  color: 'var(--color-primary)',
                  display: 'block',
                  marginBottom: '8px',
                  fontSize: '13px'
                }}
              >
                {t('quick_presc_tmpl')}
              </label>
              <select className="form-control" onChange={handleTemplateChange}>
                <option value="">-- Choose Diagnosis Template --</option>
                <option value="fever">{t('tmpl_fever')}</option>
                <option value="cold">{t('tmpl_cold')}</option>
                <option value="acidity">{t('tmpl_acidity')}</option>
                <option value="loose_motion">{t('tmpl_stomach')}</option>
              </select>
            </div>
          )}

          <div className="form-group">
            <label>{t('lbl_clinical_notes')}</label>
            <textarea
              className="form-control"
              rows="3"
              placeholder="Advised medications and rest."
              value={prescNotes}
              onChange={(e) => setPrescNotes(e.target.value)}
              required
              readOnly={isViewMode}
            />
          </div>

          <div className="form-group">
            <label>{t('lbl_presc_meds')}</label>
            <textarea
              className="form-control"
              rows="4"
              placeholder="Paracetamol 650mg - twice daily for 3 days."
              value={prescMedicines}
              onChange={(e) => setPrescMedicines(e.target.value)}
              required
              readOnly={isViewMode}
            />
          </div>

          <div className="form-group" style={{ maxWidth: '250px' }}>
            <label>Follow-up Date (optional)</label>
            <input
              type="date"
              className="form-control"
              value={prescFollowUp}
              onChange={(e) => setPrescFollowUp(e.target.value)}
              readOnly={isViewMode}
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '10px' }}>
            {isViewMode && (
              <button type="button" onClick={() => window.print()} className="btn btn-secondary">
                🖨️ Print Prescription
              </button>
            )}
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Close
            </button>
            {!isViewMode && (
              <button type="submit" className="btn btn-primary">
                Complete & Send to Patient
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
