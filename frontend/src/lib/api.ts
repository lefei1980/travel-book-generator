// Use relative URLs to hit Next.js API routes (which proxy to backend)
// This solves mixed content blocking (HTTPS frontend → HTTP backend)
const API_BASE = "";

export interface PlaceInput {
  name: string;
  place_type: "hotel" | "attraction" | "restaurant";
}

export interface DayInput {
  day_number: number;
  start_location: string;
  end_location: string;
  places: PlaceInput[];
}

export interface TripCreateRequest {
  title: string;
  start_date?: string;
  end_date?: string;
  days: DayInput[];
}

export interface TripCreateResponse {
  id: string;
  status: string;
}

export interface PlaceResponse {
  name: string;
  place_type: string;
  latitude: number | null;
  longitude: number | null;
}

export interface DayResponse {
  day_number: number;
  start_location: string | null;
  end_location: string | null;
  places: PlaceResponse[];
}

export interface TripResponse {
  id: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  status: string;
  error_message: string | null;
  days: DayResponse[];
}

export async function createTrip(
  data: TripCreateRequest
): Promise<TripCreateResponse> {
  const res = await fetch(`${API_BASE}/api/trips`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to create trip");
  }
  return res.json();
}

export async function getTrip(id: string): Promise<TripResponse> {
  const res = await fetch(`${API_BASE}/api/trips/${id}`);
  if (!res.ok) {
    throw new Error("Failed to fetch trip");
  }
  return res.json();
}

export function getDownloadUrl(id: string): string {
  return `${API_BASE}/api/trips/${id}/download`;
}
