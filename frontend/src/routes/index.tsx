import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Send, Plus, Square, Scale } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ThemeToggle } from "@/components/chat/ThemeToggle";
import { MessageBubble, type ChatMessage } from "@/components/chat/MessageBubble";
import type { ThinkingStep } from "@/components/chat/ThinkingSteps";

export const Route = createFileRoute("/")({ component: Index });

const STEP_TEMPLATES: { label: string; detail: string; ms: number }[] = [
  { label: "Mengidentifikasi Pasal yang Relevan", detail: "Mengambil beberapa pasal terkait dari KUHP", ms: 700 },
  { label: "Memilih Pasal Paling Sesuai", detail: "Menentukan pasal dengan kecocokan tertinggi", ms: 900 },
  { label: "Menganalisis Unsur-Unsur Pasal", detail: "Mengevaluasi unsur tindak pidana yang terpenuhi", ms: 800 },
  { label: "Menyusun Analisis Hukum", detail: "Merumuskan jawaban berdasarkan konteks hukum", ms: 700 },
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
      const data = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      }).then(async (res) => {
        if (!res.ok) throw new Error("Gagal mendapatkan respons dari server");
        return await res.json();
      });

      const resData = data.response || {};
      const responseText = resData.answer || data.reply || data.message || "Tidak ada respons yang diterima.";

      const realSteps: ThinkingStep[] = [
        {
          label: "Mengidentifikasi Pasal yang Relevan",
          detail: resData.goal_choices?.length ? resData.goal_choices.join(", ") : "Tidak ditemukan",
          status: "done"
        },
        {
          label: "Memilih Pasal Paling Sesuai",
          detail: resData.chosen_goal || "Tidak diketahui",
          status: "done"
        },
        {
          label: "Menganalisis Unsur-Unsur Pasal",
          detail: resData.used_postconditions?.length ? resData.used_postconditions.join(", ") : "—",
          status: "done"
        }
      ];

      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== assistantId) return m;
          return { ...m, steps: realSteps, isThinking: false, isStreaming: true };
        }),
      );

      const tokens = responseText.match(/(\s+|\S+)/g) || [];
      let acc = "";
      for (let i = 0; i < tokens.length; i++) {
        acc += tokens[i];
        updateMessage(assistantId, { content: acc });
        await wait(18 + Math.random() * 28);
      }

      updateMessage(assistantId, { isStreaming: false });
    } catch (err) {
      const cancelled = (err as Error).message === "cancelled";
      updateMessage(assistantId, {
        isThinking: false,
        isStreaming: false,
        content: cancelled
          ? "Generasi dibatalkan."
          : "Maaf, terjadi kesalahan saat menghubungi server. Pastikan backend sedang berjalan.",
      });
      if (cancelled) {
        toast("Generasi dihentikan", { description: "Anda telah membatalkan respons." });
      } else {
        toast.error("Gagal mendapatkan respons", {
          description: (err as Error).message || "Periksa apakah backend sedang berjalan.",
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
    toast("Konsultasi baru dimulai", { description: "Riwayat percakapan telah direset." });
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="relative min-h-screen bg-gradient-app overflow-hidden">
      {/* Decorative subtle texture overlay */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.025] dark:opacity-[0.04]"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")" }}
      />

      <div className="relative mx-auto flex h-screen max-w-3xl flex-col px-3 sm:px-6 py-4 sm:py-6">

        {/* Header */}
        <header className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Button
              onClick={handleNewChat}
              className="glass rounded-full h-10 px-4 text-foreground hover:text-foreground bg-transparent hover:bg-accent/40 font-medium"
            >
              <Plus className="h-4 w-4 mr-1.5" />
              Konsultasi Baru
            </Button>
          </div>

          {/* Center branding */}
          <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center pointer-events-none select-none">
            <h1 className="text-base sm:text-lg font-serif font-bold tracking-tight leading-none">
              <span className="text-gradient-primary">ChatKUHP</span>
            </h1>
            <span className="text-[10px] text-muted-foreground tracking-widest uppercase mt-0.5 font-medium">
              Asisten Hukum Pidana
            </span>
          </div>

          <ThemeToggle />
        </header>

        {/* Gold divider */}
        <hr className="gold-divider mb-4" />

        {/* Chat area */}
        <div
          ref={scrollRef}
          className="scrollbar-thin flex-1 overflow-y-auto rounded-2xl px-1 sm:px-2 py-2"
        >
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center px-4 gap-4">
              {/* Scale of Justice icon */}
              <div className="h-16 w-16 rounded-2xl bg-gradient-primary flex items-center justify-center shadow-xl animate-pulse-glow animate-stamp-in">
                <Scale className="h-8 w-8 text-primary-foreground" strokeWidth={1.5} />
              </div>

              <div>
                <h2 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight mb-2">
                  Selamat Datang di{" "}
                  <span className="text-gradient-primary">ChatKUHP</span>
                </h2>
                <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
                  Ajukan pertanyaan hukum Anda. Sistem akan menganalisis kasus berdasarkan{" "}
                  <strong>Kitab Undang-Undang Hukum Pidana (KUHP)</strong> dan memberikan penjelasan yang terstruktur.
                </p>
              </div>

              {/* Example prompts */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 w-full max-w-lg">
                {[
                  "Apa sanksi untuk tindak pidana pencurian?",
                  "Bagaimana hukum penggelapan dalam jabatan?",
                  "Apa unsur-unsur tindak pidana penipuan?",
                  "Apa perbedaan pencurian biasa dan pencurian berat?",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); }}
                    className="glass text-left text-xs text-muted-foreground hover:text-foreground px-3 py-2.5 rounded-xl transition-all hover:bg-accent/30 hover:border-primary/30 border border-transparent"
                  >
                    {q}
                  </button>
                ))}
              </div>
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
          <div className="glass rounded-2xl p-2 flex items-end gap-2">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Tuliskan pertanyaan atau kasus hukum Anda…"
              rows={1}
              className="scrollbar-thin flex-1 resize-none border-0 bg-transparent text-sm focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none min-h-[44px] max-h-40 py-3 px-3"
            />
            {isGenerating ? (
              <Button
                onClick={handleCancel}
                size="icon"
                className="h-10 w-10 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground shrink-0"
                aria-label="Batalkan generasi"
              >
                <Square className="h-4 w-4 fill-current" />
              </Button>
            ) : (
              <Button
                onClick={handleSend}
                disabled={!input.trim()}
                size="icon"
                className="h-10 w-10 rounded-xl bg-gradient-primary text-primary-foreground shrink-0 disabled:opacity-40 hover:opacity-90"
                aria-label="Kirim pertanyaan"
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground/60 text-center mt-2">
            ChatKUHP hanya sebagai referensi. Konsultasikan dengan advokat untuk kepastian hukum.
          </p>
        </div>
      </div>
    </main>
  );
}
