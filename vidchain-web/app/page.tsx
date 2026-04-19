"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Shield,
  Search,
  Terminal,
  Zap,
  Send,
  Activity,
  FileScan,
  Database,
  BrainCircuit,
  Loader2,
  CircleDot,
  Trash2,
  Plus,
  MessageSquare,
  ChevronDown,
  Edit2,
  Check,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────
type Sender = "user" | "baburao" | "system";

type Message = {
  id: string;
  sender: Sender;
  text: string;
  timestamp: string;
  video_id?: string | null;
};

type Session = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
};

type Log = {
  id: string;
  text: string;
  type: "info" | "success" | "error" | "warn";
  timestamp: string;
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function timeStr() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function monoTime() {
  return new Date().toLocaleTimeString([], { hour12: false });
}
function relativeTime(ts: number) {
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function SpideyChainDashboard() {
  const [mounted, setMounted] = useState(false);

  // Sessions state
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingSession, setIsLoadingSession] = useState(false);

  // Input state
  const [videoPath, setVideoPath] = useState("");
  const [query, setQuery] = useState("");

  // Status
  const [serverOnline, setServerOnline] = useState(false);
  const [indexedVideos, setIndexedVideos] = useState<string[]>([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // ── Init ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    setMounted(true);
    addLog("Stark-Tech neural handshake initiated.", "info");
    fetchSessions();
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isQuerying]);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  // ── API Calls ─────────────────────────────────────────────────────────────
  const addLog = (text: string, type: Log["type"] = "info") => {
    setLogs((prev) => [
      ...prev.slice(-49), // keep last 50
      { id: Math.random().toString(36), text, type, timestamp: monoTime() },
    ]);
  };

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setServerOnline(true);
        setIndexedVideos(data.indexed_videos ?? []);
      } else {
        setServerOnline(false);
      }
    } catch {
      setServerOnline(false);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        const list: Session[] = data.sessions ?? [];
        setSessions(list);
        if (list.length > 0 && !activeSessionId) {
          loadSession(list[0].id);
        }
      }
    } catch {
      addLog("Could not fetch sessions from server.", "error");
    }
  };

  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoadingSession(true);
    setActiveSessionId(sessionId);
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages ?? []);
        addLog(`Session "${data.title}" loaded.`, "info");
      }
    } catch {
      addLog("Failed to load session.", "error");
    } finally {
      setIsLoadingSession(false);
    }
  }, []);

  const createSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Session" }),
      });
      if (res.ok) {
        const session = await res.json();
        setSessions((prev) => [
          { ...session, message_count: 0 },
          ...prev,
        ]);
        setActiveSessionId(session.id);
        setMessages([]);
        addLog("New session created.", "success");
        setTimeout(() => queryInputRef.current?.focus(), 100);
      }
    } catch {
      addLog("Failed to create session.", "error");
    }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        if (remaining.length > 0) {
          loadSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
        }
      }
      addLog("Session deleted.", "warn");
    } catch {
      addLog("Failed to delete session.", "error");
    }
  };

  const startRename = (session: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingId(session.id);
    setRenameValue(session.title);
  };

  const commitRename = async () => {
    if (!renamingId) return;
    try {
      await fetch(`${API_BASE}/api/sessions/${renamingId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: renameValue.trim() || "Untitled" }),
      });
      setSessions((prev) =>
        prev.map((s) =>
          s.id === renamingId ? { ...s, title: renameValue.trim() || "Untitled" } : s
        )
      );
    } catch {
      addLog("Rename failed.", "error");
    }
    setRenamingId(null);
  };

  // ── Ingestion ─────────────────────────────────────────────────────────────
  const handleIngest = async () => {
    if (!videoPath.trim() || isIngesting) return;
    setIsIngesting(true);
    const fname = videoPath.split(/[/\\]/).pop() ?? videoPath;
    addLog(`Initiating neural scan: ${fname}`, "info");

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_source: videoPath,
          session_id: activeSessionId,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        addLog("Multimodal pipeline dispatched.", "success");
        // If server created a new session, switch to it
        if (data.session_id && data.session_id !== activeSessionId) {
          await fetchSessions();
          await loadSession(data.session_id);
        }
        setVideoPath("");
        // Poll for completion message
        scheduleSessionRefresh(data.session_id ?? activeSessionId!, 8000);
      } else {
        addLog(data.detail || "Scan failed.", "error");
      }
    } catch {
      addLog("Telemetry lost. Is the server running?", "error");
    } finally {
      setIsIngesting(false);
    }
  };

  const scheduleSessionRefresh = (sessionId: string, delay: number) => {
    // Refresh the active session messages after ingestion completes
    setTimeout(async () => {
      if (sessionId) {
        try {
          const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
          if (res.ok) {
            const data = await res.json();
            if (activeSessionId === sessionId) {
              setMessages(data.messages ?? []);
            }
            setSessions((prev) =>
              prev.map((s) =>
                s.id === sessionId
                  ? { ...s, message_count: data.messages?.length ?? s.message_count }
                  : s
              )
            );
          }
        } catch {}
      }
    }, delay);
  };

  // ── Query ─────────────────────────────────────────────────────────────────
  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isQuerying) return;

    let sid = activeSessionId;
    if (!sid) {
      // Create a session on the fly
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Session" }),
      });
      if (res.ok) {
        const s = await res.json();
        sid = s.id;
        setActiveSessionId(s.id);
        setSessions((prev) => [{ ...s, message_count: 0 }, ...prev]);
      }
    }

    const userMsg = query;
    setQuery("");
    setIsQuerying(true);

    // Optimistic UI update
    const tempId = `user-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: tempId, sender: "user", text: userMsg, timestamp: timeStr() },
    ]);

    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg, session_id: sid }),
      });
      const data = await res.json();
      const aiMsg: Message = {
        id: `baburao-${Date.now()}`,
        sender: "baburao",
        text: data.response ?? "No data reconstructed.",
        timestamp: timeStr(),
      };
      setMessages((prev) => [...prev, aiMsg]);

      // Update session list title / count
      setSessions((prev) =>
        prev.map((s) =>
          s.id === (data.session_id ?? sid)
            ? { ...s, message_count: s.message_count + 2, updated_at: Date.now() / 1000 }
            : s
        )
      );
    } catch {
      addLog("Query failed. Check backend.", "error");
    } finally {
      setIsQuerying(false);
      setTimeout(() => queryInputRef.current?.focus(), 100);
    }
  };

  // ── Render helpers ────────────────────────────────────────────────────────
  const activeSession = sessions.find((s) => s.id === activeSessionId);

  if (!mounted) return <div className="bg-background h-screen" />;

  return (
    <div className="flex h-screen bg-background font-sans overflow-hidden text-foreground">
      {/* ── Grid BG ── */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(#1A1F2B 1px,transparent 1px),linear-gradient(90deg,#1A1F2B 1px,transparent 1px)",
          backgroundSize: "48px 48px",
          opacity: 0.25,
        }}
      />

      {/* ════════════════ SESSIONS SIDEBAR ════════════════ */}
      <aside className="relative z-10 w-64 flex flex-col border-r border-stark-border bg-background shrink-0">
        {/* Brand */}
        <div className="p-5 border-b border-stark-border flex items-center gap-3">
          <div className="w-9 h-9 bg-spider-red rounded-xl flex items-center justify-center shadow-lg shadow-red-500/30 shrink-0">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-black tracking-tight leading-none">SPIDEY-CHAIN</h1>
            <p className="text-[8px] text-stark-gold font-bold tracking-[0.2em] uppercase mt-0.5">
              B.A.B.U.R.A.O. v0.6
            </p>
          </div>
        </div>

        {/* New Session Button */}
        <div className="p-3 border-b border-stark-border">
          <button
            onClick={createSession}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl border border-stark-border hover:border-spider-red/40 hover:bg-stark-card/50 transition-all text-[11px] font-bold uppercase tracking-widest text-gray-400 hover:text-white"
          >
            <Plus className="w-3.5 h-3.5 text-spider-red" />
            New Session
          </button>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1" style={{ scrollbarWidth: "none" }}>
          {sessions.length === 0 && (
            <p className="text-center text-[10px] text-gray-700 py-8 uppercase tracking-widest">
              No sessions yet
            </p>
          )}
          <AnimatePresence>
            {sessions.map((session) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                className={cn(
                  "group relative flex items-start gap-2.5 px-3 py-3 rounded-xl cursor-pointer transition-all",
                  activeSessionId === session.id
                    ? "bg-stark-card border border-spider-red/20"
                    : "hover:bg-stark-card/50 border border-transparent"
                )}
                onClick={() => loadSession(session.id)}
              >
                <MessageSquare className={cn(
                  "w-3.5 h-3.5 mt-0.5 shrink-0",
                  activeSessionId === session.id ? "text-spider-red" : "text-gray-600"
                )} />

                <div className="flex-1 min-w-0">
                  {renamingId === session.id ? (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        ref={renameInputRef}
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") commitRename(); if (e.key === "Escape") setRenamingId(null); }}
                        className="flex-1 bg-transparent text-[11px] font-bold outline-none border-b border-spider-red pb-0.5"
                      />
                      <button onClick={commitRename} className="text-green-400 hover:text-green-300"><Check className="w-3 h-3" /></button>
                      <button onClick={() => setRenamingId(null)} className="text-gray-600 hover:text-red-400"><X className="w-3 h-3" /></button>
                    </div>
                  ) : (
                    <p className="text-[11px] font-bold truncate text-gray-300 leading-tight">
                      {session.title}
                    </p>
                  )}
                  <p className="text-[9px] text-gray-600 mt-1">
                    {session.message_count} msgs · {relativeTime(session.updated_at)}
                  </p>
                </div>

                {/* Action icons on hover */}
                {renamingId !== session.id && (
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-1">
                    <button
                      onClick={(e) => startRename(session, e)}
                      className="p-1 rounded text-gray-600 hover:text-white hover:bg-stark-card transition-colors"
                    >
                      <Edit2 className="w-2.5 h-2.5" />
                    </button>
                    <button
                      onClick={(e) => deleteSession(session.id, e)}
                      className="p-1 rounded text-gray-600 hover:text-spider-red hover:bg-stark-card transition-colors"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Server Status Footer */}
        <div className="p-4 border-t border-stark-border space-y-3">
          <div className="flex items-center gap-2">
            <span className={cn(
              "w-1.5 h-1.5 rounded-full shrink-0",
              serverOnline ? "bg-green-400 shadow-[0_0_6px_#4ade80]" : "bg-spider-red shadow-[0_0_6px_#D80032]"
            )} />
            <span className="text-[9px] font-bold uppercase tracking-widest text-gray-600">
              {serverOnline ? "Backend Online" : "Backend Offline"}
            </span>
          </div>
          {indexedVideos.length > 0 && (
            <div className="space-y-1">
              <p className="text-[8px] text-gray-700 uppercase tracking-widest font-bold flex items-center gap-1.5">
                <Database className="w-2.5 h-2.5 text-stark-gold" /> {indexedVideos.length} video{indexedVideos.length > 1 ? "s" : ""} indexed
              </p>
              {indexedVideos.slice(0, 3).map((v) => (
                <div key={v} className="flex items-center gap-1.5">
                  <CircleDot className="w-1.5 h-1.5 text-spider-red shrink-0" />
                  <span className="text-[8px] text-gray-600 truncate">{v}</span>
                </div>
              ))}
              {indexedVideos.length > 3 && (
                <p className="text-[8px] text-gray-700">+{indexedVideos.length - 3} more</p>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* ════════════════ MAIN PANEL ════════════════ */}
      <div className="relative z-10 flex-1 flex flex-col min-w-0">

        {/* Top Bar */}
        <div className="shrink-0 h-14 border-b border-stark-border bg-stark-navy/10 backdrop-blur-md flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <span className="text-sm font-black truncate max-w-sm">
              {activeSession?.title ?? "Select a Session"}
            </span>
            {activeSession && (
              <span className="text-[9px] text-gray-600 font-bold uppercase tracking-widest">
                #{activeSession.id}
              </span>
            )}
          </div>

          {/* Ingest row */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <FileScan className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600 pointer-events-none" />
              <input
                type="text"
                placeholder="Video path..."
                value={videoPath}
                onChange={(e) => setVideoPath(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleIngest()}
                className="w-72 bg-stark-card/50 border border-stark-border rounded-lg py-2 pl-9 pr-3 text-xs placeholder:text-gray-700 focus:outline-none focus:border-spider-red/50 transition-colors"
              />
            </div>
            <button
              onClick={handleIngest}
              disabled={isIngesting || !videoPath.trim()}
              className="bg-spider-red hover:bg-red-700 disabled:bg-stark-card disabled:text-gray-700 disabled:cursor-not-allowed text-white font-black px-4 py-2 rounded-lg transition-all text-[10px] uppercase tracking-widest flex items-center gap-1.5 shadow shadow-red-500/20 active:scale-95"
            >
              {isIngesting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
              {isIngesting ? "Scanning" : "Scan"}
            </button>
          </div>
        </div>

        {/* Chat Canvas */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-8 py-10"
          style={{ scrollbarWidth: "none" }}
        >
          <div className="max-w-3xl mx-auto space-y-10">
            {isLoadingSession && (
              <div className="flex items-center gap-3 text-gray-700">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-[10px] uppercase tracking-widest font-bold">Loading session...</span>
              </div>
            )}

            {!isLoadingSession && messages.length === 0 && (
              <div className="text-center py-20 space-y-4 opacity-30">
                <BrainCircuit className="w-12 h-12 mx-auto text-spider-red" />
                <p className="text-sm font-bold uppercase tracking-widest">B.A.B.U.R.A.O. Standby</p>
                <p className="text-xs text-gray-600">Ingest a video or start typing to begin</p>
              </div>
            )}

            <AnimatePresence mode="popLayout">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className={cn(
                    "flex flex-col",
                    msg.sender === "user" ? "items-end" : "items-start"
                  )}
                >
                  {/* Label */}
                  <div className="flex items-center gap-2 mb-2">
                    {msg.sender === "baburao" && <BrainCircuit className="w-3 h-3 text-spider-red" />}
                    <span className={cn(
                      "text-[9px] font-black uppercase tracking-[0.3em]",
                      msg.sender === "baburao" ? "text-spider-red" :
                      msg.sender === "system" ? "text-stark-gold" : "text-gray-600"
                    )}>
                      {msg.sender === "baburao" ? "B.A.B.U.R.A.O. Intelligence" :
                       msg.sender === "system" ? "System" : "You"}
                    </span>
                    <span className="text-[9px] text-gray-700">{msg.timestamp}</span>
                  </div>

                  {/* Bubble */}
                  <div className={cn(
                    "max-w-[88%] px-5 py-4 rounded-2xl text-sm leading-relaxed",
                    msg.sender === "user"
                      ? "bg-stark-navy/80 border border-stark-border text-gray-300 rounded-br-sm"
                      : msg.sender === "system"
                        ? "border border-dashed border-stark-gold/25 text-stark-gold/70 italic text-xs px-4 py-3"
                        : "bg-stark-card border-l-2 border-spider-red text-gray-100 shadow-lg shadow-black/30 rounded-bl-sm"
                  )}>
                    {msg.text.split("\n").map((line, i) => (
                      <p key={i} className={i > 0 ? "mt-2" : ""}>{line}</p>
                    ))}
                  </div>

                  {msg.sender === "baburao" && (
                    <div className="mt-1.5 flex gap-1 opacity-25">
                      <span className="w-1 h-1 rounded-full bg-spider-red inline-block" />
                      <span className="w-1 h-1 rounded-full bg-spider-red/50 inline-block" />
                      <span className="w-1 h-1 rounded-full bg-spider-red/20 inline-block" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Typing Indicator */}
            {isQuerying && (
              <motion.div
                key="typing"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <BrainCircuit className="w-3 h-3 text-spider-red" />
                <span className="text-[9px] text-spider-red font-black uppercase tracking-[0.3em]">
                  Processing
                </span>
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.span
                      key={i}
                      animate={{ opacity: [0.2, 1, 0.2] }}
                      transition={{ duration: 1, delay: i * 0.2, repeat: Infinity }}
                      className="w-1 h-1 rounded-full bg-spider-red inline-block"
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Input Bar */}
        <div className="shrink-0 border-t border-stark-border bg-background/80 backdrop-blur-md px-8 py-4">
          <form onSubmit={handleQuery} className="flex gap-3 max-w-3xl mx-auto">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600 pointer-events-none" />
              <input
                ref={queryInputRef}
                type="text"
                placeholder={
                  indexedVideos.length > 0
                    ? "Ask B.A.B.U.R.A.O. about the footage..."
                    : "Ingest a video first, then ask questions here..."
                }
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-stark-card/60 border border-stark-border rounded-2xl py-3.5 pl-11 pr-4 text-sm placeholder:text-gray-700 focus:outline-none focus:border-spider-red/50 transition-colors text-gray-200"
              />
            </div>
            <button
              type="submit"
              disabled={!query.trim() || isQuerying}
              className="bg-spider-red hover:bg-red-700 disabled:bg-stark-card disabled:cursor-not-allowed text-white p-3.5 rounded-2xl transition-all shadow shadow-red-500/20 hover:scale-105 active:scale-95 flex items-center justify-center"
            >
              {isQuerying ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </form>
          <p className="text-center text-[8px] text-gray-700 uppercase tracking-[0.25em] mt-2.5">
            VidChain v0.6 · Local-First · GraphRAG + Whisper + OCR + YOLO
          </p>
        </div>
      </div>

      {/* ════════════════ TELEMETRY SIDEBAR ════════════════ */}
      <aside className="relative z-10 w-56 flex flex-col border-l border-stark-border bg-background shrink-0">
        <div className="p-4 border-b border-stark-border">
          <h3 className="text-[9px] font-black text-gray-600 uppercase tracking-[0.3em] flex items-center gap-2">
            <Terminal className="w-3 h-3 text-spider-red" /> Live Telemetry
          </h3>
        </div>
        <div
          className="flex-1 overflow-y-auto p-4 space-y-1.5 font-mono text-[9px] leading-tight"
          style={{ scrollbarWidth: "none" }}
        >
          {logs.map((log) => (
            <div key={log.id} className="flex gap-2">
              <span className="text-gray-800 shrink-0">{log.timestamp}</span>
              <span className={cn(
                log.type === "success" ? "text-green-500" :
                log.type === "error" ? "text-spider-red" :
                log.type === "warn" ? "text-stark-gold" : "text-gray-600"
              )}>
                {log.text}
              </span>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-stark-border">
          <div className="flex items-center gap-2">
            <Activity className="w-3 h-3 text-spider-red" />
            <span className="text-[8px] text-gray-700 uppercase tracking-widest font-bold">
              Authorized Only
            </span>
          </div>
        </div>
      </aside>
    </div>
  );
}
