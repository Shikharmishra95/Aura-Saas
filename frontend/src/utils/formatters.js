/**
 * AURA Hospital SaaS Formatters and UI Utilities
 */

export const formatDoctorTimingsToEnglish = (timings) => {
  if (!timings) return 'Mon – Sat: 10:00 AM – 01:00 PM';
  return timings
    .replace(/सोम–शनि/g, 'Mon–Sat')
    .replace(/सोम–शुक्र/g, 'Mon–Fri')
    .replace(/सोम/g, 'Mon')
    .replace(/मंगल/g, 'Tue')
    .replace(/बुध/g, 'Wed')
    .replace(/गुरु/g, 'Thu')
    .replace(/शुक्र/g, 'Fri')
    .replace(/शनि/g, 'Sat')
    .replace(/रवि/g, 'Sun');
};

export const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return '₹0';
  const num = typeof amount === 'number' ? amount : parseFloat(amount) || 0;
  return `₹${num.toLocaleString('en-IN')}`;
};

export const formatDateDisplay = (dateStr) => {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-IN', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateStr;
  }
};

export const safeFormatDate = (dateStr, options = {}, lang = 'en') => {
  if (!dateStr) return 'N/A';
  try {
    const parts = String(dateStr).split('T')[0].split('-');
    if (parts.length === 3) {
      const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString(lang === 'en' ? 'en-IN' : 'hi-IN', options);
      }
    }
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString(lang === 'en' ? 'en-IN' : 'hi-IN', options);
    }
  } catch (e) {}
  return dateStr || 'N/A';
};

export const translateScheduleString = (rawStr, currentLang = 'en') => {
  if (!rawStr) return '';
  let str = rawStr.replace(/Timing:/gi, '').trim();
  if (currentLang === 'hi') {
    return str
      .replace(/Monday|Mon/gi, 'सोम')
      .replace(/Tuesday|Tue/gi, 'मंगल')
      .replace(/Wednesday|Wed/gi, 'बुध')
      .replace(/Thursday|Thu/gi, 'गुरु')
      .replace(/Friday|Fri/gi, 'शुक्र')
      .replace(/Saturday|Sat/gi, 'शनि')
      .replace(/Sunday|Sun/gi, 'रवि');
  } else {
    return str
      .replace(/सोम/g, 'Mon')
      .replace(/मंगल/g, 'Tue')
      .replace(/बुध/g, 'Wed')
      .replace(/गुरु/g, 'Thu')
      .replace(/शुक्र/g, 'Fri')
      .replace(/शनि/g, 'Sat')
      .replace(/रवि/g, 'Sun');
  }
};

