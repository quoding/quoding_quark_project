import { useRef, useState } from "react";
import { useQuarkChat } from "@/hooks/useQuarkChat";

export default function Chat() {
  const { messages, streaming, error, send, stop } = useQuarkChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    await send(text);
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="flex flex-col h-screen p-4 gap-4">
      <h1 className="text-xl font-semibold shrink-0">QUARK Chat</h1>

      <div className="flex-1 overflow-y-auto flex flex-col gap-3 min-h-0">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-2xl rounded-lg p-3 text-sm ${
              msg.role === "user"
                ? "self-end bg-primary text-primary-foreground"
                : "self-start bg-card border border-border"
            }`}
          >
            {msg.content || (streaming && msg.role === "assistant" ? "▌" : "")}
          </div>
        ))}
        {error && (
          <p className="text-destructive text-xs self-start">{error}</p>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 shrink-0">
        <input
          className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm outline-none focus:border-primary"
          placeholder="QUARK에게 말하기..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          disabled={streaming}
        />
        {streaming ? (
          <button
            className="px-4 py-2 rounded-lg bg-destructive text-sm font-medium"
            onClick={stop}
          >
            중지
          </button>
        ) : (
          <button
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
            onClick={handleSend}
            disabled={!input.trim()}
          >
            전송
          </button>
        )}
      </div>
    </div>
  );
}
