import { Mistral } from "@mistralai/mistralai";
import { NextResponse } from "next/server";

const MODEL = "mistral-small-latest";

type ChatMessage = { role: "user" | "assistant"; content: string };

function isValidMessages(value: unknown): value is ChatMessage[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(
      (m) =>
        typeof m === "object" &&
        m !== null &&
        (m.role === "user" || m.role === "assistant") &&
        typeof m.content === "string" &&
        m.content.trim().length > 0
    )
  );
}

export async function POST(request: Request) {
  const apiKey = process.env.MISTRAL_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: "MISTRAL_API_KEY is not configured on the server." },
      { status: 500 }
    );
  }

  let messages: unknown;
  try {
    const body = await request.json();
    messages = body?.messages;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  if (!isValidMessages(messages)) {
    return NextResponse.json(
      { error: "messages must be a non-empty array of { role, content }." },
      { status: 400 }
    );
  }

  const client = new Mistral({ apiKey });

  try {
    const response = await client.chat.complete({
      model: MODEL,
      messages,
    });
    const content = response.choices?.[0]?.message?.content;
    const reply = typeof content === "string" ? content.trim() : "";
    if (!reply) {
      return NextResponse.json(
        { error: "Received an empty response from the Mistral API." },
        { status: 502 }
      );
    }
    return NextResponse.json({ reply });
  } catch (error) {
    console.error(
      "Mistral API error:",
      error instanceof Error ? error.message : error
    );
    return NextResponse.json(
      { error: "Failed to get a response from the Mistral API." },
      { status: 502 }
    );
  }
}
