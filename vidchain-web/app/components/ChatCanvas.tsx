"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, Crosshair, Copy, BrainCircuit } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "./utils";

interface Message {
  id: string;
  sender: "user" | "iris" | "system";
  text: string;
  timestamp: string;
  confidence?: number;
  telemetry?: { cpu_score?: number; gpu_score?: number };
}

interface ChatCanvasProps {
  messages: Message[];
  isQuerying: boolean;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  jumpToContext: (ts: string) => void;
  copyMessage: (text: string) => void;
}

export function ChatCanvas({ messages, isQuerying, scrollRef, jumpToContext, copyMessage }: ChatCanvasProps) {

  const renderWithLinks = (text: string) =>
    text.split(/(\[[\d.]+s\])/g).map((part, i) =>
      part.match(/\[[\d.]+s\]/) ? (
        <button key={i} type="button" onClick={() => jumpToContext(part)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold border border-sp-red/30 bg-sp-red/10 text-sp-red hover:bg-sp-red/20 transition-all mx-0.5">
          <Crosshair className="w-2 h-2" />{part}
        </button>
      ) : part
    );

  const ConfidenceMeter = ({ value }: { value: number }) => {
    const pct = Math.round(value);
    const color = pct > 80 ? "#22c55e" : pct > 50 ? "#F5C518" : "#E8192C";
    return (
      <div className="mt-3 pt-3 border-t border-white/5">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-[7px] font-bold uppercase tracking-widest text-white/30">Confidence</span>
          <span className="text-[8px] font-mono" style={{ color }}>{pct}%</span>
        </div>
        <div className="h-0.5 bg-white/5 rounded-full overflow-hidden">
          <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }}
            className="h-full rounded-full" style={{ backgroundColor: color }} />
        </div>
      </div>
    );
  };

  const Markdown = ({ content }: { content: string }) => (
    <div className="prose prose-invert prose-sm max-w-none w-full break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
        p: ({ children }) => (
          <p className="mb-2 last:mb-0 text-[11px] leading-relaxed text-white/80">
            {React.Children.map(children, c => typeof c === "string" ? renderWithLinks(c) : c)}
          </p>
        ),
        h1: ({ children }) => <h1 className="text-[11px] font-black uppercase tracking-[0.15em] text-sp-red mt-3 mb-1.5 first:mt-0">{children}</h1>,
        h2: ({ children }) => <h2 className="text-[10px] font-bold uppercase tracking-wider text-white mt-3 mb-1 first:mt-0">{children}</h2>,
        ul: ({ children }) => <ul className="space-y-1 mb-2 list-none">{children}</ul>,
        li: ({ children }) => (
          <li className="flex gap-2 text-[11px] text-white/70">
            <span className="text-sp-red shrink-0">›</span>
            <span>{React.Children.map(children, c => typeof c === "string" ? renderWithLinks(c) : c)}</span>
          </li>
        ),
        code: ({ children }) => (
          <code className="text-[9px] bg-white/5 px-1.5 py-0.5 rounded text-yellow-400 font-mono border border-white/5">{children}</code>
        ),
      }}>{content}</ReactMarkdown>
    </div>
  );

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-5 scroll-smooth" style={{ scrollbarWidth: "none" }}>
      <AnimatePresence initial={false}>
        {messages.map(msg => (
          <motion.div key={msg.id}
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className={cn("flex gap-3 max-w-2xl mx-auto", msg.sender === "user" ? "flex-row-reverse" : "flex-row")}>

            {/* Avatar */}
            <div className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center shrink-0 border",
              msg.sender === "iris" ? "bg-sp-red/10 border-sp-red/30 text-sp-red" :
              msg.sender === "system" ? "bg-sp-blue/10 border-sp-blue/30 text-sp-blue-light" :
              "bg-white/5 border-sp-border text-white/60"
            )}>
              {msg.sender === "iris" ? <Bot className="w-3.5 h-3.5" /> :
               msg.sender === "system" ? <BrainCircuit className="w-3.5 h-3.5" /> :
               <User className="w-3.5 h-3.5" />}
            </div>

            {/* Bubble */}
            <div className={cn("flex-1 min-w-0 group relative", msg.sender === "user" ? "items-end" : "items-start")}>
              <div className={cn(
                "px-4 py-3 rounded-2xl border text-sm",
                msg.sender === "user"
                  ? "bg-sp-red text-white border-transparent rounded-tr-sm"
                  : msg.sender === "system"
                  ? "bg-sp-blue/10 border-sp-blue/20 text-sp-blue-light italic rounded-tl-sm text-[11px]"
                  : "bg-sp-web border-sp-border rounded-tl-sm"
              )}>
                {msg.sender === "user"
                  ? <p className="text-[11px] font-medium leading-relaxed">{msg.text}</p>
                  : <>
                      <Markdown content={msg.text} />
                      {msg.sender === "iris" && msg.confidence !== undefined && <ConfidenceMeter value={msg.confidence} />}
                    </>
                }
              </div>
              <div className="flex items-center gap-2 mt-1 px-1">
                <span className="text-[7px] text-white/20 font-mono">{msg.timestamp}</span>
              </div>

              {/* Copy button */}
              <button onClick={() => copyMessage(msg.text)}
                className={cn(
                  "absolute top-2 opacity-0 group-hover:opacity-100 transition-all p-1 rounded text-white/30 hover:text-white hover:bg-white/5",
                  msg.sender === "user" ? "left-0 -translate-x-full -ml-1" : "right-0 translate-x-full ml-1"
                )}>
                <Copy className="w-3 h-3" />
              </button>
            </div>
          </motion.div>
        ))}

        {isQuerying && (
          <motion.div key="typing" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="flex gap-3 max-w-2xl mx-auto">
            <div className="w-7 h-7 rounded-full bg-sp-red/10 border border-sp-red/30 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 text-sp-red animate-pulse" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-sp-web border border-sp-border flex items-center gap-1.5">
              {[0, 0.15, 0.3].map((delay, i) => (
                <motion.div key={i} animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
                  transition={{ duration: 0.8, repeat: Infinity, delay }}
                  className="w-1 h-1 rounded-full bg-sp-red" />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}