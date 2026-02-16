import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const response = await fetch(`${BACKEND_URL}/api/trips/${id}/preview`, {
      method: "GET",
    });

    if (!response.ok) {
      const data = await response.json();
      return NextResponse.json(
        { detail: data.detail || "Failed to fetch preview" },
        { status: response.status }
      );
    }

    // Return HTML response
    const html = await response.text();
    return new NextResponse(html, {
      headers: {
        "Content-Type": "text/html",
      },
    });
  } catch (error) {
    console.error("Error proxying preview request:", error);
    return NextResponse.json(
      { detail: "Failed to connect to backend" },
      { status: 500 }
    );
  }
}
