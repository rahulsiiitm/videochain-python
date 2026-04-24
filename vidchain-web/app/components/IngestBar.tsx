"use client";

import React from "react";
import { Share2, Settings, Shield, Globe, Terminal } from "lucide-react";
import { cn } from "./utils";

interface IngestBarProps {
  sessionState: string;
  activeSession: any;
  videoPath: string;
  setVideoPath: (val: string) => void;
  handleIngest: () => void;
  isIngesting: boolean;
  serverOnline: boolean;
  exportInsightReport: () => void;
  liveStatus: string;
  onToggleSidebar: () => void;
  onToggleTelemetry: () => void;
  onSettingsClick: () => void;
}

export function IngestBar({
  sessionState, activeSession, videoPath, setVideoPath, handleIngest, 
  isIngesting, serverOnline, exportInsightReport, liveStatus,
  onToggleSidebar, onToggleTelemetry, onSettingsClick
}: IngestBarProps) {
  
  return (
    <header className="h-16 shrink-0 border-b border-[#1a1a1a] bg-[#050505] flex items-center justify-between px-6 relative z-20">
      
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className={cn("w-1.5 h-1.5 rounded-full", serverOnline ? "bg-white shadow-[0_0_8px_rgba(255,255,255,0.4)]" : "bg-zinc-800")} />
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground opacity-60">
            {serverOnline ? "Ready to Help" : "Signal Lost"}
          </span>
        </div>
        
        {activeSession && sessionState === "ready" && (
          <div className="flex items-center gap-3 border-l border-[#1a1a1a] pl-6">
             <span className="text-[11px] font-bold text-white tracking-tight">{activeSession.title}</span>
             <span className="metric-pill">Active Memory</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        {sessionState === "ready" && (
          <button onClick={exportInsightReport}
            className="btn-secondary py-1.5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider">
            <Share2 className="w-3.5 h-3.5" />
            Share Insights
          </button>
        )}
        
        <div className="flex items-center gap-2 ml-4">
           <button onClick={onSettingsClick}
             className="p-2 rounded text-muted-foreground hover:text-white hover:bg-[#111] transition-all">
              <Settings className="w-4 h-4" />
           </button>
        </div>
      </div>
    </header>
  );
}