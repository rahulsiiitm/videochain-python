"use client";

import React from "react";
import { Download, Activity, ShieldCheck, Loader2, PanelLeft, PanelRight, Wifi, WifiOff } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "./utils";

type SessionState = "no_session" | "awaiting_video" | "ingesting" | "ready";

interface IngestBarProps {
  sessionState: SessionState;
  activeSession: any;
  videoPath: string;
  setVideoPath: (path: string) => void;
  handleIngest: () => void;
  isIngesting: boolean;
  serverOnline: boolean;
  exportInsightReport: () => void;
  liveStatus: string;
  onToggleSidebar: () => void;
  onToggleTelemetry: () => void;
}

export function IngestBar({
  sessionState, activeSession, videoPath, setVideoPath, handleIngest,
  isIngesting, serverOnline, exportInsightReport, liveStatus,
  onToggleSidebar, onToggleTelemetry,
}: IngestBarProps) {
  return (
    <header className="h-14 border-b border-sp-border bg-sp-surface/80 backdrop-blur-md flex items-center px-3 sm:px-4 gap-2 sm:gap-3 shrink-0 z-20">

      {/* Tablet-only: sidebar toggle */}
      <button onClick={onToggleSidebar}
        className="p-2 rounded-lg text-sp-muted hover:text-white hover:bg-white/5 transition-all lg:hidden shrink-0">
        <PanelLeft className="w-4 h-4" />
      </button>

      {/* Session name */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-sp-red" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-white/60 hidden sm:block">
          {activeSession ? activeSession.title?.slice(0, 20) : "No Session"}
        </span>
      </div>

      <div className="w-px h-5 bg-sp-border hidden sm:block shrink-0" />

      {/* Status pill */}
      <div className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          {sessionState === "ingesting" && (
            <motion.div key="ingesting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 min-w-0">
              <Loader2 className="w-3 h-3 text-sp-red animate-spin shrink-0" />
              <motion.span key={liveStatus} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="text-[9px] font-mono text-white/50 truncate">
                {liveStatus === "Idle" ? "Finalizing..." : liveStatus}
              </motion.span>
            </motion.div>
          )}
          {sessionState === "ready" && (
            <motion.div key="ready" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 min-w-0">
              <ShieldCheck className="w-3 h-3 text-green-500 shrink-0" />
              <span className="text-[9px] font-mono text-white/40 truncate">{activeSession?.video_id}</span>
            </motion.div>
          )}
          {(sessionState === "awaiting_video" || sessionState === "no_session") && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="hidden sm:flex items-center gap-2">
              <Activity className="w-3 h-3 text-sp-muted" />
              <span className="text-[9px] text-white/30 font-mono">
                {sessionState === "no_session" ? "Connect to IRIS" : "Ready for Visual Input"}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Server status */}
        <div className={cn("flex items-center gap-1.5 text-[8px] font-bold uppercase tracking-widest hidden sm:flex",
          serverOnline ? "text-green-500" : "text-sp-red")}>
          {serverOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
          <span className="hidden md:block">{serverOnline ? "Online" : "Offline"}</span>
        </div>

        <div className="w-px h-5 bg-sp-border hidden sm:block" />

        <button onClick={exportInsightReport} disabled={sessionState !== "ready"}
          className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-widest transition-all border",
            sessionState === "ready"
              ? "border-sp-blue/40 text-sp-blue-light hover:bg-sp-blue hover:text-white hover:border-sp-blue"
              : "border-sp-border/30 text-sp-muted/40 cursor-not-allowed")}>
          <Download className="w-3 h-3" />
          <span className="hidden sm:inline">Export</span>
        </button>

        {/* Tablet-only: telemetry toggle */}
        <button onClick={onToggleTelemetry}
          className="p-2 rounded-lg text-sp-muted hover:text-white hover:bg-white/5 transition-all lg:hidden">
          <PanelRight className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}