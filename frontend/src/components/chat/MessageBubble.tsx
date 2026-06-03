import { cn } from "@/lib/utils";
import { Sparkles, User, ChevronDown } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ThinkingSteps, type ThinkingStep } from "./ThinkingSteps";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  steps?: ThinkingStep[];
  isThinking?: boolean;
  isStreaming?: boolean;
};

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "flex w-full gap-3 animate-bubble-in",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser && (
        <div className="shrink-0 h-8 w-8 rounded-full bg-gradient-primary flex items-center justify-center shadow-md">
          <Sparkles className="h-4 w-4 text-primary-foreground" />
        </div>
      )}
      <div className={cn("flex flex-col max-w-[85%] sm:max-w-[75%]", isUser && "items-end")}>
        {!isUser && message.steps && message.steps.length > 0 && (
          <ThinkingSteps steps={message.steps} isThinking={!!message.isThinking} />
        )}
        {(message.content || message.isStreaming) && (
          <div
            className={cn(
              "px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words",
              isUser
                ? "bg-gradient-primary text-primary-foreground rounded-br-md shadow-lg"
                : "glass text-foreground rounded-bl-md",
            )}
          >
            {message.content}
            {message.isStreaming && (
              <span className="inline-block ml-0.5 w-1.5 h-4 align-middle bg-current opacity-70 animate-pulse rounded-sm" />
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="shrink-0 h-8 w-8 rounded-full glass flex items-center justify-center">
          <User className="h-4 w-4 text-foreground" />
        </div>
      )}
    </div>
  );
}

export function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1">
      <span className="h-1.5 w-1.5 rounded-full bg-primary typing-dot" />
      <span
        className="h-1.5 w-1.5 rounded-full bg-primary typing-dot"
        style={{ animationDelay: "0.15s" }}
      />
      <span
        className="h-1.5 w-1.5 rounded-full bg-primary typing-dot"
        style={{ animationDelay: "0.3s" }}
      />
    </div>
  );
}