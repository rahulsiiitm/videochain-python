import sys
import time
from PyQt5 import QtWidgets, QtCore, QtGui

# ══════════════════════════════════════════
# ### STEP 1: Define the Background Thread ###
# Put this at the top, outside your UI class.
# ══════════════════════════════════════════
class GPUWorker(QtCore.QThread):
    # This signal sends an integer (0-100) and a string (status text) back to the UI
    progress_signal = QtCore.pyqtSignal(int, str)
    # This signal tells the UI when the whole job is done
    finished_signal = QtCore.pyqtSignal() 

    def run(self):
        """
        Everything inside this function runs on a separate CPU thread, 
        leaving the Main Thread free to keep the UI glowing and animated.
        """
        # --- MOCKING THE PIPELINE FOR NOW ---
        # Later, you will import VideoLoader, AudioProcessor, etc. here.
        
        self.progress_signal.emit(10, "Extracting Audio & Keyframes...")
        time.sleep(1.5) # Simulating heavy work
        
        self.progress_signal.emit(40, "Running Whisper on RTX 3050 (CUDA)...")
        time.sleep(2)   # Simulating heavy work
        
        self.progress_signal.emit(70, "Running Vision Model on RTX 3050...")
        time.sleep(2)   # Simulating heavy work
        
        self.progress_signal.emit(90, "Fusing Multimodal Knowledge Base...")
        time.sleep(1)   # Simulating heavy work
        
        self.progress_signal.emit(100, "PIPELINE COMPLETE. RAG ONLINE.")
        self.finished_signal.emit()


# ══════════════════════════════════════════
# MAIN UI CLASS
# ══════════════════════════════════════════
class vidchainHUD(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ── Frameless + translucent window ──
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowTitle("vidchain – SEC-INTEL HUD")
        self.resize(1100, 700)
        self._drag_pos = None

        root = QtWidgets.QWidget()
        root.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setCentralWidget(root)
        
        main_layout = QtWidgets.QHBoxLayout(root)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ── LEFT PANEL: CONTROLS ──
        left_w = QtWidgets.QWidget()
        left_w.setFixedWidth(300)
        left_w.setStyleSheet("QWidget { background: rgba(6, 12, 28, 220); border: 1px solid rgba(0, 217, 255, 40); border-radius: 5px; }")
        lp = QtWidgets.QVBoxLayout(left_w)
        
        title = QtWidgets.QLabel("vidchain")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #00D9FF; letter-spacing: 4px; border: none; background: transparent;")
        lp.addWidget(title)
        
        sub = QtWidgets.QLabel("MULTIMODAL RAG ENGINE")
        sub.setStyleSheet("font-size: 9px; color: #475569; letter-spacing: 2px; border: none; background: transparent;")
        lp.addWidget(sub)
        lp.addSpacing(30)

        self.btn_load = QtWidgets.QPushButton("TARGET VIDEO [ .MP4 ]")
        self.btn_load.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_load.setStyleSheet("""
            QPushButton { background: rgba(0,217,255,10); color: #00D9FF; border: 1px solid rgba(0,217,255,60); font-family: 'Courier New'; padding: 10px; }
            QPushButton:hover { background: rgba(0,217,255,30); }
            QPushButton:disabled { color: #475569; border: 1px solid #475569; }
        """)
        lp.addWidget(self.btn_load)
        
        # ### STEP 2: Connect the button click to your custom function ###
        self.btn_load.clicked.connect(self.start_pipeline)
        
        lp.addSpacing(20)

        lbl_status = QtWidgets.QLabel("PIPELINE STATUS")
        lbl_status.setStyleSheet("font-size: 8px; color: #1E3A5F; border: none; background: transparent;")
        lp.addWidget(lbl_status)
        
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar { border: none; background: #060C1C; } QProgressBar::chunk { background: #00D9FF; }")
        lp.addWidget(self.progress)
        
        self.lbl_action = QtWidgets.QLabel("AWAITING VIDEO INGESTION...")
        self.lbl_action.setStyleSheet("font-size: 10px; color: #E2E8F0; font-family: 'Courier New'; border: none; background: transparent;")
        lp.addWidget(self.lbl_action)
        lp.addSpacing(30)

        self.add_metric_card(lp, "VISION TOKENS", "000", "#F59E0B")
        self.add_metric_card(lp, "AUDIO TRANSCRIPT", "0.0s", "#00D9FF")
        self.add_metric_card(lp, "GPU VRAM", "0 MB", "#22C55E")
        
        lp.addStretch()
        
        btn_exit = QtWidgets.QPushButton("TERMINATE SESSION")
        btn_exit.setStyleSheet("background: rgba(239, 68, 68, 20); color: #EF4444; border: 1px solid #EF4444; padding: 5px;")
        btn_exit.clicked.connect(self.close)
        lp.addWidget(btn_exit)

        main_layout.addWidget(left_w)

        # ── RIGHT PANEL: AI TERMINAL ──
        right_w = QtWidgets.QWidget()
        right_w.setStyleSheet("background: rgba(6, 12, 28, 220); border: 1px solid rgba(0, 217, 255, 40); border-radius: 5px;")
        rp = QtWidgets.QVBoxLayout(right_w)

        term_lbl = QtWidgets.QLabel("INTELLIGENCE QUERY TERMINAL")
        term_lbl.setStyleSheet("font-size: 10px; color: #00D9FF; letter-spacing: 2px; border: none; background: transparent;")
        rp.addWidget(term_lbl)

        self.chat_log = QtWidgets.QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet("QTextEdit { background: rgba(0, 10, 20, 100); color: #E2E8F0; font-family: 'Courier New'; font-size: 13px; border: 1px solid rgba(0, 217, 255, 20); padding: 10px; }")
        self.chat_log.append("> SYSTEM: vidchain RAG Engine Online.")
        self.chat_log.append("> SYSTEM: Waiting for temporal knowledge base...")
        rp.addWidget(self.chat_log)

        input_layout = QtWidgets.QHBoxLayout()
        self.query_input = QtWidgets.QLineEdit()
        self.query_input.setPlaceholderText("Enter query (e.g., 'When did the suspect enter?')...")
        self.query_input.setStyleSheet("QLineEdit { background: #060C1C; color: #00D9FF; font-family: 'Courier New'; font-size: 14px; border: 1px solid #00D9FF; padding: 8px; }")
        input_layout.addWidget(self.query_input)

        btn_send = QtWidgets.QPushButton("EXECUTE")
        btn_send.setFixedSize(100, 35)
        btn_send.setStyleSheet("background: #00D9FF; color: #000; font-weight: bold; border: none;")
        input_layout.addWidget(btn_send)

        rp.addLayout(input_layout)
        main_layout.addWidget(right_w, stretch=1)

    # ══════════════════════════════════════════
    # ### STEP 3: The UI Update Functions ###
    # ══════════════════════════════════════════
    def start_pipeline(self):
        # 1. Disable the button so the user doesn't click it twice and crash the GPU
        self.btn_load.setEnabled(False)
        self.chat_log.append("\n> SYSTEM: Ingesting target video. Allocating GPU memory...")
        
        # 2. Create the worker thread
        self.worker = GPUWorker()
        
        # 3. Connect the thread's signals to the UI functions
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.pipeline_finished)
        
        # 4. START THE THREAD
        self.worker.start()

    def update_progress(self, percent, text):
        # This gets called automatically every time the worker emits a signal!
        self.progress.setValue(percent)
        self.lbl_action.setText(text)

    def pipeline_finished(self):
        # Re-enable the button once everything is done
        self.btn_load.setEnabled(True)
        self.chat_log.append("> SYSTEM: Knowledge base generated successfully.")
        self.chat_log.append("> SYSTEM: RAG Engine is ready for queries.")


    # ── UI Helpers ──
    def add_metric_card(self, layout, title, val, color):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet(f"background: rgba(0,0,0,80); border-left: 2px solid {color}; border-radius: 2px; padding: 5px;")
        flay = QtWidgets.QVBoxLayout(frame)
        lbl = QtWidgets.QLabel(title)
        lbl.setStyleSheet("font-size: 8px; color: #475569; border: none; background: transparent;")
        val_lbl = QtWidgets.QLabel(val)
        val_lbl.setStyleSheet(f"font-size: 18px; color: {color}; font-family: 'Courier New'; border: none; background: transparent;")
        flay.addWidget(lbl)
        flay.addWidget(val_lbl)
        layout.addWidget(frame)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == QtCore.Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = vidchainHUD()
    window.show()
    sys.exit(app.exec_())