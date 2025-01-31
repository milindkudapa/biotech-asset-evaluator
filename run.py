#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Import and run the main function
from src.main import main

if __name__ == "__main__":
    main() 