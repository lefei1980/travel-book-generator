"use client";

import { DayInput, PlaceInput } from "@/lib/api";

interface DaySectionProps {
  day: DayInput;
  onChange: (day: DayInput) => void;
  onRemove: () => void;
}

const PLACE_TYPES = ["attraction", "restaurant", "hotel"] as const;

export default function DaySection({ day, onChange, onRemove }: DaySectionProps) {
  const updatePlace = (index: number, field: keyof PlaceInput, value: string) => {
    const newPlaces = [...day.places];
    newPlaces[index] = { ...newPlaces[index], [field]: value };
    onChange({ ...day, places: newPlaces });
  };

  const addPlace = () => {
    if (day.places.length >= 5) return;
    onChange({
      ...day,
      places: [...day.places, { name: "", place_type: "attraction" }],
    });
  };

  const removePlace = (index: number) => {
    onChange({
      ...day,
      places: day.places.filter((_, i) => i !== index),
    });
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

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Start Location</label>
          <input
            type="text"
            value={day.start_location}
            onChange={(e) => onChange({ ...day, start_location: e.target.value })}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm text-gray-900"
            placeholder="e.g., Hotel name or airport"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">End Location</label>
          <input
            type="text"
            value={day.end_location}
            onChange={(e) => onChange({ ...day, end_location: e.target.value })}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm text-gray-900"
            placeholder="e.g., Hotel name"
          />
        </div>
      </div>

      <div className="mb-2">
        <label className="block text-sm text-gray-600 mb-1">
          Places ({day.places.length}/5)
        </label>
        {day.places.map((place, idx) => (
          <div key={idx} className="flex gap-2 mb-2">
            <input
              type="text"
              value={place.name}
              onChange={(e) => updatePlace(idx, "name", e.target.value)}
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
        ))}
        {day.places.length < 5 && (
          <button
            type="button"
            onClick={addPlace}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            + Add Place
          </button>
        )}
      </div>
    </div>
  );
}
