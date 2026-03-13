/**
 * Shared utility functions for eBird Explorer
 */

/**
 * Escape HTML special characters to prevent XSS attacks.
 * @param {string} str - The string to escape
 * @returns {string} The escaped string
 */
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Debounce a function call.
 * @param {Function} func - The function to debounce
 * @param {number} wait - The debounce delay in milliseconds
 * @returns {Function} The debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export for use in modules (if needed in future)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { escapeHtml, debounce };
}
