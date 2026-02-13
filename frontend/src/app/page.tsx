import TripForm from "@/components/TripForm";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-2xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">TravelBook Generator</h1>
          <p className="text-sm text-gray-500">Create a beautiful PDF travel guide from your itinerary</p>
        </div>
      </header>
      <main className="py-6">
        <TripForm />
      </main>
    </div>
  );
}
