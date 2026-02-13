"use client";

import { useState } from "react";
import { DayInput, PlaceInput } from "@/lib/api";

interface DaySectionProps {
  day: DayInput;
  onChange: (day: DayInput) => void;
  onRemove: () => void;
}

const PLACE_TYPES = ["attraction", "restaurant", "hotel"] as const;

export default function DaySection({ day, onChange, onRemove }: DaySectionProps) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

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
          Places ({day.places.length}/5) <span className="text-gray-400">— drag to reorder</span>
        </label>
        {day.places.map((place, idx) => (
          <div
            key={idx}
            draggable
            onDragStart={() => handleDragStart(idx)}
            onDragOver={(e) => handleDragOver(e, idx)}
            onDrop={() => handleDrop(idx)}
            onDragEnd={handleDragEnd}
            className={`flex gap-2 mb-2 items-center transition-all ${
              dragIndex === idx ? "opacity-40" : ""
            } ${dragOverIndex === idx && dragIndex !== idx ? "border-t-2 border-blue-400" : ""}`}
          >
            <span
              className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 select-none px-1"
              title="Drag to reorder"
            >
              ⠿
            </span>
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
