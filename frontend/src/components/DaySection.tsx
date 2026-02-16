"use client";

import { useState } from "react";
import { DayInput, PlaceInput, GeocodeResult } from "@/lib/api";
import LocationPreview from "./LocationPreview";

interface DaySectionProps {
  day: DayInput;
  onChange: (day: DayInput) => void;
  onRemove: () => void;
  sharedLocation?: string; // From trip-level "all days same" setting
  disabled?: boolean; // Disable start/end inputs when using shared location
}

const PLACE_TYPES = ["attraction", "restaurant", "hotel"] as const;
const SOFT_LIMIT_WARNING = 10;

export default function DaySection({ day, onChange, onRemove, sharedLocation, disabled }: DaySectionProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [showStartPreview, setShowStartPreview] = useState(false);
  const [showEndPreview, setShowEndPreview] = useState(false);
  const [showPlacePreview, setShowPlacePreview] = useState<number | null>(null);
  const [sameEndAsStart, setSameEndAsStart] = useState(true); // Default: end = start

  const updatePlace = (index: number, field: keyof PlaceInput, value: string) => {
    const newPlaces = [...day.places];
    newPlaces[index] = { ...newPlaces[index], [field]: value };
    onChange({ ...day, places: newPlaces });
  };

  const addPlace = () => {
    onChange({
      ...day,
      places: [...day.places, { name: "", place_type: "attraction" }],
    });
  };

  const handleSelectLocation = (field: "start_location" | "end_location", result: GeocodeResult) => {
    const updates: Partial<DayInput> = { [field]: result.display_name };
    // Auto-copy to end location if "same end as start" is checked
    if (field === "start_location" && sameEndAsStart && !disabled) {
      updates.end_location = result.display_name;
    }
    onChange({ ...day, ...updates });
    if (field === "start_location") setShowStartPreview(false);
    if (field === "end_location") setShowEndPreview(false);
  };

  const handleStartLocationChange = (value: string) => {
    const updates: Partial<DayInput> = { start_location: value };
    // Auto-copy to end location if "same end as start" is checked
    if (sameEndAsStart && !disabled) {
      updates.end_location = value;
    }
    onChange({ ...day, ...updates });
  };

  const handleSameEndAsStartChange = (checked: boolean) => {
    setSameEndAsStart(checked);
    if (checked && !disabled) {
      // Copy start to end
      onChange({ ...day, end_location: day.start_location });
    }
  };

  const handleSelectPlace = (index: number, result: GeocodeResult) => {
    updatePlace(index, "name", result.display_name);
    setShowPlacePreview(null);
  };

  const removePlace = (index: number) => {
    onChange({
      ...day,
      places: day.places.filter((_, i) => i !== index),
    });
  };

  const handleDragStart = (index: number) => {
    setDragIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDrop = (index: number) => {
    if (dragIndex === null || dragIndex === index) {
      setDragIndex(null);
      setDragOverIndex(null);
      return;
    }
    const newPlaces = [...day.places];
    const [moved] = newPlaces.splice(dragIndex, 1);
    newPlaces.splice(index, 0, moved);
    onChange({ ...day, places: newPlaces });
    setDragIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDragIndex(null);
    setDragOverIndex(null);
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 mb-4 bg-white">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold text-gray-800">Day {day.day_number}</h3>
        <button
          type="button"
          onClick={onRemove}
          className="text-red-500 hover:text-red-700 text-sm"
        >
          Remove Day
        </button>
      </div>

      {disabled && sharedLocation && (
        <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
          Using shared location: <strong>{sharedLocation}</strong>
        </div>
      )}

      {!disabled && (
        <div className="mb-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 mb-2 cursor-pointer">
            <input
              type="checkbox"
              checked={sameEndAsStart}
              onChange={(e) => handleSameEndAsStartChange(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>End at same location as start</span>
          </label>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Start Location</label>
          <input
            type="text"
            value={disabled ? sharedLocation || "" : day.start_location}
            onChange={(e) => handleStartLocationChange(e.target.value)}
            onFocus={() => !disabled && setShowStartPreview(true)}
            onBlur={() => setTimeout(() => setShowStartPreview(false), 300)}
            disabled={disabled}
            className={`w-full border rounded px-3 py-2 text-sm ${
              disabled
                ? "border-gray-200 bg-gray-50 text-gray-500 cursor-not-allowed"
                : "border-gray-300 text-gray-900"
            }`}
            placeholder="e.g., Hotel name or airport"
          />
          {showStartPreview && day.start_location && !disabled && (
            <LocationPreview
              query={day.start_location}
              onSelect={(result) => handleSelectLocation("start_location", result)}
            />
          )}
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">End Location</label>
          <input
            type="text"
            value={disabled ? sharedLocation || "" : day.end_location}
            onChange={(e) => onChange({ ...day, end_location: e.target.value })}
            onFocus={() => !disabled && !sameEndAsStart && setShowEndPreview(true)}
            onBlur={() => setTimeout(() => setShowEndPreview(false), 300)}
            disabled={disabled || sameEndAsStart}
            className={`w-full border rounded px-3 py-2 text-sm ${
              disabled || sameEndAsStart
                ? "border-gray-200 bg-gray-50 text-gray-500 cursor-not-allowed"
                : "border-gray-300 text-gray-900"
            }`}
            placeholder="e.g., Hotel name"
          />
          {showEndPreview && day.end_location && !disabled && !sameEndAsStart && (
            <LocationPreview
              query={day.end_location}
              onSelect={(result) => handleSelectLocation("end_location", result)}
            />
          )}
        </div>
      </div>

      <div className="mb-2">
        <label className="block text-sm text-gray-600 mb-1">
          Places ({day.places.length}) <span className="text-gray-400">— drag to reorder</span>
        </label>
        {day.places.length >= SOFT_LIMIT_WARNING && (
          <div className="mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
            ⚠️ You have {day.places.length} places. This day may span {Math.ceil(day.places.length / 5)} pages in the PDF.
          </div>
        )}
        {day.places.map((place, idx) => (
          <div key={idx} className="mb-2">
            <div
              onDragOver={(e) => handleDragOver(e, idx)}
              onDrop={() => handleDrop(idx)}
              className={`flex gap-2 items-center transition-all ${
                dragIndex === idx ? "opacity-40" : ""
              } ${dragOverIndex === idx && dragIndex !== idx ? "border-t-2 border-blue-400" : ""}`}
            >
              <span
                draggable
                onDragStart={() => handleDragStart(idx)}
                onDragEnd={handleDragEnd}
                className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 select-none px-1"
                title="Drag to reorder"
              >
                ⋮⋮
              </span>
              <input
                type="text"
                value={place.name}
                onChange={(e) => updatePlace(idx, "name", e.target.value)}
                onFocus={() => setShowPlacePreview(idx)}
                onBlur={() => setTimeout(() => setShowPlacePreview(null), 300)}
                className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm text-gray-900"
                placeholder="Place name"
              />
              <select
                value={place.place_type}
                onChange={(e) => updatePlace(idx, "place_type", e.target.value)}
                className="border border-gray-300 rounded px-3 py-2 text-sm text-gray-900"
              >
                {PLACE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removePlace(idx)}
                className="text-red-400 hover:text-red-600 px-2"
              >
                X
              </button>
            </div>
            {showPlacePreview === idx && place.name && (
              <LocationPreview
                query={place.name}
                onSelect={(result) => handleSelectPlace(idx, result)}
                className="ml-6"
              />
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={addPlace}
          className="text-blue-600 hover:text-blue-800 text-sm"
        >
          + Add Place
        </button>
      </div>
    </div>
  );
}
