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

export function getPreviewUrl(id: string): string {
  return `${API_BASE}/api/trips/${id}/preview`;
}

export async function updateTrip(
  id: string,
  data: TripCreateRequest
): Promise<TripCreateResponse> {
  const res = await fetch(`${API_BASE}/api/trips/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to update trip");
  }
  return res.json();
}

export async function generatePDF(id: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/trips/${id}/generate-pdf`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to generate PDF");
  }
  return res.json();
}

export interface GeocodeResult {
  display_name: string;
  lat: number;
  lon: number;
  type: string;
  importance: number;
}

export interface GeocodePreviewResponse {
  query: string;
  results: GeocodeResult[];
  total: number;
  message?: string;
}

// --- Chat API ---

export interface ChatMessageRequest {
  session_id?: string | null;
  message: string;
}

export interface ChatMessageResponse {
  session_id: string;
  reply: string;
}

export interface FinalizeResponse {
  trip_id: string;
  title: string;
  status: string;
}

export interface EditTripResponse {
  session_id: string;
}

export interface ChatSessionResponse {
  session_id: string;
  messages: Array<{ role: string; content: string }>;
}

export async function sendChatMessage(
  data: ChatMessageRequest
): Promise<ChatMessageResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to send message");
  }
  return res.json();
}

export async function finalizeChat(sessionId: string): Promise<FinalizeResponse> {
  const res = await fetch(`${API_BASE}/api/chat/${sessionId}/finalize`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to finalize itinerary");
  }
  return res.json();
}

export async function editTrip(tripId: string): Promise<EditTripResponse> {
  const res = await fetch(`${API_BASE}/api/trips/${tripId}/edit`, {
    method: "POST",
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "This trip cannot be edited via chat");
  }
  return res.json();
}

export async function getChatSession(sessionId: string): Promise<ChatSessionResponse> {
  const res = await fetch(`${API_BASE}/api/chat/${sessionId}`);
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to load chat session");
  }
  return res.json();
}

export async function geocodePreview(
  query: string,
  limit: number = 10
): Promise<GeocodePreviewResponse> {
  if (!query.trim()) {
    return {
      query,
      results: [],
      total: 0,
      message: "Query cannot be empty",
    };
  }

  const res = await fetch(
    `${API_BASE}/api/geocode/preview?q=${encodeURIComponent(query)}&limit=${limit}`
  );
  if (!res.ok) {
    throw new Error("Failed to fetch geocoding preview");
  }
  return res.json();
}
