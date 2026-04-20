from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file (for development)
# .env file is in the project root (Eclaireur/), one level up from BASE_DIR (Projet/)
env_path = BASE_DIR.parent / '.env'

print(f"Looking for .env file at: {env_path}")