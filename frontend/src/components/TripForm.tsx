"use client";

import { useState, useEffect, useCallback } from "react";
import { createTrip, getTrip, getDownloadUrl, DayInput, TripCreateRequest } from "@/lib/api";
import DaySection from "./DaySection";

const STATUS_MESSAGES: Record<string, string> = {
  pending: "Preparing your trip...",
  geocoding: "Geocoding locations...",
  routing: "Calculating routes...",
  enriching: "Fetching images and descriptions...",
  rendering: "Rendering your PDF...",
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

export default function TripForm() {
  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [days, setDays] = useState<DayInput[]>([EMPTY_DAY(1)]);
  const [tripId, setTripId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      } else if (trip.status === "complete") {
        setSubmitting(false);
      } else {
        setTimeout(() => pollStatus(id), 2000);
      }
    } catch {
      setError("Failed to check trip status");
      setSubmitting(false);
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

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
      return;
    }

    const request: TripCreateRequest = {
      title,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      days: cleanDays,
    };

    try {
      const result = await createTrip(request);
      setTripId(result.id);
      setStatus(result.status);
      localStorage.removeItem(STORAGE_KEY);
      pollStatus(result.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create trip");
      setSubmitting(false);
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

  const resetForm = () => {
    setTripId(null);
    setStatus(null);
    setError(null);
    setTitle("");
    setStartDate("");
    setDays([EMPTY_DAY(1)]);
    localStorage.removeItem(STORAGE_KEY);
  };

  // Status view
  if (tripId && status) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">{title}</h2>

          <div className="mb-6">
            <p className="text-lg text-gray-600">{STATUS_MESSAGES[status] || status}</p>
            {status !== "complete" && status !== "error" && (
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

      <div className="mb-4">
        {days.map((day, idx) => (
          <DaySection
            key={idx}
            day={day}
            onChange={(d) => updateDay(idx, d)}
            onRemove={() => removeDay(idx)}
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
