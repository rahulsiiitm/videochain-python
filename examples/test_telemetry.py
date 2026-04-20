import psutil
from vidchain.telemetry import HardwareMonitor

print("Initial sample (interval=None):")
print(HardwareMonitor.get_instant_sample())

import time
time.sleep(1)

print("Second sample (interval=None) after 1s:")
print(HardwareMonitor.get_instant_sample())
