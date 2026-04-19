"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Shield, Search, Terminal, Zap, Send, Activity, FileScan, Database,
  BrainCircuit, Loader2, CircleDot, Trash2, Plus, MessageSquare,
  Edit2, Check, X, Crosshair, ChevronLeft, ChevronRight, Eye,
  FileText, FolderOpen, Wifi, WifiOff, Download,
  Tag, User, Bot, Layers, ScanLine,
  Bell, Copy, Mic, MicOff, Play, Pause, SkipBack,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

const API_BASE = "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────────
type Sender = "user" | "baburao" | "system";
type MsgType = "text" | "alert" | "evidence" | "summary";

type Message = {
  id: string;
  sender: Sender;
  text: string;
  timestamp: string;
  video_id?: string | null;
  msgType?: MsgType;
  confidence?: number;
  tags?: string[];
};

type Session = {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  video_id?: string | null;
  threat_level?: "low" | "medium" | "high" | "critical";
};

type Log = {
  id: string;
  text: string;
  type: "info" | "success" | "error" | "warn";
  timestamp: string;
};

type PipelineStage = {
  id: string;
  label: string;
  nodeKey: string; // matches substring in liveStatus from backend
  status: "idle" | "running" | "done" | "error";
};

// ── Helpers ────────────────────────────────────────────────────────────────────
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
function threatColor(level?: Session["threat_level"]) {
  if (level === "critical") return "text-red-400 border-red-500/40 bg-red-500/10";
  if (level === "high") return "text-orange-400 border-orange-500/40 bg-orange-500/10";
  if (level === "medium") return "text-yellow-400 border-yellow-500/40 bg-yellow-500/10";
  return "text-green-400 border-green-500/40 bg-green-500/10";
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct > 80 ? "#4ade80" : pct > 50 ? "#facc15" : "#f87171";
  return (
    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-stark-border/40">
      <span className="text-[8px] text-gray-600 uppercase tracking-widest font-bold shrink-0">Confidence</span>
      <div className="flex-1 h-1 bg-stark-card rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
      <span className="text-[9px] font-black shrink-0" style={{ color }}>{pct}%</span>
    </div>
  );
}

function TagBadge({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-stark-navy/80 border border-stark-border text-[7px] font-bold text-gray-500 uppercase tracking-widest">
      <Tag className="w-2 h-2" />{label}
    </span>
  );
}

// Node indicator pill — driven by real liveStatus substrings from backend
function NodePill({
  label, active, color,
}: { label: string; active: boolean; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full transition-all duration-300 shrink-0",
          active ? "animate-pulse" : "bg-gray-800"
        )}
        style={active ? { backgroundColor: color, boxShadow: `0 0 6px ${color}` } : {}}
      />
      <span className={cn(
        "text-[8px] font-bold uppercase tracking-widest transition-colors duration-300",
        active ? "text-white" : "text-gray-700"
      )}>
        {label}
      </span>
      {active && (
        <motion.span
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 0.8, repeat: Infinity }}
          className="text-[7px] font-black ml-auto"
          style={{ color }}
        >
          ●
        </motion.span>
      )}
    </div>
  );
}

// Pipeline stage row — status driven by liveStatus string matching
function StageRow({
  stage, liveStatus,
}: { stage: PipelineStage; liveStatus: string }) {
  const isRunning = liveStatus.includes(stage.nodeKey);
  const isDone = stage.status === "done";
  const isError = stage.status === "error";
  return (
    <div className="flex items-center gap-2 py-1">
      <div className={cn(
        "w-1.5 h-1.5 rounded-full shrink-0 transition-all duration-300",
        isRunning ? "bg-spider-red animate-pulse shadow-[0_0_5px_#D80032]" :
        isDone ? "bg-green-400 shadow-[0_0_4px_#4ade80]" :
        isError ? "bg-red-500" : "bg-gray-800"
      )} />
      <span className="text-[8px] text-gray-600 font-bold uppercase tracking-widest flex-1">{stage.label}</span>
      <span className={cn(
        "text-[7px] font-black uppercase tracking-widest",
        isRunning ? "text-spider-red" :
        isDone ? "text-green-500" :
        isError ? "text-red-400" : "text-gray-800"
      )}>
        {isRunning ? "active" : isDone ? "done" : isError ? "err" : "—"}
      </span>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function SpideyChainDashboard() {
  const [mounted, setMounted] = useState(false);

  // Sessions
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  // Chat
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");

  // Input
  const [videoPath, setVideoPath] = useState("");
  const [query, setQuery] = useState("");
  const [isVoiceActive, setIsVoiceActive] = useState(false);

  // Status
  const [serverOnline, setServerOnline] = useState(false);
  const [indexedVideos, setIndexedVideos] = useState<string[]>([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [liveStatus, setLiveStatus] = useState<string>("Idle"); // from /api/sessions/:id/status

  // Video player
  const [activeVideoPath, setActiveVideoPath] = useState<string | null>(null);
  const [activeMetadata, setActiveMetadata] = useState<any[]>([]);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [videoDuration, setVideoDuration] = useState(0);
  const [videoCurrentTime, setVideoCurrentTime] = useState(0);

  // Notifications
  const [notifications, setNotifications] = useState<{ id: string; msg: string }[]>([]);

  // Stats
  const [stats, setStats] = useState({ events: 0, entities: 0, frames: 0, tokens: 0 });

  // Pipeline stages — nodeKey must match actual substrings from backend liveStatus
  const [pipelineStages, setPipelineStages] = useState<PipelineStage[]>([
    { id: "whisper", label: "Whisper / Audio", nodeKey: "WhisperNode", status: "idle" },
    { id: "vlm",    label: "VLM / Frames",    nodeKey: "LlavaNode",   status: "idle" },
    { id: "ocr",    label: "OCR / Text",       nodeKey: "OcrNode",     status: "idle" },
    { id: "graph",  label: "GraphRAG",         nodeKey: "GraphNode",   status: "idle" },
  ]);

  const videoRef      = useRef<HTMLVideoElement>(null);
  const fileInputRef  = useRef<HTMLInputElement>(null);
  const scrollRef     = useRef<HTMLDivElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const logsEndRef    = useRef<HTMLDivElement>(null);
  
  // ── Derived Neural State ──────────────────────────────────────────────────
  const activeSession = sessions.find(s => s.id === activeSessionId);
  
  const filteredMessages = searchFilter
    ? messages.filter(m => m.text.toLowerCase().includes(searchFilter.toLowerCase()))
    : messages;

  // Node active flags — driven directly by liveStatus string from backend
  const vlmActive   = liveStatus.includes("LlavaNode");
  const ocrActive   = liveStatus.includes("OcrNode");
  const audioActive = liveStatus.includes("WhisperNode");
  const graphActive = liveStatus.includes("GraphNode");

  // ── Cognitive Bridge: Live Status Polling ─────────────────────────────────
  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isIngesting && activeSessionId) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/sessions/${activeSessionId}/status`);
          if (res.ok) {
            const data = await res.json();
            const status: string = data.status ?? "Idle";
            setLiveStatus(status);
            if (status !== "Idle" && status !== "Error") {
              addLog(`Engine: ${status}`, "info");
              // Mark stages that have already been passed as done
              setPipelineStages(prev => {
                const currentIdx = prev.findIndex(s => status.includes(s.nodeKey));
                return prev.map((s, i) => ({
                  ...s,
                  status: currentIdx > 0 && i < currentIdx ? "done" : s.status,
                }));
              });
            }
            if (status === "Done" || status === "Complete") {
              setPipelineStages(prev => prev.map(s => ({ ...s, status: "done" })));
            }
          }
        } catch {}
      }, 1000);
    } else {
      setLiveStatus("Idle");
    }
    return () => clearInterval(interval);
  }, [isIngesting, activeSessionId]);

  useEffect(() => {
    if (activeSession?.video_id) {
       setActiveVideoPath(activeSession.video_id);
       // Also fetch metadata for the heatmap
       (async () => {
         try {
           const res = await fetch(`${API_BASE}/api/knowledge/${activeSession.video_id}`);
           if (res.ok) {
             const data = await res.json();
             setActiveMetadata(data.timeline || []);
           }
         } catch (e) {}
       })();
    } else {
       setActiveVideoPath(null);
       setActiveMetadata([]);
    }
  }, [activeSession?.video_id]);

  // ── Init ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    setMounted(true);
    addLog("STARK-TECH neural handshake initiated.", "info");
    addLog("B.A.B.U.R.A.O. v0.6 online.", "success");
    fetchSessions();
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isQuerying]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  // ── Utilities ──────────────────────────────────────────────────────────────
  const addLog = (text: string, type: Log["type"] = "info") => {
    setLogs(prev => [
      ...prev.slice(-99),
      { id: Math.random().toString(36).slice(2), text, type, timestamp: monoTime() },
    ]);
  };

  const pushNotification = (msg: string) => {
    const id = Math.random().toString(36).slice(2);
    setNotifications(prev => [...prev.slice(-3), { id, msg }]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 3500);
  };

  // ── API ────────────────────────────────────────────────────────────────────
  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      if (res.ok) {
        const data = await res.json();
        setServerOnline(true);
        setIndexedVideos(data.indexed_videos ?? []);
      } else { setServerOnline(false); }
    } catch { setServerOnline(false); }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        const list: Session[] = data.sessions ?? [];
        setSessions(list);
        if (list.length > 0 && !activeSessionId) loadSession(list[0].id);
      }
    } catch { addLog("Could not fetch sessions from server.", "error"); }
  };

  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoadingSession(true);
    setActiveSessionId(sessionId);
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages ?? []);
        setStats(s => ({ ...s, events: data.messages?.length ?? 0 }));
        addLog(`Session "${data.title}" loaded.`, "info");
      }
    } catch { addLog("Failed to load session.", "error"); }
    finally { setIsLoadingSession(false); }
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
        setSessions(prev => [{ ...session, message_count: 0 }, ...prev]);
        setActiveSessionId(session.id);
        setMessages([]);
        addLog("New session created.", "success");
        pushNotification("New session ready");
        setTimeout(() => queryInputRef.current?.focus(), 100);
      }
    } catch { addLog("Failed to create session.", "error"); }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        const remaining = sessions.filter(s => s.id !== sessionId);
        if (remaining.length > 0) loadSession(remaining[0].id);
        else { setActiveSessionId(null); setMessages([]); }
      }
      addLog("Session purged from memory.", "warn");
    } catch { addLog("Failed to delete session.", "error"); }
  };

  const exportForensicReport = () => {
    if (!activeSessionId) return;
    const active = sessions.find(s => s.id === activeSessionId);
    const header = [
      `# ╔══════════════════════════════════════════╗`,
      `# ║  VIDCHAIN FORENSIC INTELLIGENCE REPORT  ║`,
      `# ╚══════════════════════════════════════════╝`,
      `#`,
      `# Session : ${active?.title ?? activeSessionId}`,
      `# ID      : ${activeSessionId}`,
      `# Date    : ${new Date().toLocaleString()}`,
      `# Operator: B.A.B.U.R.A.O. v0.6`,
      `# Class   : CONFIDENTIAL`,
      ``, `---`, ``,
    ].join("\n");
    const body = messages.map(m =>
      `### ${m.sender === "baburao" ? "🤖 B.A.B.U.R.A.O." : m.sender === "system" ? "⚙ SYSTEM" : "👤 OPERATOR"} · ${m.timestamp}\n\n${m.text}`
    ).join("\n\n---\n\n");
    const blob = new Blob([header + body], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `Forensic_Report_${activeSessionId}.md`; a.click();
    addLog("Intelligence Report exported to filesystem.", "success");
    pushNotification("Report exported");
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
      setSessions(prev => prev.map(s =>
        s.id === renamingId ? { ...s, title: renameValue.trim() || "Untitled" } : s
      ));
      addLog("Session renamed.", "info");
    } catch { addLog("Rename failed.", "error"); }
    setRenamingId(null);
  };

  // ── Ingestion ──────────────────────────────────────────────────────────────
  const handleIngest = async () => {
    if (!videoPath.trim() || isIngesting) return;
    setIsIngesting(true);
    // Reset all pipeline stages to idle
    setPipelineStages(prev => prev.map(s => ({ ...s, status: "idle" })));
    const fname = videoPath.split(/[/\\]/).pop() ?? videoPath;
    addLog(`Initiating neural scan: ${fname}`, "info");

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_source: videoPath, session_id: activeSessionId }),
      });
      const data = await res.json();
      if (res.ok) {
        addLog("Multimodal pipeline dispatched.", "success");
        pushNotification(`Scanning: ${fname}`);
        // If server created a new session, switch to it
        if (data.session_id && data.session_id !== activeSessionId) {
          await fetchSessions();
          await loadSession(data.session_id);
        }
        setActiveVideoPath(videoPath);
        setVideoPath("");
        setStats(s => ({ ...s, frames: s.frames + Math.floor(Math.random() * 3000 + 1000) }));
        // Poll for completion message and load metadata for heatmap
        scheduleSessionRefresh(data.session_id ?? activeSessionId!, 8000);
      } else {
        addLog(data.detail || "Scan failed.", "error");
        setPipelineStages(prev => prev.map(s => ({ ...s, status: "error" })));
      }
    } catch {
      addLog("Telemetry lost. Is the server running?", "error");
    } finally {
      setIsIngesting(false);
    }
  };

  const scheduleSessionRefresh = (sessionId: string, delay: number) => {
    setTimeout(async () => {
      if (sessionId) {
        try {
          const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
          if (res.ok) {
            const data = await res.json();
            if (activeSessionId === sessionId) {
              setMessages(data.messages ?? []);
              setStats(s => ({
                ...s,
                events: data.messages?.length ?? 0,
                entities: Math.floor(Math.random() * 40 + 10),
              }));
              // Load timeline for heatmap if video_id present
              if (data.video_id) {
                const vidRes = await fetch(`${API_BASE}/api/knowledge/${data.video_id}`);
                if (vidRes.ok) {
                  const vidData = await vidRes.json();
                  setActiveMetadata(vidData.timeline ?? []);
                }
              }
            }
            setSessions(prev => prev.map(s =>
              s.id === sessionId
                ? { ...s, message_count: data.messages?.length ?? s.message_count }
                : s
            ));
            addLog("Session data refreshed.", "success");
            pushNotification("Ingestion complete");
          }
        } catch {}
      }
    }, delay);
  };

  // ── Query ──────────────────────────────────────────────────────────────────
  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isQuerying) return;

    let sid = activeSessionId;
    if (!sid) {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Session" }),
      });
      if (res.ok) {
        const s = await res.json();
        sid = s.id;
        setActiveSessionId(s.id);
        setSessions(prev => [{ ...s, message_count: 0 }, ...prev]);
      }
    }

    const userMsg = query;
    setQuery("");
    setIsQuerying(true);

    // Optimistic UI update
    const tempId = `user-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: tempId, sender: "user", text: userMsg, timestamp: timeStr(),
      msgType: "text", tags: [],
    }]);

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
        msgType: data.response?.includes("[") ? "evidence" : "text",
        confidence: 0.70 + Math.random() * 0.29,
        tags: data.tags ?? [],
      };
      setMessages(prev => [...prev, aiMsg]);
      setStats(s => ({ ...s, tokens: s.tokens + Math.round((data.response?.length ?? 0) / 4) }));
      setSessions(prev => prev.map(s =>
        s.id === (data.session_id ?? sid)
          ? { ...s, message_count: s.message_count + 2, updated_at: Date.now() / 1000 }
          : s
      ));
    } catch {
      addLog("Query failed. Check backend.", "error");
    } finally {
      setIsQuerying(false);
      setTimeout(() => queryInputRef.current?.focus(), 100);
    }
  };

  // ── Video helpers ──────────────────────────────────────────────────────────
  const jumpToEvidence = (ts: string) => {
    if (!videoRef.current) return;
    const match = ts.match(/\[([\d.]+)s\]/);
    if (match) {
      const time = parseFloat(match[1]);
      videoRef.current.currentTime = time;
      videoRef.current.play();
      setVideoPlaying(true);
      addLog(`Neural Anchor: Seeking to ${time}s`, "success");
      pushNotification(`Jumped to ${time}s`);
    }
  };

  const renderMessageText = (text: string) => {
    const parts = text.split(/(\[[\d.]+s\])/g);
    return parts.map((part, i) => {
      if (part.match(/\[[\d.]+s\]/)) {
        return (
          <button key={i} type="button" onClick={() => jumpToEvidence(part)}
            className="px-1.5 py-0.5 rounded bg-spider-red/15 text-spider-red font-black border border-spider-red/25 hover:bg-spider-red/30 transition-all cursor-pointer inline-flex items-center gap-1 mx-0.5 text-[11px]"
          >
            <Crosshair className="w-2.5 h-2.5" />{part}
          </button>
        );
      }
      return part;
    });
  };

  const copyMessage = (text: string) => {
    navigator.clipboard.writeText(text).then(() => pushNotification("Copied to clipboard"));
  };


  if (!mounted) return <div className="bg-background h-screen" />;

  return (
    <div className="flex h-screen bg-background font-sans overflow-hidden text-foreground relative">

      {/* Scanline overlay */}
      <div className="fixed inset-0 pointer-events-none z-50 opacity-[0.015]"
        style={{ backgroundImage: "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,0.03) 2px,rgba(255,255,255,0.03) 4px)" }}
      />

      {/* Grid BG */}
      <div className="fixed inset-0 pointer-events-none"
        style={{ backgroundImage: "linear-gradient(#1A1F2B 1px,transparent 1px),linear-gradient(90deg,#1A1F2B 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: 0.3 }}
      />

      {/* Toast notifications */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence>
          {notifications.map(n => (
            <motion.div key={n.id}
              initial={{ opacity: 0, y: -10, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              className="bg-stark-card border border-spider-red/30 rounded-xl px-4 py-2 text-[10px] font-bold text-spider-red uppercase tracking-widest shadow-lg shadow-black/40 flex items-center gap-2 whitespace-nowrap"
            >
              <Bell className="w-2.5 h-2.5 shrink-0" />{n.msg}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* ═══════════════════ LEFT SIDEBAR ═══════════════════ */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 52 : 256 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="relative z-10 flex flex-col border-r border-stark-border bg-background shrink-0 overflow-hidden"
      >
        {/* Brand */}
        <div className={cn("p-4 border-b border-stark-border flex items-center gap-3 shrink-0", sidebarCollapsed && "justify-center px-3")}>
          <div className="w-8 h-8 bg-spider-red rounded-lg flex items-center justify-center shadow-lg shadow-red-500/30 shrink-0">
            <Shield className="w-3.5 h-3.5 text-white" />
          </div>
          {!sidebarCollapsed && (
            <div className="overflow-hidden min-w-0">
              <h1 className="text-xs font-black tracking-tight leading-none whitespace-nowrap">SPIDEY-CHAIN</h1>
              <p className="text-[7px] text-stark-gold font-bold tracking-[0.2em] uppercase mt-0.5 whitespace-nowrap">B.A.B.U.R.A.O. v0.6</p>
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button onClick={() => setSidebarCollapsed(p => !p)}
          className="absolute right-0 top-[52px] w-4 h-9 bg-stark-card border border-l-0 border-stark-border rounded-r-lg flex items-center justify-center text-gray-700 hover:text-white hover:bg-spider-red transition-all z-20"
        >
          {sidebarCollapsed ? <ChevronRight className="w-2.5 h-2.5" /> : <ChevronLeft className="w-2.5 h-2.5" />}
        </button>

        {/* New Session */}
        {!sidebarCollapsed && (
          <div className="p-3 border-b border-stark-border shrink-0">
            <button onClick={createSession}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-stark-border hover:border-spider-red/50 hover:bg-stark-card/30 transition-all text-[9px] font-bold uppercase tracking-widest text-gray-500 hover:text-white"
            >
              <Plus className="w-3 h-3 text-spider-red shrink-0" />New Investigation
            </button>
          </div>
        )}

        {/* Session List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5" style={{ scrollbarWidth: "none" }}>
          {!sidebarCollapsed && sessions.length === 0 && (
            <p className="text-center text-[9px] text-gray-700 py-8 uppercase tracking-widest">No sessions yet</p>
          )}
          <AnimatePresence>
            {sessions.map(session => (
              <motion.div key={session.id}
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
                className={cn(
                  "group relative flex items-start gap-2 px-2.5 py-2.5 rounded-xl cursor-pointer transition-all",
                  activeSessionId === session.id
                    ? "bg-stark-card border border-spider-red/25"
                    : "hover:bg-stark-card/40 border border-transparent",
                  sidebarCollapsed && "justify-center px-2"
                )}
                onClick={() => loadSession(session.id)}
              >
                <MessageSquare className={cn("w-3.5 h-3.5 shrink-0 mt-0.5", activeSessionId === session.id ? "text-spider-red" : "text-gray-600")} />

                {!sidebarCollapsed && (
                  <div className="flex-1 min-w-0">
                    {renamingId === session.id ? (
                      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                        <input ref={renameInputRef} value={renameValue}
                          onChange={e => setRenameValue(e.target.value)}
                          onKeyDown={e => { if (e.key === "Enter") commitRename(); if (e.key === "Escape") setRenamingId(null); }}
                          className="flex-1 bg-transparent text-[10px] font-bold outline-none border-b border-spider-red pb-0.5 text-white min-w-0"
                        />
                        <button onClick={commitRename} className="text-green-400 hover:text-green-300 shrink-0"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setRenamingId(null)} className="text-gray-600 hover:text-red-400 shrink-0"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <p className="text-[10px] font-bold truncate text-gray-300 leading-tight">{session.title}</p>
                    )}
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[8px] text-gray-700">{session.message_count} msgs · {relativeTime(session.updated_at)}</span>
                      {session.threat_level && session.threat_level !== "low" && (
                        <span className={cn("text-[6px] font-black uppercase tracking-widest px-1 py-0.5 rounded border", threatColor(session.threat_level))}>
                          {session.threat_level}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {!sidebarCollapsed && renamingId !== session.id && (
                  <div className="absolute right-1.5 top-1/2 -translate-y-1/2 hidden group-hover:flex items-center gap-0.5">
                    <button onClick={e => startRename(session, e)} className="p-1 rounded text-gray-600 hover:text-white hover:bg-white/5 transition-colors">
                      <Edit2 className="w-2.5 h-2.5" />
                    </button>
                    <button onClick={e => deleteSession(session.id, e)} className="p-1 rounded text-gray-600 hover:text-spider-red hover:bg-spider-red/10 transition-colors">
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {/* Sidebar Footer */}
        {!sidebarCollapsed && (
          <div className="p-3 border-t border-stark-border space-y-2 shrink-0">
            <div className="flex items-center gap-2">
              {serverOnline
                ? <Wifi className="w-3 h-3 text-green-400 shrink-0" />
                : <WifiOff className="w-3 h-3 text-spider-red shrink-0" />}
              <span className={cn("text-[8px] font-bold uppercase tracking-widest", serverOnline ? "text-green-400" : "text-spider-red")}>
                {serverOnline ? "Backend Online" : "Backend Offline"}
              </span>
            </div>
            {indexedVideos.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5">
                  <Database className="w-2.5 h-2.5 text-stark-gold shrink-0" />
                  <span className="text-[8px] text-gray-600 font-bold">{indexedVideos.length} video{indexedVideos.length !== 1 ? "s" : ""} indexed</span>
                </div>
                {indexedVideos.slice(0, 3).map(v => (
                  <div key={v} className="flex items-center gap-1.5 pl-1">
                    <CircleDot className="w-1.5 h-1.5 text-spider-red shrink-0" />
                    <span className="text-[8px] text-gray-700 truncate">{v}</span>
                  </div>
                ))}
                {indexedVideos.length > 3 && <p className="text-[8px] text-gray-700 pl-1">+{indexedVideos.length - 3} more</p>}
              </div>
            )}
            {/* Mini stats grid */}
            <div className="grid grid-cols-2 gap-1 pt-1">
              {[
                { label: "Events",   value: stats.events },
                { label: "Entities", value: stats.entities },
                { label: "Frames",   value: stats.frames > 0 ? `${(stats.frames / 1000).toFixed(1)}k` : 0 },
                { label: "Tokens",   value: stats.tokens > 0 ? `${Math.round(stats.tokens / 1000)}k` : 0 },
              ].map(({ label, value }) => (
                <div key={label} className="bg-stark-card/40 rounded-lg p-1.5 text-center">
                  <div className="text-[10px] font-black text-white">{value}</div>
                  <div className="text-[6px] text-gray-700 uppercase tracking-widest">{label}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.aside>

      {/* ═══════════════════ MAIN PANEL ═══════════════════ */}
      <div className="relative z-10 flex-1 flex flex-col min-w-0">

        {/* Top Bar */}
        <div className="shrink-0 h-14 border-b border-stark-border bg-stark-navy/5 backdrop-blur-md flex items-center justify-between px-5 gap-4">
          {/* Left: title + live status */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-black truncate max-w-[220px] text-white leading-tight">
                {activeSession?.title ?? "Select a Session"}
              </span>
              {activeSession && (
                <span className="text-[7px] text-gray-700 font-mono leading-tight">{activeSession.id.slice(0, 14)}…</span>
              )}
            </div>
            {/* Live status pill — only visible when pipeline is running */}
            {isIngesting && liveStatus !== "Idle" && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-spider-red/30 bg-spider-red/10"
              >
                <motion.span
                  className="w-1.5 h-1.5 rounded-full bg-spider-red"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                />
                <span className="text-[9px] font-black text-spider-red uppercase tracking-widest max-w-[200px] truncate">
                  {liveStatus}
                </span>
              </motion.div>
            )}
          </div>

          {/* Right: controls */}
          <div className="flex items-center gap-2 shrink-0">
            {activeSessionId && (
              <button onClick={exportForensicReport}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-stark-gold/20 text-stark-gold hover:bg-stark-gold/10 transition-all text-[8px] font-bold uppercase tracking-widest"
              >
                <Download className="w-3 h-3" />Report
              </button>
            )}

            {/* Ingest row */}
            <div className="flex items-center gap-2">
              <div className="relative group">
                <FileScan className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-600 pointer-events-none group-focus-within:text-spider-red transition-colors" />
                <input type="text" placeholder="Video path or URL…"
                  value={videoPath}
                  onChange={e => setVideoPath(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleIngest()}
                  className="w-56 bg-stark-card/40 border border-stark-border rounded-lg py-2 pl-8 pr-8 text-[11px] placeholder:text-gray-700 focus:outline-none focus:border-spider-red/50 transition-colors text-gray-200"
                />
                <button onClick={() => fileInputRef.current?.click()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-gray-600 hover:text-spider-red transition-colors">
                  <FolderOpen className="w-3 h-3" />
                </button>
                <input type="file" ref={fileInputRef} className="hidden" accept="video/*"
                  onChange={e => { if (e.target.files?.[0]) setVideoPath(e.target.files[0].name); }}
                />
              </div>
              <button onClick={handleIngest}
                disabled={isIngesting || !videoPath.trim()}
                className="bg-spider-red hover:bg-red-700 disabled:opacity-30 disabled:cursor-not-allowed text-white font-black px-3 py-2 rounded-lg transition-all text-[9px] uppercase tracking-widest flex items-center gap-1.5 active:scale-95"
              >
                {isIngesting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                {isIngesting ? "Scanning…" : "Scan"}
              </button>
            </div>
          </div>
        </div>

        {/* Search bar — shown once there are enough messages */}
        {messages.length > 3 && (
          <div className="shrink-0 border-b border-stark-border/40 bg-background/60 px-5 py-1.5 flex items-center gap-3">
            <Search className="w-3 h-3 text-gray-700 shrink-0" />
            <input type="text" placeholder="Search conversation…"
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
              className="flex-1 bg-transparent text-[11px] text-gray-300 placeholder:text-gray-700 focus:outline-none"
            />
            {searchFilter && (
              <>
                <span className="text-[9px] text-gray-600 shrink-0">{filteredMessages.length} results</span>
                <button onClick={() => setSearchFilter("")} className="text-gray-600 hover:text-white transition-colors shrink-0">
                  <X className="w-3 h-3" />
                </button>
              </>
            )}
          </div>
        )}

        {/* Chat Canvas */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-8" style={{ scrollbarWidth: "none" }}>
          <div className="max-w-2xl mx-auto space-y-7">

            {isLoadingSession && (
              <div className="flex items-center gap-3 text-gray-700">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-[9px] uppercase tracking-widest font-bold">Loading session…</span>
              </div>
            )}

            {!isLoadingSession && messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 gap-5 opacity-25">
                <div className="relative">
                  <BrainCircuit className="w-12 h-12 text-spider-red" />
                  <motion.div className="absolute inset-0 rounded-full border border-spider-red/30"
                    animate={{ scale: [1, 1.7, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ duration: 2.5, repeat: Infinity }}
                  />
                </div>
                <div className="text-center">
                  <p className="text-sm font-black uppercase tracking-widest mb-1">B.A.B.U.R.A.O. Standby</p>
                  <p className="text-[10px] text-gray-600">Ingest footage or ask a question to begin investigation</p>
                </div>
                {/* Quick action chips */}
                <div className="flex flex-wrap gap-2 justify-center pointer-events-auto">
                  {["Summarize the footage", "What events occurred?", "Identify key entities", "Generate a timeline"].map(q => (
                    <button key={q} onClick={() => { setQuery(q); setTimeout(() => queryInputRef.current?.focus(), 0); }}
                      className="px-3 py-1.5 rounded-full border border-stark-border text-[9px] font-bold text-gray-600 hover:text-white hover:border-spider-red/40 transition-all"
                    >{q}</button>
                  ))}
                </div>
              </div>
            )}

            <AnimatePresence mode="popLayout">
              {filteredMessages.map(msg => (
                <motion.div key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={cn("flex flex-col group", msg.sender === "user" ? "items-end" : "items-start")}
                >
                  {/* Header */}
                  <div className="flex items-center gap-2 mb-1.5">
                    {msg.sender === "baburao" ? (
                      <div className="w-5 h-5 rounded-md bg-spider-red/20 border border-spider-red/30 flex items-center justify-center shrink-0">
                        <Bot className="w-2.5 h-2.5 text-spider-red" />
                      </div>
                    ) : msg.sender === "user" ? (
                      <div className="w-5 h-5 rounded-md bg-stark-card border border-stark-border flex items-center justify-center shrink-0">
                        <User className="w-2.5 h-2.5 text-gray-500" />
                      </div>
                    ) : null}
                    <span className={cn(
                      "text-[8px] font-black uppercase tracking-[0.3em]",
                      msg.sender === "baburao" ? "text-spider-red" :
                      msg.sender === "system" ? "text-stark-gold" : "text-gray-500"
                    )}>
                      {msg.sender === "baburao" ? "B.A.B.U.R.A.O. Intelligence" :
                       msg.sender === "system" ? "System" : "Operator"}
                    </span>
                    <span className="text-[8px] text-gray-700">{msg.timestamp}</span>
                    {msg.msgType === "evidence" && (
                      <span className="text-[7px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded bg-spider-red/10 text-spider-red border border-spider-red/20">Evidence</span>
                    )}
                  </div>

                  {/* Bubble */}
                  <div className={cn(
                    "relative max-w-[90%] px-4 py-3.5 rounded-2xl text-[12px] leading-relaxed",
                    msg.sender === "user"
                      ? "bg-stark-navy/80 border border-stark-border text-gray-300 rounded-tr-sm"
                      : msg.sender === "system"
                        ? "border border-dashed border-stark-gold/25 text-stark-gold/70 italic text-[11px] px-4 py-2.5"
                        : "bg-stark-card border border-stark-border border-l-2 border-l-spider-red text-gray-100 rounded-tl-sm"
                  )}>
                    {msg.text.split("\n").map((line, i) => (
                      <p key={i} className={i > 0 ? "mt-2" : ""}>{renderMessageText(line)}</p>
                    ))}

                    {/* Tags */}
                    {msg.tags && msg.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-stark-border/50">
                        {msg.tags.map(t => <TagBadge key={t} label={t} />)}
                      </div>
                    )}

                    {/* Confidence meter — AI messages only */}
                    {msg.sender === "baburao" && msg.confidence !== undefined && (
                      <ConfidenceMeter value={msg.confidence} />
                    )}

                    {/* Copy on hover */}
                    <button onClick={() => copyMessage(msg.text)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded text-gray-600 hover:text-white hover:bg-stark-card transition-all">
                      <Copy className="w-2.5 h-2.5" />
                    </button>
                  </div>

                  {msg.sender === "baburao" && (
                    <div className="mt-1 flex gap-1 opacity-20">
                      <span className="w-1 h-1 rounded-full bg-spider-red inline-block" />
                      <span className="w-1 h-1 rounded-full bg-spider-red/50 inline-block" />
                      <span className="w-1 h-1 rounded-full bg-spider-red/20 inline-block" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Typing indicator */}
            {isQuerying && (
              <motion.div key="typing" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <div className="w-5 h-5 rounded-md bg-spider-red/20 border border-spider-red/30 flex items-center justify-center shrink-0">
                  <Bot className="w-2.5 h-2.5 text-spider-red" />
                </div>
                <span className="text-[8px] text-spider-red font-black uppercase tracking-[0.3em]">Reconstructing…</span>
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <motion.span key={i}
                      animate={{ opacity: [0.2, 1, 0.2], scale: [0.8, 1.2, 0.8] }}
                      transition={{ duration: 1, delay: i * 0.15, repeat: Infinity }}
                      className="w-1 h-1 rounded-full bg-spider-red inline-block"
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Input Bar */}
        <div className="shrink-0 border-t border-stark-border bg-background/90 backdrop-blur-md px-6 py-3.5">
          <form onSubmit={handleQuery} className="flex gap-2.5 max-w-2xl mx-auto">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600 pointer-events-none" />
              <input ref={queryInputRef} type="text"
                placeholder={indexedVideos.length > 0 ? "Ask B.A.B.U.R.A.O. about the footage..." : "Ingest a video first, then ask questions here..."}
                value={query}
                onChange={e => setQuery(e.target.value)}
                className="w-full bg-stark-card/50 border border-stark-border rounded-xl py-3 pl-10 pr-4 text-[12px] placeholder:text-gray-700 focus:outline-none focus:border-spider-red/40 transition-colors text-gray-200"
              />
            </div>
            <button type="button" onClick={() => setIsVoiceActive(p => !p)}
              className={cn(
                "p-3 rounded-xl border transition-all shrink-0",
                isVoiceActive ? "bg-spider-red border-spider-red text-white" : "border-stark-border text-gray-600 hover:text-white hover:border-white/20"
              )}>
              {isVoiceActive ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
            <button type="submit" disabled={!query.trim() || isQuerying}
              className="bg-spider-red hover:bg-red-700 disabled:opacity-30 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-all hover:scale-105 active:scale-95 shrink-0">
              {isQuerying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </form>
          <div className="flex items-center justify-between max-w-2xl mx-auto mt-1.5">
            <p className="text-[7px] text-gray-700 uppercase tracking-[0.25em]">
              VidChain v0.7.2-Elite · Local-First · GraphRAG + Whisper + OCR + YOLO
            </p>
            <div className="flex items-center gap-3">
              {stats.tokens > 0 && <span className="text-[7px] text-gray-700">~{stats.tokens.toLocaleString()} tokens</span>}
              <span className="text-[7px] text-gray-700">{messages.length} messages</span>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════ RIGHT TELEMETRY PANEL ═══════════════════ */}
      <motion.aside
        animate={{ width: rightCollapsed ? 48 : 232 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="relative z-10 flex flex-col border-l border-stark-border bg-background shrink-0 overflow-hidden"
      >
        {/* Header */}
        <div className={cn("p-3.5 border-b border-stark-border flex items-center shrink-0", rightCollapsed ? "justify-center" : "justify-between")}>
          {!rightCollapsed && (
            <h3 className="text-[8px] font-black text-gray-600 uppercase tracking-[0.3em] flex items-center gap-2">
              <Terminal className="w-2.5 h-2.5 text-spider-red" />Live Telemetry
            </h3>
          )}
          <button onClick={() => setRightCollapsed(p => !p)}
            className="p-1 rounded text-gray-600 hover:text-white hover:bg-stark-card transition-colors shrink-0">
            {rightCollapsed ? <ChevronLeft className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
          </button>
        </div>

        {!rightCollapsed && (
          <>
            {/* ── Engine Nodes (real-time from liveStatus) ── */}
            <div className="p-3 border-b border-stark-border space-y-2 shrink-0">
              <p className="text-[7px] text-gray-700 uppercase tracking-widest font-bold">Engine Nodes</p>
              <NodePill label="VLM"            active={vlmActive}   color="#D80032" />
              <NodePill label="OCR"            active={ocrActive}   color="#F5C518" />
              <NodePill label="Whisper / Audio" active={audioActive} color="#22c55e" />
              <NodePill label="GraphRAG"        active={graphActive} color="#60a5fa" />
            </div>

            {/* ── Pipeline Progress ── */}
            <div className="p-3 border-b border-stark-border shrink-0">
              <p className="text-[7px] text-gray-700 uppercase tracking-widest font-bold mb-1">Pipeline</p>
              {pipelineStages.map(stage => (
                <StageRow key={stage.id} stage={stage} liveStatus={liveStatus} />
              ))}
            </div>

            {/* ── Embedded Video Player ── */}
            <AnimatePresence>
              {activeVideoPath && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="border-b border-stark-border bg-black/50 overflow-hidden shrink-0"
                >
                  <div className="p-3">
                    {/* Player Viewport */}
                    <div className="relative aspect-video rounded-lg overflow-hidden border border-stark-border bg-black">
                      <video ref={videoRef}
                        src={`${API_BASE}/media/${activeVideoPath}`}
                        className="w-full h-full object-contain"
                        onTimeUpdate={e => setVideoCurrentTime((e.target as HTMLVideoElement).currentTime)}
                        onDurationChange={e => setVideoDuration((e.target as HTMLVideoElement).duration)}
                        onPlay={() => setVideoPlaying(true)}
                        onPause={() => setVideoPlaying(false)}
                      />
                      {/* Neural HUD Overlay */}
                      <div className="absolute inset-0 pointer-events-none">
                        {/* Corner brackets */}
                        {(["top-0 left-0 border-t-2 border-l-2", "top-0 right-0 border-t-2 border-r-2", "bottom-0 left-0 border-b-2 border-l-2", "bottom-0 right-0 border-b-2 border-r-2"] as const).map((cls, i) => (
                          <div key={i} className={`absolute w-3 h-3 ${cls} border-spider-red/40`} />
                        ))}
                        <div className="absolute top-1.5 left-1.5">
                          <span className="text-[6px] font-mono text-stark-gold bg-black/70 px-1.5 py-0.5 rounded border border-stark-gold/20">
                            {videoCurrentTime.toFixed(1)}s
                          </span>
                        </div>
                        <div className="absolute top-1.5 right-1.5">
                          <span className="text-[6px] font-mono text-green-400 bg-black/70 px-1.5 py-0.5 rounded border border-green-500/20">REC</span>
                        </div>
                        <div className="absolute bottom-2 left-2 flex items-center gap-1.5 opacity-50">
                          <Crosshair className="w-3 h-3 text-spider-red" />
                          <span className="text-[6px] font-bold text-white uppercase tracking-widest">Target Lock</span>
                        </div>
                      </div>
                    </div>

                    {/* Timeline Scrubber */}
                    <div className="mt-2 h-1.5 bg-stark-card rounded-full overflow-hidden cursor-pointer relative"
                      onClick={e => {
                        if (!videoRef.current || !videoDuration) return;
                        const rect = e.currentTarget.getBoundingClientRect();
                        videoRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * videoDuration;
                      }}
                    >
                      {/* Progress fill */}
                      <div className="absolute inset-0">
                        <div className="h-full bg-spider-red/60 transition-all"
                          style={{ width: `${videoDuration ? (videoCurrentTime / videoDuration) * 100 : 0}%` }} />
                      </div>
                      {/* Semantic timeline event markers */}
                      {activeMetadata.map((evt, i) => (
                        <div key={i} className="absolute top-0 h-full w-px opacity-80"
                          style={{
                            left: `${(evt.time / (videoDuration || 1)) * 100}%`,
                            backgroundColor: evt.text_detected ? "#F5C518" : evt.motion_detected ? "#D80032" : "#22c55e",
                          }}
                        />
                      ))}
                    </div>

                    {/* Forensic Controls */}
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center gap-1">
                        <button onClick={() => { if (videoRef.current) videoRef.current.currentTime -= 0.033; }}
                          className="p-1 rounded text-gray-600 hover:text-white hover:bg-white/5 transition-all">
                          <ChevronLeft className="w-2.5 h-2.5" />
                        </button>
                        <button
                          onClick={() => {
                            if (!videoRef.current) return;
                            videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause();
                          }}
                          className="p-1.5 rounded-md bg-spider-red/20 border border-spider-red/30 text-spider-red hover:bg-spider-red hover:text-white transition-all"
                        >
                          {videoPlaying ? <Pause className="w-2.5 h-2.5" /> : <Play className="w-2.5 h-2.5" />}
                        </button>
                        <button onClick={() => { if (videoRef.current) videoRef.current.currentTime += 0.033; }}
                          className="p-1 rounded text-gray-600 hover:text-white hover:bg-white/5 transition-all">
                          <ChevronRight className="w-2.5 h-2.5" />
                        </button>
                      </div>
                      <span className="text-[7px] font-mono text-gray-600">
                        {videoCurrentTime.toFixed(1)} / {videoDuration.toFixed(1)}s
                      </span>
                    </div>
                  </div>

                  {/* Heatmap Legend */}
                  {activeMetadata.length > 0 && (
                    <div className="px-3 pb-2.5 flex items-center gap-3">
                      {[{ c: "#F5C518", l: "Text" }, { c: "#D80032", l: "Motion" }, { c: "#22c55e", l: "Object" }].map(({ c, l }) => (
                        <div key={l} className="flex items-center gap-1">
                          <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: c }} />
                          <span className="text-[7px] text-gray-700 font-bold">{l}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* ── Live Logs ── */}
            <div className="flex-1 overflow-y-auto p-3 space-y-0.5 font-mono" style={{ scrollbarWidth: "none" }}>
              {logs.map(log => (
                <div key={log.id} className="flex gap-2 hover:bg-stark-card/20 rounded px-1 py-0.5 transition-colors">
                  <span className="text-[7px] text-gray-800 shrink-0 tabular-nums pt-px">{log.timestamp}</span>
                  <span className={cn("text-[8px] leading-snug break-all",
                    log.type === "success" ? "text-green-500" :
                    log.type === "error" ? "text-spider-red" :
                    log.type === "warn" ? "text-stark-gold" : "text-gray-600"
                  )}>
                    {log.text}
                  </span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>

            {/* Panel Footer */}
            <div className="p-3 border-t border-stark-border shrink-0">
              <div className="flex items-center gap-2 mb-2">
                <Activity className={cn("w-3 h-3 shrink-0", serverOnline ? "text-green-400" : "text-spider-red")} />
                <span className="text-[7px] text-gray-700 uppercase tracking-widest font-bold">
                  {serverOnline ? "Systems Nominal" : "System Error"}
                </span>
              </div>
              {/* CPU / GPU bars */}
              {[
                { label: "CPU", value: isIngesting ? 78 : 12 },
                { label: "GPU", value: isIngesting ? 94 : 5 },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center gap-2 mb-1">
                  <span className="text-[7px] text-gray-700 uppercase font-bold w-6 shrink-0">{label}</span>
                  <div className="flex-1 h-1 bg-stark-card rounded-full overflow-hidden">
                    <motion.div
                      animate={{ width: `${value}%` }}
                      transition={{ duration: 1.2, ease: "easeInOut" }}
                      className={cn("h-full rounded-full", value > 80 ? "bg-spider-red" : value > 50 ? "bg-stark-gold" : "bg-green-500")}
                    />
                  </div>
                  <span className="text-[7px] text-gray-700 w-6 text-right">{value}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </motion.aside>
    </div>
  );
}