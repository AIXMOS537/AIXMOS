#!/usr/bin/env python3
"""Installed AIXMOS entry point; works from any current directory."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'vendor')]

if __name__ == '__main__':
    from aixmos.local_cli import main
    main()
