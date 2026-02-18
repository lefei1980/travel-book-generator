"use client";

import { useState } from "react";
import TripForm from "@/components/TripForm";
import ChatPlanner from "@/components/ChatPlanner";

type Tab = "chat" | "manual";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">TravelBook Generator</h1>
          <p className="text-base text-gray-600 mb-3">
            Transform your travel itinerary into a professionally formatted, map-rich PDF travel guide.
            Chat with our AI to plan your trip, or enter your itinerary manually — we&apos;ll geocode
            locations, calculate routes, enrich each place with descriptions and images from Wikipedia,
            and render everything into a downloadable PDF.
          </p>
          <p className="text-sm text-gray-400 mb-2">
            This tool uses free public APIs (Nominatim, OSRM, Wikipedia, Wikimedia Commons) and Groq
            for AI planning. All processing happens on the server.
          </p>
          <p className="text-sm text-gray-500">Designed and developed by Fei Le</p>
        </div>
      </header>

      <main className="py-6">
        {/* Tab switcher */}
        <div className="max-w-2xl mx-auto px-6 mb-6">
          <div className="flex rounded-lg border border-gray-200 bg-white p-1 w-fit">
            <button
              onClick={() => setActiveTab("chat")}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "chat"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              AI Chat
            </button>
            <button
              onClick={() => setActiveTab("manual")}
              className={`px-5 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === "manual"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Manual Entry
            </button>
          </div>
        </div>

        {activeTab === "chat" ? <ChatPlanner /> : <TripForm />}
      </main>

      <footer className="py-8">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <p className="text-xs text-gray-400">&copy; 2026 Fei Le. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
