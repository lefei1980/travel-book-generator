"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  sendChatMessage,
  finalizeChat,
  getTrip,
  getDownloadUrl,
  getPreviewUrl,
  generatePDF,
  editTrip,
  getChatSession,
} from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const STATUS_MESSAGES: Record<string, string> = {
  pending: "Preparing your trip...",
  geocoding: "Geocoding locations...",
  routing: "Calculating routes...",
  enriching: "Fetching images and descriptions...",
  rendering: "Generating preview...",
  preview_ready: "Preview ready!",
  generating_pdf: "Generating PDF...",
  complete: "Your travel guide is ready!",
  error: "Something went wrong.",
};

const WELCOME_MESSAGE =
  "Hi! I'm your travel planning assistant. Tell me where you'd like to go and when, and I'll help you build a day-by-day itinerary with hotels, attractions, and restaurants. Where are you dreaming of visiting?";

type ViewMode = "chat" | "status" | "preview";

export default function ChatPlanner() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: WELCOME_MESSAGE },
  ]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [tripId, setTripId] = useState<string | null>(null);
  const [tripStatus, setTripStatus] = useState<string | null>(null);
  const [tripTitle, setTripTitle] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("chat");
  const [generatingPDF, setGeneratingPDF] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previewIframeRef = useRef<HTMLIFrameElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const userMessageCount = messages.filter((m) => m.role === "user").length;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const pollStatus = useCallback(async (id: string) => {
    try {
      const trip = await getTrip(id);
      setTripStatus(trip.status);
      if (trip.status === "error") {
        setError(trip.error_message || "Pipeline failed");
        setIsFinalizing(false);
      } else if (trip.status === "preview_ready") {
        setIsFinalizing(false);
        setViewMode("preview");
      } else if (trip.status === "complete") {
        setIsFinalizing(false);
        setViewMode("status");
      } else {
        setTimeout(() => pollStatus(id), 2000);
      }
    } catch {
      setError("Failed to check trip status");
      setIsFinalizing(false);
    }
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    setError(null);
    const newMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const res = await sendChatMessage({ session_id: sessionId, message: text });
      setSessionId(res.session_id);
      setMessages([...newMessages, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleFinalize = async () => {
    if (!sessionId || isFinalizing) return;
    setIsFinalizing(true);
    setError(null);
    setViewMode("status");

    try {
      const res = await finalizeChat(sessionId);
      setTripId(res.trip_id);
      setTripTitle(res.title);
      setTripStatus(res.status);
      pollStatus(res.trip_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to finalize itinerary");
      setIsFinalizing(false);
      setViewMode("chat");
    }
  };

  const handleSaveAsPDF = async () => {
    if (!tripId || generatingPDF) return;
    // Try printing the iframe first (preserves map state)
    if (previewIframeRef.current?.contentWindow) {
      previewIframeRef.current.contentWindow.print();
      return;
    }
    // Fallback: call generate-pdf endpoint
    setGeneratingPDF(true);
    setError(null);
    try {
      await generatePDF(tripId);
      setTripStatus("complete");
      setViewMode("status");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate PDF");
    } finally {
      setGeneratingPDF(false);
    }
  };

  const handleReset = () => {
    setMessages([{ role: "assistant", content: WELCOME_MESSAGE }]);
    setSessionId(null);
    setInput("");
    setIsLoading(false);
    setIsFinalizing(false);
    setTripId(null);
    setTripStatus(null);
    setTripTitle("");
    setError(null);
    setViewMode("chat");
    setGeneratingPDF(false);
  };

  const handleEditTrip = async () => {
    if (!tripId) return;
    setIsLoading(true);
    setError(null);

    try {
      // Get the session_id for this trip
      const editResponse = await editTrip(tripId);
      const sessionResponse = await getChatSession(editResponse.session_id);

      // Load the conversation history
      setSessionId(editResponse.session_id);
      setMessages(sessionResponse.messages as Message[]);

      // Switch back to chat view
      setViewMode("chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to edit trip");
    } finally {
      setIsLoading(false);
    }
  };

  // --- Preview view ---
  if (viewMode === "preview" && tripId && tripStatus === "preview_ready") {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-6xl mx-auto p-6">
          <div className="bg-white rounded-lg shadow mb-4 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-800">{tripTitle}</h2>
                <p className="text-sm text-gray-600">
                  Preview your travel guide before saving as PDF
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleReset}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
                >
                  Plan another trip
                </button>
                <button
                  onClick={handleEditTrip}
                  disabled={isLoading}
                  className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 font-medium disabled:opacity-50"
                >
                  {isLoading ? "Loading..." : "Edit Trip"}
                </button>
                <button
                  onClick={handleSaveAsPDF}
                  disabled={generatingPDF}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium disabled:opacity-50"
                >
                  {generatingPDF ? "Generating..." : "Save as PDF"}
                </button>
              </div>
            </div>
            {error && (
              <div className="mt-3 bg-red-50 text-red-700 p-3 rounded">{error}</div>
            )}
          </div>
          <div
            className="bg-white rounded-lg shadow overflow-hidden"
            style={{ height: "calc(100vh - 200px)" }}
          >
            <iframe
              ref={previewIframeRef}
              src={getPreviewUrl(tripId)}
              className="w-full h-full border-0"
              title="Trip Preview"
            />
          </div>
        </div>
      </div>
    );
  }

  // --- Status/processing view ---
  if (viewMode === "status" && tripId && tripStatus) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">{tripTitle}</h2>
          <div className="mb-6">
            <p className="text-lg text-gray-600">
              {STATUS_MESSAGES[tripStatus] || tripStatus}
            </p>
            {!["complete", "error", "preview_ready"].includes(tripStatus) && (
              <div className="mt-4">
                <div className="animate-spin inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full" />
              </div>
            )}
          </div>
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded mb-4">{error}</div>
          )}
          {tripStatus === "complete" && (
            <a
              href={getDownloadUrl(tripId)}
              className="inline-block bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 font-medium"
            >
              Download PDF
            </a>
          )}
          <button
            onClick={handleReset}
            className="block mx-auto mt-4 text-blue-600 hover:text-blue-800 text-sm"
          >
            Plan another trip
          </button>
        </div>
      </div>
    );
  }

  // --- Chat view ---
  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* Message list */}
      <div className="bg-white rounded-lg shadow flex flex-col" style={{ height: "460px" }}>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-800 rounded-bl-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex gap-1 items-center">
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 p-3">
          {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Type a message..."
              disabled={isLoading}
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Actions below chat */}
      {userMessageCount >= 1 && !isLoading && (
        <div className="mt-3 flex justify-between items-center">
          <button
            onClick={handleReset}
            className="text-sm text-gray-400 hover:text-gray-600"
          >
            Start over
          </button>
          <button
            onClick={handleFinalize}
            disabled={isFinalizing || !sessionId}
            className="bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
          >
            {isFinalizing ? "Generating..." : "Finalize Itinerary →"}
          </button>
        </div>
      )}

      <p className="mt-3 text-xs text-gray-400 text-center">
        When your plan is ready, click <strong>Finalize Itinerary</strong> to generate your travel guide.
      </p>
    </div>
  );
}
