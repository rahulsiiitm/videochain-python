"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { 
  Send, Mic, MicOff, BrainCircuit, Activity 
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// Components
import { Sidebar } from "./components/Sidebar";
import { IngestBar } from "./components/IngestBar";
import { ChatCanvas } from "./components/ChatCanvas";
import { TelemetryPanel } from "./components/TelemetryPanel";
import { cn } from "./components/utils";

const API_BASE = "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────────
type Sender = "user" | "baburao" | "system";
type Message = {
  id: string;
  sender: Sender;
  text: string;
  timestamp: string;
  video_id?: string | null;
  confidence?: number;
  telemetry?: any;
};

type Session = {
  id: string;
  title: string;
  video_id?: string | null;
  message_count: number;
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
  nodeKey: string;
  status: "idle" | "running" | "done" | "error";
};

// ── Helpers ────────────────────────────────────────────────────────────────────
const timeStr = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const monoTime = () => new Date().toLocaleTimeString([], { hour12: false });

export default function VidChainDashboard() {
  const [mounted, setMounted] = useState(false);

  // States
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [videoPath, setVideoPath] = useState("");
  const [query, setQuery] = useState("");
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [serverOnline, setServerOnline] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [liveStatus, setLiveStatus] = useState<string>("Idle");
  const [hardwareStats, setHardwareStats] = useState({ cpu: 0, gpu: 0, vram: 0 });
  
  // Video player shared state
  const [activeVideoPath, setActiveVideoPath] = useState<string | null>(null);
  const [activeMetadata, setActiveMetadata] = useState<any[]>([]);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [videoDuration, setVideoDuration] = useState(0);
  const [videoCurrentTime, setVideoCurrentTime] = useState(0);
  
  const [notifications, setNotifications] = useState<{ id: string; msg: string }[]>([]);

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId);

  // Status flags
  const vlmActive = liveStatus.includes("LlavaNode");
  const ocrActive = liveStatus.includes("OcrNode");
  const audioActive = liveStatus.includes("WhisperNode");
  const graphActive = liveStatus.includes("GraphNode");
  const trackerActive = liveStatus.includes("TrackerNode");

  // ── Logging System ──
  const addLog = useCallback((text: string, type: Log["type"] = "info") => {
    setLogs(prev => [
      ...prev.slice(-99),
      { id: Math.random().toString(36).slice(2), text, type, timestamp: monoTime() },
    ]);
  }, []);

  const pushNotification = (msg: string) => {
    const id = Math.random().toString(36).slice(2);
    setNotifications(prev => [...prev.slice(-3), { id, msg }]);
    setTimeout(() => setNotifications(prev => prev.filter(n => n.id !== id)), 3500);
  };

  // ── API Core ──
  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      setServerOnline(res.ok);
    } catch { setServerOnline(false); }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions ?? []);
        if (data.sessions?.length > 0 && !activeSessionId) {
          loadSession(data.sessions[0].id);
        }
      }
    } catch { addLog("Uplink failed: Database offline.", "error"); }
  };

  const loadSession = useCallback(async (sessionId: string) => {
    setActiveSessionId(sessionId);
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages ?? []);
        if (data.video_id) {
          setActiveVideoPath(data.video_id);
          // Fetch heatmap metadata
          const metaRes = await fetch(`${API_BASE}/api/knowledge/${data.video_id}`);
          if (metaRes.ok) {
            const metaData = await metaRes.json();
            setActiveMetadata(metaData.timeline || []);
          }
        } else {
          setActiveVideoPath(null);
          setActiveMetadata([]);
        }
        addLog(`Neural Link established: ${data.title}`, "info");
      }
    } catch { addLog("Failed to sync with session memory.", "error"); }
  }, [addLog]);

  const createSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Investigation" }),
      });
      if (res.ok) {
        const session = await res.json();
        setSessions(prev => [{ ...session, message_count: 0 }, ...prev]);
        setActiveSessionId(session.id);
        setMessages([]);
        setActiveVideoPath(null);
        setActiveMetadata([]);
        addLog("New investigation initialized.", "success");
        setTimeout(() => queryInputRef.current?.focus(), 100);
      }
    } catch { addLog("Could not create investigation.", "error"); }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
        setActiveVideoPath(null);
      }
      addLog("Forensic trace purged.", "warn");
    } catch { addLog("Purge failed.", "error"); }
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
      addLog("Neural label updated.", "info");
    } catch { addLog("Rename cycle rejected.", "error"); }
    setRenamingId(null);
  };

  const handleIngest = async () => {
    if (!videoPath.trim() || isIngesting || !activeSessionId) return;
    setIsIngesting(true);
    addLog(`Neural Scan Initiated: ${videoPath.split(/[/\\]/).pop()}`, "info");

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_source: videoPath, session_id: activeSessionId }),
      });
      const data = await res.json();
      if (res.ok) {
        addLog("Multimodal pipeline operational.", "success");
        setActiveVideoPath(videoPath);
        setVideoPath("");
        // Refresh session after 8s or poll
        setTimeout(() => loadSession(activeSessionId), 8000);
      } else { addLog(data.detail || "Scan rejected.", "error"); }
    } catch { addLog("Hardware disconnect during scan.", "error"); }
    finally { setIsIngesting(false); }
  };

  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isQuerying || !activeSessionId) return;

    const userMsg = query;
    setQuery("");
    setIsQuerying(true);

    // Optimistic Update
    const tempId = `u-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: tempId, sender: "user", text: userMsg, timestamp: timeStr()
    }]);

    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query: userMsg, 
          session_id: activeSessionId,
          video_id: activeSession?.video_id 
        }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        id: `b-${Date.now()}`,
        sender: "baburao",
        text: data.response ?? "Data decompression failed.",
        timestamp: timeStr(),
        confidence: data.confidence,
        telemetry: data.telemetry
      }]);
    } catch { addLog("Reasoning Engine offline.", "error"); }
    finally { 
      setIsQuerying(false); 
      setTimeout(() => queryInputRef.current?.focus(), 100);
    }
  };

  const exportForensicReport = () => {
    if (!activeSessionId) return;
    const body = messages.map(m => `### ${m.sender.toUpperCase()} [${m.timestamp}]\n${m.text}`).join("\n\n");
    const blob = new Blob([`# VidChain Forensic Export\n\n${body}`], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `Evidence_Report_${activeSessionId.slice(0, 8)}.md`;
    a.click();
    addLog("Intelligence Report exported.", "success");
  };

  const jumpToEvidence = (ts: string) => {
    if (!videoRef.current) return;
    const match = ts.match(/\[([\d.]+)s\]/);
    if (match) {
      videoRef.current.currentTime = parseFloat(match[1]);
      videoRef.current.play();
      setVideoPlaying(true);
      addLog(`Seeking Anchor: ${match[1]}s`, "success");
    }
  };

  // ── Lifecycles ──
  useEffect(() => {
    setMounted(true);
    fetchSessions();
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const pulse = setInterval(async () => {
      try {
        const targetId = activeSessionId || "global";
        const statusRes = await fetch(`${API_BASE}/api/sessions/${targetId}/status`);
        if (statusRes.ok) {
          const data = await statusRes.json();
          if (activeSessionId) setLiveStatus(data.status || "Idle");
          if (data.telemetry) {
            setHardwareStats({
              cpu: data.telemetry.cpu_score || 0,
              gpu: data.telemetry.gpu_score || 0,
              vram: data.telemetry.vram_score || 0
            });
          }
        }
      } catch {}
    }, 2000);
    return () => clearInterval(pulse);
  }, [activeSessionId, isIngesting]);

  if (!mounted) return <div className="h-screen bg-background" />;

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-spider-red/30">
      
      {/* ── Background Overlays ── */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] z-[99]"
        style={{ backgroundImage: "repeating-linear-gradient(0deg,#fff 0 1px,transparent 1px 2px)" }} />
      <div className="fixed inset-0 pointer-events-none opacity-20"
        style={{ backgroundImage: "radial-gradient(circle at 50% 50%, #1A1F2B 0%, transparent 100%)" }} />

      <Sidebar 
        sessions={sessions}
        activeSessionId={activeSessionId}
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
        loadSession={loadSession}
        createSession={createSession}
        deleteSession={deleteSession}
        startRename={(s, e) => { e.stopPropagation(); setRenamingId(s.id); setRenameValue(s.title); }}
        renamingId={renamingId}
        renameValue={renameValue}
        setRenameValue={setRenameValue}
        commitRename={commitRename}
        renameInputRef={renameInputRef}
      />

      <main className="flex-1 flex flex-col relative min-w-0 bg-background/40">
        <IngestBar 
          activeSession={activeSession}
          videoPath={videoPath}
          setVideoPath={setVideoPath}
          handleIngest={handleIngest}
          isIngesting={isIngesting}
          serverOnline={serverOnline}
          exportForensicReport={exportForensicReport}
          liveStatus={liveStatus}
        />

        {/* ── Chat Canvas ── */}
        <div className="flex-1 relative flex flex-col min-h-0">
          <AnimatePresence>
            {!activeSessionId ? (
              <motion.div 
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center"
              >
                <img 
                  src="/logo.svg" 
                  alt="VidChain Logo" 
                  className="h-16 w-auto object-contain mb-8 animate-pulse" 
                />
                <h2 className="text-xl font-black uppercase tracking-[0.3em] mb-2 text-white">Neural Handshake Required</h2>
                <p className="text-[10px] text-gray-500 max-w-sm uppercase tracking-widest leading-loose">
                  Awaiting primary investigation initialization. Secure uplink will remain dormant until operative authorization.
                </p>
                <button 
                  onClick={createSession}
                  className="mt-8 px-6 py-2 rounded-full bg-spider-red text-white text-[10px] font-black uppercase tracking-widest hover:scale-105 transition-all shadow-[0_0_20px_rgba(216,0,50,0.3)]"
                >
                  Bridge Connection
                </button>
              </motion.div>
            ) : (
              <ChatCanvas 
                messages={messages}
                isQuerying={isQuerying}
                scrollRef={scrollRef}
                jumpToEvidence={jumpToEvidence}
                copyMessage={t => { navigator.clipboard.writeText(t); pushNotification("Copied"); }}
              />
            )}
          </AnimatePresence>

          {/* ── Input Zone ── */}
          {activeSessionId && (
            <div className="p-6 pt-2">
              <form 
                onSubmit={handleQuery}
                className="max-w-3xl mx-auto relative group"
              >
                <div className="absolute -inset-0.5 bg-gradient-to-r from-spider-red/20 to-stark-gold/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-1000" />
                <div className="relative flex items-center bg-stark-card/80 backdrop-blur-xl border border-stark-border rounded-xl p-1.5 pl-4 shadow-2xl">
                  <input
                    ref={queryInputRef}
                    className="flex-1 bg-transparent py-2 text-[11px] font-bold text-white placeholder:text-gray-700 focus:outline-none"
                    placeholder={activeSession?.video_id ? "DESCRIBE PATTERNS OR REQUEST SCAN ANALYSIS..." : "AWAITING EVIDENCE FOR CROSS-MODAL REASONING..."}
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    disabled={isQuerying}
                  />
                  <div className="flex items-center gap-1.5 pr-2">
                    <button
                      type="button"
                      onClick={() => setIsVoiceActive(!isVoiceActive)}
                      className={cn(
                        "p-2 rounded-lg transition-all",
                        isVoiceActive ? "bg-spider-red text-white" : "text-gray-600 hover:text-white"
                      )}
                    >
                      {isVoiceActive ? <Mic className="w-3.5 h-3.5" /> : <MicOff className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      type="submit"
                      disabled={isQuerying || !query.trim()}
                      className={cn(
                        "p-2 px-4 rounded-lg bg-spider-red text-white font-black text-[9px] uppercase tracking-widest flex items-center gap-2 transition-all",
                        (!query.trim() || isQuerying) ? "opacity-50 grayscale" : "hover:bg-red-600 hover:shadow-[0_0_15px_rgba(216,0,50,0.4)] hover:scale-105"
                      )}
                    >
                      {isQuerying ? <Activity className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                      {isQuerying ? "Processing" : "Analyze"}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          )}
        </div>
      </main>

      <TelemetryPanel 
        activeVideoPath={activeVideoPath}
        videoRef={videoRef}
        videoPlaying={videoPlaying}
        setVideoPlaying={setVideoPlaying}
        videoCurrentTime={videoCurrentTime}
        setVideoCurrentTime={setVideoCurrentTime}
        videoDuration={videoDuration}
        setVideoDuration={setVideoDuration}
        activeMetadata={activeMetadata}
        liveStatus={liveStatus}
        logs={logs}
        logsEndRef={logsEndRef}
        serverOnline={serverOnline}
        isIngesting={isIngesting}
        vlmActive={vlmActive}
        ocrActive={ocrActive}
        audioActive={audioActive}
        trackerActive={trackerActive}
        graphActive={graphActive}
        hardwareStats={hardwareStats}
      />
      
      {/* Notifications */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2">
        <AnimatePresence>
          {notifications.map(n => (
            <motion.div key={n.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="bg-stark-navy/90 border border-spider-red/30 px-4 py-2 rounded-full text-[9px] font-black uppercase tracking-widest text-spider-red shadow-2xl backdrop-blur-md"
            >
              {n.msg}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

    </div>
  );
}