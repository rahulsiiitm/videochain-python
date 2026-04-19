import psutil
import time
import os
import threading
from typing import Dict, Any, Optional

try:
    import pynvml
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

class HardwareMonitor:
    """
    Forensic Neural HUD v0.7.5: Peak Load Sampler.
    Uses background threading to capture computational spikes during AI processing.
    """
    def __init__(self):
        self.stats = {
            "cpu_score": 0.0,
            "gpu_score": 0.0,
            "latency": 0.0
        }
        self._peak_cpu = 0.0
        self._peak_gpu = 0.0
        self._stop_event = threading.Event()
        self._poll_thread = None
        
        self.nvml_initialized = False
        if HAS_GPU:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
            except:
                pass

    def _poll_load(self):
        """Background thread logic to catch hardware spikes."""
        while not self._stop_event.is_set():
            # Sample CPU Load
            current_cpu = psutil.cpu_percent(interval=None)
            self._peak_cpu = max(self._peak_cpu, current_cpu)
            
            # Sample GPU Load
            if self.nvml_initialized:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    self._peak_gpu = max(self._peak_gpu, float(util.gpu))
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
        self.stats["latency"] = round(time.time() - self.start_time, 2)

    def get_stats(self) -> Dict[str, float]:
        return self.stats

    def __del__(self):
        if self.nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except:
                pass
