import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Bot, Sparkles, AlertCircle } from "lucide-react";
import { copilotApi, type CopilotResponse } from "@/api/endpoints";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const SUGGESTIONS = [
  "Summarize the current operational situation.",
  "Which deliveries are most likely to be late?",
  "Which deliveries should be prioritized?",
  "What is causing today's largest operational risk?",
];

type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; meta: CopilotResponse };

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (q: string) => copilotApi.query(q),
    onSuccess: (res, question) => {
      setMessages((m) => [
        ...m,
        { role: "user", content: question },
        { role: "assistant", content: res.answer, meta: res },
      ]);
    },
    onError: (e, question) => {
      setMessages((m) => [
        ...m,
        { role: "user", content: question },
        { role: "assistant", content: `Failed to answer: ${e instanceof Error ? e.message : "unknown error"}`, meta: { question, answer: "", source: "fallback", tool_used: "error", facts: {} } },
      ]);
    },
  });

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mutation.isPending]);

  const send = (question: string) => {
    const q = question.trim();
    if (!q) return;
    setInput("");
    mutation.mutate(q);
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-11rem)] max-w-4xl flex-col">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Copilot</h1>
        <p className="text-sm text-muted-foreground">
          Bounded operations assistant · uses backend tools, never invents operational facts
        </p>
      </div>

      <div className="mt-4 flex-1 space-y-4 overflow-y-auto rounded-lg border bg-white p-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="h-4 w-4" /> Try one of these:
            </div>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-md border bg-slate-50 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}

        {mutation.isPending && (
          <div className="flex items-start gap-2 text-sm text-muted-foreground">
            <Bot className="mt-0.5 h-4 w-4" />
            <div>Thinking…</div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(input); }}
        className="mt-3 flex gap-2"
      >
        <Input
          placeholder="Ask about deliveries, risk, priorities…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={mutation.isPending}
        />
        <Button type="submit" disabled={mutation.isPending || !input.trim()}>
          <Send className="h-4 w-4" /> Send
        </Button>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  const { meta } = message;
  const isFallback = meta.source === "fallback";
  return (
    <div className="flex items-start gap-2">
      <Bot className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
      <div className="max-w-[85%] space-y-1.5">
        <div className="rounded-lg border bg-white px-3 py-2 text-sm whitespace-pre-wrap">
          {message.content}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Badge variant={isFallback ? "muted" : "info"}>
            {isFallback ? "deterministic fallback" : "llm"}
          </Badge>
          <span>tool: {meta.tool_used}</span>
          {isFallback && (
            <span className="inline-flex items-center gap-1">
              <AlertCircle className="h-3 w-3" /> AI rephrasing disabled
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
