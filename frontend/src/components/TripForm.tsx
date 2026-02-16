"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { createTrip, updateTrip, getTrip, getDownloadUrl, getPreviewUrl, generatePDF, DayInput, TripCreateRequest } from "@/lib/api";
import DaySection from "./DaySection";

const STATUS_MESSAGES: Record<string, string> = {
  pending: "Preparing your trip...",
  geocoding: "Geocoding locations...",
  routing: "Calculating routes...",
  enriching: "Fetching images and descriptions...",
  rendering: "Generating preview...",
  preview_ready: "Preview ready!",
  generating_pdf: "Generating PDF...",
  complete: "Your travel guide is ready!",
  error: "Something went wrong.",
};

const EMPTY_DAY = (dayNumber: number): DayInput => ({
  day_number: dayNumber,
  start_location: "",
  end_location: "",
  places: [{ name: "", place_type: "attraction" }],
});

const STORAGE_KEY = "travelbook_draft";

type ViewMode = 'form' | 'status' | 'preview';

export default function TripForm() {
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [days, setDays] = useState<DayInput[]>([EMPTY_DAY(1)]);
  const [tripId, setTripId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('form');
  const [generatingPDF, setGeneratingPDF] = useState(false);
  const previewIframeRef = useRef<HTMLIFrameElement>(null);

  // Location shortcuts
  const [useAllSameLocation, setUseAllSameLocation] = useState(false);
  const [sharedLocation, setSharedLocation] = useState("");

  // Auto-calculate end date from start date + number of days
  const endDate = startDate && days.length > 0
    ? (() => {
        const start = new Date(startDate + "T00:00:00");
        start.setDate(start.getDate() + days.length - 1);
        return start.toISOString().split("T")[0];
      })()
    : "";

  // Load draft from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const draft = JSON.parse(saved);
        setTitle(draft.title || "");
        setStartDate(draft.startDate || "");
        if (draft.days?.length) setDays(draft.days);
      } catch {
        // ignore invalid saved data
      }
    }
  }, []);

  // Save draft to localStorage
  useEffect(() => {
    if (!tripId) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ title, startDate, days }));
    }
  }, [title, startDate, days, tripId]);

  // Poll for status
  const pollStatus = useCallback(async (id: string) => {
    try {
      const trip = await getTrip(id);
      setStatus(trip.status);
      if (trip.status === "error") {
        setError(trip.error_message || "Pipeline failed");
        setSubmitting(false);
        setViewMode('status');
      } else if (trip.status === "preview_ready") {
        setSubmitting(false);
        setViewMode('preview');
      } else if (trip.status === "complete") {
        setSubmitting(false);
        setViewMode('status');
      } else {
        setTimeout(() => pollStatus(id), 2000);
      }
    } catch {
      setError("Failed to check trip status");
      setSubmitting(false);
      setViewMode('status');
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    setViewMode('status');

    // Filter out empty places and empty days
    const cleanDays = days
      .map((d) => ({
        ...d,
        places: d.places.filter((p) => p.name.trim()),
      }))
      .filter((d) => d.places.length > 0);

    if (!cleanDays.length) {
      setError("Add at least one day with at least one place");
      setSubmitting(false);
      setViewMode('form');
      return;
    }

    const request: TripCreateRequest = {
      title,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      days: cleanDays,
    };

    try {
      let result;
      if (tripId) {
        // Update existing trip (editing from preview)
        result = await updateTrip(tripId, request);
      } else {
        // Create new trip
        result = await createTrip(request);
        setTripId(result.id);
      }
      setStatus(result.status);
      localStorage.removeItem(STORAGE_KEY);
      pollStatus(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create trip");
      setSubmitting(false);
      setViewMode('form');
    }
  };

  const handleEdit = () => {
    setViewMode('form');
    setError(null);
  };

  const handleDownloadPDF = () => {
    // Trigger print dialog on the iframe content
    // This preserves the current zoom/pan state of maps
    if (previewIframeRef.current?.contentWindow) {
      previewIframeRef.current.contentWindow.print();
    } else {
      setError("Preview not loaded. Please try again.");
    }
  };

  const addDay = () => {
    setDays([...days, EMPTY_DAY(days.length + 1)]);
  };

  const removeDay = (index: number) => {
    const newDays = days
      .filter((_, i) => i !== index)
      .map((d, i) => ({ ...d, day_number: i + 1 }));
    setDays(newDays.length ? newDays : [EMPTY_DAY(1)]);
  };

  const updateDay = (index: number, day: DayInput) => {
    const newDays = [...days];
    newDays[index] = day;
    setDays(newDays);
  };

  const handleUseAllSameLocationChange = (checked: boolean) => {
    setUseAllSameLocation(checked);
    if (checked && sharedLocation) {
      // Auto-fill all days with shared location
      const updatedDays = days.map(d => ({
        ...d,
        start_location: sharedLocation,
        end_location: sharedLocation,
      }));
      setDays(updatedDays);
    }
  };

  const handleSharedLocationChange = (value: string) => {
    setSharedLocation(value);
    if (useAllSameLocation) {
      // Auto-update all days
      const updatedDays = days.map(d => ({
        ...d,
        start_location: value,
        end_location: value,
      }));
      setDays(updatedDays);
    }
  };

  const resetForm = () => {
    setTripId(null);
    setStatus(null);
    setError(null);
    setTitle("");
    setStartDate("");
    setDays([EMPTY_DAY(1)]);
    localStorage.removeItem(STORAGE_KEY);
  };

  // Preview view
  if (viewMode === 'preview' && tripId && status === "preview_ready") {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-6xl mx-auto p-6">
          <div className="bg-white rounded-lg shadow mb-4 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-800">{title}</h2>
                <p className="text-sm text-gray-600">Preview your travel guide before generating PDF</p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleEdit}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
                >
                  ← Edit Trip
                </button>
                <button
                  onClick={handleDownloadPDF}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
                >
                  Save as PDF
                </button>
              </div>
            </div>
            {error && (
              <div className="mt-3 bg-red-50 text-red-700 p-3 rounded">{error}</div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
            <iframe
              ref={previewIframeRef}
              src={getPreviewUrl(tripId)}
              className="w-full h-full border-0"
              title="Trip Preview"
            />
          </div>
        </div>
      </div>
    );
  }

  // Status view (processing or complete)
  if (viewMode === 'status' && tripId && status) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">{title}</h2>

          <div className="mb-6">
            <p className="text-lg text-gray-600">{STATUS_MESSAGES[status] || status}</p>
            {!["complete", "error", "preview_ready"].includes(status) && (
              <div className="mt-4">
                <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
              </div>
            )}
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded mb-4">{error}</div>
          )}

          {status === "complete" && (
            <a
              href={getDownloadUrl(tripId)}
              className="inline-block bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 font-medium"
            >
              Download PDF
            </a>
          )}

          <button
            onClick={resetForm}
            className="block mx-auto mt-4 text-blue-600 hover:text-blue-800 text-sm"
          >
            Create another trip
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">Trip Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-2 text-gray-900"
          placeholder="e.g., Paris Summer 2025"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 text-gray-900"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            End Date {endDate && <span className="text-gray-400 font-normal">(auto)</span>}
          </label>
          <input
            type="date"
            value={endDate}
            readOnly
            className="w-full border border-gray-200 rounded-lg px-4 py-2 text-gray-500 bg-gray-50 cursor-not-allowed"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg mb-4">{error}</div>
      )}

      {/* Location Shortcuts */}
      <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3 cursor-pointer">
          <input
            type="checkbox"
            checked={useAllSameLocation}
            onChange={(e) => handleUseAllSameLocationChange(e.target.checked)}
            className="rounded border-gray-300"
          />
          <span>All days start and end at the same location</span>
          <span className="text-gray-400 font-normal">(e.g., same hotel entire trip)</span>
        </label>

        {useAllSameLocation && (
          <div>
            <label className="block text-sm text-gray-600 mb-1">Shared Location</label>
            <input
              type="text"
              value={sharedLocation}
              onChange={(e) => handleSharedLocationChange(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900"
              placeholder="e.g., Grand Hotel Paris"
            />
            <p className="mt-1 text-xs text-gray-500">This location will be used for all days' start and end locations</p>
          </div>
        )}
      </div>

      <div className="mb-4">
        {days.map((day, idx) => (
          <DaySection
            key={idx}
            day={day}
            onChange={(d) => updateDay(idx, d)}
            onRemove={() => removeDay(idx)}
            sharedLocation={useAllSameLocation ? sharedLocation : undefined}
            disabled={useAllSameLocation}
          />
        ))}
      </div>

      <div className="flex justify-between">
        <button
          type="button"
          onClick={addDay}
          className="text-blue-600 hover:text-blue-800 font-medium"
        >
          + Add Day
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
        >
          {submitting ? "Generating..." : "Generate Travel Guide"}
        </button>
      </div>
    </form>
  );
}
