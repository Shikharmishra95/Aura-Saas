import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# ── Complete translation map: Hindi string → (key, English translation) ──
TRANSLATIONS = {
    # Table headers / column labels
    "समय (Time)":                          ("col_time",         "Time"),
    "मरीज (Patient)":                      ("col_patient",      "Patient"),
    "मोबाइल (Mobile)":                     ("col_mobile",       "Mobile"),
    "समस्या (Reason)":                     ("col_reason",       "Reason / Problem"),
    "भुगतान (Payment)":                    ("col_payment",      "Payment"),
    "स्थिति/कार्रवाई (Status/Action)":    ("col_status_action","Status / Action"),
    "डॉक्टर, समय एवं फीस सूची":          ("doc_fee_list",     "Doctor, Schedule & Fee List"),

    # Date navigation buttons
    "◀ पिछला (Prev)":   ("btn_prev",  "◀ Prev"),
    "आज (Today)":       ("btn_today", "Today"),
    "अगला (Next) ▶":    ("btn_next",  "Next ▶"),

    # Empty / error states
    "इस तारीख के लिए कोई भी अपॉइंटमेंट बुक नहीं है। (No bookings for this date)":
                                            ("no_bookings_date", "No appointments booked for this date."),
    "खोज विफल रही। कृपया पुनः प्रयास करें।":
                                            ("search_failed",    "Search failed. Please try again."),
    "\" से कोई मरीज रिकॉर्ड नहीं मिला।":("no_patient_found", "No patient record found."),

    # Status / badge labels
    "⚠️ छुट्टी पर (On Leave)":             ("on_leave",         "⚠️ On Leave"),
    "Off Duty / Closed (छुट्टी)":          ("off_duty",         "Off Duty / Closed"),
    "⚠️ DOCTOR IS ON LEAVE (डॉक्टर छुट्टी पर हैं)":
                                            ("doc_on_leave_banner","⚠️ DOCTOR IS ON LEAVE"),

    # Section headings
    "Patient Lookup Engine (मरीज़ खोज इंजन)":
                                            ("patient_lookup_heading","Patient Lookup Engine"),
    "📅 Active Doctor Leaves (डॉक्टरों की छुट्टियाँ)":
                                            ("active_leaves_heading","📅 Active Doctor Leaves"),
    "📝 Apply For Leave (अवकाश के लिए आवेदन)":
                                            ("apply_leave_heading","📝 Apply For Leave"),
    "📅 My Registered Leaves (मेरे अवकाश)":
                                            ("my_leaves_heading","📅 My Registered Leaves"),
    "रिसेप्शनिस्ट डैशबोर्ड — AI वॉयस बुकिंग सिस्टम":
                                            ("recep_dashboard_sub","Receptionist Dashboard — AI Voice Booking System"),

    # Form field labels
    "Doctor (चिकित्सक)":                   ("lbl_doctor",       "Doctor"),
    "Receptionist (रिसेप्शनिस्ट)":        ("lbl_receptionist", "Receptionist"),
    "OPD Fees (फीस ₹)":                   ("lbl_opd_fees",     "OPD Fees (₹)"),
    "Slot Duration (मिनट) *":              ("lbl_slot_dur",     "Slot Duration (min) *"),
    "Schedule Days (साप्ताहिक दिन) *":    ("lbl_sched_days",   "Schedule Days (Weekly) *"),
    "Reason (कारण)":                       ("lbl_reason",       "Reason"),
    "Admin Username (लॉगिन यूजरनेम) *":   ("lbl_admin_uname",  "Admin Username *"),
    "Admin Password (लॉगिन पासवर्ड)":     ("lbl_admin_pass",   "Admin Password"),
    "AI Greeting Message (नमस्ते स्वागत संदेश) *":
                                            ("lbl_ai_greeting",  "AI Greeting Message *"),
    "Custom System Prompt (वर्चुअल डॉक्टर निर्देश - Optional)":
                                            ("lbl_sys_prompt",   "Custom System Prompt (Optional)"),
    "Doctor Password (लॉगिन पासवर्ड)":    ("lbl_doc_pass",     "Doctor Password"),
    "Password (पासवर्ड)":                  ("lbl_password_field","Password"),
    "कृपया डॉक्टर का चयन करें (Please select a doctor).":
                                            ("err_select_doc",   "Please select a doctor."),
    "कृपया समय स्लॉट (Time Slot) का चयन करें.":
                                            ("err_select_slot",  "Please select a time slot."),

    # Payment selection
    "💳 Payment Mode Selection (भुगतान विकल्प)":
                                            ("payment_mode_heading","💳 Payment Mode"),

    # Prescription templates
    "⚡ Quick Prescription Template (त्वरित पर्चा टेम्पलेट)":
                                            ("quick_presc_tmpl", "⚡ Quick Prescription Template"),
    "Mild Fever & Body Pain (सामान्य बुखार)":
                                            ("tmpl_fever",       "Mild Fever & Body Pain"),
    "Cold, Cough & Throat Infection (सर्दी-खांसी)":
                                            ("tmpl_cold",        "Cold, Cough & Throat Infection"),
    "Stomach Acidity & Gas (गैस-एसिडिटी)":
                                            ("tmpl_acidity",     "Stomach Acidity & Gas"),
    "Stomach Infection / Loose Motion (दस्त / दस्त-उल्टी)":
                                            ("tmpl_stomach",     "Stomach Infection / Loose Motion"),
    "Clinical Notes / Diagnosis Summary (क्लीनिकल नोट्स)":
                                            ("lbl_clinical_notes","Clinical Notes / Diagnosis Summary"),
    "Prescription Medicines & Dosage (दवाइयों की सूची)":
                                            ("lbl_presc_meds",   "Prescription Medicines & Dosage"),

    # Day abbreviations
    "सोम (Mon)":   ("day_mon", "Mon"),
    "मंगल (Tue)":  ("day_tue", "Tue"),
    "बुध (Wed)":   ("day_wed", "Wed"),
    "गुरु (Thu)":  ("day_thu", "Thu"),
    "शुक्र (Fri)": ("day_fri", "Fri"),
    "शनि (Sat)":   ("day_sat", "Sat"),
    "रवि (Sun)":   ("day_sun", "Sun"),

    # Confirmation dialogs
    "क्या आप सच में इस छुट्टी (leave) को हटाना चाहते हैं?":
                                            ("confirm_del_leave",    "Are you sure you want to delete this leave?"),
    "क्या आप सच में इस छुट्टी (leave) को स्वीकृत (Approve) करना चाहते हैं?":
                                            ("confirm_appr_leave",   "Are you sure you want to approve this leave?"),
    "क्या आप सच में इस छुट्टी (leave) को अस्वीकृत (Reject) करना चाहते हैं?":
                                            ("confirm_rej_leave",    "Are you sure you want to reject this leave?"),
    "क्या आप सच में इस स्टाफ (चिकित्सक/रिसेप्शनिस्ट) को हटाना चाहते हैं?":
                                            ("confirm_del_staff",    "Are you sure you want to remove this staff member?"),

    # Default schedule text
    "सोम–शुक्र, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM":
                                            ("default_schedule",     "Mon–Fri, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM"),

    # Placeholder / default texts
    "उदा. Sick Leave, Personal Work":      ("leave_reason_placeholder", "e.g. Sick Leave, Personal Work"),
    "तुम अपोलो हॉस्पिटल की AI वर्चुअल रिसेप्शनिस्ट हो। तुम्हारा काम...":
                                            ("ai_prompt_placeholder",    "You are the AI virtual receptionist. Your job is..."),
}

# ── Now generate the updated TRANSLATIONS object to paste in App.jsx ──

print("=" * 70)
print("📋 TOTAL STRINGS TO REPLACE:", len(TRANSLATIONS))
print("=" * 70)
print()

# Print the new English entries to add to TRANSLATIONS dict
en_entries = []
hi_entries = []
for hindi_str, (key, english_str) in TRANSLATIONS.items():
    en_entries.append(f'    {key}: "{english_str}",')
    hi_entries.append(f'    {key}: "{hindi_str}",')

print("// ── ADD THESE TO TRANSLATIONS.en ──")
for e in en_entries:
    print(e)

print()
print("// ── ADD THESE TO TRANSLATIONS.hi ──")
for h in hi_entries:
    print(h)

print()
print("=" * 70)
print("✅ Done. Now generating replacement map...")
print("=" * 70)
