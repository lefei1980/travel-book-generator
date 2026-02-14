import TripForm from "@/components/TripForm";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-2xl mx-auto px-6 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">TravelBook Generator</h1>
          <p className="text-base text-gray-600 mb-3">
            Transform your travel itinerary into a professionally formatted, map-rich PDF travel guide.
            Simply enter your trip details, destinations, and points of interest — we'll geocode locations,
            calculate routes, enrich each place with descriptions and images from Wikipedia, and render
            everything into a downloadable PDF with embedded interactive maps.
          </p>
          <p className="text-sm text-gray-400 mb-2">
            This tool uses free public APIs (Nominatim for geocoding, OSRM for routing, Wikipedia and
            Wikimedia Commons for content enrichment). All processing happens on the server, and your
            generated PDFs are available for immediate download.
          </p>
          <p className="text-sm text-gray-500">
            Designed and developed by Fei Le
          </p>
        </div>
      </header>
      <main className="py-6">
        <TripForm />
      </main>
      <footer className="py-8">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <p className="text-xs text-gray-400">
            &copy; 2026 Fei Le. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
