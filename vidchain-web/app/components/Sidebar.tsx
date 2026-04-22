"use client";

import React from "react";
import { Plus, Trash2, Edit2, MessageSquare, ChevronLeft, ChevronRight } from "lucide-react";
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
      animate={{ width: sidebarCollapsed ? 48 : 240 }}
      transition={{ duration: 0.18, ease: "easeInOut" }}
      className="relative flex flex-col border-r border-sp-border bg-sp-surface shrink-0 overflow-hidden"
    >
      {/* Logo */}
      <div className={cn(
        "h-14 border-b border-sp-border flex items-center shrink-0 overflow-hidden",
        sidebarCollapsed ? "justify-center px-3" : "px-4 gap-3"
      )}>
        <div className="w-8 h-8 rounded-full overflow-hidden shrink-0 shadow-[0_0_15px_rgba(232,25,44,0.3)]">
          <img src="/logo.png" alt="IRIS Logo" className="w-full h-full object-cover" />
        </div>
        {!sidebarCollapsed && (
          <div>
            <p className="text-[11px] font-black uppercase tracking-[0.15em] text-white leading-none">I R I S</p>
            <p className="text-[7px] text-sp-red font-bold tracking-[0.25em] uppercase mt-0.5">Insight Engine</p>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        className="absolute right-0 top-[56px] w-3.5 h-8 bg-sp-surface border border-l-0 border-sp-border rounded-r-md flex items-center justify-center text-sp-muted hover:text-white hover:bg-sp-red transition-all z-20"
      >
        {sidebarCollapsed ? <ChevronRight className="w-2.5 h-2.5" /> : <ChevronLeft className="w-2.5 h-2.5" />}
      </button>

      {/* New session */}
      {!sidebarCollapsed && (
        <div className="p-3 border-b border-sp-border shrink-0">
          <button onClick={createSession}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-sp-border hover:border-sp-red/50 hover:bg-sp-red/5 transition-all text-[9px] font-bold uppercase tracking-widest text-sp-muted hover:text-white group">
            <Plus className="w-3 h-3 text-sp-red shrink-0" />
            Start New Insight
          </button>
        </div>
      )}

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2" style={{ scrollbarWidth: "none" }}>
        {sessions.map(s => {
          const isActive = activeSessionId === s.id;
          return (
            <div key={s.id} onClick={() => loadSession(s.id)}
              className={cn(
                "group relative mx-2 my-0.5 rounded-lg cursor-pointer transition-all border",
                isActive ? "bg-sp-red/10 border-sp-red/40" : "border-transparent hover:bg-white/3 hover:border-sp-border"
              )}>
              {sidebarCollapsed ? (
                <div className="flex justify-center py-3">
                  <MessageSquare className={cn("w-3.5 h-3.5", isActive ? "text-sp-red" : "text-sp-muted")} />
                </div>
              ) : (
                <div className="flex items-center gap-2.5 px-3 py-2.5">
                  <div className={cn("w-1 h-6 rounded-full shrink-0 transition-all", isActive ? "bg-sp-red" : "bg-sp-border")} />
                  <div className="flex-1 min-w-0">
                    {renamingId === s.id ? (
                      <input ref={renameInputRef}
                        className="w-full bg-background border border-sp-red rounded px-1.5 py-0.5 text-[10px] font-bold text-white focus:outline-none"
                        value={renameValue} onChange={e => setRenameValue(e.target.value)}
                        onBlur={commitRename} onKeyDown={e => e.key === "Enter" && commitRename()}
                        onClick={e => e.stopPropagation()} />
                    ) : (
                      <>
                        <p className={cn("text-[10px] font-semibold truncate", isActive ? "text-white" : "text-sp-muted")}>{s.title}</p>
                        <p className="text-[7px] text-sp-muted/60 mt-0.5">{s.message_count} messages</p>
                      </>
                    )}
                  </div>
                  <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity shrink-0">
                    <button onClick={e => startRename(s, e)} className="p-1 rounded hover:bg-white/5 text-sp-muted hover:text-white">
                      <Edit2 className="w-2.5 h-2.5" />
                    </button>
                    <button onClick={e => deleteSession(s.id, e)} className="p-1 rounded hover:bg-sp-red/20 text-sp-muted hover:text-sp-red">
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