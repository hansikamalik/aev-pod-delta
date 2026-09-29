import sys
from pathlib import Path

# Make sure `sync_engine` is importable when pytest is run from this folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
