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

const PROFILE_LINKS = [
  { label: "GitHub", href: "https://github.com/YashrajKupekar17", icon: "github" },
  { label: "Blog", href: "https://yashrajkupekar17.github.io", icon: "globe" },
  { label: "LinkedIn", href: "https://www.linkedin.com/in/yashraj-kupekar-8b3a58243/", icon: "linkedin" },
];

const PHONE_NUMBER = "+1 (539) 238-4323";

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
  return [...new Set(matches)];
}

function hasCalendarSource(sources?: Source[]): boolean {
  return !!sources?.some((s) => s.tool === "get_available_slots");
}

function hasBookingSource(sources?: Source[]): boolean {
  return !!sources?.some((s) => s.tool === "book_meeting");
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

function GlobeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function PhoneIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

function ExternalLinkIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function SunIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function NewChatIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

const iconMap: Record<string, React.FC<{ className?: string }>> = {
  github: GitHubIcon,
  globe: GlobeIcon,
  linkedin: LinkedInIcon,
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [dark, setDark] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Initialize dark mode from system preference
  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const stored = localStorage.getItem("theme");
    const isDark = stored ? stored === "dark" : prefersDark;
    setDark(isDark);
    document.documentElement.classList.toggle("dark", isDark);
  }, []);

  function toggleDark() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  }

  function resetChat() {
    if (isStreaming) return;
    setMessages([]);
    setInput("");
  }

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

  function handleSubmit(e: React.FormEvent) {
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
    <div className="flex flex-col items-center justify-center min-h-screen bg-background p-2 sm:p-4">
      <Card className="w-full max-w-2xl flex flex-col h-[95vh] sm:h-[85vh] shadow-lg overflow-hidden">
        {/* Header */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b bg-card">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <h1 className="text-lg font-semibold">Yashraj Kupekar</h1>
              <p className="text-xs sm:text-sm text-muted-foreground">
                AI representative — ask about my work, projects, and skills
              </p>
            </div>
            <div className="flex items-center gap-1">
              {PROFILE_LINKS.map((link) => {
                const Icon = iconMap[link.icon];
                return (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={link.label}
                    className="p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Icon className="w-4 h-4" />
                  </a>
                );
              })}
              <div className="w-px h-4 bg-border mx-1" />
              {messages.length > 0 && (
                <button
                  onClick={resetChat}
                  title="New chat"
                  disabled={isStreaming}
                  className="p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground hover:text-foreground disabled:opacity-40"
                >
                  <NewChatIcon className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={toggleDark}
                title={dark ? "Light mode" : "Dark mode"}
                className="p-2 rounded-lg hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
              >
                {dark ? <SunIcon className="w-4 h-4" /> : <MoonIcon className="w-4 h-4" />}
              </button>
            </div>
          </div>
          {/* Quick actions banner */}
          <div className="mt-2.5 flex items-center gap-3 px-3 py-2 rounded-lg bg-muted/50 border border-border">
            <div className="flex items-center gap-2 min-w-0">
              <PhoneIcon className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs text-muted-foreground shrink-0">Voice agent:</span>
              <a
                href={`tel:${PHONE_NUMBER.replace(/[^+\d]/g, "")}`}
                className="text-xs font-medium text-foreground hover:underline"
              >
                {PHONE_NUMBER}
              </a>
            </div>
            <div className="w-px h-3.5 bg-border shrink-0" />
            <a
              href={`${API_URL}/resume`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs font-medium text-foreground hover:underline shrink-0"
            >
              <DownloadIcon className="w-3.5 h-3.5 text-muted-foreground" />
              Resume
            </a>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
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
                        <ReactMarkdown
                          components={{
                            a: ({ href, children }) => (
                              <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-primary underline underline-offset-2 hover:text-primary/80 font-medium"
                              >
                                {children}
                                <ExternalLinkIcon className="w-3 h-3 shrink-0" />
                              </a>
                            ),
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
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
          className="px-4 sm:px-6 py-3 sm:py-4 border-t bg-card flex gap-2"
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
