"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STARTER_CHIPS = [
  "Who is Yashraj?",
  "What are his skills?",
  "Tell me about his projects",
  "Can I schedule a call?",
];

type Source = { tool: string; args: string };

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
};

/** Extract HH:MM time slots from a calendar response */
function extractSlots(content: string): string[] {
  const matches = content.match(/\b\d{2}:\d{2}\b/g);
  if (!matches) return [];
  // Deduplicate
  return [...new Set(matches)];
}

function hasCalendarSource(sources?: Source[]): boolean {
  return !!sources?.some((s) => s.tool === "get_available_slots");
}

function hasBookingSource(sources?: Source[]): boolean {
  return !!sources?.some((s) => s.tool === "book_meeting");
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim() || isStreaming) return;

    const userMessage: Message = { role: "user", content: text };
    const history = [...messages, userMessage];
    setMessages(history);
    setInput("");
    setIsStreaming(true);

    setMessages([...history, { role: "assistant", content: "" }]);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history.map(({ role, content }) => ({ role, content })),
        }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = "";
      let sources: Source[] = [];
      let buffer = "";

      if (!reader) throw new Error("No response body");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let eventType = "";
        for (let line of lines) {
          line = line.replace(/\r$/, "");
          if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const raw = line.slice(5);
            const data = raw.startsWith(" ") ? raw.slice(1) : raw;
            if (eventType === "token") {
              // Empty data line = newline in original content (SSE multi-line encoding)
              fullText += data || "\n";
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: fullText,
                };
                return updated;
              });
            } else if (eventType === "sources") {
              try {
                sources = JSON.parse(data);
              } catch {
                /* ignore */
              }
            }
          }
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullText,
          sources,
        };
        return updated;
      });
    } catch {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    sendMessage(input);
  }

  const toolLabel: Record<string, string> = {
    lookup_facts: "Facts",
    search_knowledge: "Knowledge Search",
    get_available_slots: "Calendar",
    book_meeting: "Booking",
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
      <Card className="w-full max-w-2xl flex flex-col h-[85vh] shadow-lg overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b bg-card">
          <h1 className="text-lg font-semibold">Yashraj Kupekar</h1>
          <p className="text-sm text-muted-foreground">
            Chat with my representative about my work, projects, and skills
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-6">
              <div className="text-center">
                <p className="text-lg font-medium">
                  Hey, I represent Yashraj!
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Ask me anything about his work, or pick a topic below.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-md">
                {STARTER_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => sendMessage(chip)}
                    className="px-4 py-2 text-sm rounded-full border border-border hover:bg-accent hover:border-primary/30 transition-all cursor-pointer"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i}>
                <div
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {/* Message content */}
                    {msg.role === "assistant" && msg.content ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:my-1 [&>ul]:my-1 [&>ol]:my-1 [&>li]:my-0.5">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <span>{msg.content}</span>
                    )}

                    {/* Loading state */}
                    {msg.content === "" && isStreaming && (
                      <span className="animate-pulse text-muted-foreground">
                        Thinking...
                      </span>
                    )}

                    {/* Booking confirmation card */}
                    {hasBookingSource(msg.sources) && (
                      <div className="mt-2 p-2 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 text-xs text-green-700 dark:text-green-300">
                        Meeting confirmed
                      </div>
                    )}

                    {/* Source badges */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="flex gap-1.5 mt-2 flex-wrap">
                        {msg.sources.map((s, j) => (
                          <Badge
                            key={j}
                            variant="secondary"
                            className="text-xs"
                          >
                            {toolLabel[s.tool] || s.tool}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Slot picker buttons — shown below calendar messages */}
                {hasCalendarSource(msg.sources) && !isStreaming && (() => {
                  const slots = extractSlots(msg.content);
                  if (slots.length === 0) return null;
                  return (
                    <div className="mt-2 ml-0">
                      <p className="text-xs text-muted-foreground mb-1.5">
                        Pick a slot:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {slots.map((slot) => (
                          <button
                            key={slot}
                            onClick={() =>
                              sendMessage(`I'd like the ${slot} UTC slot`)
                            }
                            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-card hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all cursor-pointer"
                          >
                            {slot} UTC
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="px-6 py-4 border-t bg-card flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about Yashraj..."
            disabled={isStreaming}
            className="flex-1"
          />
          <Button type="submit" disabled={isStreaming || !input.trim()}>
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}
