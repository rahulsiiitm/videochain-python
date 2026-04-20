"use client";

import React from "react";
import { 
  Terminal, Search, FileScan, Zap, ShieldCheck, Download, Activity, Loader2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "./utils";

interface IngestBarProps {
  activeSession: any;
  videoPath: string;
  setVideoPath: (path: string) => void;
  handleIngest: () => void;
  isIngesting: boolean;
  serverOnline: boolean;
  exportForensicReport: () => void;
  liveStatus: string;
}

export function IngestBar({
  activeSession,
  videoPath,
  setVideoPath,
  handleIngest,
  isIngesting,
  serverOnline,
  exportForensicReport,
  liveStatus
}: IngestBarProps) {
  
  const hasVideo = !!activeSession?.video_id;

  return (
    <header className="h-14 border-b border-stark-border bg-background/80 backdrop-blur-md flex items-center px-4 gap-4 shrink-0 relative z-20">
      <div className="flex items-center gap-4 flex-1">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stark-card/50 border border-stark-border">
          <Terminal className="w-3.5 h-3.5 text-spider-red" />
          <span className="text-[10px] font-black uppercase tracking-widest text-white">Investigation:</span>
          <span className="text-[10px] font-mono text-stark-gold uppercase">
            {activeSession ? (activeSession.title || activeSession.id.slice(0, 8)) : "N/A"}
          </span>
        </div>

        {/* ── Path Input / Proof of Presence ── */}
        <div className="flex-1 max-w-2xl relative">
          <AnimatePresence mode="wait">
            {!activeSession ? (
              <motion.div 
                key="no-session"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex items-center gap-2 px-4 py-1.5 rounded-lg border border-stark-border bg-stark-navy/30 text-gray-600 italic text-[10px]"
              >
                <Activity className="w-3 h-3 animate-pulse" />
                Initialize primary investigation to enable neural scanning...
              </motion.div>
            ) : hasVideo ? (
              <motion.div 
                key="has-video"
                initial={{ opacity: 0, y: 5 }} animate={{ opacity: 0.9, y: 0 }} exit={{ opacity: 0 }}
                className="flex items-center gap-3 px-4 py-1.5 rounded-lg border border-green-500/30 bg-green-500/5"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
                <span className="text-[9px] font-black uppercase tracking-widest text-green-400">Secure Evidence Locked:</span>
                <span className="text-[9px] font-mono text-gray-300 truncate max-w-sm">{activeSession.video_id}</span>
                <div className="flex items-center gap-1.5 ml-auto text-[7px] font-bold text-gray-500">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  ISOLATED_STREAM
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="ingest-input"
                initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <div className="relative flex-1">
                  <FileScan className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                  <input
                    className="w-full bg-stark-navy/40 border border-stark-border hover:border-spider-red/40 focus:border-spider-red rounded-lg pl-9 pr-4 py-1.5 text-[10px] font-bold text-white placeholder:text-gray-700 transition-all focus:outline-none focus:ring-1 focus:ring-spider-red/20 shadow-inner"
                    placeholder="ENTER ABSOLUTE PATH TO VIDEO EVIDENCE (MP4/MKV/AVI)..."
                    value={videoPath}
                    onChange={e => setVideoPath(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleIngest()}
                  />
                </div>
                <button
                  onClick={handleIngest}
                  disabled={isIngesting || !videoPath.trim()}
                  className={cn(
                    "px-4 py-1.5 rounded-lg font-black text-[9px] uppercase tracking-[0.2em] transition-all flex items-center gap-2",
                    isIngesting ? "bg-spider-red text-white cursor-wait" : 
                    "bg-stark-card border border-stark-border text-gray-500 hover:text-white hover:border-spider-red hover:bg-spider-red"
                  )}
                >
                  {isIngesting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                  {isIngesting ? "Scanning..." : "Sync Scan"}
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Intelligence Controls ── */}
      <div className="flex items-center gap-3">
        <div className="flex flex-col items-end px-2 border-r border-stark-border/30 mr-2">
          <span className={cn("text-[7px] font-black uppercase tracking-widest", serverOnline ? "text-green-500" : "text-spider-red")}>
            {serverOnline ? "Neural Uplink: Active" : "Neural Uplink: Lost"}
          </span>
          <span className="text-[6px] font-mono text-gray-700 mt-0.5">{liveStatus}</span>
        </div>
        
        <button 
          onClick={exportForensicReport}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stark-gold/10 border border-stark-gold/20 text-stark-gold hover:bg-stark-gold hover:text-black transition-all text-[9px] font-black uppercase tracking-widest"
        >
          <Download className="w-3 h-3" />
          Export Intel
        </button>
      </div>
    </header>
  );
}
