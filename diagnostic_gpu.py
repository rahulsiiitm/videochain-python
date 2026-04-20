import pynvml
import psutil
import time

try:
    pynvml.nvmlInit()
    device_count = pynvml.nvmlDeviceGetCount()
    print(f"GPUs detected: {device_count}")
    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        print(f"GPU {i}: {name}")
        print(f"  Utilization: {util.gpu}%")
        print(f"  Memory: {mem.used / 1024**2:.1f}MB / {mem.total / 1024**2:.1f}MB")
    pynvml.nvmlShutdown()
except Exception as e:
    print(f"NVML Error: {e}")

print(f"CPU Utilization: {psutil.cpu_percent(interval=1)}%")
