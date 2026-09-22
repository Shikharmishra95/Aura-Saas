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
