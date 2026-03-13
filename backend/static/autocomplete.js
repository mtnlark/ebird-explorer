/**
 * Species autocomplete with fuzzy search using Fuse.js
 * Requires: utils.js (escapeHtml), Fuse.js
 *
 * Expects these elements in the DOM:
 * - #species-input: text input for typing
 * - #species: hidden input for the species code
 * - #autocomplete-results: container for dropdown results
 */
(function() {
    'use strict';

    const input = document.getElementById('species-input');
    const hidden = document.getElementById('species');
    const results = document.getElementById('autocomplete-results');
    if (!input) return;

    let taxonomy = null;
    let fuse = null;
    let debounceTimer;
    let loading = false;
    let selectedIndex = -1;
    let currentMatches = [];

    // Set up ARIA attributes
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', 'autocomplete-results');
    results.setAttribute('role', 'listbox');
    results.setAttribute('aria-label', 'Species suggestions');

    // Preload taxonomy on focus
    async function loadTaxonomy() {
        if (taxonomy || loading) return;
        loading = true;
        input.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch('/api/taxonomy');
            taxonomy = await response.json();
            fuse = new Fuse(taxonomy, {
                keys: ['name', 'sciName'],
                threshold: 0.4,
                distance: 100,
                ignoreLocation: true,
                includeScore: true
            });
        } catch (e) {
            console.error('Failed to load taxonomy:', e);
        }
        loading = false;
        input.setAttribute('aria-busy', 'false');
    }

    input.addEventListener('focus', loadTaxonomy);

    function search(query) {
        if (!taxonomy || !fuse) return [];

        const q = query.toLowerCase();

        // Find exact prefix matches
        const prefixMatches = taxonomy.filter(s =>
            s.name.toLowerCase().startsWith(q) ||
            s.sciName.toLowerCase().startsWith(q)
        ).slice(0, 5);

        // Get fuzzy matches
        const fuzzyResults = fuse.search(query, { limit: 15 });
        const fuzzyMatches = fuzzyResults
            .map(r => r.item)
            .filter(item => !prefixMatches.some(p => p.code === item.code));

        // Combine: prefix first, then fuzzy
        const combined = [...prefixMatches, ...fuzzyMatches].slice(0, 10);
        return combined;
    }

    function renderResults(matches) {
        currentMatches = matches;
        selectedIndex = -1;

        if (matches.length === 0) {
            results.innerHTML = '<div class="autocomplete-item no-results" role="status">No species found</div>';
            input.setAttribute('aria-expanded', 'true');
        } else {
            results.innerHTML = matches.map((s, index) =>
                `<div class="autocomplete-item"
                     id="autocomplete-option-${index}"
                     role="option"
                     aria-selected="false"
                     data-code="${escapeHtml(s.code)}"
                     data-name="${escapeHtml(s.name)}">
                    <span class="species-common">${escapeHtml(s.name)}</span>
                    <span class="species-sci">${escapeHtml(s.sciName)}</span>
                </div>`
            ).join('');
            input.setAttribute('aria-expanded', 'true');
        }
        results.style.display = 'block';
    }

    function hideResults() {
        results.style.display = 'none';
        results.innerHTML = '';
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
        selectedIndex = -1;
        currentMatches = [];
    }

    function selectItem(index) {
        // Remove previous selection
        const prevSelected = results.querySelector('[aria-selected="true"]');
        if (prevSelected) {
            prevSelected.setAttribute('aria-selected', 'false');
            prevSelected.classList.remove('selected');
        }

        // Select new item
        if (index >= 0 && index < currentMatches.length) {
            selectedIndex = index;
            const item = document.getElementById(`autocomplete-option-${index}`);
            if (item) {
                item.setAttribute('aria-selected', 'true');
                item.classList.add('selected');
                input.setAttribute('aria-activedescendant', `autocomplete-option-${index}`);
                // Scroll into view if needed
                item.scrollIntoView({ block: 'nearest' });
            }
        } else {
            selectedIndex = -1;
            input.removeAttribute('aria-activedescendant');
        }
    }

    function confirmSelection() {
        if (selectedIndex >= 0 && selectedIndex < currentMatches.length) {
            const match = currentMatches[selectedIndex];
            input.value = match.name;
            hidden.value = match.code;
            hideResults();
        }
    }

    input.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const q = this.value.trim();

        if (q.length < 2) {
            hideResults();
            return;
        }

        debounceTimer = setTimeout(() => {
            if (!taxonomy) {
                results.innerHTML = '<div class="autocomplete-item no-results" role="status" aria-live="polite"><span class="loading-text"><span class="loading-spinner"></span>Loading species list...</span></div>';
                results.style.display = 'block';
                input.setAttribute('aria-expanded', 'true');
                loadTaxonomy().then(() => {
                    if (input.value.trim().length >= 2) {
                        input.dispatchEvent(new Event('input'));
                    }
                });
                return;
            }

            const matches = search(q);
            renderResults(matches);
        }, 150);
    });

    // Keyboard navigation
    input.addEventListener('keydown', function(e) {
        if (results.style.display !== 'block' || currentMatches.length === 0) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectItem(selectedIndex < currentMatches.length - 1 ? selectedIndex + 1 : 0);
                break;
            case 'ArrowUp':
                e.preventDefault();
                selectItem(selectedIndex > 0 ? selectedIndex - 1 : currentMatches.length - 1);
                break;
            case 'Enter':
                if (selectedIndex >= 0) {
                    e.preventDefault();
                    confirmSelection();
                }
                break;
            case 'Escape':
                e.preventDefault();
                hideResults();
                break;
            case 'Tab':
                // Allow natural tab behavior but close results
                hideResults();
                break;
        }
    });

    results.addEventListener('click', function(e) {
        const item = e.target.closest('.autocomplete-item');
        if (item && item.dataset.code) {
            input.value = item.dataset.name;
            hidden.value = item.dataset.code;
            hideResults();
        }
    });

    // Mouse hover updates selection for visual feedback
    results.addEventListener('mouseover', function(e) {
        const item = e.target.closest('.autocomplete-item');
        if (item && item.dataset.code) {
            const index = Array.from(results.querySelectorAll('.autocomplete-item[data-code]')).indexOf(item);
            if (index >= 0) selectItem(index);
        }
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.autocomplete-wrapper')) {
            hideResults();
        }
    });
})();
