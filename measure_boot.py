import time
start = time.time()
from opendbc.car.interfaces import get_interfaces
get_interfaces()
end = time.time()
print(f"Boot time: {end - start:.5f}s")
