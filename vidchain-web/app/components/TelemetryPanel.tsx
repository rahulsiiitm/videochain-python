"use client";

import React from "react";
import { Play, Pause, Activity, MonitorPlay, Terminal, Cpu, Database, Clock, Shield } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "./utils";

interface TelemetryPanelProps {
  activeVideoPath: string | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  videoPlaying: boolean;
  setVideoPlaying: (playing: boolean) => void;
  videoCurrentTime: number;
  setVideoCurrentTime: (time: number) => void;
  videoDuration: number;
  setVideoDuration: (duration: number) => void;
  activeMetadata: any[];
  liveStatus: string;
  logs: any[];
  logsEndRef: React.RefObject<HTMLDivElement | null>;
  serverOnline: boolean;
  isIngesting: boolean;
  hardwareStats: { cpu: number; gpu: number; vram: number };
  layout?: "sidebar" | "workstation";
}

export function TelemetryPanel({
  activeVideoPath, videoRef, videoPlaying, setVideoPlaying, videoCurrentTime,
  setVideoCurrentTime, videoDuration, setVideoDuration, activeMetadata,
  liveStatus, logs, logsEndRef, serverOnline, isIngesting, hardwareStats,
  layout = "sidebar"
}: TelemetryPanelProps) {

  return (
    <aside className="flex flex-col h-full bg-[#09090b]">
      
      {/* Header */}
      <div className="h-12 shrink-0 border-b border-[#1a1a1a] bg-[#080808] flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <MonitorPlay className="w-4 h-4 text-muted-foreground opacity-50" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Video Feed</span>
        </div>
        <div className="flex items-center gap-2">
           {isIngesting && <span className="text-[9px] font-bold uppercase tracking-widest text-white animate-pulse">Exploring...</span>}
        </div>
      </div>

      {/* Video Content */}
      <div className="border-b border-[#1a1a1a] p-4 bg-black">
        <div className="relative aspect-video rounded overflow-hidden bg-zinc-950 border border-[#1a1a1a] group shadow-inner">
          {activeVideoPath ? (
            <video ref={videoRef}
              src={`http://localhost:8000/api/media-stream?path=${encodeURIComponent(activeVideoPath)}`}
              className="w-full h-full object-contain"
              onTimeUpdate={e => setVideoCurrentTime((e.target as HTMLVideoElement).currentTime)}
              onDurationChange={e => setVideoDuration((e.target as HTMLVideoElement).duration)}
              onPlay={() => setVideoPlaying(true)}
              onPause={() => setVideoPlaying(false)}
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-800">
              <MonitorPlay className="w-8 h-8 mb-2" />
              <p className="text-[10px] font-bold uppercase tracking-widest">No Active Stream</p>
            </div>
          )}
        </div>

        {/* Video Controls */}
        <div className="mt-4 flex flex-col gap-3">
          <div className="h-1 bg-zinc-900 rounded-full overflow-hidden cursor-pointer relative"
            onClick={e => {
              if (!videoRef.current || !videoDuration) return;
              const rect = e.currentTarget.getBoundingClientRect();
              videoRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * videoDuration;
            }}>
            <motion.div className="absolute inset-0 bg-accent rounded-full"
              style={{ width: `${videoDuration ? (videoCurrentTime / videoDuration) * 100 : 0}%` }} />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button onClick={() => { if (!videoRef.current) return; videoRef.current.paused ? videoRef.current.play() : videoRef.current.pause(); }}
                className="w-8 h-8 flex items-center justify-center rounded-lg bg-[#18181b] border border-[#27272a] text-white hover:bg-[#27272a] transition-all">
                {videoPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
              </button>
              <div className="flex items-center gap-2 px-3 py-1 bg-[#18181b] rounded-md border border-[#27272a]">
                 <Clock className="w-3 h-3 text-muted-foreground" />
                 <span className="text-[11px] font-mono font-bold text-zinc-300">
                   {videoCurrentTime.toFixed(2)}s
                 </span>
              </div>
            </div>
            <span className="text-[10px] font-mono text-zinc-500">
               Duration: {videoDuration.toFixed(2)}s
            </span>
          </div>
        </div>
      </div>

      {/* Resource Metrics */}
      <div className="p-4 border-b border-[#27272a] bg-[#0c0c0e]">
         <div className="grid grid-cols-3 gap-3">
            {[{ label: "CPU", val: hardwareStats.cpu, icon: Cpu }, { label: "GPU", val: hardwareStats.gpu, icon: Activity }, { label: "MEM", val: hardwareStats.vram, icon: Database }].map(stat => (
               <div key={stat.label} className="panel p-3 flex flex-col gap-2 bg-[#09090b]">
                  <div className="flex items-center justify-between">
                     <stat.icon className="w-3 h-3 text-muted-foreground" />
                     <span className="text-[10px] font-bold text-zinc-500">{stat.label}</span>
                  </div>
                  <div className="flex items-end justify-between">
                     <span className="text-xs font-mono font-bold text-white">{stat.val}%</span>
                     <div className="flex-1 h-1 bg-zinc-900 ml-2 rounded-full overflow-hidden">
                        <motion.div animate={{ width: `${stat.val}%` }} className="h-full bg-accent" />
                     </div>
                  </div>
               </div>
            ))}
         </div>
      </div>

      {/* Terminal Logs */}
      <div className="flex-1 flex flex-col min-h-0 bg-black">
        <div className="h-8 shrink-0 flex items-center px-4 border-b border-[#1a1a1a] bg-[#080808]">
           <Terminal className="w-3 h-3 text-muted-foreground mr-2 opacity-50" />
           <span className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground opacity-60">Assistant Activity</span>
        </div>
        <div className="flex-1 overflow-y-auto p-4 font-mono text-[9px] space-y-1 custom-scrollbar">
          {logs.slice(-100).map(log => (
            <div key={log.id} className="flex gap-3 leading-relaxed border-b border-white/[0.01] pb-1 last:border-0">
              <span className="text-zinc-800 shrink-0 select-none">[{log.timestamp}]</span>
              <span className={cn(
                "break-words font-medium tracking-tight",
                log.type === "error" ? "text-zinc-400 underline decoration-zinc-700" :
                log.type === "success" ? "text-white" :
                log.type === "warn" ? "text-zinc-200" : "text-zinc-500"
              )}>{log.text}</span>
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    </aside>
  );
}