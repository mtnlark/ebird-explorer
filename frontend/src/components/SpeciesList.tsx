import React, { useState } from 'react';
import type { SpeciesMap } from '../types';

interface SpeciesListProps {
  species: SpeciesMap;
}

const SpeciesList: React.FC<SpeciesListProps> = ({ species }) => {
  const [sortBy, setSortBy] = useState<'name' | 'count'>('count');
  const [searchTerm, setSearchTerm] = useState('');

  const speciesArray = Object.entries(species).map(([name, data]) => ({
    name,
    ...data,
  }));

  // Filter by search term
  const filteredSpecies = speciesArray.filter((sp) =>
    sp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sp.scientific_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort species
  const sortedSpecies = [...filteredSpecies].sort((a, b) => {
    if (sortBy === 'count') {
      return b.count - a.count;
    }
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
      {/* Header with Search and Sort Controls */}
      <div className="bg-gradient-to-r from-sky-500 to-blue-600 px-6 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Species Found ({filteredSpecies.length})
          </h3>
        </div>
      </div>

      <div className="p-6">
        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Search species..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent transition duration-200"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'name' | 'count')}
            className="px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent transition duration-200 bg-white cursor-pointer"
          >
            <option value="count">Sort by Count</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>

        {/* Species Grid */}
        {sortedSpecies.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedSpecies.map((sp) => (
              <div
                key={sp.name}
                className="group bg-gradient-to-br from-white to-gray-50 border border-gray-200 rounded-lg p-5 hover:shadow-lg hover:border-sky-300 transition-all duration-200 cursor-pointer"
              >
                <div className="flex items-start justify-between mb-3">
                  <h4 className="text-lg font-semibold text-gray-800 group-hover:text-sky-600 transition-colors line-clamp-2">
                    {sp.name}
                  </h4>
                  <span className="ml-2 flex-shrink-0 inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-100 text-sky-700">
                    {sp.count}
                  </span>
                </div>
                <p className="text-sm text-gray-600 italic mb-3 line-clamp-1">
                  {sp.scientific_name}
                </p>
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Last seen: {new Date(sp.last_seen).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="mt-4 text-gray-500 font-medium">No species match your search</p>
            <p className="mt-1 text-sm text-gray-400">Try adjusting your search terms</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SpeciesList;
