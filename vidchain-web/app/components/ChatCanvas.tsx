"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Crosshair, Copy, Shield, FileText, CheckCircle2 } from "lucide-react";
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
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#18181b] border border-[#27272a] text-accent hover:border-accent/50 transition-all mx-0.5">
          <Crosshair className="w-3 h-3" />{part}
        </button>
      ) : part
    );

  const Markdown = ({ content }: { content: string }) => (
    <div className="prose prose-invert prose-sm max-w-none w-full break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
        p: ({ children }) => (
          <p className="mb-4 last:mb-0 text-[13px] leading-relaxed text-zinc-300 font-medium">
            {React.Children.map(children, c => typeof c === "string" ? renderWithLinks(c) : c)}
          </p>
        ),
        h1: ({ children }) => <h1 className="text-[15px] font-bold text-white mt-6 mb-3 first:mt-0 border-b border-[#1a1a1a] pb-2 uppercase tracking-wider">{children}</h1>,
        h2: ({ children }) => <h2 className="text-[13px] font-bold text-white mt-5 mb-2 first:mt-0 uppercase tracking-tight">{children}</h2>,
        ul: ({ children }) => <ul className="space-y-2 mb-4 list-disc pl-5 text-zinc-500">{children}</ul>,
        li: ({ children }) => (
          <li className="text-[13px] text-zinc-200 leading-relaxed">
            {React.Children.map(children, c => typeof c === "string" ? renderWithLinks(c) : c)}
          </li>
        ),
        code: ({ children }) => (
          <code className="text-[11px] bg-[#18181b] px-1.5 py-0.5 rounded text-zinc-200 font-mono border border-[#27272a]">{children}</code>
        ),
      }}>{content}</ReactMarkdown>
    </div>
  );

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-6 scroll-smooth custom-scrollbar">
      <AnimatePresence initial={false}>
        {messages.length === 0 && !isQuerying && (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
             <Shield className="w-10 h-10 mb-4 text-muted-foreground" />
             <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-muted-foreground">Ready to explore some memories with you</p>
          </div>
        )}
        
        {messages.map(msg => (
          <motion.div key={msg.id}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className={cn("flex gap-4", msg.sender === "user" ? "flex-row-reverse" : "flex-row")}>

            <div className={cn(
              "w-8 h-8 rounded flex items-center justify-center shrink-0 border transition-all duration-300",
              msg.sender === "iris" ? "bg-white border-white text-black shadow-[0_0_15px_rgba(255,255,255,0.2)]" :
              msg.sender === "system" ? "bg-zinc-900 border-zinc-800 text-zinc-500" :
              "bg-zinc-900 border-zinc-800 text-zinc-400"
            )}>
              {msg.sender === "iris" ? <Shield className="w-4 h-4" /> :
               msg.sender === "system" ? <CheckCircle2 className="w-4 h-4" /> :
               <User className="w-4 h-4" />}
            </div>

            <div className={cn("flex-1 min-w-0 group relative", msg.sender === "user" ? "text-right" : "text-left")}>
              <div className={cn(
                "px-4 py-3 rounded transition-all duration-200 border",
                msg.sender === "user"
                  ? "bg-[#111] border-[#222] text-white shadow-lg"
                  : msg.sender === "system"
                  ? "bg-transparent border-dashed border-[#1a1a1a] text-muted-foreground text-[11px]"
                  : "bg-[#080808] border-[#1a1a1a] shadow-xl"
              )}>
                {msg.sender === "user"
                  ? <p className="text-[13px] font-medium leading-relaxed text-left">{msg.text}</p>
                  : <Markdown content={msg.text} />
                }
                
                {msg.sender === "iris" && msg.confidence !== undefined && (
                   <div className="mt-4 pt-3 border-t border-[#1a1a1a] flex items-center justify-between">
                      <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground opacity-50">Clarity Index</span>
                      <span className="text-[10px] font-mono font-bold text-white">{Math.round(msg.confidence)}%</span>
                   </div>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1 px-1">
                <span className="text-[8px] text-zinc-700 font-mono">{msg.timestamp}</span>
              </div>

              <button onClick={() => copyMessage(msg.text)}
                className="absolute top-0 opacity-0 group-hover:opacity-100 transition-all p-2 text-zinc-600 hover:text-zinc-300"
                style={msg.sender === "user" ? { left: -40 } : { right: -40 }}>
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>
          </motion.div>
        ))}

        {isQuerying && (
          <motion.div key="typing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
            <div className="w-8 h-8 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-accent animate-pulse" />
            </div>
            <div className="px-4 py-3 rounded-xl bg-[#18181b] border border-[#27272a] flex items-center gap-1.5">
              {[0, 0.1, 0.2].map(d => (
                <motion.div key={d} animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1, repeat: Infinity, delay: d }}
                  className="w-1.5 h-1.5 rounded-full bg-accent" />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}