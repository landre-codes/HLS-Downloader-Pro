import os
import subprocess
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["PYTHONIOENCODING"] = "utf-8"

A = """
import sys, os
from PySide6.QtCore import QCoreApplication, QTimer
sys.path.insert(0, os.getcwd())
import main
app = QCoreApplication([])
print("A principal:", main._single_instance(), flush=True)
QTimer.singleShot(4000, app.quit)
sys.exit(app.exec())
"""

B = """
import sys, os
from PySide6.QtCore import QCoreApplication
sys.path.insert(0, os.getcwd())
import main
app = QCoreApplication([])
print("B principal (esperado False):", main._single_instance(), flush=True)
"""

pa = subprocess.Popen(
    [sys.executable, "-c", A], cwd=os.getcwd(),
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
time.sleep(1.5)
pb = subprocess.run(
    [sys.executable, "-c", B], cwd=os.getcwd(),
    capture_output=True, text=True, timeout=30,
)
out_a, _ = pa.communicate(timeout=30)
print(out_a.strip().splitlines()[0])
print(pb.stdout.strip())
assert out_a.strip().splitlines()[0].endswith("True"), out_a
assert pb.stdout.strip().endswith("False"), pb.stdout
print("OK: A principal, B bloqueado")
