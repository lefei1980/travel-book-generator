"use client";

import { useState, useEffect, useCallback } from "react";
import { geocodePreview, GeocodeResult } from "@/lib/api";

interface LocationPreviewProps {
  query: string;
  onSelect?: (result: GeocodeResult) => void;
  className?: string;
}

const DEBOUNCE_MS = 1000;
const RESULTS_PER_PAGE = 5;

export default function LocationPreview({ query, onSelect, className = "" }: LocationPreviewProps) {
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(RESULTS_PER_PAGE);
  const [shouldFetch, setShouldFetch] = useState(false);

  // Debounced fetch trigger
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setShouldFetch(false);
      return;
    }

    const timer = setTimeout(() => {
      setShouldFetch(true);
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      setShouldFetch(false);
    };
  }, [query]);

  // Fetch geocoding results
  useEffect(() => {
    if (!shouldFetch) return;

    const fetchResults = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await geocodePreview(query, 10);
        setResults(data.results);
        setVisibleCount(RESULTS_PER_PAGE); // Reset visible count on new search
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch locations");
        setResults([]);
      } finally {
        setLoading(false);
        setShouldFetch(false);
      }
    };

    fetchResults();
  }, [shouldFetch, query]);

  const handleSelect = useCallback(
    (result: GeocodeResult) => {
      if (onSelect) {
        onSelect(result);
      }
    },
    [onSelect]
  );

  const handleShowMore = () => {
    setVisibleCount((prev) => Math.min(prev + RESULTS_PER_PAGE, results.length));
  };

  if (!query.trim()) {
    return null;
  }

  if (loading) {
    return (
      <div className={`mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg ${className}`}>
        <div className="flex items-center gap-2 text-sm text-blue-700">
          <div className="animate-spin inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full" />
          <span>Searching for locations...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`mt-2 p-3 bg-red-50 border border-red-200 rounded-lg ${className}`}>
        <div className="text-sm text-red-700">❌ {error}</div>
      </div>
    );
  }

  if (results.length === 0 && !loading) {
    return (
      <div className={`mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg ${className}`}>
        <div className="text-sm text-yellow-800">
          ❌ No locations found. Try adding city or country (e.g., "Mt Britton Tower, Puerto Rico")
        </div>
      </div>
    );
  }

  const visibleResults = results.slice(0, visibleCount);
  const hasMore = visibleCount < results.length;

  return (
    <div className={`mt-2 border border-gray-300 rounded-lg bg-white shadow-sm ${className}`}>
      <div className="p-2 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">
        📍 Preview locations:
      </div>
      <div className="divide-y divide-gray-200">
        {visibleResults.map((result, idx) => (
          <button
            key={idx}
            onClick={() => handleSelect(result)}
            className="w-full p-3 text-left hover:bg-blue-50 transition-colors flex items-start gap-2 group"
          >
            <span className="text-lg">
              {idx === 0 ? "✓" : " "}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-900 group-hover:text-blue-700 truncate">
                {result.display_name}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {result.type} • {result.lat.toFixed(4)}, {result.lon.toFixed(4)}
              </div>
            </div>
            <span className="text-xs text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity">
              Select
            </span>
          </button>
        ))}
      </div>
      <div className="p-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-600 flex justify-between items-center">
        <span>
          Showing {Math.min(visibleCount, results.length)} of {results.length} results
        </span>
        {hasMore && (
          <button
            onClick={handleShowMore}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            Show {Math.min(RESULTS_PER_PAGE, results.length - visibleCount)} more
          </button>
        )}
      </div>
    </div>
  );
}
