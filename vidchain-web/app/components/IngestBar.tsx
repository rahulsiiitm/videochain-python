"use client";

import React from "react";
import {
  Terminal, Download, Activity, ShieldCheck, Loader2
} from "lucide-react";
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
  exportForensicReport: () => void;
  liveStatus: string;
  sidebarCollapsed: boolean;
}

export function IngestBar({
  sessionState,
  activeSession,
  videoPath,
  setVideoPath,
  handleIngest,
  isIngesting,
  serverOnline,
  exportForensicReport,
  liveStatus,
  sidebarCollapsed,
}: IngestBarProps) {
  return (
    <header className="h-14 border-b border-stark-border bg-background/80 backdrop-blur-md flex items-center px-4 gap-4 shrink-0 relative z-20">

      {/* Session label */}
      <div className={cn("flex items-center gap-2 px-2 py-1 rounded-lg bg-stark-card/50 border border-stark-border shrink-0 max-sm:hidden", sidebarCollapsed && "md:px-3")}>
        <Terminal className="w-3 h-3 md:w-3.5 md:h-3.5 text-spider-red" />
        <span className="text-[8px] md:text-[10px] font-black uppercase tracking-widest text-white hidden sm:inline">Investigation:</span>
        <span className="text-[8px] md:text-[10px] font-mono text-stark-gold uppercase truncate max-w-[60px] md:max-w-none">
          {activeSession ? (activeSession.title || activeSession.id.slice(0, 8)) : "N/A"}
        </span>
      </div>

      {/* Status indicator */}
      <div className="flex-1 min-w-0">
        <AnimatePresence mode="wait">
          {sessionState === "no_session" && (
            <motion.div
              key="no-session"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 px-2 md:px-4 py-1.5 rounded-lg border border-stark-border bg-stark-navy/30 text-gray-600 italic text-[9px] md:text-[10px] truncate"
            >
              <Activity className="w-3 h-3 animate-pulse shrink-0" />
              <span className="truncate">No investigation active. Select or create one.</span>
            </motion.div>
          )}

          {sessionState === "awaiting_video" && (
            <motion.div
              key="awaiting-video"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 px-2 md:px-4 py-1.5 rounded-lg border border-stark-gold/20 bg-stark-gold/5 text-stark-gold italic text-[9px] md:text-[10px] truncate"
            >
              <Activity className="w-3 h-3 animate-pulse shrink-0" />
              <span className="truncate">Awaiting evidence — load video below.</span>
            </motion.div>
          )}

          {sessionState === "ingesting" && (
            <motion.div
              key="ingesting"
              initial={{ opacity: 0 }} animate={{ opacity: 0.9 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 md:gap-3 px-2 md:px-4 py-1.5 rounded-lg border border-spider-red/30 bg-spider-red/5 min-w-0"
            >
              <Loader2 className="w-3 h-3 md:w-3.5 md:h-3.5 text-spider-red animate-spin shrink-0" />
              <span className="text-[8px] md:text-[9px] font-black uppercase tracking-widest text-spider-red hidden lg:inline">Scanning:</span>
              <motion.span
                key={liveStatus}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[8px] md:text-[9px] font-mono text-gray-400 truncate flex-1"
              >
                {liveStatus === "Idle" ? "Finalizing..." : liveStatus}
              </motion.span>
              <div className="flex items-center gap-1.5 ml-auto text-[6px] md:text-[7px] font-bold text-gray-600 shrink-0">
                <div className="w-1 md:w-1.5 h-1 md:h-1.5 rounded-full bg-spider-red animate-pulse" />
                LIVE
              </div>
            </motion.div>
          )}

          {sessionState === "ready" && (
            <motion.div
              key="ready"
              initial={{ opacity: 0, y: 5 }} animate={{ opacity: 0.9, y: 0 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 md:gap-3 px-2 md:px-4 py-1.5 rounded-lg border border-green-500/30 bg-green-500/5 min-w-0"
            >
              <ShieldCheck className="w-3 h-3 md:w-3.5 md:h-3.5 text-green-500 shrink-0" />
              <span className="text-[8px] md:text-[9px] font-black uppercase tracking-widest text-green-400 hidden lg:inline">Locked:</span>
              <span className="text-[8px] md:text-[9px] font-mono text-gray-300 truncate flex-1">
                {activeSession?.video_id}
              </span>
              <div className="flex items-center gap-1.5 ml-auto text-[6px] md:text-[7px] font-bold text-gray-500 shrink-0">
                <div className="w-1 md:w-1.5 h-1 md:h-1.5 rounded-full bg-green-500" />
                SECURED
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2 md:gap-3 ml-auto shrink-0">
        <div className="hidden sm:flex flex-col items-end px-2 border-r border-stark-border/30">
          <span className={cn(
            "text-[6px] md:text-[7px] font-black uppercase tracking-widest",
            serverOnline ? "text-green-500" : "text-spider-red"
          )}>
            {serverOnline ? "Neural: Online" : "Neural: Lost"}
          </span>
          <span className="text-[5px] md:text-[6px] font-mono text-gray-700 mt-0.5 truncate max-w-[80px]">{liveStatus}</span>
        </div>

        <button
          onClick={exportForensicReport}
          disabled={sessionState !== "ready"}
          className={cn(
            "flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 rounded-lg border text-[8px] md:text-[9px] font-black uppercase tracking-widest transition-all",
            sessionState === "ready"
              ? "bg-stark-gold/10 border-stark-gold/20 text-stark-gold hover:bg-stark-gold hover:text-black shadow-[0_0_10px_rgba(245,197,24,0.1)]"
              : "bg-transparent border-stark-border/30 text-gray-700 cursor-not-allowed"
          )}
        >
          <Download className="w-2.5 h-2.5 md:w-3 md:h-3" />
          <span className="hidden xs:inline">Export Intel</span>
        </button>
      </div>
    </header>
  );
}