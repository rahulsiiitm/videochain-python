"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { 
  Bot, User, Crosshair, Copy, Download, BrainCircuit 
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "./utils";

interface Message {
  id: string;
  sender: "user" | "baburao" | "system";
  text: string;
  timestamp: string;
  confidence?: number;
  telemetry?: {
    cpu_score?: number;
    gpu_score?: number;
  };
}

interface ChatCanvasProps {
  messages: Message[];
  isQuerying: boolean;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  jumpToEvidence: (ts: string) => void;
  copyMessage: (text: string) => void;
}

export function ChatCanvas({
  messages,
  isQuerying,
  scrollRef,
  jumpToEvidence,
  copyMessage
}: ChatCanvasProps) {

  const renderMessageTextWithLinks = (text: string) => {
    const parts = text.split(/(\[[\d.]+s\])/g);
    return parts.map((part, i) => {
      if (part.match(/\[[\d.]+s\]/)) {
        return (
          <button 
            key={i} 
            type="button" 
            onClick={() => jumpToEvidence(part)}
            className="px-1.5 py-0.5 rounded bg-spider-red/15 text-spider-red font-black border border-spider-red/25 hover:bg-spider-red/30 transition-all cursor-pointer inline-flex items-center gap-1 mx-0.5 text-[10px]"
          >
            <Crosshair className="w-2.5 h-2.5" />{part}
          </button>
        );
      }
      return part;
    });
  };

  const ConfidenceMeter = ({ value, telemetry }: { value: number, telemetry?: any }) => {
    const pct = Math.round(value);
    const color = pct > 80 ? "#4ade80" : pct > 50 ? "#facc15" : "#f87171";
    return (
      <div className="mt-3 pt-3 border-t border-white/5 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[7px] font-black text-gray-600 uppercase tracking-widest">Inference Confidence</span>
          <span className="text-[8px] font-mono" style={{ color }}>{pct}%</span>
        </div>
        <div className="h-1 bg-white/5 rounded-full overflow-hidden">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            className="h-full rounded-full"
            style={{ backgroundColor: color, boxShadow: `0 0 5px ${color}44` }}
          />
        </div>
      </div>
    );
  };

  const ForensicMarkdown = ({ content }: { content: string }) => (
    <div className="w-full break-words prose prose-invert prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="mb-2 last:mb-0 leading-relaxed text-[11px] text-gray-300">
              {React.Children.map(children, (child) => 
                typeof child === "string" ? renderMessageTextWithLinks(child) : child
              )}
            </p>
          ),
          h1: ({ children }) => (
            <h1 className="text-xs font-black uppercase tracking-[0.2em] text-spider-red mt-4 mb-2 border-b border-spider-red/10 pb-1 first:mt-0 italic">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-[10px] font-black uppercase tracking-wider text-white mt-4 mb-2 flex items-center gap-2 first:mt-0">
              <span className="w-1 h-1 bg-spider-red rounded-full" /> {children}
            </h2>
          ),
          ul: ({ children }) => <ul className="space-y-1 mb-3 list-none">{children}</ul>,
          li: ({ children }) => (
            <li className="flex gap-2 text-[11px] text-gray-400">
              <span className="text-spider-red font-black">•</span>
              <div>{React.Children.map(children, (child) => typeof child === "string" ? renderMessageTextWithLinks(child) : child)}</div>
            </li>
          ),
          code: ({ children }) => (
            <code className="text-[9px] bg-white/5 px-1.5 py-0.5 rounded border border-white/10 text-stark-gold font-mono">
              {children}
            </code>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );

  return (
    <div 
      ref={scrollRef}
      className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth"
      style={{ scrollbarWidth: "none" }}
    >
      <AnimatePresence initial={false}>
        {messages.map((msg, idx) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className={cn(
              "flex gap-4 max-w-3xl mx-auto",
              msg.sender === "user" ? "flex-row-reverse" : "flex-row"
            )}
          >
            {/* Avatar */}
            <div className={cn(
              "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border shadow-lg",
              msg.sender === "baburao" ? "bg-spider-red/10 border-spider-red/30 text-spider-red" :
              msg.sender === "system" ? "bg-stark-navy border-stark-border text-stark-gold" :
              "bg-stark-card border-stark-border text-white"
            )}>
              {msg.sender === "baburao" ? <Bot className="w-4 h-4" /> : 
               msg.sender === "system" ? <BrainCircuit className="w-4 h-4" /> :
               <User className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div className={cn(
              "flex-1 min-w-0 group relative",
              msg.sender === "user" ? "text-right" : "text-left"
            )}>
              <div className="flex items-center gap-2 mb-1.5 px-1 justify-between">
                <span className="text-[8px] font-black uppercase tracking-widest text-gray-500">
                  {msg.sender === "baburao" ? "B.A.B.U.R.A.O. Intel" : msg.sender === "user" ? "Operator" : "Neural Link"}
                </span>
                <span className="text-[7px] font-mono text-gray-600 italic opacity-0 group-hover:opacity-100 transition-opacity">
                  {msg.timestamp}
                </span>
              </div>

              <div className={cn(
                "p-4 rounded-2xl border transition-all duration-300",
                msg.sender === "baburao" ? "bg-stark-card/50 backdrop-blur-md border-stark-border hover:border-spider-red/30" :
                msg.sender === "user" ? "bg-spider-red text-white border-transparent" :
                "bg-stark-navy/50 border-stark-border italic text-stark-gold"
              )}>
                {msg.sender === "user" ? (
                  <p className="text-[11px] font-medium leading-relaxed">{msg.text}</p>
                ) : (
                  <>
                    <ForensicMarkdown content={msg.text} />
                    {msg.sender === "baburao" && msg.confidence !== undefined && (
                      <ConfidenceMeter value={msg.confidence} telemetry={msg.telemetry} />
                    )}
                  </>
                )}
              </div>

              {/* Message Actions */}
              <div className={cn(
                "absolute top-0 opacity-0 group-hover:opacity-100 transition-all flex items-center gap-1",
                msg.sender === "user" ? "right-full mr-2" : "left-full ml-2"
              )}>
                <button 
                  onClick={() => copyMessage(msg.text)}
                  className="p-1.5 rounded-md hover:bg-white/5 text-gray-700 hover:text-white transition-all border border-transparent hover:border-white/10"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>
          </motion.div>
        ))}

        {isQuerying && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-4 max-w-3xl mx-auto"
          >
            <div className="w-8 h-8 rounded-lg bg-spider-red/10 border border-spider-red/30 flex items-center justify-center shrink-0">
               <Bot className="w-4 h-4 text-spider-red animate-pulse" />
            </div>
            <div className="flex-1 space-y-2 py-2">
              <div className="h-2 w-24 bg-white/5 rounded-full animate-pulse" />
              <div className="h-2 w-48 bg-white/5 rounded-full animate-pulse opacity-50" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
