/**
 * Results page functionality - filtering, grouping, and display of observations
 * Depends on: utils.js (escapeHtml)
 */
(function() {
    'use strict';

    const dataElement = document.getElementById('observations-data');
    if (!dataElement) return;

    const observations = JSON.parse(dataElement.textContent);
    const container = document.getElementById('results-container');
    const filterInput = document.getElementById('species-filter');
    const btnGrouped = document.getElementById('view-grouped');
    const btnAll = document.getElementById('view-all');
    const isNotable = document.body.dataset.notable === 'true';

    // For Recent view, always show flat list (API returns 1 record per species)
    // For Notable view, default to grouped (API returns multiple records per species)
    let viewMode = isNotable ? 'grouped' : 'all';
    let filterText = '';
    let expandedSpecies = new Set();

    function renderLocation(obs) {
        const locName = escapeHtml(obs.locName);
        const locHtml = obs.locationPrivate
            ? `<span class="loc-name">${locName}</span>`
            : `<span class="loc-name"><a href="/hotspot/${encodeURIComponent(obs.locId)}" class="loc-link">${locName}</a></span>`;
        return `${locHtml}<a href="https://ebird.org/checklist/${encodeURIComponent(obs.subId)}" target="_blank" class="checklist-link" title="View checklist on eBird" aria-label="View checklist on eBird">📋</a>`;
    }

    function groupBySpecies(obs) {
        const groups = {};
        for (const o of obs) {
            const name = o.comName;
            if (!groups[name]) {
                groups[name] = { name, observations: [], totalCount: 0, locations: new Set(), mostRecent: o.obsDt, mostRecentFormatted: o.formattedDate };
            }
            groups[name].observations.push(o);
            groups[name].totalCount += o.howMany || 1;
            groups[name].locations.add(o.locName);
            if (o.obsDt > groups[name].mostRecent) {
                groups[name].mostRecent = o.obsDt;
                groups[name].mostRecentFormatted = o.formattedDate;
            }
        }
        return Object.values(groups).sort((a, b) => b.mostRecent.localeCompare(a.mostRecent));
    }

    function filterObservations(obs) {
        if (!filterText) return obs;
        const q = filterText.toLowerCase();
        return obs.filter(o => o.comName.toLowerCase().includes(q));
    }

    function render() {
        const filtered = filterObservations(observations);

        if (filtered.length === 0) {
            container.innerHTML = '<p class="no-results">No matching species found.</p>';
            return;
        }

        if (viewMode === 'all') {
            renderFlatList(filtered);
        } else {
            renderGroupedList(filtered);
        }
    }

    function renderFlatList(obs) {
        let html = `<table class="observations-table" role="table">
            <thead>
                <tr>
                    <th scope="col">Species</th>
                    <th scope="col">Count</th>
                    <th scope="col">Location</th>
                    <th scope="col">Date</th>
                </tr>
            </thead>
            <tbody>`;

        for (const o of obs) {
            html += `<tr>
                <td class="species-name">${escapeHtml(o.comName)}</td>
                <td class="count">${o.howMany || 'X'}</td>
                <td class="location">${renderLocation(o)}</td>
                <td class="date">${escapeHtml(o.formattedDate)}</td>
            </tr>`;
        }

        html += '</tbody></table>';
        container.innerHTML = html;
    }

    function renderGroupedList(obs) {
        const groups = groupBySpecies(obs);

        let html = `<table class="observations-table grouped-table" role="table">
            <thead>
                <tr>
                    <th scope="col">Species</th>
                    <th scope="col">Sightings</th>
                    <th scope="col">Locations</th>
                    <th scope="col">Most Recent</th>
                </tr>
            </thead>
            <tbody>`;

        for (const group of groups) {
            const isExpanded = expandedSpecies.has(group.name);
            const expandIcon = isExpanded ? '▼' : '▶';
            const escapedName = escapeHtml(group.name);
            const ariaExpanded = isExpanded ? 'true' : 'false';
            const ariaLabel = `${group.name}, ${group.observations.length} sightings. Click to ${isExpanded ? 'collapse' : 'expand'} details.`;

            html += `<tr class="species-group-row expandable"
                        data-species="${escapedName}"
                        role="button"
                        tabindex="0"
                        aria-expanded="${ariaExpanded}"
                        aria-label="${ariaLabel}">
                <td class="species-name">
                    <span class="expand-icon" aria-hidden="true">${expandIcon}</span>
                    ${escapedName}
                </td>
                <td class="count">${group.observations.length}</td>
                <td class="locations-count">${group.locations.size} location${group.locations.size !== 1 ? 's' : ''}</td>
                <td class="date">${escapeHtml(group.mostRecentFormatted)}</td>
            </tr>`;

            if (isExpanded) {
                for (const o of group.observations) {
                    html += `<tr class="species-detail-row">
                        <td class="species-name detail-indent"></td>
                        <td class="count">${o.howMany || 'X'}</td>
                        <td class="location">${renderLocation(o)}</td>
                        <td class="date">${escapeHtml(o.formattedDate)}</td>
                    </tr>`;
                }
            }
        }

        html += '</tbody></table>';
        container.innerHTML = html;

        // Add click and keyboard handlers for expandable rows
        container.querySelectorAll('.species-group-row.expandable').forEach(row => {
            row.addEventListener('click', () => toggleRow(row));
            row.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleRow(row);
                }
            });
        });
    }

    function toggleRow(row) {
        const species = row.dataset.species;
        if (expandedSpecies.has(species)) {
            expandedSpecies.delete(species);
        } else {
            expandedSpecies.add(species);
        }
        render();
        // Restore focus to the row after re-render
        const newRow = container.querySelector(`[data-species="${species}"]`);
        if (newRow) newRow.focus();
    }

    // Event listeners for toggle buttons (only present for Notable view)
    if (btnGrouped && btnAll) {
        btnGrouped.addEventListener('click', () => {
            viewMode = 'grouped';
            btnGrouped.classList.add('active');
            btnAll.classList.remove('active');
            render();
        });

        btnAll.addEventListener('click', () => {
            viewMode = 'all';
            btnAll.classList.add('active');
            btnGrouped.classList.remove('active');
            render();
        });
    }

    filterInput.addEventListener('input', (e) => {
        filterText = e.target.value.trim();
        render();
    });

    // Initial render
    render();
})();
