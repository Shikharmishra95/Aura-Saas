import sys
sys.stdout.reconfigure(encoding='utf-8')

# These are the remaining strings with their exact context in the file
# They use whitespace/newline patterns that the simple string match missed
REPLACEMENTS_2 = [
    # Date nav buttons (have newlines around them)
    ("                        ◀ पिछला (Prev)\n", "                        {t('btn_prev')}\n"),
    ("                        आज (Today)\n", "                        {t('btn_today')}\n"),
    ("                        अगला (Next) ▶\n", "                        {t('btn_next')}\n"),
    
    # Fee list heading
    ("<span>👨‍⚕️</span> डॉक्टर, समय एवं फीस सूची",
     "<span>👨‍⚕️</span> {t('doc_fee_list')}"),
    
    # No bookings message (may have different spacing)
    (">इस तारीख के लिए कोई भी अपॉइंटमेंट बुक नहीं है। (No bookings for this date)<",
     ">{t('no_bookings_date')}<"),
    ("इस तारीख के लिए कोई भी अपॉइंटमेंट बुक नहीं है। (No bookings for this date)",
     "{t('no_bookings_date')}"),
    
    # Search failed
    ("खोज विफल रही। कृपया पुनः प्रयास करें।",
     "{t('search_failed')}"),
    
    # Patient lookup heading
    ("Patient Lookup Engine (मरीज़ खोज इंजन)",
     "{t('patient_lookup_heading')}"),
    
    # Leave on status badges (used in JSX expression/ternary)
    ("'⚠️ छुट्टी पर (On Leave)'", "t('on_leave')"),
    ('"⚠️ छुट्टी पर (On Leave)"', "t('on_leave')"),
    ("'⚠️ DOCTOR IS ON LEAVE (डॉक्टर छुट्टी पर हैं)'", "t('doc_on_leave_banner')"),
    ('"⚠️ DOCTOR IS ON LEAVE (डॉक्टर छुट्टी पर हैं)"', "t('doc_on_leave_banner')"),

    # Confirmation dialogs - window.confirm() uses backticks or double quotes
    ('`क्या आप सच में इस छुट्टी (leave) को हटाना चाहते हैं?`', '`${t("confirm_del_leave")}`'),
    ('`क्या आप सच में इस छुट्टी (leave) को स्वीकृत (Approve) करना चाहते हैं?`', '`${t("confirm_appr_leave")}`'),
    ('`क्या आप सच में इस छुट्टी (leave) को अस्वीकृत (Reject) करना चाहते हैं?`', '`${t("confirm_rej_leave")}`'),
    ('`क्या आप सच में इस स्टाफ (चिकित्सक/रिसेप्शनिस्ट) को हटाना चाहते हैं?`', '`${t("confirm_del_staff")}`'),
    ('"क्या आप सच में इस छुट्टी (leave) को हटाना चाहते हैं?"', 't("confirm_del_leave")'),
    ('"क्या आप सच में इस छुट्टी (leave) को स्वीकृत (Approve) करना चाहते हैं?"', 't("confirm_appr_leave")'),
    ('"क्या आप सच में इस छुट्टी (leave) को अस्वीकृत (Reject) करना चाहते हैं?"', 't("confirm_rej_leave")'),
    ('"क्या आप सच में इस स्टाफ (चिकित्सक/रिसेप्शनिस्ट) को हटाना चाहते हैं?"', 't("confirm_del_staff")'),
    
    # Payment mode heading
    ("💳 Payment Mode Selection (भुगतान विकल्प)", "{t('payment_mode_heading')}"),
    
    # Day labels in button arrays (they appear as string values)
    ('"सोम (Mon)"', "t('day_mon')"),
    ('"मंगल (Tue)"', "t('day_tue')"),
    ('"बुध (Wed)"', "t('day_wed')"),
    ('"गुरु (Thu)"', "t('day_thu')"),
    ('"शुक्र (Fri)"', "t('day_fri')"),
    ('"शनि (Sat)"', "t('day_sat')"),
    ('"रवि (Sun)"', "t('day_sun')"),
    ("'सोम (Mon)'", "t('day_mon')"),
    ("'मंगल (Tue)'", "t('day_tue')"),
    ("'बुध (Wed)'", "t('day_wed')"),
    ("'गुरु (Thu)'", "t('day_thu')"),
    ("'शुक्र (Fri)'", "t('day_fri')"),
    ("'शनि (Sat)'", "t('day_sat')"),
    ("'रवि (Sun)'", "t('day_sun')"),
]

TARGET_FILE = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(TARGET_FILE, encoding='utf-8') as f:
    content = f.read()

replaced_count = 0
for hindi, english in REPLACEMENTS_2:
    if hindi in content:
        content = content.replace(hindi, english)
        replaced_count += 1
        print(f"✅ Replaced: {repr(hindi[:55])}")
    else:
        print(f"⚠️  NOT FOUND: {repr(hindi[:55])}")

# Also fix the date locale in safeFormatDate
old_locale = "return d.toLocaleDateString('hi-IN', options);"
new_locale = "return d.toLocaleDateString(typeof lang !== 'undefined' && lang === 'en' ? 'en-IN' : 'hi-IN', options);"
if old_locale in content:
    # Replace only second occurrence (the one inside the function, not first test)
    content = content.replace(old_locale, new_locale)
    print("✅ Fixed date locale in safeFormatDate()")

with open(TARGET_FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n{'='*60}")
print(f"✅ Total replacements made: {replaced_count}/{len(REPLACEMENTS_2)}")
print(f"{'='*60}")
