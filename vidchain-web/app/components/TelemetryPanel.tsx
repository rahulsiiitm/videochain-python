"use client";

import React, { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Play, Pause, ChevronLeft, ChevronRight, Crosshair, Activity 
} from "lucide-react";
import { cn } from "./utils";

interface TelemetryPanelProps {
  activeVideoPath: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  videoPlaying: boolean;
  videoCurrentTime: number;
  videoDuration: number;
  setVideoPlaying: (playing: boolean) => void;
  setVideoCurrentTime: (time: number) => void;
  setVideoDuration: (duration: number) => void;
  activeMetadata: any[];
  liveStatus: string;
  logs: any[];
  logsEndRef: React.RefObject<HTMLDivElement | null>;
  serverOnline: boolean;
  isIngesting: boolean;
  vlmActive: boolean;
  ocrActive: boolean;
  audioActive: boolean;
  trackerActive: boolean;
  graphActive: boolean;
  hardwareStats: { cpu: number; gpu: number; vram: number };
  apiBase?: string;
  collapsed: boolean;
  setCollapsed: (val: boolean) => void;
}

export function TelemetryPanel({
  activeVideoPath,
  videoRef,
  videoPlaying,
  videoCurrentTime,
  videoDuration,
  setVideoPlaying,
  setVideoCurrentTime,
  setVideoDuration,
  activeMetadata,
  liveStatus,
  logs,
  logsEndRef,
  serverOnline,
  isIngesting,
  vlmActive,
  ocrActive,
  audioActive,
  trackerActive,
  graphActive,
  hardwareStats,
  apiBase = "",
  collapsed,
  setCollapsed
}: TelemetryPanelProps) {

  // Node indicator pill — driven by real liveStatus substrings from backend
  const NodePill = ({ label, active, color }: { label: string; active: boolean; color: string }) => (
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

  return (
    <motion.aside
      animate={{ width: collapsed ? 52 : 320 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative z-10 flex flex-col border-l border-stark-border bg-background shrink-0 overflow-hidden"
    >
      {/* HUD Header */}
      <div className={cn("p-4 border-b border-stark-border flex items-center justify-between gap-3 shrink-0 bg-black/20", collapsed && "flex-col justify-center px-1")}>
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className={cn("w-1.5 h-1.5 rounded-full", serverOnline ? "bg-green-500 animate-pulse" : "bg-red-500")} />
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-400">Neural Sync</span>
          </div>
        )}
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "p-1 rounded bg-stark-card border border-stark-border text-gray-700 hover:text-white hover:bg-spider-red transition-all cursor-pointer",
            collapsed && "mt-1"
          )}
        >
          {collapsed ? <ChevronLeft className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        </button>
      </div>

      {!collapsed ? (
        <AnimatePresence mode="wait">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex flex-col overflow-hidden"
          >
            {/* Status indicators */}
            <div className="p-4 space-y-3 border-b border-stark-border bg-black/10">
              <NodePill label="VLM Engine" active={vlmActive} color="#D80032" />
              <NodePill label="OCR Stream" active={ocrActive} color="#F5C518" />
              <NodePill label="Audio Sync" active={audioActive} color="#22c55e" />
              <NodePill label="LK Tracking" active={trackerActive} color="#60a5fa" />
              <NodePill label="Graph RAG" active={graphActive} color="#a855f7" />
            </div>

            {/* Evidence Player */}
            <div className="border-b border-stark-border bg-black/40">
              <div className="p-3">
                <div className="relative aspect-video rounded-lg overflow-hidden border border-stark-border bg-black shadow-2xl group">
                  {activeVideoPath ? (
                    <>
                      <video
                        ref={videoRef}
                        src={activeVideoPath ? (activeVideoPath.startsWith("http") ? activeVideoPath : `${apiBase}/media/${activeVideoPath}`) : ""}
                        className="w-full h-full object-contain"
                        onTimeUpdate={e => setVideoCurrentTime((e.target as HTMLVideoElement).currentTime)}
                        onDurationChange={e => setVideoDuration((e.target as HTMLVideoElement).duration)}
                        onPlay={() => setVideoPlaying(true)}
                        onPause={() => setVideoPlaying(false)}
                      />
                      <div className="absolute inset-0 pointer-events-none">
                        {(["top-0 left-0 border-t-2 border-l-2", "top-0 right-0 border-t-2 border-r-2", "bottom-0 left-0 border-b-2 border-l-2", "bottom-0 right-0 border-b-2 border-r-2"] as const).map((cls, i) => (
                          <div key={i} className={cn("absolute w-3 h-3 border-spider-red/40", cls)} />
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-800 p-6 text-center">
                      <Activity className="w-8 h-8 mb-3 opacity-20" />
                      <p className="text-[8px] font-black uppercase tracking-widest">Awaiting Neural Link</p>
                    </div>
                  )}
                </div>

                <div 
                  className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden cursor-pointer relative"
                  onClick={e => {
                    if (!videoRef.current || !videoDuration) return;
                    const rect = e.currentTarget.getBoundingClientRect();
                    videoRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * videoDuration;
                  }}
                >
                  <div className="absolute inset-0 bg-spider-red/40" style={{ width: `${videoDuration ? (videoCurrentTime / videoDuration) * 100 : 0}%` }} />
                </div>
              </div>
            </div>

            {/* Logs Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-[8px]" style={{ scrollbarWidth: "none" }}>
              <div className="pb-2 mb-2 border-b border-stark-border/30">
                <span className="text-gray-700 text-[7px] uppercase font-bold tracking-[0.2em]">Sensor Output</span>
              </div>
              {logs.slice(-20).map(log => (
                <div key={log.id} className="flex gap-2 group">
                  <span className="text-gray-800 shrink-0 tabular-nums">[{log.timestamp}]</span>
                  <span className={cn(
                    "leading-relaxed",
                    log.type === "error" ? "text-spider-red" : 
                    log.type === "success" ? "text-green-500" : "text-gray-500"
                  )}>
                    {log.text}
                  </span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>

            {/* Hardware Status */}
            <div className="p-4 border-t border-stark-border bg-black/20 space-y-2">
              {[
                { label: "GPU", value: hardwareStats.gpu, color: "bg-spider-red" },
                { label: "VRAM", value: hardwareStats.vram, color: "bg-blue-500" },
              ].map(({ label, value, color }) => (
                <div key={label} className="space-y-1">
                  <div className="flex justify-between items-end">
                    <span className="text-[7px] font-black text-gray-500 tracking-widest">{label}</span>
                    <span className="text-[8px] font-mono text-white">{value}%</span>
                  </div>
                  <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${value}%` }} className={cn("h-full rounded-full", color)} />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </AnimatePresence>
      ) : (
        <div className="flex-1 flex flex-col items-center py-4 gap-6 text-gray-800">
           <Activity className="w-5 h-5 opacity-20" />
           <div className="flex flex-col gap-4">
             <div className={cn("w-1.5 h-1.5 rounded-full", vlmActive ? "bg-spider-red" : "bg-gray-800")} />
             <div className={cn("w-1.5 h-1.5 rounded-full", ocrActive ? "bg-stark-gold" : "bg-gray-800")} />
             <div className={cn("w-1.5 h-1.5 rounded-full", audioActive ? "bg-green-500" : "bg-gray-800")} />
           </div>
        </div>
      )}
    </motion.aside>
  );
}
