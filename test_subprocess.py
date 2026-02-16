import subprocess
import sys

try:
    print("Testing subprocess...")
    # Use explicit shell=False and full path if possible, or just command list
    result = subprocess.run(["echo", "hello"], capture_output=True, text=True, shell=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return Code:", result.returncode)
except Exception as e:
    print(f"Error: {e}")
