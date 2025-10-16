import React, { useState } from 'react';
import LocationSearch from './components/LocationSearch';
import ObservationResults from './components/ObservationResults';
import { api } from './services/api';
import type { ObservationResponse, ApiError } from './types';

function App() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ObservationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (location: string, daysBack: number) => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await api.getObservationsByLocation(location, daysBack);

      if ('error' in result) {
        // It's an ApiError
        const apiError = result as ApiError;
        setError(apiError.error + (apiError.hint ? ` ${apiError.hint}` : ''));
      } else {
        // It's an ObservationResponse
        setData(result as ObservationResponse);
      }
    } catch (err) {
      setError('Failed to fetch data. Make sure the backend is running on http://localhost:8000');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-sky-400 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
              </svg>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">eBird Explorer</h1>
              <p className="text-sm text-gray-600 mt-1">Discover and analyze bird observations near you</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <LocationSearch onSearch={handleSearch} loading={loading} />

        {error && (
          <div className="mt-6 bg-red-50 border-l-4 border-red-400 p-4 rounded-r-lg shadow-sm">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">
                  <span className="font-medium">Error:</span> {error}
                </p>
              </div>
            </div>
          </div>
        )}

        {loading && (
          <div className="mt-8 flex flex-col items-center justify-center py-12">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-sky-200 border-t-sky-600 rounded-full animate-spin"></div>
            </div>
            <p className="mt-4 text-gray-600 font-medium">Fetching bird observations...</p>
          </div>
        )}

        {data && !loading && <ObservationResults data={data} />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Powered by the <span className="font-semibold text-gray-700">eBird API</span>
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
