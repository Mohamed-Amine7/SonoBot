"""
Pytest configuration — adds the project root to sys.path so that
`from config import ...`, `from utils import ...`, etc. work without
per-file sys.path hacks.
"""

import sys
import os

# Add the project root (parent of tests/) to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
