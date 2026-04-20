import pynvml
try:
    pynvml.nvmlInit()
    print("NVML SUCCESS")
    pynvml.nvmlShutdown()
except Exception as e:
    print(f"NVML ERROR: {e}")
