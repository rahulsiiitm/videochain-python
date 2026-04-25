import psutil
import time
import os
import threading
from typing import Dict, Any, Optional

import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="pynvml")

# ── Persistent Hardware Pulse ────────────────────────────────────────────────
_NVML_INIT_FAILED = False
try:
    import pynvml
    pynvml.nvmlInit()
except Exception as e:
    print(f"[RECOVERABLE] NVML Init deferred: {e}")
    _NVML_INIT_FAILED = True

class HardwareMonitor:
    """
    IRIS Cognitive HUD v1.0.0: Peak Load Sampler.
    Uses background threading to capture computational spikes during AI processing.
    """
    def __init__(self):
        self.stats = {
            "cpu_score": 0.0,
            "gpu_score": 0.0,
            "vram_score": 0.0,
            "latency": 0.0
        }
        self._peak_cpu = 0.0
        self._peak_gpu = 0.0
        self._peak_vram = 0.0
        self._stop_event = threading.Event()
        self._poll_thread = None

    def _poll_load(self):
        """Background thread logic to catch hardware spikes."""
        global _NVML_INIT_FAILED
        while not self._stop_event.is_set():
            # Sample CPU Load
            current_cpu = psutil.cpu_percent(interval=None)
            self._peak_cpu = max(self._peak_cpu, current_cpu)
            
            # Sample GPU Load
            try:
                if _NVML_INIT_FAILED:
                    pynvml.nvmlInit()
                    _NVML_INIT_FAILED = False
                
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                self._peak_gpu = max(self._peak_gpu, float(util.gpu))
                self._peak_vram = max(self._peak_vram, (mem.used / mem.total) * 100)
            except:
                pass
            
            time.sleep(0.1) # 100ms polling pulse

    def __enter__(self):
        self.start_time = time.time()
        self._stop_event.clear()
        self._poll_thread = threading.Thread(target=self._poll_load, daemon=True)
        self._poll_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Stop the pulse
        self._stop_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=0.5)
            
        # Final snapshots and latency
        self.stats["cpu_score"] = round(self._peak_cpu, 1)
        self.stats["gpu_score"] = round(self._peak_gpu, 1)
        self.stats["vram_score"] = round(self._peak_vram, 1)
        self.stats["latency"] = round(time.time() - self.start_time, 2)

    def get_stats(self) -> Dict[str, float]:
        return self.stats

    @staticmethod
    def get_instant_sample() -> Dict[str, float]:
        """One-shot sample of current hardware load for live dashboards."""
        global _NVML_INIT_FAILED
        gpu = 0.0
        vram = 0.0
        
        try:
            if _NVML_INIT_FAILED:
                import pynvml
                pynvml.nvmlInit()
                _NVML_INIT_FAILED = False
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            gpu = float(util.gpu)
            vram = (mem.used / mem.total) * 100 if mem.total > 0 else 0.0
        except Exception as e:
            # We don't print here to avoid flooding logs, but we flag failure
            _NVML_INIT_FAILED = True
        
        # CPU sample
        cpu = psutil.cpu_percent(interval=0.1) 
        return {
            "cpu_score": round(cpu, 1), 
            "gpu_score": round(gpu, 1),
            "vram_score": round(vram, 1)
        }

    def __del__(self):
        pass
