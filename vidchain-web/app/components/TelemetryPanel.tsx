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
  hardwareStats
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
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="w-80 border-l border-stark-border bg-background/80 backdrop-blur-xl flex flex-col shrink-0 overflow-hidden relative"
    >
      {/* ── Status HUD ── */}
      <div className="p-4 border-b border-stark-border bg-black/20">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className={cn("w-1.5 h-1.5 rounded-full", serverOnline ? "bg-green-500 animate-pulse" : "bg-red-500")} />
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-gray-400">Neural Sync</span>
          </div>
          <span className="text-[9px] font-mono text-stark-gold/80">{serverOnline ? "STARK_OS_v4" : "DISCONNECTED"}</span>
        </div>

        <div className="space-y-3">
          <NodePill label="VLM Engine" active={vlmActive} color="#D80032" />
          <NodePill label="OCR Stream" active={ocrActive} color="#F5C518" />
          <NodePill label="Audio Sync" active={audioActive} color="#22c55e" />
          <NodePill label="LK Tracking" active={trackerActive} color="#60a5fa" />
          <NodePill label="Graph RAG" active={graphActive} color="#a855f7" />
        </div>
      </div>

      {/* ── Evidence Player (Restored Elite Design) ── */}
      <div className="border-b border-stark-border bg-black/40">
        <div className="p-3">
          <div className="relative aspect-video rounded-lg overflow-hidden border border-stark-border bg-black shadow-2xl group">
            {activeVideoPath ? (
              <>
                <video
                  ref={videoRef}
                  src={`/media/${activeVideoPath}`}
                  className="w-full h-full object-contain"
                  onTimeUpdate={e => setVideoCurrentTime((e.target as HTMLVideoElement).currentTime)}
                  onDurationChange={e => setVideoDuration((e.target as HTMLVideoElement).duration)}
                  onPlay={() => setVideoPlaying(true)}
                  onPause={() => setVideoPlaying(false)}
                />
                
                {/* ── Neural HUD Overlays (RE-INSTATED) ── */}
                <div className="absolute inset-0 pointer-events-none">
                  {/* Corner brackets */}
                  {(["top-0 left-0 border-t-2 border-l-2", "top-0 right-0 border-t-2 border-r-2", "bottom-0 left-0 border-b-2 border-l-2", "bottom-0 right-0 border-b-2 border-r-2"] as const).map((cls, i) => (
                    <div key={i} className={cn("absolute w-3 h-3 border-spider-red/40", cls)} />
                  ))}
                  
                  <div className="absolute top-1.5 left-1.5">
                    <span className="text-[6px] font-mono text-stark-gold bg-black/70 px-1.5 py-0.5 rounded border border-stark-gold/20">
                      {videoCurrentTime.toFixed(1)}s
                    </span>
                  </div>
                  
                  <div className="absolute top-1.5 right-1.5">
                    <div className="flex items-center gap-1 bg-black/70 px-1.5 py-0.5 rounded border border-green-500/20">
                      <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                      <span className="text-[6px] font-mono text-green-400">REC</span>
                    </div>
                  </div>
                  
                  <div className="absolute bottom-2 left-2 flex items-center gap-1.5 opacity-50">
                    <Crosshair className="w-3 h-3 text-spider-red" />
                    <span className="text-[6px] font-bold text-white uppercase tracking-widest">Target Lock</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-800 p-6 text-center">
                <Activity className="w-8 h-8 mb-3 opacity-20" />
                <p className="text-[8px] font-black uppercase tracking-widest">Awaiting Neural Link</p>
                <p className="text-[7px] mt-1 opacity-50">Evidence stream not initialized</p>
              </div>
            )}
          </div>

          {/* ── Smart Scrubber (RE-INSTATED) ── */}
          <div 
            className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden cursor-pointer relative group/scrubber"
            onClick={e => {
              if (!videoRef.current || !videoDuration) return;
              const rect = e.currentTarget.getBoundingClientRect();
              videoRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * videoDuration;
            }}
          >
            {/* Progress fill */}
            <div 
              className="absolute inset-0 bg-spider-red/40 transition-all shadow-[0_0_8px_rgba(216,0,50,0.5)]"
              style={{ width: `${videoDuration ? (videoCurrentTime / videoDuration) * 100 : 0}%` }}
            />
            {/* Semantic timeline event markers */}
            {activeMetadata.map((evt, i) => (
              <div 
                key={i} 
                className="absolute top-0 h-full w-px opacity-80"
                style={{
                  left: `${((evt.time || evt.current_time) / (videoDuration || 1)) * 100}%`,
                  backgroundColor: evt.ocr ? "#F5C518" : evt.camera_motion ? "#60a5fa" : "#22c55e",
                }}
              />
            ))}
          </div>

          {/* ── Forensic Controls (RE-INSTATED) ── */}
          <div className="flex items-center justify-between mt-3 px-1">
            <div className="flex items-center gap-1">
              <button 
                onClick={() => { if (videoRef.current) videoRef.current.currentTime -= 0.033; }}
                className="p-1 rounded hover:bg-white/5 text-gray-500 hover:text-white transition-all"
                title="Prev Frame"
              >
                <ChevronLeft className="w-3 h-3" />
              </button>
              
              <button
                onClick={() => {
                  if (!videoRef.current) return;
                  videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause();
                }}
                className="w-7 h-7 flex items-center justify-center rounded bg-spider-red/20 border border-spider-red/30 text-spider-red hover:bg-spider-red hover:text-white transition-all"
              >
                {videoPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              </button>

              <button 
                onClick={() => { if (videoRef.current) videoRef.current.currentTime += 0.033; }}
                className="p-1 rounded hover:bg-white/5 text-gray-500 hover:text-white transition-all"
                title="Next Frame"
              >
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
            
            <div className="flex flex-col items-end">
              <span className="text-[8px] font-mono text-white tracking-widest tabular-nums">
                {videoCurrentTime.toFixed(2)}s
              </span>
              <span className="text-[6px] font-mono text-gray-600 uppercase">
                / {videoDuration.toFixed(1)}s
              </span>
            </div>
          </div>

          {/* ── Heatmap Legend ── */}
          {activeMetadata.length > 0 && (
            <div className="mt-3 flex items-center gap-3">
              {[{ c: "#F5C518", l: "Text" }, { c: "#60a5fa", l: "Motion" }, { c: "#22c55e", l: "Logic" }].map(({ c, l }) => (
                <div key={l} className="flex items-center gap-1.5">
                  <div className="w-1 h-1 rounded-full" style={{ backgroundColor: c }} />
                  <span className="text-[7px] text-gray-600 font-black uppercase tracking-tighter">{l}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Live Log Stream ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-[8px]" style={{ scrollbarWidth: "none" }}>
        <div className="pb-2 mb-2 border-b border-stark-border/30">
          <span className="text-gray-700 text-[7px] uppercase font-bold tracking-[0.2em]">Sensor Output</span>
        </div>
        {logs.slice(-40).map(log => (
          <div key={log.id} className="flex gap-2 group">
            <span className="text-gray-800 shrink-0 tabular-nums">[{log.timestamp}]</span>
            <span className={cn(
              "leading-relaxed",
              log.type === "error" ? "text-spider-red" : 
              log.type === "success" ? "text-green-500" :
              log.type === "warn" ? "text-stark-gold" : "text-gray-500"
            )}>
              {log.text}
            </span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>

      {/* ── Hardware Telemetry (ACTIVATED) ── */}
      <div className="p-4 border-t border-stark-border bg-black/20 space-y-3">
        {[
          { label: "CPU CORE", value: hardwareStats.cpu, color: "bg-stark-gold" },
          { label: "GPU LOAD", value: hardwareStats.gpu, color: "bg-spider-red" },
          { label: "VRAM UTIL", value: hardwareStats.vram, color: "bg-blue-500" },
        ].map(({ label, value, color }) => (
          <div key={label} className="space-y-1">
            <div className="flex justify-between items-end">
              <span className="text-[7px] font-black text-gray-500 tracking-widest">{label}</span>
              <span className="text-[8px] font-mono text-white">{value}%</span>
            </div>
            <div className="h-1 bg-white/5 rounded-full overflow-hidden">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${value}%` }}
                 className={cn("h-full rounded-full", color)}
               />
            </div>
          </div>
        ))}
      </div>
    </motion.aside>
  );
}
