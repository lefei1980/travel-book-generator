import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const response = await fetch(`${BACKEND_URL}/api/chat/${id}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: data.detail || "Failed to fetch session" },
        { status: response.status }
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error proxying chat GET request:", error);
    return NextResponse.json({ detail: "Failed to connect to backend" }, { status: 500 });
  }
}
