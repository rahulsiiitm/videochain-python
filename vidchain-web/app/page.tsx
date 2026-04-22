"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Send, Activity, Mic, MicOff, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Sidebar } from "./components/Sidebar";
import { IngestBar } from "./components/IngestBar";
import { ChatCanvas } from "./components/ChatCanvas";
import { TelemetryPanel } from "./components/TelemetryPanel";
import { cn } from "./components/utils";

const API_BASE = "http://localhost:8000";

type Sender = "user" | "iris" | "system";
type Message = { id: string; sender: Sender; text: string; timestamp: string; video_id?: string | null; confidence?: number; telemetry?: any; };
type Session = { id: string; title: string; video_id?: string | null; message_count: number; };
type SessionState = "no_session" | "awaiting_video" | "ingesting" | "ready";
type Log = { id: string; text: string; type: "info" | "success" | "error" | "warn"; timestamp: string; };

const timeStr = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const monoTime = () => new Date().toLocaleTimeString([], { hour12: false });

export default function VidChainDashboard() {
  const [mounted, setMounted] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>("no_session");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // Desktop: inline collapsed. Tablet: overlay.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [telemetryOpen, setTelemetryOpen] = useState(false);

  const [messages, setMessages] = useState<Message[]>([]);
  const [videoPath, setVideoPath] = useState("");
  const [query, setQuery] = useState("");
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [liveStatus, setLiveStatus] = useState("Idle");
  const [hardwareStats, setHardwareStats] = useState({ cpu: 0, gpu: 0, vram: 0 });
  const [activeVideoPath, setActiveVideoPath] = useState<string | null>(null);
  const [activeMetadata, setActiveMetadata] = useState<any[]>([]);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [videoDuration, setVideoDuration] = useState(0);
  const [videoCurrentTime, setVideoCurrentTime] = useState(0);
  const [notifications, setNotifications] = useState<{ id: string; msg: string }[]>([]);

  const videoRef = useRef<HTMLVideoElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const ingestPollRef = useRef<NodeJS.Timeout | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<any>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const vlmActive = liveStatus.includes("LlavaNode");
  const ocrActive = liveStatus.includes("OcrNode");
  const audioActive = liveStatus.includes("WhisperNode");
  const graphActive = liveStatus.includes("GraphNode");
  const trackerActive = liveStatus.includes("TrackerNode");

  const addLog = useCallback((text: string, type: Log["type"] = "info") => {
    setLogs(prev => [...prev.slice(-99), { id: Math.random().toString(36).slice(2), text, type, timestamp: monoTime() }]);
  }, []);

  const pushNotification = (msg: string) => {
    const id = Math.random().toString(36).slice(2);
    setNotifications(prev => [...prev.slice(-3), { id, msg }]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 3500);
  };

  const checkHealth = async () => {
    try { const res = await fetch(`${API_BASE}/api/health`); setServerOnline(res.ok); }
    catch { setServerOnline(false); }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      if (res.ok) { const data = await res.json(); setSessions(data.sessions ?? []); }
    } catch { addLog("Uplink failed.", "error"); }
  };

  const startIngestPoll = useCallback((sessionId: string) => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);
    ingestPollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/status`);
        if (!res.ok) return;
        const data = await res.json();
        const status = data.status || "Idle";
        setLiveStatus(status);
        if (data.telemetry) setHardwareStats({ cpu: data.telemetry.cpu_score || 0, gpu: data.telemetry.gpu_score || 0, vram: data.telemetry.vram_score || 0 });
        if (status === "Idle" || status === "Error") {
          clearInterval(ingestPollRef.current!);
          ingestPollRef.current = null;
          setIsIngesting(false);
          const sRes = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
          if (sRes.ok) {
            const sData = await sRes.json();
            setMessages(sData.messages ?? []);
            setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, message_count: sData.messages?.length ?? 0 } : s));
          }
          setSessionState(status === "Error" ? "awaiting_video" : "ready");
          if (status === "Idle") { pushNotification("Chat unlocked."); addLog("Ingest complete.", "success"); setTimeout(() => queryInputRef.current?.focus(), 200); }
          else addLog("Ingest failed.", "error");
        }
      } catch {}
    }, 1500);
  }, [addLog]);

  const loadSession = useCallback(async (sessionId: string) => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);
    setActiveSessionId(sessionId);
    setSidebarOpen(false); // close overlay on tablet
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (!res.ok) return;
      const data = await res.json();
      setMessages(data.messages ?? []);
      if (data.video_id) {
        // Prefer the actual file path for playback, fall back to ID
        setActiveVideoPath(data.video_path || data.video_id);
        const sRes = await fetch(`${API_BASE}/api/sessions/${sessionId}/status`);
        if (sRes.ok) {
          const sData = await sRes.json();
          const status = sData.status || "Idle";
          setLiveStatus(status);
          if (status === "Idle" || status === "Error") { 
            setSessionState("ready"); 
            setIsIngesting(false); 
          }
          else { 
            setSessionState("ingesting"); 
            setIsIngesting(true); 
            startIngestPoll(sessionId); 
          }
        } else {
          setSessionState("ready");
        }
        const mRes = await fetch(`${API_BASE}/api/knowledge/${data.video_id}`);
        if (mRes.ok) { 
          const mData = await mRes.json(); 
          setActiveMetadata(mData.timeline || []); 
        }
      } else {
        setActiveVideoPath(null); 
        setActiveMetadata([]); 
        setSessionState("awaiting_video");
      }
    } catch { addLog("Failed to load session.", "error"); }
  }, [addLog, startIngestPoll]);

  const createSession = async () => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);
    // DEFERRED CREATION: Don't hit the API yet.
    // Set a "pending" ID so the UI knows we are starting a new discovery.
    setActiveSessionId("pending_insight");
    setMessages([]);
    setActiveVideoPath(null);
    setActiveMetadata([]);
    setVideoPath("");
    setIsIngesting(false);
    setSessionState("awaiting_video");
    setSidebarOpen(false);
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const session = sessions.find(s => s.id === sessionId);
    setSessionToDelete(session);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    const sessionId = sessionToDelete.id;
    setDeleteModalOpen(false);

    if (ingestPollRef.current && activeSessionId === sessionId) clearInterval(ingestPollRef.current);
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) { 
        setActiveSessionId(null); 
        setMessages([]); 
        setActiveVideoPath(null); 
        setActiveMetadata([]);
        setSessionState("no_session"); 
        setIsIngesting(false); 
      }
      pushNotification("Insight deleted.");
    } catch {
      addLog("Failed to delete session.", "error");
    }
  };

  const commitRename = async () => {
    if (!renamingId) return;
    try {
      await fetch(`${API_BASE}/api/sessions/${renamingId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: renameValue.trim() || "Untitled" }) });
      setSessions(prev => prev.map(s => s.id === renamingId ? { ...s, title: renameValue.trim() || "Untitled" } : s));
    } catch {}
    setRenamingId(null);
  };

  const handleIngest = async () => {
    if (!videoPath.trim() || isIngesting || !activeSessionId) return;
    
    let sessionId = activeSessionId;
    setIsIngesting(true);
    setSessionState("ingesting");

    addLog(`Preparing Insight: ${videoPath.split(/[/\\]/).pop()}`, "info");

    try {
      // If the session is still "pending", create it now!
      if (sessionId === "pending_insight") {
        const sRes = await fetch(`${API_BASE}/api/sessions`, { 
          method: "POST", 
          headers: { "Content-Type": "application/json" }, 
          body: JSON.stringify({ title: "New Insight Session" }) 
        });
        if (sRes.ok) {
          const sData = await sRes.json();
          sessionId = sData.id;
          setActiveSessionId(sessionId);
          setSessions(prev => [{ ...sData, message_count: 0 }, ...prev]);
        } else { throw new Error("Session init failed"); }
      }

      const res = await fetch(`${API_BASE}/api/ingest`, { 
        method: "POST", 
        headers: { "Content-Type": "application/json" }, 
        body: JSON.stringify({ video_source: videoPath, session_id: sessionId }) 
      });
      const data = await res.json();
      if (res.ok) {
        setActiveVideoPath(data.video_path || videoPath);
        setVideoPath("");
        setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, video_id: data.video_id } : s));
        startIngestPoll(sessionId);
      } else { 
        addLog(data.detail || "Analysis rejected.", "error"); 
        setIsIngesting(false); 
        setSessionState("awaiting_video"); 
      }
    } catch (err) { 
      addLog("Analysis interrupted.", "error"); 
      setIsIngesting(false); 
      setSessionState("awaiting_video"); 
    }
  };

  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isQuerying || !activeSessionId || sessionState !== "ready") return;
    const userMsg = query; setQuery(""); setIsQuerying(true);
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, sender: "user", text: userMsg, timestamp: timeStr() }]);
    try {
      const res = await fetch(`${API_BASE}/api/query`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: userMsg, session_id: activeSessionId, video_id: activeSession?.video_id }) });
      const data = await res.json();
      setMessages(prev => [...prev, { id: `b-${Date.now()}`, sender: "iris", text: data.response ?? "No response.", timestamp: timeStr(), confidence: data.confidence, telemetry: data.telemetry }]);
      setSessions(prev => prev.map(s => s.id === activeSessionId ? { ...s, message_count: s.message_count + 2 } : s));
    } catch { addLog("Reasoning engine offline.", "error"); }
    finally { setIsQuerying(false); setTimeout(() => queryInputRef.current?.focus(), 100); }
  };

  const exportInsightReport = () => {
    if (!activeSessionId) return;
    const body = messages.map(m => `### ${m.sender.toUpperCase()} [${m.timestamp}]\n${m.text}`).join("\n\n");
    const blob = new Blob([`# IRIS Insight Report\n\n${body}`], { type: "text/markdown" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `IRIS_Report_${activeSessionId.slice(0, 8)}.md`; a.click();
  };

  const jumpToContext = (ts: string) => {
    if (!videoRef.current) return;
    const match = ts.match(/\[([\d.]+)s\]/);
    if (match) {
      videoRef.current.currentTime = parseFloat(match[1]);
      videoRef.current.play();
      addLog(`Jumped to ${match[1]}s context`, "info");
    }
  };

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);

  useEffect(() => {
    if (!activeSessionId || isIngesting) return;
    const pulse = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sessions/${activeSessionId}/status`);
        if (res.ok) { const data = await res.json(); if (data.telemetry) setHardwareStats({ cpu: data.telemetry.cpu_score || 0, gpu: data.telemetry.gpu_score || 0, vram: data.telemetry.vram_score || 0 }); }
      } catch {}
    }, 3000);
    return () => clearInterval(pulse);
  }, [activeSessionId, isIngesting]);

  useEffect(() => {
    setMounted(true); fetchSessions(); checkHealth();
    const i = setInterval(checkHealth, 5000);
    return () => { clearInterval(i); if (ingestPollRef.current) clearInterval(ingestPollRef.current); };
  }, []);

  if (!mounted) return <div className="h-screen bg-background" />;

  const telemetryProps = {
    activeVideoPath, videoRef, videoPlaying, setVideoPlaying, videoCurrentTime, setVideoCurrentTime,
    videoDuration, setVideoDuration, activeMetadata, liveStatus, logs, logsEndRef,
    serverOnline, isIngesting, vlmActive, ocrActive, audioActive, trackerActive, graphActive, hardwareStats,
  };

  // Web pattern background for landing states
  const WebPattern = () => (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      <svg className="absolute inset-0 w-full h-full opacity-[0.04]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="web" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
            <line x1="40" y1="0" x2="40" y2="80" stroke="#E8192C" strokeWidth="0.5"/>
            <line x1="0" y1="40" x2="80" y2="40" stroke="#E8192C" strokeWidth="0.5"/>
            <line x1="0" y1="0" x2="80" y2="80" stroke="#E8192C" strokeWidth="0.3"/>
            <line x1="80" y1="0" x2="0" y2="80" stroke="#E8192C" strokeWidth="0.3"/>
            <circle cx="40" cy="40" r="15" fill="none" stroke="#E8192C" strokeWidth="0.3"/>
            <circle cx="40" cy="40" r="30" fill="none" stroke="#E8192C" strokeWidth="0.2"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#web)"/>
      </svg>
    </div>
  );

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans">

      {/* Tablet backdrops */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 bg-black/70 z-30 lg:hidden" />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {telemetryOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setTelemetryOpen(false)}
            className="fixed inset-0 bg-black/70 z-30 lg:hidden" />
        )}
      </AnimatePresence>

      {/* Sidebar — desktop */}
      <div className="hidden lg:flex shrink-0">
        <Sidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
          loadSession={loadSession}
          createSession={createSession}
          deleteSession={deleteSession}
          startRename={(s, e) => {
            e.stopPropagation();
            setRenamingId(s.id);
            setRenameValue(s.title);
          }}
          renamingId={renamingId}
          renameValue={renameValue}
          setRenameValue={setRenameValue}
          commitRename={commitRename}
          renameInputRef={renameInputRef}
        />
      </div>

      {/* Sidebar — tablet overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div initial={{ x: -260 }} animate={{ x: 0 }} exit={{ x: -260 }}
            transition={{ type: "tween", duration: 0.18 }}
            className="fixed left-0 top-0 h-full z-40 lg:hidden">
            <Sidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              sidebarCollapsed={false}
              setSidebarCollapsed={() => setSidebarOpen(false)}
              loadSession={loadSession}
              createSession={createSession}
              deleteSession={deleteSession}
              startRename={(s, e) => {
                e.stopPropagation();
                setRenamingId(s.id);
                setRenameValue(s.title);
              }}
              renamingId={renamingId}
              renameValue={renameValue}
              setRenameValue={setRenameValue}
              commitRename={commitRename}
              renameInputRef={renameInputRef}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main */}
      <main className="flex-1 flex flex-col relative min-w-0">
        <IngestBar
          sessionState={sessionState} activeSession={activeSession}
          videoPath={videoPath} setVideoPath={setVideoPath}
          handleIngest={handleIngest} isIngesting={isIngesting}
          serverOnline={serverOnline} exportInsightReport={exportInsightReport}
          liveStatus={liveStatus}
          onToggleSidebar={() => setSidebarOpen(v => !v)}
          onToggleTelemetry={() => setTelemetryOpen(v => !v)}
        />

        <div className="flex-1 relative flex flex-col min-h-0">
          <AnimatePresence mode="wait">

            {/* No session */}
            {sessionState === "no_session" && (
              <motion.div key="no-session" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center text-center p-8">
                <WebPattern />
                <div className="relative z-10 flex flex-col items-center">
                  <h1 className="text-2xl font-black uppercase tracking-[0.2em] text-white mb-1">I R I S</h1>
                  <p className="text-[9px] text-white/30 uppercase tracking-[0.3em] mb-8">Intelligent Video Assistant</p>
                  <button onClick={createSession}
                    className="px-8 py-3 rounded-full bg-sp-red text-white text-[11px] font-black uppercase tracking-widest hover:scale-105 hover:shadow-[0_0_30px_rgba(232,25,44,0.4)] transition-all">
                    Launch IRIS Suite
                  </button>
                </div>
              </motion.div>
            )}

            {/* Awaiting video */}
            {sessionState === "awaiting_video" && (
              <motion.div key="awaiting-video" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-6 overflow-y-auto">
                <WebPattern />
                <div className="relative z-10 w-full max-w-md">
                  <div className="mb-6 flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl overflow-hidden shadow-[0_0_30px_rgba(232,25,44,0.3)] border border-white/10">
                      <img src="/logo.png" alt="IRIS" className="w-full h-full object-cover" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full bg-sp-blue-light animate-pulse" />
                        <p className="text-[9px] font-bold uppercase tracking-[0.3em] text-white/40">Visual Context Required</p>
                      </div>
                      <h2 className="text-xl font-black uppercase tracking-[0.15em] text-white">Upload Video</h2>
                    </div>
                  </div>
                  <p className="text-[10px] text-white/30 mb-8">Connect a video source for IRIS to analyze.</p>

                  <div className="space-y-3">
                    <input autoFocus
                      className="w-full bg-sp-web border border-sp-border hover:border-sp-red/40 focus:border-sp-red rounded-xl px-4 py-3.5 text-[11px] font-mono text-white placeholder:text-white/20 transition-all focus:outline-none focus:ring-1 focus:ring-sp-red/20"
                      placeholder="/absolute/path/to/video.mp4"
                      value={videoPath} onChange={e => setVideoPath(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && handleIngest()} />
                    <p className="text-[7px] text-white/20">MP4 · MKV · AVI — local paths only</p>
                    <button onClick={handleIngest} disabled={!videoPath.trim()}
                      className={cn("w-full py-3 rounded-xl font-black text-[10px] uppercase tracking-[0.2em] transition-all",
                        videoPath.trim()
                          ? "bg-sp-red text-white hover:bg-red-600 shadow-[0_0_20px_rgba(232,25,44,0.25)] hover:shadow-[0_0_30px_rgba(232,25,44,0.4)]"
                          : "bg-sp-web border border-sp-border text-white/20 cursor-not-allowed")}>
                      Analyze Video Source
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Ingesting */}
            {sessionState === "ingesting" && (
              <motion.div key="ingesting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center">
                <WebPattern />
                <div className="relative z-10 w-full max-w-sm">
                  {/* Spinning web ring */}
                  <div className="relative w-24 h-24 mx-auto mb-8">
                    <svg className="absolute inset-0 w-full h-full opacity-10" viewBox="0 0 96 96">
                      <circle cx="48" cy="48" r="44" fill="none" stroke="#E8192C" strokeWidth="1"/>
                      <circle cx="48" cy="48" r="30" fill="none" stroke="#E8192C" strokeWidth="0.5"/>
                      <line x1="48" y1="4" x2="48" y2="92" stroke="#E8192C" strokeWidth="0.5"/>
                      <line x1="4" y1="48" x2="92" y2="48" stroke="#E8192C" strokeWidth="0.5"/>
                      <line x1="16" y1="16" x2="80" y2="80" stroke="#E8192C" strokeWidth="0.3"/>
                      <line x1="80" y1="16" x2="16" y2="80" stroke="#E8192C" strokeWidth="0.3"/>
                    </svg>
                    <motion.div animate={{ rotate: 360 }} transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-0 rounded-full border-2 border-transparent border-t-sp-red" />
                    <motion.div animate={{ rotate: -360 }} transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-4 rounded-full border border-transparent border-t-sp-blue-light/60" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-8 h-8 rounded-full bg-sp-red flex items-center justify-center">
                        <Activity className="w-4 h-4 text-white" />
                      </div>
                    </div>
                  </div>

                  <h2 className="text-sm font-black uppercase tracking-[0.25em] text-white mb-1">Optimizing Insights</h2>
                  <p className="text-[9px] text-white/30 uppercase tracking-widest mb-6">Chat available shortly</p>

                  <div className="bg-sp-web border border-sp-border rounded-xl px-4 py-3 mb-4 text-left">
                    <p className="text-[7px] font-bold uppercase tracking-widest text-white/30 mb-1">Active Node</p>
                    <motion.p key={liveStatus} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className="text-[9px] font-mono text-sp-red truncate">
                      {liveStatus === "Idle" ? "Finalizing..." : liveStatus || "Initializing..."}
                    </motion.p>
                  </div>

                  <div className="space-y-2">
                    {[{ label: "CPU", value: hardwareStats.cpu, color: "#F5C518" }, { label: "GPU", value: hardwareStats.gpu, color: "#E8192C" }, { label: "VRAM", value: hardwareStats.vram, color: "#2952C8" }].map(({ label, value, color }) => (
                      <div key={label} className="flex items-center gap-3">
                        <span className="text-[7px] font-bold text-white/30 w-8 text-right">{label}</span>
                        <div className="flex-1 h-0.5 bg-white/5 rounded-full overflow-hidden">
                          <motion.div animate={{ width: `${value}%` }} className="h-full rounded-full" style={{ backgroundColor: color }} />
                        </div>
                        <span className="text-[7px] font-mono text-white/30 w-7">{value}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Ready — chat */}
            {sessionState === "ready" && (
              <ChatCanvas key="chat" messages={messages} isQuerying={isQuerying}
                scrollRef={scrollRef} jumpToContext={jumpToContext}
                copyMessage={t => { navigator.clipboard.writeText(t); pushNotification("Copied"); }} />
            )}

          </AnimatePresence>

          {/* Input */}
          {sessionState === "ready" && (
            <div className="p-3 sm:p-5 shrink-0 border-t border-sp-border bg-sp-surface/50">
              <form onSubmit={handleQuery} className="max-w-2xl mx-auto flex items-center gap-2 bg-sp-web border border-sp-border rounded-xl px-3 sm:px-4 py-2 focus-within:border-sp-red/40 transition-all">
                <input ref={queryInputRef}
                  className="flex-1 bg-transparent py-1.5 text-[11px] font-medium text-white placeholder:text-white/20 focus:outline-none min-w-0"
                  placeholder="How can I help you understand this video?"
                  value={query} onChange={e => setQuery(e.target.value)} disabled={isQuerying} />
                <button type="button" onClick={() => setIsVoiceActive(!isVoiceActive)}
                  className={cn("p-1.5 rounded-lg transition-all hidden sm:flex shrink-0", isVoiceActive ? "text-sp-red" : "text-white/20 hover:text-white/60")}>
                  {isVoiceActive ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
                </button>
                <button type="submit" disabled={isQuerying || !query.trim()}
                  className={cn("shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all",
                    query.trim() && !isQuerying ? "bg-sp-red text-white hover:bg-red-600" : "bg-sp-border/30 text-white/20 cursor-not-allowed")}>
                  {isQuerying ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                </button>
              </form>
            </div>
          )}
        </div>
      </main>

      {/* Telemetry — desktop */}
      <div className="hidden lg:flex shrink-0">
        <TelemetryPanel {...telemetryProps} />
      </div>

      {/* Telemetry — tablet overlay */}
      <AnimatePresence>
        {telemetryOpen && (
          <motion.div initial={{ x: 290 }} animate={{ x: 0 }} exit={{ x: 290 }}
            transition={{ type: "tween", duration: 0.18 }}
            className="fixed right-0 top-0 h-full z-40 lg:hidden">
            <TelemetryPanel {...telemetryProps} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Notifications */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2">
        <AnimatePresence>
          {notifications.map(n => (
            <motion.div key={n.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="bg-sp-surface border border-sp-border px-4 py-2 rounded-full text-[9px] font-bold uppercase tracking-widest text-white/60 shadow-xl backdrop-blur-md">
              {n.msg}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Deletion Modal */}
      <AnimatePresence>
        {deleteModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setDeleteModalOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
            <motion.div initial={{ opacity: 0, scale: 0.95, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative w-full max-w-sm bg-sp-web border border-sp-border rounded-2xl p-6 shadow-2xl">
              <div className="w-12 h-12 rounded-full bg-sp-red/10 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-sp-red" />
              </div>
              <h2 className="text-lg font-black uppercase tracking-wider text-white mb-2">Purge Memory?</h2>
              <p className="text-[11px] text-white/40 leading-relaxed mb-6">
                You are about to permanently delete <span className="text-white">"{sessionToDelete?.title}"</span>. 
                This will wipe all visual context, knowledge graphs, and vector data associated with this session.
              </p>
              <div className="flex gap-3">
                <button onClick={() => setDeleteModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl bg-sp-surface border border-sp-border text-[10px] font-bold uppercase tracking-widest text-sp-muted hover:text-white transition-all">
                  Keep Session
                </button>
                <button onClick={confirmDelete}
                  className="flex-1 py-2.5 rounded-xl bg-sp-red text-white text-[10px] font-bold uppercase tracking-widest hover:bg-red-600 transition-all shadow-[0_0_20px_rgba(232,25,44,0.3)]">
                  Confirm Purge
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}