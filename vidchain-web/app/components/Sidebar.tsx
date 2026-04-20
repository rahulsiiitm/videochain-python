"use client";

import React from "react";
import { 
  Shield, Plus, Trash2, Edit2, MessageSquare, ChevronLeft, ChevronRight 
} from "lucide-react";
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
  sessions,
  activeSessionId,
  sidebarCollapsed,
  setSidebarCollapsed,
  loadSession,
  createSession,
  deleteSession,
  startRename,
  renamingId,
  renameValue,
  setRenameValue,
  commitRename,
  renameInputRef
}: SidebarProps) {
  return (
    <motion.aside
      animate={{ width: sidebarCollapsed ? 52 : 256 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative z-10 flex flex-col border-r border-stark-border bg-background shrink-0 overflow-hidden"
    >
      {/* Brand */}
      <div className={cn("p-4 border-b border-stark-border flex items-center gap-3 shrink-0", sidebarCollapsed && "justify-center px-3")}>
        <img 
          src="/logo.svg" 
          alt="VidChain Logo" 
          className={cn("h-6 w-auto object-contain", !sidebarCollapsed && "h-7")} 
        />
        {!sidebarCollapsed && (
          <div className="overflow-hidden min-w-0">
            <h1 className="text-xs font-black tracking-tight leading-none whitespace-nowrap uppercase">Vid-CHAIN</h1>
            <p className="text-[7px] text-stark-gold font-bold tracking-[0.2em] uppercase mt-0.5 whitespace-nowrap">Neural Command</p>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button 
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="absolute right-0 top-[52px] w-4 h-9 bg-stark-card border border-l-0 border-stark-border rounded-r-lg flex items-center justify-center text-gray-700 hover:text-white hover:bg-spider-red transition-all z-20"
      >
        {sidebarCollapsed ? <ChevronRight className="w-2.5 h-2.5" /> : <ChevronLeft className="w-2.5 h-2.5" />}
      </button>

      {/* Action button */}
      {!sidebarCollapsed && (
        <div className="p-3 border-b border-stark-border shrink-0">
          <button 
            onClick={createSession}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-stark-border hover:border-spider-red/50 hover:bg-stark-card/30 transition-all text-[9px] font-bold uppercase tracking-widest text-gray-500 hover:text-white group"
          >
            <Plus className="w-3 h-3 text-spider-red shrink-0 group-hover:scale-110 transition-transform" />
            New Investigation
          </button>
        </div>
      )}

      {/* Session List */}
      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "none" }}>
        {sessions.map(s => {
          const isActive = activeSessionId === s.id;
          return (
            <div
              key={s.id}
              onClick={() => loadSession(s.id)}
              className={cn(
                "group relative mx-2 my-1 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-200 border",
                isActive ? "bg-stark-card border-spider-red shadow-[0_0_15px_rgba(216,0,50,0.1)]" : "border-transparent hover:bg-stark-card/40 hover:border-stark-border"
              )}
            >
              {sidebarCollapsed ? (
                <div className="flex justify-center">
                  <MessageSquare className={cn("w-3.5 h-3.5", isActive ? "text-spider-red" : "text-gray-600")} />
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-1 h-8 rounded-full transition-all duration-300",
                    isActive ? "bg-spider-red" : "bg-gray-800"
                  )} />
                  
                  <div className="flex-1 min-w-0">
                    {renamingId === s.id ? (
                      <input
                        ref={renameInputRef}
                        className="w-full bg-background border border-spider-red rounded px-1.5 py-0.5 text-[10px] font-bold text-white focus:outline-none"
                        value={renameValue}
                        onChange={e => setRenameValue(e.target.value)}
                        onBlur={commitRename}
                        onKeyDown={e => e.key === "Enter" && commitRename()}
                        onClick={e => e.stopPropagation()}
                      />
                    ) : (
                      <>
                        <h4 className={cn("text-[10px] font-bold truncate tracking-tight transition-colors", isActive ? "text-white" : "text-gray-500")}>
                          {s.title}
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[7px] text-gray-700 font-black uppercase tracking-tighter tabular-nums">
                            {s.message_count} LOGS
                          </span>
                          <span className="text-[6px] text-gray-800">•</span>
                          <span className="text-[7px] text-gray-700 font-black uppercase tracking-tighter">SECURED</span>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="opacity-0 group-hover:opacity-100 flex items-center transition-opacity">
                    <button 
                      onClick={e => startRename(s, e)}
                      className="p-1 px-1.5 rounded hover:bg-white/5 text-gray-700 hover:text-stark-gold"
                    >
                      <Edit2 className="w-2.5 h-2.5" />
                    </button>
                    <button 
                      onClick={e => deleteSession(s.id, e)}
                      className="p-1 px-1.5 rounded hover:bg-spider-red/20 text-gray-700 hover:text-spider-red"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </motion.aside>
  );
}
