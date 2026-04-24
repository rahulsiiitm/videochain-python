"use client";

import React from "react";
import { Plus, Trash2, Edit2, Search, ChevronLeft, ChevronRight, FileText, Database, Shield } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "./utils";

interface Session {
  id: string;
  title: string;
  message_count: number;
}

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  loadSession: (id: string) => void;
  createSession: () => void;
  deleteSession: (id: string, e: React.MouseEvent) => void;
  startRename: (session: Session, e: React.MouseEvent) => void;
  renamingId: string | null;
  renameValue: string;
  setRenameValue: (val: string) => void;
  commitRename: () => void;
  renameInputRef: React.RefObject<HTMLInputElement | null>;
}

export function Sidebar({
  sessions, activeSessionId, sidebarCollapsed, setSidebarCollapsed,
  loadSession, createSession, deleteSession, startRename,
  renamingId, renameValue, setRenameValue, commitRename, renameInputRef,
}: SidebarProps) {
  return (
    <motion.aside
      animate={{ width: sidebarCollapsed ? 64 : 260 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="relative flex flex-col border-r border-[#27272a] bg-[#09090b] shrink-0 overflow-hidden z-30"
    >
      {/* Header */}
      <div className={cn(
        "h-16 flex items-center shrink-0 px-5 mb-2",
        sidebarCollapsed ? "justify-center" : "gap-3"
      )}>
        <div className="w-10 h-10 rounded overflow-hidden bg-black flex items-center justify-center border border-[#1a1a1a]">
           <img src="/logo_noir_rembg.png" className="w-8 h-8 invert brightness-200" alt="IRIS" />
        </div>
        {!sidebarCollapsed && (
          <div className="flex flex-col">
            <span className="text-[12px] font-black tracking-tighter text-white uppercase leading-none">IRIS</span>
            <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-widest opacity-50">Intelligence Suite</span>
          </div>
        )}
      </div>

      {/* Action */}
      <div className="px-3 mb-4">
        <button onClick={createSession}
          className={cn(
            "flex items-center justify-center rounded border border-[#222] bg-[#0c0c0c] hover:bg-[#1a1a1a] transition-all duration-200 text-white group",
            sidebarCollapsed ? "w-10 h-10 mx-auto" : "w-full gap-2 px-3 py-2"
          )}>
          <Plus className={cn("shrink-0", sidebarCollapsed ? "w-5 h-5" : "w-4 h-4")} />
          {!sidebarCollapsed && <span className="text-[11px] font-bold uppercase tracking-wider">New Session</span>}
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1 pb-6 custom-scrollbar">
        {!sidebarCollapsed && (
          <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest ml-2 mb-3 mt-4 opacity-40">Previous Sessions</p>
        )}
        
        {sessions.map(s => {
          const isActive = activeSessionId === s.id;
          return (
            <div key={s.id} onClick={() => loadSession(s.id)}
              className={cn(
                "group relative rounded cursor-pointer transition-all duration-200",
                isActive 
                  ? "bg-[#111] text-white border border-[#222]" 
                  : "text-muted-foreground hover:bg-[#0c0c0c] hover:text-white"
              )}>
              
              {sidebarCollapsed ? (
                <div className="flex justify-center py-3">
                   <FileText className={cn("w-5 h-5", isActive ? "text-white" : "text-muted-foreground")} />
                </div>
              ) : (
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <FileText className={cn("w-3.5 h-3.5 shrink-0", isActive ? "text-white" : "text-muted-foreground")} />
                  <div className="flex-1 min-w-0">
                    {renamingId === s.id ? (
                      <input ref={renameInputRef}
                        className="w-full bg-black border border-white/20 rounded px-2 py-1 text-[12px] text-white focus:outline-none"
                        value={renameValue} onChange={e => setRenameValue(e.target.value)}
                        onBlur={commitRename} onKeyDown={e => e.key === "Enter" && commitRename()}
                        onClick={e => e.stopPropagation()} />
                    ) : (
                      <div className="flex flex-col">
                        <p className="text-[12px] font-bold truncate tracking-tight">{s.title}</p>
                        <p className="text-[9px] text-muted-foreground font-medium">{s.message_count} insights</p>
                      </div>
                    )}
                  </div>
                  
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-2 transition-all shrink-0 ml-2">
                      <button onClick={e => startRename(s, e)} className="p-1.5 hover:text-white transition-colors">
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={e => deleteSession(s.id, e)} className="p-1.5 text-zinc-600 hover:text-red-500 transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-[#27272a]">
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-full h-9 flex items-center justify-center rounded-lg hover:bg-[#18181b] text-muted-foreground hover:text-white transition-all group"
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <div className="flex items-center gap-2">
              <ChevronLeft className="w-4 h-4" />
              <span className="text-[12px] font-medium">Collapse</span>
            </div>}
          </button>
      </div>
    </motion.aside>
  );
}