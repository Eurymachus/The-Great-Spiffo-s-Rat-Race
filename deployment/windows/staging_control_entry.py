"""Isolated interpreter entry; import only the administrator-controlled directory."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import staging_control
sys.argv = [__file__, "process"]
staging_control.main()
