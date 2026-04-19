import psutil
import time
from vidchain.telemetry import HardwareMonitor

print("--- Neural Telemetry Diagnostic ---")
with HardwareMonitor() as hud:
    print("Simulating neural load for 2 seconds...")
    # Generate some synthetic CPU load
    x = 0
    start = time.time()
    while time.time() - start < 2:
        x += 1
    
stats = hud.get_stats()
print(f"Captured Telemetery: {stats}")

if stats['cpu_score'] == 0:
    print("[ERROR] CPU Score remains zero. Probe failure.")
else:
    print("[SUCCESS] CPU Probe operational.")

if stats['gpu_score'] == 0:
    print("[WARNING] GPU Score is zero. This is expected if no NVIDIA GPU is active or if load was too fast to capture.")
else:
    print("[SUCCESS] GPU Probe operational.")
