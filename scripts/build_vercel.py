import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_SRC = BASE_DIR / "static"
PUBLIC_DIR = BASE_DIR / "public"
STATIC_DEST = PUBLIC_DIR / "static"

def build_vercel_static():
    if not STATIC_SRC.exists():
        print(f"Error: Source static directory {STATIC_SRC} does not exist.")
        return

    # Create public directory if needed
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    # Recursively copy static directory to public/static, overwriting existing files
    shutil.copytree(STATIC_SRC, STATIC_DEST, dirs_exist_ok=True)
    print(f"Successfully copied {STATIC_SRC} -> {STATIC_DEST}")


if __name__ == "__main__":
    build_vercel_static()
