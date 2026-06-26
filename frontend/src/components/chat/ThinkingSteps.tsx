import { useState } from "react";
import { ChevronDown, BookOpen, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type ThinkingStep = {
  label: string;
  detail?: string;
  status: "pending" | "active" | "done";
};

interface ThinkingStepsProps {
  steps: ThinkingStep[];
  isThinking: boolean;
}

export function ThinkingSteps({ steps, isThinking }: ThinkingStepsProps) {
  const [open, setOpen] = useState(true);
  if (steps.length === 0) return null;

  return (
    <div className="glass rounded-2xl overflow-hidden mb-2 max-w-[85%]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-accent/30 transition-colors"
      >
        {/* Buku hukum icon */}
        <BookOpen className="h-4 w-4 text-primary shrink-0" strokeWidth={1.75} />
        <span className={cn("font-medium", isThinking ? "shimmer-text" : "text-foreground")}>
          {isThinking ? "Menganalisis…" : "Proses Analisis Hukum"}
        </span>
        <span className="text-xs text-muted-foreground ml-auto mr-1">{steps.length} tahap</span>
        <ChevronDown
          className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>
      <div
        className={cn(
          "grid transition-all duration-300 ease-out",
          open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
        )}
      >
        <div className="overflow-hidden">
          <ol className="px-4 pb-3 pt-1 space-y-2 border-t border-border/40">
            {steps.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm animate-bubble-in">
                <div className="mt-0.5 shrink-0">
                  {s.status === "done" ? (
                    <Check className="h-3.5 w-3.5 text-primary" />
                  ) : s.status === "active" ? (
                    <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
                  ) : (
                    <div className="h-3.5 w-3.5 rounded-full border border-muted-foreground/40" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div
                    className={cn(
                      "font-medium",
                      s.status === "done" ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {s.label}
                  </div>
                  {s.detail && (
                    <div className="text-xs text-muted-foreground/80 mt-0.5">{s.detail}</div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}