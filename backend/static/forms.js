/**
 * Form enhancement utilities
 * Adds loading states to forms during submission
 */
(function() {
    'use strict';

    // Add loading state to submit buttons when form is submitted
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.tagName !== 'FORM') return;

        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.classList.add('loading');
            submitButton.setAttribute('aria-busy', 'true');
            // Prevent double submission
            submitButton.disabled = true;
        }
    });

    // Re-enable buttons if the user navigates back
    window.addEventListener('pageshow', function(e) {
        if (e.persisted) {
            document.querySelectorAll('button[type="submit"].loading').forEach(btn => {
                btn.classList.remove('loading');
                btn.removeAttribute('aria-busy');
                btn.disabled = false;
            });
        }
    });
})();
