
import os
import platform
import sys

print("================================")
print("Doppel Kubernetes Smoke Test")
print("================================")

print("Python version:", sys.version)
print("Platform:", platform.platform())
print("Project:", os.getenv("PROJECT_NAME", "Doppel"))

print("Smoke test completed successfully.")