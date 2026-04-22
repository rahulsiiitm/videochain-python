"use client";

import React from "react";
import { motion } from "framer-motion";
import { Play, Pause, ChevronLeft, ChevronRight, Activity, Crosshair } from "lucide-react";
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
  activeVideoPath, videoRef, videoPlaying, videoCurrentTime, videoDuration,
  setVideoPlaying, setVideoCurrentTime, setVideoDuration,
  activeMetadata, liveStatus, logs, logsEndRef, serverOnline, isIngesting,
  vlmActive, ocrActive, audioActive, trackerActive, graphActive, hardwareStats,
}: TelemetryPanelProps) {

  const nodes = [
    { label: "VLM", active: vlmActive, color: "#E8192C" },
    { label: "OCR", active: ocrActive, color: "#F5C518" },
    { label: "Audio", active: audioActive, color: "#22c55e" },
    { label: "Track", active: trackerActive, color: "#60a5fa" },
    { label: "Graph", active: graphActive, color: "#a855f7" },
  ];

  return (
    <aside className="w-72 border-l border-sp-border bg-sp-surface flex flex-col shrink-0 overflow-hidden">

      {/* Node status */}
      <div className="p-4 border-b border-sp-border">
        <p className="text-[8px] font-black uppercase tracking-[0.2em] text-sp-muted mb-3">Neural Nodes</p>
        <div className="flex flex-wrap gap-2">
          {nodes.map(({ label, active, color }) => (
            <div key={label} className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[8px] font-bold uppercase tracking-widest transition-all",
              active ? "border-transparent text-white" : "border-sp-border text-sp-muted"
            )} style={active ? { backgroundColor: `${color}20`, borderColor: `${color}50`, color } : {}}>
              <span className={cn("w-1 h-1 rounded-full", active ? "animate-pulse" : "bg-sp-border")}
                style={active ? { backgroundColor: color } : {}} />
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* Video player */}
      <div className="border-b border-sp-border p-3">
        <div className="relative aspect-video rounded-lg overflow-hidden bg-black border border-sp-border">
          {activeVideoPath ? (
            <>
              <video ref={videoRef}
                src={`http://localhost:8000/api/media-stream?path=${encodeURIComponent(activeVideoPath)}`}
                className="w-full h-full object-contain"
                onTimeUpdate={e => setVideoCurrentTime((e.target as HTMLVideoElement).currentTime)}
                onDurationChange={e => setVideoDuration((e.target as HTMLVideoElement).duration)}
                onPlay={() => setVideoPlaying(true)}
                onPause={() => setVideoPlaying(false)}
              />
              {/* Corner brackets */}
              <div className="absolute inset-0 pointer-events-none">
                {(["top-0 left-0 border-t border-l", "top-0 right-0 border-t border-r", "bottom-0 left-0 border-b border-l", "bottom-0 right-0 border-b border-r"] as const).map((cls, i) => (
                  <div key={i} className={cn("absolute w-3 h-3 border-sp-red/60", cls)} />
                ))}
                <span className="absolute bottom-1.5 left-2 text-[6px] font-mono text-sp-red/70">
                  {videoCurrentTime.toFixed(2)}s
                </span>
              </div>
            </>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-sp-muted/30">
              <Activity className="w-6 h-6 mb-2" />
              <p className="text-[7px] font-bold uppercase tracking-widest">No Context</p>
            </div>
          )}
        </div>

        {/* Scrubber */}
        <div className="mt-2 h-1 bg-white/5 rounded-full overflow-hidden cursor-pointer relative"
          onClick={e => {
            if (!videoRef.current || !videoDuration) return;
            const rect = e.currentTarget.getBoundingClientRect();
            videoRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * videoDuration;
          }}>
          <div className="absolute inset-0 bg-sp-red/50 rounded-full transition-all"
            style={{ width: `${videoDuration ? (videoCurrentTime / videoDuration) * 100 : 0}%` }} />
          {activeMetadata.map((evt, i) => (
            <div key={i} className="absolute top-0 h-full w-px opacity-60"
              style={{ left: `${((evt.time || evt.current_time) / (videoDuration || 1)) * 100}%`, backgroundColor: evt.ocr ? "#F5C518" : evt.camera_motion ? "#60a5fa" : "#22c55e" }} />
          ))}
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between mt-2 px-1">
          <div className="flex items-center gap-1">
            <button onClick={() => { if (videoRef.current) videoRef.current.currentTime -= 0.033; }}
              className="p-1 rounded text-sp-muted hover:text-white transition-all">
              <ChevronLeft className="w-3 h-3" />
            </button>
            <button onClick={() => { if (!videoRef.current) return; videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause(); }}
              className="w-6 h-6 flex items-center justify-center rounded-full bg-sp-red/20 border border-sp-red/40 text-sp-red hover:bg-sp-red hover:text-white transition-all">
              {videoPlaying ? <Pause className="w-2.5 h-2.5" /> : <Play className="w-2.5 h-2.5" />}
            </button>
            <button onClick={() => { if (videoRef.current) videoRef.current.currentTime += 0.033; }}
              className="p-1 rounded text-sp-muted hover:text-white transition-all">
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
          <span className="text-[8px] font-mono text-white/40">
            {videoCurrentTime.toFixed(1)}s / {videoDuration.toFixed(1)}s
          </span>
        </div>
      </div>

      {/* Logs */}
      <div className="flex-1 overflow-y-auto p-3 font-mono text-[8px] space-y-0.5" style={{ scrollbarWidth: "none" }}>
        <p className="text-[7px] font-bold uppercase tracking-[0.2em] text-sp-muted/50 pb-2 mb-1 border-b border-sp-border/30">Analysis Feed</p>
        {logs.slice(-40).map(log => (
          <div key={log.id} className="flex gap-2">
            <span className="text-sp-muted/40 shrink-0">[{log.timestamp}]</span>
            <span className={cn(
              log.type === "error" ? "text-sp-red" :
              log.type === "success" ? "text-green-500" :
              log.type === "warn" ? "text-yellow-500" : "text-white/30"
            )}>{log.text}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>

      {/* Hardware stats */}
      <div className="p-3 border-t border-sp-border space-y-2">
        {[
          { label: "CPU", value: hardwareStats.cpu, color: "bg-yellow-500" },
          { label: "GPU", value: hardwareStats.gpu, color: "bg-sp-red" },
          { label: "VRAM", value: hardwareStats.vram, color: "bg-sp-blue-light" },
        ].map(({ label, value, color }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-[7px] font-bold text-sp-muted/60 w-7">{label}</span>
            <div className="flex-1 h-0.5 bg-white/5 rounded-full overflow-hidden">
              <motion.div animate={{ width: `${value}%` }} className={cn("h-full rounded-full", color)} />
            </div>
            <span className="text-[7px] font-mono text-white/30 w-6 text-right">{value}%</span>
          </div>
        ))}
      </div>
    </aside>
  );
}