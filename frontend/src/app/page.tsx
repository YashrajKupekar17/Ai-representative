"use client";

import { useState, useRef, useEffect } from "react";
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
        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            // SSE spec: strip optional single space after "data:"
            const raw = line.slice(5);
            const data = raw.startsWith(" ") ? raw.slice(1) : raw;
            if (eventType === "token" && data) {
              fullText += data;
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
                /* ignore parse errors */
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
      <Card className="w-full max-w-2xl flex flex-col h-[85vh] shadow-lg">
        {/* Header */}
        <div className="px-6 py-4 border-b">
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
              <div className="flex flex-wrap gap-2 justify-center">
                {STARTER_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    onClick={() => sendMessage(chip)}
                    className="px-3 py-1.5 text-sm rounded-full border border-border hover:bg-accent transition-colors cursor-pointer"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {msg.content}
                  {msg.content === "" && isStreaming && (
                    <span className="animate-pulse">Thinking...</span>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex gap-1.5 mt-2 flex-wrap">
                      {msg.sources.map((s, j) => (
                        <Badge key={j} variant="secondary" className="text-xs">
                          {toolLabel[s.tool] || s.tool}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="px-6 py-4 border-t flex gap-2">
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
