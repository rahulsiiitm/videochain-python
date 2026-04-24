"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Send, Activity, Shield, Crosshair, FileText, Plus, Search, Play, Clock, CheckCircle2, User } from "lucide-react";
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

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [telemetryOpen, setTelemetryOpen] = useState(false);

  const [messages, setMessages] = useState<Message[]>([]);
  const [videoPath, setVideoPath] = useState("");
  const [query, setQuery] = useState("");
  const [serverOnline, setServerOnline] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [liveStatus, setLiveStatus] = useState("Idle");
  const [hardwareStats, setHardwareStats] = useState({ cpu: 0, gpu: 0, vram: 0 });
  const [activeVideoPath, setActiveVideoPath] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState("");
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
  const [settingsOpen, setSettingsOpen] = useState(false);
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
          if (status === "Idle") { pushNotification("Analysis Ready."); addLog("Ingest complete.", "success"); setTimeout(() => queryInputRef.current?.focus(), 200); }
          else addLog("Ingest failed.", "error");
        }
      } catch {}
    }, 1500);
  }, [addLog]);

  const loadSession = useCallback(async (sessionId: string) => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);
    setActiveSessionId(sessionId);
    setSidebarOpen(false);
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
      if (!res.ok) return;
      const data = await res.json();
      setMessages(data.messages ?? []);
      if (data.video_id) {
        setActiveVideoPath(data.video_path || data.video_id);
        const sRes = await fetch(`${API_BASE}/api/sessions/${sessionId}/status`);
        if (sRes.ok) {
          const sData = await sRes.json();
          const status = sData.status || "Idle";
          setLiveStatus(status);
          if (status === "Idle" || status === "Error") { setSessionState("ready"); setIsIngesting(false); }
          else { setSessionState("ingesting"); setIsIngesting(true); startIngestPoll(sessionId); }
        } else { setSessionState("ready"); }
        const mRes = await fetch(`${API_BASE}/api/knowledge/${data.video_id}`);
        if (mRes.ok) { const mData = await mRes.json(); setActiveMetadata(mData.timeline || []); }
      } else {
        setActiveVideoPath(null); setActiveMetadata([]); setSessionState("awaiting_video");
      }
    } catch { addLog("Failed to load session.", "error"); }
  }, [addLog, startIngestPoll]);

  const createNewSession = async () => {
    if (ingestPollRef.current) clearInterval(ingestPollRef.current);
    setActiveSessionId("pending_insight");
    setMessages([]);
    setActiveVideoPath(null);
    setActiveMetadata([]);
    setVideoPath("");
    setSessionTitle("");
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
        setActiveSessionId(null); setMessages([]); setActiveVideoPath(null); 
        setActiveMetadata([]); setSessionState("no_session"); setIsIngesting(false); 
      }
      pushNotification("Session Erased.");
    } catch { addLog("Deletion failed.", "error"); }
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
    addLog(`Loading: ${videoPath.split(/[/\\]/).pop()}`, "info");
    try {
      if (sessionId === "pending_insight") {
        const sRes = await fetch(`${API_BASE}/api/sessions`, { 
          method: "POST", headers: { "Content-Type": "application/json" }, 
          body: JSON.stringify({ title: sessionTitle.trim() || "Untitled Session" }) 
        });
        if (sRes.ok) {
          const sData = await sRes.json();
          sessionId = sData.id;
          setActiveSessionId(sessionId);
          setSessions(prev => [{ ...sData, message_count: 0 }, ...prev]);
        } else { throw new Error("Session init failed"); }
      }
      const res = await fetch(`${API_BASE}/api/ingest`, { 
        method: "POST", headers: { "Content-Type": "application/json" }, 
        body: JSON.stringify({ video_source: videoPath, session_id: sessionId }) 
      });
      const data = await res.json();
      if (res.ok) {
        setActiveVideoPath(data.video_path || videoPath);
        setVideoPath("");
        setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, video_id: data.video_id } : s));
        startIngestPoll(sessionId);
      } else { addLog(data.detail || "Analysis rejected.", "error"); setIsIngesting(false); setSessionState("awaiting_video"); }
    } catch (err) { addLog("Analysis failed.", "error"); setIsIngesting(false); setSessionState("awaiting_video"); }
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
    } catch { addLog("Uplink failed.", "error"); }
    finally { setIsQuerying(false); setTimeout(() => queryInputRef.current?.focus(), 100); }
  };

  const exportInsightReport = () => {
    if (!activeSessionId) return;
    const body = messages.map(m => `### ${m.sender.toUpperCase()} [${m.timestamp}]\n${m.text}`).join("\n\n");
    const blob = new Blob([`# Video Insights\n\n${body}`], { type: "text/markdown" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `Insights_${activeSessionId.slice(0, 8)}.md`; a.click();
  };

  const jumpToContext = (ts: string) => {
    if (!videoRef.current) return;
    const match = ts.match(/\[([\d.]+)s\]/);
    if (match) { videoRef.current.currentTime = parseFloat(match[1]); videoRef.current.play(); }
  };

  const copyMessage = (t: string) => {
    navigator.clipboard.writeText(t);
    pushNotification("Copied to clipboard.");
  };

  const startRename = (s: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingId(s.id);
    setRenameValue(s.title);
  };

  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);
  useEffect(() => { if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: "smooth" }); }, [logs]);

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
    serverOnline, isIngesting, hardwareStats,
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden relative">
      
      <Sidebar
        sessions={sessions} activeSessionId={activeSessionId} sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed} loadSession={loadSession} createSession={createNewSession}
        deleteSession={deleteSession} startRename={startRename} renamingId={renamingId}
        renameValue={renameValue} setRenameValue={setRenameValue} commitRename={commitRename}
        renameInputRef={renameInputRef}
      />

      <main className="flex-1 flex flex-col min-w-0 bg-background relative">
        <IngestBar
          sessionState={sessionState} activeSession={activeSession} videoPath={videoPath}
          setVideoPath={setVideoPath} handleIngest={handleIngest} isIngesting={isIngesting}
          serverOnline={serverOnline} exportInsightReport={exportInsightReport} liveStatus={liveStatus}
          onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
          onSettingsClick={() => setSettingsOpen(true)}
          onToggleTelemetry={() => {}}
        />

        <div className="flex-1 flex overflow-hidden p-4 gap-4">
          <AnimatePresence mode="wait">
            {sessionState === "no_session" && (
              <motion.div key="landing" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="flex-1 flex items-center justify-center">
                <div className="max-w-md w-full panel p-10 text-center">
                   <div className="w-16 h-16 bg-white rounded flex items-center justify-center mx-auto mb-6 shadow-xl">
                      <Shield className="w-8 h-8 text-black" />
                   </div>
                   <h1 className="text-2xl font-bold mb-3 tracking-tighter uppercase">Hello, I'm IRIS</h1>
                   <p className="text-muted-foreground text-sm mb-8 leading-relaxed font-medium">
                      Your friendly neighborhood assistant. Just give me a video, and I'll help you explore its story.
                   </p>
                   
                   <div className="space-y-4">
                      <div className="relative group">
                         <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-white transition-colors" />
                         <input
                           className="w-full bg-black border border-[#1a1a1a] rounded px-11 py-3 text-sm focus:outline-none focus:border-white transition-all font-medium"
                           placeholder="Enter video path (e.g. C:\Videos\clip.mp4)"
                           value={videoPath} onChange={e => setVideoPath(e.target.value)}
                         />
                      </div>
                      <button onClick={handleIngest} disabled={!videoPath || isIngesting}
                        className="btn-primary w-full h-12 flex items-center justify-center gap-2 disabled:opacity-30">
                        {isIngesting ? <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" /> : <Play className="w-4 h-4" />}
                        Explore Video
                      </button>
                   </div>
                   
                   <div className="mt-10 grid grid-cols-2 gap-4">
                      <div className="p-4 rounded bg-[#0c0c0c] border border-[#1a1a1a] text-left">
                         <span className="text-[10px] font-bold text-white uppercase block mb-1">Summarize</span>
                         <span className="text-[9px] text-muted-foreground font-medium uppercase opacity-50">Friendly Overviews</span>
                      </div>
                      <div className="p-4 rounded bg-[#0c0c0c] border border-[#1a1a1a] text-left">
                         <span className="text-[10px] font-bold text-white uppercase block mb-1">Explain</span>
                         <span className="text-[9px] text-muted-foreground font-medium uppercase opacity-50">Detailed Insights</span>
                      </div>
                   </div>
                </div>
              </motion.div>
            )}

            {sessionState === "awaiting_video" && (
              <motion.div key="new-session" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="flex-1 flex items-center justify-center">
                <div className="w-full max-w-lg panel p-10 bg-[#080808] border border-[#1a1a1a]">
                  <div className="flex items-center gap-5 mb-10">
                    <div className="w-12 h-12 rounded bg-[#111] border border-[#222] flex items-center justify-center">
                      <Plus className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white uppercase tracking-tight">New Session</h2>
                      <p className="text-xs text-muted-foreground font-medium">Share a video with me to get started.</p>
                    </div>
                  </div>
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground opacity-50">Session Title</label>
                      <input className="w-full bg-black border border-[#1a1a1a] focus:border-white rounded px-4 py-2.5 text-[13px] text-white focus:outline-none transition-all font-medium"
                        placeholder="e.g., Weekend Walk" value={sessionTitle} onChange={e => setSessionTitle(e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground opacity-50">Video Path</label>
                      <input autoFocus className="w-full bg-black border border-[#1a1a1a] focus:border-white rounded px-4 py-2.5 text-[13px] font-mono text-white focus:outline-none transition-all"
                        placeholder="C:\Users\You\Videos\clip.mp4" value={videoPath} onChange={e => setVideoPath(e.target.value)} onKeyDown={e => e.key === "Enter" && handleIngest()} />
                    </div>
                    <button onClick={handleIngest} disabled={!videoPath.trim()}
                      className={cn("w-full py-3 rounded font-bold text-[11px] uppercase tracking-widest transition-all",
                        videoPath.trim() ? "bg-white text-black" : "bg-[#111] text-muted-foreground cursor-not-allowed border border-[#222]")}>
                      Explore Video
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {sessionState === "ingesting" && (
              <motion.div key="ingesting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 flex items-center justify-center">
                <div className="w-full max-w-md panel p-12 text-center bg-[#080808]">
                  <div className="mb-10">
                    <Activity className="w-12 h-12 text-white mx-auto animate-pulse" />
                  </div>
                  <h2 className="text-lg font-bold text-white mb-2 uppercase tracking-widest">Exploring Memory</h2>
                  <p className="text-xs text-muted-foreground mb-8 font-medium">Looking through the video for you...</p>
                  
                  <div className="bg-[#111] border border-[#1a1a1a] rounded p-4 mb-10 text-left">
                    <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-50">Current Step</p>
                    <p className="text-xs font-mono font-bold text-white truncate">{liveStatus || "Starting up..."}</p>
                  </div>

                  <div className="space-y-4">
                    {[{ label: "CPU", value: hardwareStats.cpu }, { label: "GPU", value: hardwareStats.gpu }, { label: "MEM", value: hardwareStats.vram }].map(({ label, value }) => (
                      <div key={label} className="flex items-center gap-4">
                        <span className="text-[9px] font-bold text-muted-foreground w-8">{label}</span>
                        <div className="flex-1 h-1 bg-[#1a1a1a] rounded-full overflow-hidden">
                          <motion.div animate={{ width: `${value}%` }} className="h-full bg-white opacity-40" />
                        </div>
                        <span className="text-[9px] font-mono font-bold text-white/20 w-10">{value}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {sessionState === "ready" && (
              <motion.div key="workspace" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex-1 flex gap-4 overflow-hidden">
                
                <div className="w-[60%] flex flex-col gap-4 overflow-hidden">
                   <div className="flex-1 panel overflow-hidden bg-black border border-[#1a1a1a]">
                      <TelemetryPanel {...telemetryProps} layout="workstation" />
                   </div>
                </div>

                <div className="w-[40%] flex flex-col gap-4 overflow-hidden">
                   <div className="flex-1 panel overflow-hidden flex flex-col bg-[#080808] border border-[#1a1a1a] relative">
                      <div className="px-6 py-4 border-b border-[#1a1a1a] flex items-center justify-between bg-[#080808]">
                         <div className="flex items-center gap-2">
                            <Shield className="w-3.5 h-3.5 text-white" />
                            <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Assistant Hub</span>
                         </div>
                         <button onClick={exportInsightReport} className="text-[10px] font-bold text-muted-foreground hover:text-white transition-colors uppercase tracking-widest opacity-60">Save Notes</button>
                      </div>
                      
                      <ChatCanvas
                        messages={messages} isQuerying={isQuerying} scrollRef={scrollRef}
                        jumpToContext={jumpToContext} copyMessage={copyMessage}
                      />
                      
                      <div className="p-6 border-t border-[#1a1a1a] bg-black">
                        <form onSubmit={handleQuery} className="flex items-center gap-2 bg-[#0c0c0e] border border-[#1a1a1a] rounded px-3 py-1.5 focus-within:border-white transition-all">
                          <input ref={queryInputRef} className="flex-1 bg-transparent py-2 text-[13px] text-white placeholder:text-zinc-700 focus:outline-none min-w-0 font-medium"
                            placeholder="Ask me anything about the video..." value={query} onChange={e => setQuery(e.target.value)} disabled={isQuerying} />
                          <button type="submit" disabled={isQuerying || !query.trim()}
                            className={cn("p-2 rounded transition-all",
                              query.trim() && !isQuerying ? "text-white" : "text-muted-foreground/10 cursor-not-allowed")}>
                            {isQuerying ? <Activity className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                          </button>
                        </form>
                        <p className="text-[9px] text-center mt-4 text-muted-foreground uppercase tracking-[0.2em] opacity-30 font-bold">
                           Your Friendly Neighborhood Assistant
                        </p>
                      </div>
                   </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3">
        <AnimatePresence>
          {notifications.map(n => (
            <motion.div key={n.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
              className="bg-[#111] border border-[#222] px-4 py-2.5 rounded text-xs font-bold text-white shadow-2xl flex items-center gap-3">
              <div className="w-1 h-1 rounded-full bg-white animate-pulse" />
              {n.msg}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {deleteModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/90 backdrop-blur-sm">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm panel bg-[#080808] border border-[#1a1a1a] p-8 text-center">
              <h2 className="text-xl font-bold text-white mb-2 uppercase tracking-tighter">Erase Memory?</h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-8 font-medium">This will remove all insights for <span className="text-white">"{sessionToDelete?.title}"</span>. Are you sure?</p>
              <div className="flex gap-3">
                <button onClick={() => setDeleteModalOpen(false)} className="flex-1 btn-secondary">Wait, No</button>
                <button onClick={confirmDelete} className="flex-1 bg-white text-black py-2 rounded text-xs font-bold uppercase tracking-widest hover:bg-zinc-200 transition-all">Yes, Erase</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {settingsOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/90 backdrop-blur-sm">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}
              className="relative w-full max-w-sm panel bg-[#080808] border border-[#1a1a1a] p-8">
              <h2 className="text-xl font-bold text-white mb-2 uppercase tracking-tighter">Settings</h2>
              <p className="text-xs text-muted-foreground leading-relaxed mb-8 font-medium">Assistant preferences and local server configuration.</p>
              
              <div className="space-y-4 mb-8">
                 <div className="flex items-center justify-between p-3 rounded bg-black border border-[#1a1a1a]">
                    <span className="text-xs font-bold text-white uppercase tracking-widest">Noir Grain</span>
                    <div className="w-10 h-5 bg-white rounded-full flex items-center px-1">
                       <div className="w-3 h-3 bg-black rounded-full" />
                    </div>
                 </div>
                 <div className="flex items-center justify-between p-3 rounded bg-black border border-[#1a1a1a]">
                    <span className="text-xs font-bold text-white uppercase tracking-widest">Auto-Scroll</span>
                    <div className="w-10 h-5 bg-white rounded-full flex items-center justify-end px-1">
                       <div className="w-3 h-3 bg-black rounded-full" />
                    </div>
                 </div>
              </div>

              <button onClick={() => setSettingsOpen(false)} className="w-full btn-primary">Done</button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}