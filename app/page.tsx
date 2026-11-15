"use client";

import { useEffect, useRef, useState } from "react";

type Message = { role: "user" | "assistant"; content: string };

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || isLoading) return;

    const nextMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.error ?? "Something went wrong.");
      }
      setMessages([...nextMessages, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="mx-auto flex h-screen max-w-2xl flex-col p-4">
      <header className="border-b border-neutral-800 pb-4">
        <h1 className="text-lg font-semibold">Chainpiece Chat</h1>
        <p className="text-sm text-neutral-400">
          Powered by mistral-small-latest via the Mistral TypeScript SDK
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto py-4">
        {messages.length === 0 && !isLoading && (
          <p className="pt-8 text-center text-sm text-neutral-500">
            Ask anything to start the conversation.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2"
                : "mr-auto max-w-[85%] rounded-2xl rounded-bl-sm bg-neutral-800 px-4 py-2"
            }
          >
            <p className="whitespace-pre-wrap text-sm">{m.content}</p>
          </div>
        ))}
        {isLoading && (
          <div className="mr-auto max-w-[85%] rounded-2xl rounded-bl-sm bg-neutral-800 px-4 py-2">
            <p className="animate-pulse text-sm text-neutral-400">Thinking…</p>
          </div>
        )}
        {error && (
          <p className="rounded-lg bg-red-950 px-4 py-2 text-sm text-red-300">
            {error}
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="flex gap-2 border-t border-neutral-800 pt-4"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage();
        }}
      >
        <input
          className="flex-1 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-blue-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={isLoading}
          autoFocus
        />
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium disabled:opacity-50"
          disabled={isLoading || input.trim().length === 0}
        >
          Send
        </button>
      </form>
    </main>
  );
}
