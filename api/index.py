import os
import sys

# Ensure repository root is on sys.path for Vercel Serverless Function imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()
