/**
 * Species autocomplete with fuzzy search using Fuse.js
 * Requires Fuse.js to be loaded first.
 *
 * Expects these elements in the DOM:
 * - #species-input: text input for typing
 * - #species: hidden input for the species code
 * - #autocomplete-results: container for dropdown results
 */
(function() {
    const input = document.getElementById('species-input');
    const hidden = document.getElementById('species');
    const results = document.getElementById('autocomplete-results');
    if (!input) return;

    let taxonomy = null;
    let fuse = null;
    let debounceTimer;
    let loading = false;

    // Preload taxonomy on focus
    async function loadTaxonomy() {
        if (taxonomy || loading) return;
        loading = true;
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

    input.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const q = this.value.trim();

        if (q.length < 2) {
            results.innerHTML = '';
            results.style.display = 'none';
            return;
        }

        debounceTimer = setTimeout(() => {
            if (!taxonomy) {
                results.innerHTML = '<div class="autocomplete-item no-results">Loading species list...</div>';
                results.style.display = 'block';
                loadTaxonomy().then(() => {
                    if (input.value.trim().length >= 2) {
                        input.dispatchEvent(new Event('input'));
                    }
                });
                return;
            }

            const matches = search(q);

            if (matches.length === 0) {
                results.innerHTML = '<div class="autocomplete-item no-results">No species found</div>';
            } else {
                results.innerHTML = matches.map(s =>
                    `<div class="autocomplete-item" data-code="${s.code}" data-name="${s.name}">
                        <span class="species-common">${s.name}</span>
                        <span class="species-sci">${s.sciName}</span>
                    </div>`
                ).join('');
            }
            results.style.display = 'block';
        }, 150);
    });

    results.addEventListener('click', function(e) {
        const item = e.target.closest('.autocomplete-item');
        if (item && item.dataset.code) {
            input.value = item.dataset.name;
            hidden.value = item.dataset.code;
            results.style.display = 'none';
        }
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.autocomplete-wrapper')) {
            results.style.display = 'none';
        }
    });
})();
