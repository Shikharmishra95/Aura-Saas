import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Map: exact Hindi string in code → t('key') replacement
REPLACEMENTS = {
    # Table column headers (JSX text nodes)
    ">समय (Time)<":           ">{t('col_time')}<",
    ">मरीज (Patient)<":       ">{t('col_patient')}<",
    ">मोबाइल (Mobile)<":      ">{t('col_mobile')}<",
    ">समस्या (Reason)<":      ">{t('col_reason')}<",
    ">भुगतान (Payment)<":     ">{t('col_payment')}<",
    ">स्थिति/कार्रवाई (Status/Action)<": ">{t('col_status_action')}<",
    ">डॉक्टर, समय एवं फीस सूची<":      ">{t('doc_fee_list')}<",

    # Date navigation buttons
    ">◀ पिछला (Prev)<":   ">{t('btn_prev')}<",
    ">आज (Today)<":       ">{t('btn_today')}<",
    ">अगला (Next) ▶<":   ">{t('btn_next')}<",

    # Empty / error state strings (JSX text)
    ">इस तारीख के लिए कोई भी अपॉइंटमेंट बुक नहीं है। (No bookings for this date)<":
        ">{t('no_bookings_date')}<",
    ">खोज विफल रही। कृपया पुनः प्रयास करें।<":
        ">{t('search_failed')}<",

    # Section headings (JSX text)
    ">Patient Lookup Engine (मरीज़ खोज इंजन)<": ">{t('patient_lookup_heading')}<",
    ">📅 Active Doctor Leaves (डॉक्टरों की छुट्टियाँ)<": ">{t('active_leaves_heading')}<",
    ">📝 Apply For Leave (अवकाश के लिए आवेदन)<": ">{t('apply_leave_heading')}<",
    ">📅 My Registered Leaves (मेरे अवकाश)<": ">{t('my_leaves_heading')}<",

    # Dashboard subtitle
    "{lang === 'hi' ? 'रिसेप्शनिस्ट डैशबोर्ड — AI वॉयस बुकिंग सिस्टम' : 'Receptionist Dashboard — AI Voice Booking System'}":
        "{t('recep_dashboard_sub')}",

    # Status / leave badge strings
    "'⚠️ छुट्टी पर (On Leave)'":   "t('on_leave')",
    "'Off Duty / Closed (छुट्टी)'": "t('off_duty')",
    "'⚠️ DOCTOR IS ON LEAVE (डॉक्टर छुट्टी पर हैं)'": "t('doc_on_leave_banner')",
    '"⚠️ छुट्टी पर (On Leave)"':   "t('on_leave')",
    '"Off Duty / Closed (छुट्टी)"': "t('off_duty')",
    '"⚠️ DOCTOR IS ON LEAVE (डॉक्टर छुट्टी पर हैं)"': "t('doc_on_leave_banner')",

    # Form labels (JSX text and string literals)
    ">Doctor (चिकित्सक)<":                          ">{t('lbl_doctor')}<",
    ">Receptionist (रिसेप्शनिस्ट)<":               ">{t('lbl_receptionist')}<",
    ">OPD Fees (फीस ₹)<":                           ">{t('lbl_opd_fees')}<",
    ">Slot Duration (मिनट) *<":                     ">{t('lbl_slot_dur')}<",
    ">Schedule Days (साप्ताहिक दिन) *<":            ">{t('lbl_sched_days')}<",
    ">Reason (कारण)<":                              ">{t('lbl_reason')}<",
    ">Admin Username (लॉगिन यूजरनेम) *<":          ">{t('lbl_admin_uname')}<",
    ">Admin Password (लॉगिन पासवर्ड)<":            ">{t('lbl_admin_pass')}<",
    ">AI Greeting Message (नमस्ते स्वागत संदेश) *<":">{t('lbl_ai_greeting')}<",
    ">Custom System Prompt (वर्चुअल डॉक्टर निर्देश - Optional)<": ">{t('lbl_sys_prompt')}<",
    ">Doctor Password (लॉगिन पासवर्ड)<":           ">{t('lbl_doc_pass')}<",
    ">Password (पासवर्ड)<":                         ">{t('lbl_password_field')}<",

    # Alert/confirm strings (inside window.confirm() or alert())
    "'क्या आप सच में इस छुट्टी (leave) को हटाना चाहते हैं?'":
        "t('confirm_del_leave')",
    "'क्या आप सच में इस छुट्टी (leave) को स्वीकृत (Approve) करना चाहते हैं?'":
        "t('confirm_appr_leave')",
    "'क्या आप सच में इस छुट्टी (leave) को अस्वीकृत (Reject) करना चाहते हैं?'":
        "t('confirm_rej_leave')",
    "'क्या आप सच में इस स्टाफ (चिकित्सक/रिसेप्शनिस्ट) को हटाना चाहते हैं?'":
        "t('confirm_del_staff')",

    # Prescription templates
    ">⚡ Quick Prescription Template (त्वरित पर्चा टेम्पलेट)<": ">{t('quick_presc_tmpl')}<",
    ">Mild Fever & Body Pain (सामान्य बुखार)<":    ">{t('tmpl_fever')}<",
    ">Cold, Cough & Throat Infection (सर्दी-खांसी)<":">{t('tmpl_cold')}<",
    ">Stomach Acidity & Gas (गैस-एसिडिटी)<":       ">{t('tmpl_acidity')}<",
    ">Stomach Infection / Loose Motion (दस्त / दस्त-उल्टी)<":">{t('tmpl_stomach')}<",
    ">Clinical Notes / Diagnosis Summary (क्लीनिकल नोट्स)<":">{t('lbl_clinical_notes')}<",
    ">Prescription Medicines & Dosage (दवाइयों की सूची)<":">{t('lbl_presc_meds')}<",

    # Payment mode heading
    ">💳 Payment Mode Selection (भुगतान विकल्प)<": ">{t('payment_mode_heading')}<",

    # Day labels
    ">सोम (Mon)<":    ">{t('day_mon')}<",
    ">मंगल (Tue)<":   ">{t('day_tue')}<",
    ">बुध (Wed)<":    ">{t('day_wed')}<",
    ">गुरु (Thu)<":   ">{t('day_thu')}<",
    ">शुक्र (Fri)<":  ">{t('day_fri')}<",
    ">शनि (Sat)<":    ">{t('day_sat')}<",
    ">रवि (Sun)<":    ">{t('day_sun')}<",

    # Placeholder strings
    '"उदा. Sick Leave, Personal Work"': '"e.g. Sick Leave, Personal Work"',
    # (keep as English string, no t() needed since placeholder is not a translated key)

    # Error inline messages
    '"कृपया डॉक्टर का चयन करें (Please select a doctor)."': "t('err_select_doc')",
    '"कृपया समय स्लॉट (Time Slot) का चयन करें."':           "t('err_select_slot')",

    # Default schedule display
    '"सोम–शुक्र, 10:00 AM - 01:00 PM | 02:00 PM - 05:00 PM"': "{t('default_schedule')}",
}

TARGET_FILE = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(TARGET_FILE, encoding='utf-8') as f:
    content = f.read()

replaced_count = 0
for hindi, english in REPLACEMENTS.items():
    if hindi in content:
        content = content.replace(hindi, english)
        replaced_count += 1
        print(f"✅ Replaced: {hindi[:60]}")
    else:
        print(f"⚠️  NOT FOUND: {hindi[:60]}")

with open(TARGET_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n{'='*60}")
print(f"✅ Total replacements made: {replaced_count}/{len(REPLACEMENTS)}")
print(f"{'='*60}")
