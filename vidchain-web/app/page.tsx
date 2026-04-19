"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Shield,
  Search,
  Terminal,
  Zap,
  Send,
  Cpu,
  Activity,
  FileScan,
  Database,
  BrainCircuit,
  Loader2,
  CircleDot,
  Trash2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = "http://localhost:8000";

type Message = {
  id: string;
  sender: "user" | "baburao" | "system";
  text: string;
  timestamp: string;
};

type Log = {
  id: string;
  text: string;
  type: "info" | "success" | "error" | "warn";
  timestamp: string;
};

export default function SpideyChainDashboard() {
  const [mounted, setMounted] = useState(false);
  const [videoPath, setVideoPath] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [serverOnline, setServerOnline] = useState(false);
  const [indexedVideos, setIndexedVideos] = useState<string[]>([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [query, setQuery] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setMounted(true);
    addLog("Neural handshake initiated.", "info");
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/api/history`);
      if (res.ok) {
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
          addLog(`Restored ${data.messages.length} messages from local storage.`, "success");
        } else {
          // Fresh session — show welcome message
          const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          setMessages([{
            id: "initial",
            sender: "baburao",
            text: "Neural Link established. Stark-Tech Multimodal Engine online.\n\nDirective: Cross-Modal Forensic Intelligence. Load a video feed to begin.",
            timestamp: time,
          }]);
        }
      }
    } catch {
      // Server offline — still show welcome
      const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMessages([{
        id: "initial",
        sender: "baburao",
        text: "Neural Link established. Stark-Tech Multimodal Engine online.\n\nDirective: Cross-Modal Forensic Intelligence. Load a video feed to begin.",
        timestamp: time,
      }]);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const clearHistory = async () => {
    try {
      await fetch(`${API_BASE}/api/history`, { method: "DELETE" });
      const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMessages([{
        id: "cleared",
        sender: "system",
        text: "Chat history cleared. Knowledge graph and vector index remain intact.",
        timestamp: time,
      }]);
      addLog("Chat history cleared.", "warn");
    } catch {
      addLog("Failed to clear history.", "error");
    }
  };

  useEffect(() => {
    if (!mounted) return;
    checkHealth();
    const interval = setInterval(checkHealth, 4000);
    return () => clearInterval(interval);
  }, [mounted]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isQuerying]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setServerOnline(true);
        setIndexedVideos(data.indexed_videos || []);
      } else {
        setServerOnline(false);
      }
    } catch {
      setServerOnline(false);
    }
  };

  const addLog = (text: string, type: Log["type"] = "info") => {
    setLogs((prev) => [
      ...prev,
      {
        id: Math.random().toString(36),
        text,
        type,
        timestamp: new Date().toLocaleTimeString([], { hour12: false }),
      },
    ]);
  };

  const handleIngest = async () => {
    if (!videoPath.trim() || isIngesting) return;
    setIsIngesting(true);
    const filename = videoPath.split(/[/\\]/).pop() ?? videoPath;
    addLog(`Scan initiated: ${filename}`, "info");

    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(36),
        sender: "system",
        text: `Neural scan started for "${filename}". GraphRAG mapping is active. Query B.A.B.U.R.A.O. after ingestion completes.`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_source: videoPath }),
      });
      const data = await res.json();
      if (res.ok) {
        addLog("Multimodal pipeline dispatched to background.", "success");
        setVideoPath("");
      } else {
        addLog(data.detail || "Scan terminated.", "error");
      }
    } catch {
      addLog("Telemetry lost. Is the backend server running?", "error");
    } finally {
      setIsIngesting(false);
    }
  };

  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isQuerying) return;

    const userMsg = query;
    setQuery("");
    setIsQuerying(true);

    setMessages((prev) => [
      ...prev,
      {
        id: Math.random().toString(36),
        sender: "user",
        text: userMsg,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);

    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: Math.random().toString(36),
          sender: "baburao",
          text: data.response || "No forensic data found.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch {
      addLog("Neural query failed. Check server connection.", "error");
    } finally {
      setIsQuerying(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  if (!mounted) return <div className="bg-background h-screen" />;

  return (
    <div className="flex h-screen bg-background font-sans overflow-hidden">
      {/* Grid Background */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(to right, #1A1F2B 1px, transparent 1px), linear-gradient(to bottom, #1A1F2B 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          opacity: 0.3,
        }}
      />
      <div className="fixed inset-0 pointer-events-none bg-gradient-to-br from-spider-red/5 via-transparent to-transparent" />

      {/* ───────────────────────── SIDEBAR ───────────────────────── */}
      <aside className="relative z-10 w-72 flex flex-col border-r border-stark-border bg-stark-navy/20 backdrop-blur-2xl shrink-0">
        {/* Brand */}
        <div className="p-6 border-b border-stark-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-spider-red rounded-xl flex items-center justify-center shadow-lg shadow-red-500/30 shrink-0">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-black tracking-tight text-white leading-none">
                SPIDEY-CHAIN
              </h1>
              <p className="text-[9px] text-stark-gold font-bold tracking-[0.2em] uppercase mt-0.5">
                Stark-Tech HUD v0.6
              </p>
            </div>
          </div>

          {/* Live Status */}
          <div className="mt-5 flex items-center gap-2.5">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                serverOnline
                  ? "bg-green-400 shadow-[0_0_8px_#4ade80] animate-pulse"
                  : "bg-spider-red shadow-[0_0_8px_#D80032] animate-pulse"
              )}
            />
            <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
              {serverOnline ? "Neural Hub — Online" : "Neural Hub — Offline"}
            </span>
          </div>
        </div>

        {/* System Stats */}
        <div className="p-6 border-b border-stark-border space-y-5">
          <h3 className="text-[9px] font-black text-gray-600 uppercase tracking-[0.35em] flex items-center gap-2">
            <Cpu className="w-3 h-3 text-spider-red" /> System Biometrics
          </h3>
          <HudStat label="GPU Backbone" value="RTX 3050" />
          <HudStat label="VLM Core" value="Moondream" />
          <HudStat label="GraphRAG" value={indexedVideos.length > 0 ? "Active" : "Standby"} />
          <HudStat label="Audio Decoder" value="Whisper-Base" />
        </div>

        {/* Indexed Videos */}
        <div className="p-6 border-b border-stark-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[9px] font-black text-gray-600 uppercase tracking-[0.35em] flex items-center gap-2">
              <Database className="w-3 h-3 text-stark-gold" /> Knowledge Base
            </h3>
            <button
              onClick={clearHistory}
              title="Clear chat history"
              className="flex items-center gap-1 text-[9px] text-gray-600 hover:text-spider-red transition-colors font-bold uppercase tracking-widest"
            >
              <Trash2 className="w-3 h-3" /> Clear
            </button>
          </div>
          {indexedVideos.length === 0 ? (
            <p className="text-[10px] text-gray-600 italic">No videos indexed yet.</p>
          ) : (
            <div className="space-y-2">
              {indexedVideos.map((vid) => (
                <div key={vid} className="flex items-center gap-2">
                  <CircleDot className="w-2 h-2 text-spider-red shrink-0" />
                  <span className="text-[9px] text-gray-400 font-bold truncate tracking-wide">
                    {vid}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Live Telemetry Logs */}
        <div className="flex-1 flex flex-col p-6 gap-3 min-h-0">
          <h3 className="text-[9px] font-black text-gray-600 uppercase tracking-[0.35em] flex items-center gap-2 shrink-0">
            <Terminal className="w-3 h-3 text-spider-red" /> Live Telemetry
          </h3>
          <div
            ref={logRef}
            className="flex-1 min-h-0 overflow-y-auto font-mono text-[9px] space-y-1.5 leading-tight pr-1"
            style={{ scrollbarWidth: "none" }}
          >
            {logs.map((log) => (
              <div key={log.id} className="flex gap-2">
                <span className="text-gray-700 shrink-0">{log.timestamp}</span>
                <span
                  className={cn(
                    log.type === "success"
                      ? "text-green-400"
                      : log.type === "error"
                      ? "text-spider-red"
                      : log.type === "warn"
                      ? "text-stark-gold"
                      : "text-gray-500"
                  )}
                >
                  {log.text}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-stark-border flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-spider-red" />
          <span className="text-[9px] text-gray-600 uppercase tracking-[0.2em] font-bold">
            Engine v0.6.0 — Authorised Only
          </span>
        </div>
      </aside>

      {/* ───────────────────────── MAIN CANVAS ───────────────────────── */}
      <main className="relative z-10 flex-1 flex flex-col min-w-0">
        {/* Top Bar: Video Ingestion */}
        <div className="shrink-0 p-4 border-b border-stark-border bg-stark-navy/10 backdrop-blur-md">
          <div className="flex gap-3 max-w-5xl mx-auto">
            <div className="relative flex-1">
              <FileScan className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 pointer-events-none" />
              <input
                type="text"
                placeholder="Enter video file path — e.g. C:\Users\...\sample.mp4"
                value={videoPath}
                onChange={(e) => setVideoPath(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleIngest()}
                className="w-full bg-stark-card/50 border border-stark-border rounded-xl py-3 pl-11 pr-4 text-sm placeholder:text-gray-700 focus:outline-none focus:border-spider-red/60 transition-colors font-medium text-gray-200"
              />
            </div>
            <button
              onClick={handleIngest}
              disabled={isIngesting || !videoPath.trim()}
              className="bg-spider-red hover:bg-red-700 disabled:bg-stark-card disabled:text-gray-600 disabled:cursor-not-allowed text-white font-black px-7 rounded-xl transition-all text-xs uppercase tracking-widest flex items-center gap-2.5 shadow-lg shadow-red-500/20 active:scale-95"
            >
              {isIngesting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              {isIngesting ? "Scanning..." : "Launch Scan"}
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-6 py-8 space-y-1"
          style={{ scrollbarWidth: "none" }}
        >
          <div className="max-w-4xl mx-auto space-y-10">
            {isLoadingHistory && (
              <div className="flex items-center gap-3 text-gray-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-[10px] uppercase tracking-widest font-bold">Restoring session...</span>
              </div>
            )}
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    "flex flex-col",
                    msg.sender === "user" ? "items-end" : "items-start"
                  )}
                >
                  {/* Label row */}
                  <div className="flex items-center gap-2.5 mb-2.5">
                    {msg.sender === "baburao" && (
                      <BrainCircuit className="w-3.5 h-3.5 text-spider-red" />
                    )}
                    <span
                      className={cn(
                        "text-[9px] font-black uppercase tracking-[0.3em]",
                        msg.sender === "baburao"
                          ? "text-spider-red"
                          : msg.sender === "system"
                          ? "text-stark-gold"
                          : "text-gray-500"
                      )}
                    >
                      {msg.sender === "baburao"
                        ? "B.A.B.U.R.A.O. Intelligence"
                        : msg.sender === "system"
                        ? "System Protocol"
                        : "Authorized Query"}
                    </span>
                    <span className="text-[9px] text-gray-700">{msg.timestamp}</span>
                  </div>

                  {/* Bubble */}
                  <div
                    className={cn(
                      "max-w-[88%] px-6 py-5 rounded-2xl text-sm leading-relaxed",
                      msg.sender === "user"
                        ? "bg-stark-navy/70 border border-stark-border text-gray-300"
                        : msg.sender === "system"
                        ? "border border-dashed border-stark-gold/30 text-stark-gold/80 italic text-xs"
                        : "bg-stark-card border-l-2 border-spider-red text-gray-100 shadow-xl shadow-black/30"
                    )}
                  >
                    {msg.text.split("\n").map((line, i) => (
                      <p key={i} className={i > 0 ? "mt-2.5" : ""}>
                        {line}
                      </p>
                    ))}
                  </div>

                  {/* Baburao dot trail */}
                  {msg.sender === "baburao" && (
                    <div className="mt-2 flex gap-1">
                      <span className="w-1 h-1 bg-spider-red/40 rounded-full inline-block" />
                      <span className="w-1 h-1 bg-spider-red/25 rounded-full inline-block" />
                      <span className="w-1 h-1 bg-spider-red/10 rounded-full inline-block" />
                    </div>
                  )}
                </motion.div>
              ))}

              {/* Typing indicator */}
              {isQuerying && (
                <motion.div
                  key="typing"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-3"
                >
                  <BrainCircuit className="w-3.5 h-3.5 text-spider-red" />
                  <span className="text-[9px] text-spider-red font-black uppercase tracking-[0.3em]">
                    B.A.B.U.R.A.O. Processing
                  </span>
                  <Loader2 className="w-3 h-3 text-spider-red animate-spin" />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Query Input Bar */}
        <div className="shrink-0 p-4 border-t border-stark-border bg-stark-navy/10 backdrop-blur-md">
          <form onSubmit={handleQuery} className="flex gap-3 max-w-4xl mx-auto">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 pointer-events-none" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask B.A.B.U.R.A.O. about the footage..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-stark-card/50 border border-stark-border rounded-2xl py-4 pl-11 pr-4 text-sm placeholder:text-gray-700 focus:outline-none focus:border-spider-red/60 transition-colors text-gray-200"
              />
            </div>
            <button
              type="submit"
              disabled={!query.trim() || isQuerying}
              className="bg-spider-red hover:bg-red-700 disabled:bg-stark-card disabled:cursor-not-allowed text-white p-4 rounded-2xl transition-all shadow-lg shadow-red-500/20 hover:scale-105 active:scale-95 flex items-center justify-center"
            >
              {isQuerying ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </form>
          <p className="text-center text-[9px] text-gray-700 uppercase tracking-[0.25em] mt-3">
            Powered by VidChain v0.6.0 · Local-First · GraphRAG + Multimodal Fusion
          </p>
        </div>
      </main>
    </div>
  );
}

function HudStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-[9px] text-gray-600 font-bold uppercase tracking-wider">{label}</span>
      <span className="text-[9px] text-spider-red font-black uppercase tracking-tight">{value}</span>
    </div>
  );
}
