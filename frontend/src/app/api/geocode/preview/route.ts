import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const q = searchParams.get("q");
    const limit = searchParams.get("limit") || "10";

    if (!q) {
      return NextResponse.json(
        { query: "", results: [], total: 0, message: "Query parameter 'q' is required" },
        { status: 400 }
      );
    }

    const url = `${BACKEND_URL}/api/geocode/preview?q=${encodeURIComponent(q)}&limit=${limit}`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || "Failed to fetch geocoding preview" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Error proxying geocode preview request:", error);
    return NextResponse.json(
      { detail: "Failed to connect to backend" },
      { status: 500 }
    );
  }
}
