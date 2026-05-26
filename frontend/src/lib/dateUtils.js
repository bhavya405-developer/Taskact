/**
 * Shared date formatting utility for TaskAct
 * Standard format: DD-MMM-YY (e.g., "25-May-26")
 */

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Format a date string or Date object to DD-MMM-YY
 * @param {string|Date} dateValue - ISO string, Date object, or any parseable date
 * @returns {string} Formatted date like "25-May-26" or empty string if invalid
 */
export function formatDate(dateValue) {
  if (!dateValue) return '';
  try {
    const d = new Date(dateValue);
    if (isNaN(d.getTime())) return '';
    const day = String(d.getDate()).padStart(2, '0');
    const month = MONTHS[d.getMonth()];
    const year = String(d.getFullYear()).slice(-2);
    return `${day}-${month}-${year}`;
  } catch {
    return '';
  }
}

/**
 * Format a date+time string to DD-MMM-YY HH:MM AM/PM
 * @param {string|Date} dateValue
 * @returns {string} e.g. "25-May-26 02:30 PM"
 */
export function formatDateTime(dateValue) {
  if (!dateValue) return '';
  try {
    const d = new Date(dateValue);
    if (isNaN(d.getTime())) return '';
    const day = String(d.getDate()).padStart(2, '0');
    const month = MONTHS[d.getMonth()];
    const year = String(d.getFullYear()).slice(-2);
    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    return `${day}-${month}-${year} ${String(hours).padStart(2, '0')}:${minutes} ${ampm}`;
  } catch {
    return '';
  }
}
