"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Send, Mic, MicOff, Activity, FolderOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Sidebar } from "./components/Sidebar";
import { IngestBar } from "./components/IngestBar";
import { ChatCanvas } from "./components/ChatCanvas";
import { TelemetryPanel } from "./components/TelemetryPanel";
import { cn } from "./components/utils";

const API_BASE = "http://localhost:8000";

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

// 3 distinct states for the session lifecycle
type SessionState = "no_session" | "awaiting_video" | "ingesting" | "ready";

type Log = {
  id: string;
  text: string;
  type: "info" | "success" | "error" | "warn";
  timestamp: string;
};

const timeStr = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const monoTime = () => new Date().toLocaleTimeString([], { hour12: false });

export default function VidChainDashboard() {
  const [mounted, setMounted] = useState(false);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>("no_session");

  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [telemetryCollapsed, setTelemetryCollapsed] = useState(false);
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

  // Polling ref to stop ingest poll when done
  const ingestPollRef = useRef<NodeJS.Timeout | null>(null);

  const activeSession = sessions.find(s => s.id === activeSessionId);

  const vlmActive = liveStatus.includes("LlavaNode");
  const ocrActive = liveStatus.includes("OcrNode");
  const audioActive = liveStatus.includes("WhisperNode");
  const graphActive = liveStatus.includes("GraphNode");
  const trackerActive = liveStatus.includes("TrackerNode");

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
        // Don't auto-load — let user pick
      }
    } catch { addLog("Uplink failed: Database offline.", "error"); }
  };

  const loadSession = useCallback(async (sessionId: string) => {
    // Stop any ongoing ingest poll for previous session
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);

    setActiveSessionId(sessionId);
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages ?? []);

        if (data.video_id) {
          // Resolve actual video source from knowledge base (Fixes 404 bug)
          const metaRes = await fetch(`${API_BASE}/api/knowledge/${data.video_id}`);
          if (metaRes.ok) {
            const metaData = await metaRes.json();
            // Use metadata.source (full path) for the media player
            setActiveVideoPath(metaData.metadata?.source || data.video_id);
            setActiveMetadata(metaData.timeline || []);
            setSessionState("ready");
          } else {
            setActiveVideoPath(data.video_id);
            setActiveMetadata([]);
            setSessionState("ready");
          }
        } else {
          // Session exists but no video yet — show video input
          setActiveVideoPath(null);
          setActiveMetadata([]);
          setSessionState("awaiting_video");
        }
        addLog(`Neural Link established: ${data.title}`, "info");
      }
    } catch { addLog("Failed to sync with session memory.", "error"); }
  }, [addLog]);

  // Poll until ingest is complete
  const startIngestPoll = useCallback((sessionId: string) => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);

    ingestPollRef.current = setInterval(async () => {
      try {
        const statusRes = await fetch(`${API_BASE}/api/sessions/${sessionId}/status`);
        if (!statusRes.ok) return;
        const statusData = await statusRes.json();
        const status = statusData.status || "Idle";
        setLiveStatus(status);

        if (statusData.telemetry) {
          setHardwareStats({
            cpu: statusData.telemetry.cpu_score || 0,
            gpu: statusData.telemetry.gpu_score || 0,
            vram: statusData.telemetry.vram_score || 0,
          });
        }

        if (status === "Idle" || status === "Error") {
          // Ingest done — reload session to get system message + unlock chat
          clearInterval(ingestPollRef.current!);
          ingestPollRef.current = null;
          setIsIngesting(false);

          const sessionRes = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
          if (sessionRes.ok) {
            const data = await sessionRes.json();
            setMessages(data.messages ?? []);
            setSessions(prev => prev.map(s =>
              s.id === sessionId ? { ...s, message_count: data.messages?.length ?? 0 } : s
            ));
          }

          setSessionState(status === "Error" ? "awaiting_video" : "ready");
          if (status === "Idle") {
            pushNotification("Evidence locked. Chat unlocked.");
            addLog("Ingest complete. Neural reasoning ready.", "success");
            setTimeout(() => queryInputRef.current?.focus(), 200);
          } else {
            addLog("Ingest failed. Try again.", "error");
          }
        }
      } catch {}
    }, 1500);
  }, [addLog]);

  // Create a new session and immediately put it in awaiting_video state
  const createSession = async () => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);
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
        setVideoPath("");
        setIsIngesting(false);
        setSessionState("awaiting_video"); // Always start at video input
        addLog("New investigation initialized. Awaiting evidence.", "success");
      }
    } catch { addLog("Could not create investigation.", "error"); }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (ingestPollRef.current && activeSessionId === sessionId) {
      clearInterval(ingestPollRef.current);
    }
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
        setMessages([]);
        setActiveVideoPath(null);
        setSessionState("no_session");
        setIsIngesting(false);
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
    } catch { addLog("Rename rejected.", "error"); }
    setRenamingId(null);
  };

  // Ingest: only callable when sessionState === "awaiting_video"
  const handleIngest = async () => {
    if (!videoPath.trim() || isIngesting || !activeSessionId) return;

    setIsIngesting(true);
    setSessionState("ingesting");
    addLog(`Neural Scan Initiated: ${videoPath.split(/[/\\]/).pop()}`, "info");

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_source: videoPath, session_id: activeSessionId }),
      });
      const data = await res.json();
      if (res.ok) {
        setActiveVideoPath(videoPath);
        setVideoPath("");
        // Bind video_id to session in local state immediately
        setSessions(prev => prev.map(s =>
          s.id === activeSessionId ? { ...s, video_id: data.video_id } : s
        ));
        addLog("Pipeline started. Monitoring nodes...", "info");
        startIngestPoll(activeSessionId);
      } else {
        addLog(data.detail || "Scan rejected.", "error");
        setIsIngesting(false);
        setSessionState("awaiting_video");
      }
    } catch {
      addLog("Hardware disconnect during scan.", "error");
      setIsIngesting(false);
      setSessionState("awaiting_video");
    }
  };
  
  const handleQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    // Hard gate: only allow queries when state is ready
    if (!query.trim() || isQuerying || !activeSessionId || sessionState !== "ready") return;

    const userMsg = query;
    setQuery("");
    setIsQuerying(true);

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
      const botMsg: Message = {
        id: `b-${Date.now()}`,
        sender: "baburao",
        text: data.response ?? "Data decompression failed.",
        timestamp: timeStr(),
        confidence: data.confidence,
        telemetry: data.telemetry,
      };
      setMessages(prev => [...prev, botMsg]);
      setSessions(prev => prev.map(s =>
        s.id === activeSessionId ? { ...s, message_count: s.message_count + 2 } : s
      ));
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

  // Background status poll (only for hardware stats when NOT ingesting)
  useEffect(() => {
    if (!activeSessionId || isIngesting) return;
    const pulse = setInterval(async () => {
      try {
        const statusRes = await fetch(`${API_BASE}/api/sessions/${activeSessionId}/status`);
        if (statusRes.ok) {
          const data = await statusRes.json();
          if (data.telemetry) {
            setHardwareStats({
              cpu: data.telemetry.cpu_score || 0,
              gpu: data.telemetry.gpu_score || 0,
              vram: data.telemetry.vram_score || 0,
            });
          }
        }
      } catch {}
    }, 3000);
    return () => clearInterval(pulse);
  }, [activeSessionId, isIngesting]);

  // Auto-scroll chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    setMounted(true);
    fetchSessions();
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => {
      clearInterval(interval);
      if (ingestPollRef.current) clearInterval(ingestPollRef.current);
    };
  }, []);

  if (!mounted) return <div className="h-screen bg-background" />;

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans selection:bg-spider-red/30">

      {/* Background Overlays */}
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
          sessionState={sessionState}
          activeSession={activeSession}
          videoPath={videoPath}
          setVideoPath={setVideoPath}
          handleIngest={handleIngest}
          isIngesting={isIngesting}
          serverOnline={serverOnline}
          exportForensicReport={exportForensicReport}
          liveStatus={liveStatus}
          sidebarCollapsed={sidebarCollapsed}
        />

        <div className="flex-1 relative flex flex-col min-h-0">
          <AnimatePresence mode="wait">

            {/* STATE 1: No session selected */}
            {sessionState === "no_session" && (
              <motion.div
                key="no-session"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center"
              >
                <img src="/logo.svg" alt="VidChain Logo" className="h-16 w-auto object-contain mb-8 opacity-30" />
                <h2 className="text-xl font-black uppercase tracking-[0.3em] mb-2 text-white">Neural Handshake Required</h2>
                <p className="text-[10px] text-gray-500 max-w-sm uppercase tracking-widest leading-loose">
                  Select an existing investigation from the sidebar or create a new one to begin.
                </p>
                <button
                  onClick={createSession}
                  className="mt-8 px-6 py-2 rounded-full bg-spider-red text-white text-[10px] font-black uppercase tracking-widest hover:scale-105 transition-all shadow-[0_0_20px_rgba(216,0,50,0.3)]"
                >
                  New Investigation
                </button>
              </motion.div>
            )}

            {/* STATE 2: Session open, waiting for video */}
            {sessionState === "awaiting_video" && (
              <motion.div
                key="awaiting-video"
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center"
              >
                <div className="w-full max-w-lg">
                  <img src="/logo.svg" alt="VidChain Logo" className="h-12 w-auto object-contain mb-8 mx-auto opacity-50" />
                  <h2 className="text-lg font-black uppercase tracking-[0.25em] mb-2 text-white">Load Evidence</h2>
                  <p className="text-[9px] text-gray-500 uppercase tracking-widest mb-8">
                    This investigation requires a video file before the neural chain can begin.
                  </p>

                  {/* Big video path input */}
                  <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-spider-red/30 to-stark-gold/10 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-700" />
                    <div className="relative flex flex-col gap-3 bg-stark-card/80 border border-stark-border rounded-2xl p-6">
                      <label className="text-[8px] font-black uppercase tracking-[0.3em] text-gray-500 text-left">
                        Absolute path to video evidence
                      </label>
                      <input
                        autoFocus
                        className="w-full bg-background/60 border border-stark-border hover:border-spider-red/40 focus:border-spider-red rounded-xl px-4 py-3 text-[11px] font-bold text-white placeholder:text-gray-700 transition-all focus:outline-none focus:ring-1 focus:ring-spider-red/20 outline-none"
                        placeholder="/path/to/evidence.mp4"
                        value={videoPath}
                        onChange={e => setVideoPath(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && handleIngest()}
                      />
                      <p className="text-[7px] text-gray-700 text-left">Supports MP4, MKV, AVI — local disk paths only</p>
                      <button
                        onClick={handleIngest}
                        disabled={!videoPath.trim()}
                        className={cn(
                          "w-full py-2.5 rounded-xl font-black text-[10px] uppercase tracking-[0.2em] transition-all",
                          videoPath.trim()
                            ? "bg-spider-red text-white hover:bg-red-600 shadow-[0_0_20px_rgba(216,0,50,0.3)] hover:scale-[1.01]"
                            : "bg-stark-navy border border-stark-border text-gray-700 cursor-not-allowed"
                        )}
                      >
                        Begin Neural Scan
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* STATE 3: Ingesting — show progress, block chat */}
            {sessionState === "ingesting" && (
              <motion.div
                key="ingesting"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center p-12 text-center"
              >
                <div className="w-full max-w-md">
                  {/* Animated scan ring */}
                  <div className="relative w-24 h-24 mx-auto mb-8">
                    <div className="absolute inset-0 rounded-full border-2 border-spider-red/20" />
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-0 rounded-full border-2 border-transparent border-t-spider-red"
                    />
                    <motion.div
                      animate={{ rotate: -360 }}
                      transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                      className="absolute inset-3 rounded-full border border-transparent border-t-stark-gold/50"
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <Activity className="w-6 h-6 text-spider-red animate-pulse" />
                    </div>
                  </div>

                  <h2 className="text-sm font-black uppercase tracking-[0.3em] text-white mb-2">Processing Evidence</h2>
                  <p className="text-[9px] text-gray-500 uppercase tracking-widest mb-6">
                    Neural pipeline active. Chat will unlock when complete.
                  </p>

                  {/* Live status */}
                  <div className="bg-stark-card/60 border border-stark-border rounded-xl px-5 py-3">
                    <motion.p
                      key={liveStatus}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-[9px] font-mono text-stark-gold"
                    >
                      {liveStatus === "Idle" ? "Finalizing..." : liveStatus}
                    </motion.p>
                  </div>

                  {/* Hardware bars */}
                  <div className="mt-4 space-y-2">
                    {[
                      { label: "CPU", value: hardwareStats.cpu, color: "#FDCB58" },
                      { label: "GPU", value: hardwareStats.gpu, color: "#D80032" },
                      { label: "VRAM", value: hardwareStats.vram, color: "#60a5fa" },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="flex items-center gap-3">
                        <span className="text-[7px] font-black text-gray-600 w-8 text-right">{label}</span>
                        <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                          <motion.div
                            animate={{ width: `${value}%` }}
                            className="h-full rounded-full"
                            style={{ backgroundColor: color }}
                          />
                        </div>
                        <span className="text-[7px] font-mono text-gray-600 w-7">{value}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* STATE 4: Ready — show chat */}
            {sessionState === "ready" && (
              <ChatCanvas
                key="chat"
                messages={messages}
                isQuerying={isQuerying}
                scrollRef={scrollRef}
                jumpToEvidence={jumpToEvidence}
                copyMessage={t => { navigator.clipboard.writeText(t); pushNotification("Copied"); }}
              />
            )}

          </AnimatePresence>

          {/* Input — only when ready */}
          {sessionState === "ready" && (
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
                    placeholder="DESCRIBE PATTERNS OR REQUEST SCAN ANALYSIS..."
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
        apiBase={API_BASE}
        collapsed={telemetryCollapsed}
        setCollapsed={setTelemetryCollapsed}
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