import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Send, Plus, Square, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ThemeToggle } from "@/components/chat/ThemeToggle";
import { MessageBubble, type ChatMessage } from "@/components/chat/MessageBubble";
import type { ThinkingStep } from "@/components/chat/ThinkingSteps";

export const Route = createFileRoute("/")({
  component: Index,
});

const STEP_TEMPLATES: { label: string; detail: string; ms: number }[] = [
  { label: "Identified Potential Goals (Pasal)", detail: "Mengambil beberapa pasal terkait", ms: 700 },
  { label: "Selected Relevant Goal", detail: "Memilih salah satu pasal terbaik", ms: 900 },
  { label: "Evaluated Elements (Postconditions)", detail: "Menganalisa pasal dengan kriteria yang cocok", ms: 800 },
  { label: "Drafting Answer", detail: "Menyusun dari semua pasal yang diambil", ms: 700 },
];

function Index() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const cancelRef = useRef<{ cancelled: boolean }>({ cancelled: false });
  const scrollRef = useRef<HTMLDivElement>(null);
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const clearTimers = () => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  };

  const wait = (ms: number) =>
    new Promise<void>((resolve, reject) => {
      const t = setTimeout(() => {
        if (cancelRef.current.cancelled) reject(new Error("cancelled"));
        else resolve();
      }, ms);
      timeoutsRef.current.push(t);
    });

  const updateMessage = (id: string, patch: Partial<ChatMessage>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isGenerating) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text };
    const assistantId = crypto.randomUUID();
    const initialSteps: ThinkingStep[] = STEP_TEMPLATES.map((s) => ({
      label: s.label,
      detail: s.detail,
      status: "pending",
    }));
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      steps: initialSteps,
      isThinking: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setIsGenerating(true);
    cancelRef.current = { cancelled: false };

    try {
      // 1. Fire the actual backend request and get the JSON data
      const data = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      }).then(async (res) => {
        if (!res.ok) throw new Error("Failed to get response from server");
        return await res.json();
      });

      // 2. Extract data safely
      const resData = data.response || {};
      const responseText = resData.answer || data.reply || data.message || "No response received.";

      // 3. Format the real thinking steps based on the backend response
      const realSteps: ThinkingStep[] = [
        {
          label: "Identified Potential Goals (Pasal)",
          detail: resData.goal_choices?.length ? resData.goal_choices.join(", ") : "None found",
          status: "done"
        },
        {
          label: "Selected Relevant Goal",
          detail: resData.chosen_goal || "Unknown",
          status: "done"
        },
        {
          label: "Evaluated Elements (Postconditions)",
          detail: resData.used_postconditions?.length ? resData.used_postconditions.join(", ") : "None",
          status: "done"
        }
      ];

      // Mark all done, start streaming
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== assistantId) return m;
          return {
            ...m,
            steps: realSteps,
            isThinking: false,
            isStreaming: true,
          };
        }),
      );

      // 3. Stream the actual backend response text to the UI
      const words = responseText.split(" ");
      let acc = "";
      for (let i = 0; i < words.length; i++) {
        acc += (i === 0 ? "" : " ") + words[i];
        updateMessage(assistantId, { content: acc });
        await wait(20 + Math.random() * 30); // slight typing delay
      }

      updateMessage(assistantId, { isStreaming: false });
    } catch (err) {
      const cancelled = (err as Error).message === "cancelled";
      updateMessage(assistantId, {
        isThinking: false,
        isStreaming: false,
        content: cancelled
          ? "Generation cancelled."
          : "Sorry, something went wrong while generating a response from the server.",
      });
      if (cancelled) {
        toast("Generation stopped", { description: "You cancelled the response." });
      } else {
        toast.error("Generation failed", {
          description: (err as Error).message || "Please check if your backend is running.",
        });
      }
    } finally {
      clearTimers();
      setIsGenerating(false);
      cancelRef.current.cancelled = false;
    }
  };

  const handleCancel = () => {
    cancelRef.current.cancelled = true;
    clearTimers();
  };

  const handleNewChat = () => {
    if (isGenerating) handleCancel();
    setMessages([]);
    setInput("");
    toast("New chat started", { description: "Your conversation has been reset." });
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="relative min-h-screen bg-gradient-app overflow-hidden">
      {/* Decorative blobs */}
      {/* <div className="pointer-events-none absolute -top-24 -left-24 h-96 w-96 rounded-full bg-primary/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -right-24 h-[28rem] w-[28rem] rounded-full bg-primary-glow/20 blur-3xl" /> */}

      <div className="relative mx-auto flex h-screen max-w-3xl flex-col px-3 sm:px-6 py-4 sm:py-6">
        {/* Header */}
        <header className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Button
              onClick={handleNewChat}
              className="glass rounded-full h-10 px-4 text-foreground hover:text-foreground bg-transparent hover:bg-accent/40"
            >
              <Plus className="h-4 w-4 mr-1.5" />
              New chat
            </Button>
          </div>
          <h1 className="absolute left-1/2 -translate-x-1/2 text-base sm:text-lg font-semibold tracking-tight pointer-events-none">
            <span className="text-gradient-primary">ChatKUHP</span>
          </h1>
          <ThemeToggle />
        </header>

        {/* Chat area */}
        <div
          ref={scrollRef}
          className="scrollbar-thin flex-1 overflow-y-auto rounded-3xl px-1 sm:px-2 py-2"
        >
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center px-4">
              <div className="h-14 w-14 rounded-2xl bg-gradient-primary flex items-center justify-center shadow-xl mb-5 animate-pulse-glow">
                <Sparkles className="h-7 w-7 text-primary-foreground" />
              </div>
              <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight mb-2">
                How can I help you <span className="text-gradient-primary">today</span>?
              </h2>
              <p className="text-sm text-muted-foreground max-w-md">
                Ask anything — I'll show you my reasoning before answering.
              </p>
            </div>
          ) : (
            <div className="space-y-5 pb-4">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="mt-3 sm:mt-4">
          <div className="glass rounded-3xl p-2 flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Message Here…"
              rows={1}
              className="scrollbar-thin flex-1 resize-none border-0 bg-transparent text-sm focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none min-h-[44px] max-h-40 py-3 px-3"
            />
            {isGenerating ? (
              <Button
                onClick={handleCancel}
                size="icon"
                className="h-10 w-10 rounded-2xl bg-destructive hover:bg-destructive/90 text-destructive-foreground shrink-0"
                aria-label="Cancel generation"
              >
                <Square className="h-4 w-4 fill-current" />
              </Button>
            ) : (
              <Button
                onClick={handleSend}
                disabled={!input.trim()}
                size="icon"
                className="h-10 w-10 rounded-2xl bg-gradient-primary text-primary-foreground shrink-0 disabled:opacity-40 hover:opacity-90"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground/70 text-center mt-2">
            ChatKUHP can make mistakes. Verify important information.
          </p>
        </div>
      </div>
    </main>
  );
}
