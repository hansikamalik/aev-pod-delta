import sys
from pathlib import Path

# Add project root directory to Python path for pytest module resolution
sys.path.insert(0, str(Path(__file__).parent))
