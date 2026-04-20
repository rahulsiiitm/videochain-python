"""
VidChain Studio — Native Desktop Application
Communicates with the vidchain-serve FastAPI edge server.
"""

import threading
import subprocess
import sys
import os
import tkinter as tk
import tkinter.filedialog as filedialog
from datetime import datetime

import customtkinter as ctk
import requests

# ─────────────────────────────────────────────────────────
# App Theme Configuration
# ─────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

API_BASE = "http://localhost:8000"

COLORS = {
    "bg_deep":    "#0A0D12",  # Deep Midnight
    "bg_panel":   "#1A1F2B",  # Navy shadow
    "bg_card":    "#242B3D",  # Suit Blue
    "accent":     "#E23636",  # Heroic Red
    "accent2":    "#0047AB",  # Navy Blue
    "success":    "#FDCB58",  # Spider-Yellow
    "warning":    "#FF9500",
    "danger":     "#FF4560",
    "text_main":  "#E8ECFF",
    "text_dim":   "#6B7281",
    "border":     "#31394D",
}


class VidChainStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🕸️ VID-CHAIN HQ")
        self.geometry("1200x780")
        self.minsize(1000, 650)
        self.configure(fg_color=COLORS["bg_deep"])

        # State
        self.current_video_id = None
        self.server_online = False
        self.ingesting = False

        self._build_ui()
        self._check_server_status()

    # ─────────────────────────────────────────────────────
    # UI Construction
    # ─────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], height=56, corner_radius=0)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        ctk.CTkLabel(
            topbar, text="🕸️  VID-CHAIN HQ",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            topbar, text="Stark-Tech Multimodal Observation Engine",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"]
        ).pack(side="left", padx=4)

        # Server status badge
        self.status_badge = ctk.CTkLabel(
            topbar, text="⬤  Connecting...",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["warning"]
        )
        self.status_badge.pack(side="right", padx=20)

        # ── Main split layout ─────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(10, 16))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Left panel
        self._build_left_panel(body)

        # Right panel
        self._build_right_panel(body)

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], width=320, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_propagate(False)

        # Section: Video Source
        self._section_label(left, "VIDEO SOURCE")

        self.video_entry = ctk.CTkEntry(
            left, placeholder_text="Path to video file...",
            fg_color=COLORS["bg_card"], border_color=COLORS["border"],
            text_color=COLORS["text_main"], font=ctk.CTkFont(size=12),
            height=38, corner_radius=8
        )
        self.video_entry.pack(fill="x", padx=14, pady=(4, 6))

        ctk.CTkButton(
            left, text="Browse File",
            command=self._browse_file,
            fg_color=COLORS["bg_card"], hover_color=COLORS["border"],
            text_color=COLORS["text_dim"], font=ctk.CTkFont(size=12),
            height=34, corner_radius=8, border_width=1, border_color=COLORS["border"]
        ).pack(fill="x", padx=14, pady=(0, 14))

        # Section: Pipeline
        self._section_label(left, "PIPELINE")

        ctk.CTkLabel(
            left, text="Vision Engine",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"]
        ).pack(anchor="w", padx=14)

        self.pipeline_var = ctk.StringVar(value="moondream")
        self.pipeline_menu = ctk.CTkOptionMenu(
            left,
            values=["moondream", "llava", "llava:7b", "yolo (legacy)"],
            variable=self.pipeline_var,
            fg_color=COLORS["bg_card"], button_color=COLORS["accent2"],
            button_hover_color="#6450D4",
            dropdown_fg_color=COLORS["bg_card"],
            text_color=COLORS["text_main"],
            font=ctk.CTkFont(size=12), height=36, corner_radius=8
        )
        self.pipeline_menu.pack(fill="x", padx=14, pady=(4, 14))

        # Ingest button
        self.ingest_btn = ctk.CTkButton(
            left, text="🕸️  Launch Web-Scan",
            command=self._start_ingest,
            fg_color=COLORS["accent"], hover_color="#B22222",
            text_color="#FFFFFF", font=ctk.CTkFont(size=13, weight="bold"),
            height=44, corner_radius=10
        )
        self.ingest_btn.pack(fill="x", padx=14, pady=(0, 4))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            left, fg_color=COLORS["bg_card"],
            progress_color=COLORS["accent"], height=4, corner_radius=2
        )
        self.progress_bar.pack(fill="x", padx=14, pady=(0, 14))
        self.progress_bar.set(0)

        # Section: Status log
        self._section_label(left, "SYSTEM LOG")
        self.log_box = ctk.CTkTextbox(
            left, fg_color=COLORS["bg_card"], text_color=COLORS["text_dim"],
            font=ctk.CTkFont(family="Consolas", size=10),
            border_color=COLORS["border"], border_width=1,
            corner_radius=8, wrap="word"
        )
        self.log_box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log_box.configure(state="disabled")

    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=0)
        right.columnconfigure(0, weight=1)

        # Chat history
        self.chat_display = ctk.CTkTextbox(
            right, fg_color=COLORS["bg_card"],
            text_color=COLORS["text_main"],
            font=ctk.CTkFont(family="Segoe UI", size=13),
            border_color=COLORS["border"], border_width=1,
            corner_radius=10, wrap="word", state="disabled"
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 8))

        # Input row
        input_row = ctk.CTkFrame(right, fg_color="transparent")
        input_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        input_row.columnconfigure(0, weight=1)

        self.query_entry = ctk.CTkEntry(
            input_row, placeholder_text="Ask B.A.B.U.R.A.O. anything about the video...",
            fg_color=COLORS["bg_card"], border_color=COLORS["accent2"],
            text_color=COLORS["text_main"], font=ctk.CTkFont(size=13),
            height=46, corner_radius=10
        )
        self.query_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.query_entry.bind("<Return>", lambda e: self._send_query())

        self.send_btn = ctk.CTkButton(
            input_row, text="Send  ➤",
            command=self._send_query,
            fg_color=COLORS["accent2"], hover_color="#6450D4",
            text_color=COLORS["text_main"],
            font=ctk.CTkFont(size=13, weight="bold"),
            height=46, width=110, corner_radius=10
        )
        self.send_btn.grid(row=0, column=1)

        # Welcome message
        self._append_chat("B.A.B.U.R.A.O.", 
            "🕷️ Web-Net Secure. Narrative interface ready for feed analysis.\n"
            "Status: Scanning for forensic evidence and entity relationships.",
            color=COLORS["accent"])

    def _section_label(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=COLORS["text_dim"]
        ).pack(anchor="w", padx=14, pady=(14, 2))

    # ─────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────

    def _browse_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")]
        )
        if path:
            self.video_entry.delete(0, "end")
            self.video_entry.insert(0, path)

    def _start_ingest(self):
        if self.ingesting:
            return

        video_path = self.video_entry.get().strip()
        if not video_path:
            self._log("⚠ Please select a video file first.")
            return

        if not os.path.exists(video_path):
            self._log(f"✗ File not found: {video_path}")
            return

        if not self.server_online:
            self._log("✗ Edge Server offline. Start it with: vidchain-serve")
            self._append_chat("System", "Edge server is offline. Please run `vidchain-serve` in a terminal.", color=COLORS["danger"])
            return

        self.ingesting = True
        self.ingest_btn.configure(text="⏳  Indexing...", state="disabled", fg_color=COLORS["text_dim"])
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        selected = self.pipeline_var.get()
        vlm_model = None if "legacy" in selected else selected

        self._log(f"→ Starting ingestion: {os.path.basename(video_path)}")
        self._log(f"→ Pipeline: {'VLM: ' + vlm_model if vlm_model else 'Legacy YOLO'}")
        self._append_chat("System", f"Indexing `{os.path.basename(video_path)}` using **{selected}** pipeline. This may take a few minutes...", color=COLORS["warning"])

        threading.Thread(target=self._ingest_thread, args=(video_path, vlm_model), daemon=True).start()

    def _ingest_thread(self, video_path, vlm_model):
        try:
            payload = {"video_source": video_path}
            if vlm_model:
                payload["vlm_model"] = vlm_model

            resp = requests.post(f"{API_BASE}/api/ingest", json=payload, timeout=10)
            data = resp.json()
            self.current_video_id = data.get("video_id")
            self.after(0, lambda: self._ingest_done(True, data.get("message", "Ingestion started.")))
        except Exception as e:
            self.after(0, lambda: self._ingest_done(False, str(e)))

    def _ingest_done(self, success, message):
        self.ingesting = False
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.ingest_btn.configure(
            text="⚡  Index Video", state="normal",
            fg_color=COLORS["success"] if success else COLORS["danger"]
        )
        self.after(3000, lambda: self.ingest_btn.configure(fg_color=COLORS["accent"]))

        if success:
            self.progress_bar.set(1.0)
            self._log(f"✓ {message}")
            self._append_chat("System", "Video successfully indexed! B.A.B.U.R.A.O. is now aware of this video. You can start querying.", color=COLORS["success"])
        else:
            self.progress_bar.set(0)
            self._log(f"✗ Error: {message}")

    def _send_query(self):
        query = self.query_entry.get().strip()
        if not query:
            return
        if not self.server_online:
            self._append_chat("System", "Edge server offline. Run `vidchain-serve` first.", color=COLORS["danger"])
            return

        self.query_entry.delete(0, "end")
        self._append_chat("You", query, color=COLORS["text_main"])
        self.send_btn.configure(state="disabled", text="...")
        threading.Thread(target=self._query_thread, args=(query,), daemon=True).start()

    def _query_thread(self, query):
        try:
            payload = {"query": query}
            if self.current_video_id:
                payload["video_id"] = self.current_video_id

            resp = requests.post(f"{API_BASE}/api/query", json=payload, timeout=60)
            answer = resp.json().get("response", "No response.")
            self.after(0, lambda: self._query_done(answer))
        except Exception as e:
            self.after(0, lambda: self._query_done(f"[Error] {e}"))

    def _query_done(self, answer):
        self.send_btn.configure(state="normal", text="Send  ➤")
        self._append_chat("B.A.B.U.R.A.O.", answer, color=COLORS["accent"])

    # ─────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────

    def _check_server_status(self):
        def _poll():
            try:
                resp = requests.get(f"{API_BASE}/api/health", timeout=2)
                online = resp.status_code == 200
            except Exception:
                online = False

            self.after(0, lambda: self._update_status(online))
            self.after(5000, _poll)

        threading.Thread(target=_poll, daemon=True).start()

    def _update_status(self, online: bool):
        self.server_online = online
        if online:
            self.status_badge.configure(text="⬤  Edge Server Online", text_color=COLORS["success"])
        else:
            self.status_badge.configure(text="⬤  Edge Server Offline", text_color=COLORS["danger"])

    def _append_chat(self, sender: str, message: str, color: str = None):
        self.chat_display.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M")

        self.chat_display.insert("end", f"\n[{timestamp}] {sender}\n", "sender")
        self.chat_display.insert("end", f"{message}\n", "message")
        self.chat_display.insert("end", "─" * 60 + "\n", "divider")

        self.chat_display.tag_config("sender", foreground=color or COLORS["accent"])
        self.chat_display.tag_config("message", foreground=COLORS["text_main"])
        self.chat_display.tag_config("divider", foreground=COLORS["border"])

        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}] {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")


def main_app():
    app = VidChainStudio()
    app.mainloop()


if __name__ == "__main__":
    main_app()
