"""Configuration settings for SATARK Backend."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Database configuration
DB_PATH = os.getenv("SATARK_DB_PATH", str(BASE_DIR / "satark.db"))

# Policy and template configuration
POLICY_FILE_PATH = os.getenv("SATARK_POLICY_FILE", str(BASE_DIR / "policy" / "policy.yaml"))
TEMPLATE_MAP_PATH = os.getenv("SATARK_TEMPLATE_MAP", str(BASE_DIR / "policy" / "template_map.json"))

# Model configuration: the single copy of the trained bundle lives in model_service/models/
MODEL_PATH = os.getenv("SATARK_MODEL_PATH", str(BASE_DIR.parent / "model_service" / "models" / "satark_model.joblib"))
THRESHOLDS_PATH = os.getenv("SATARK_THRESHOLDS_PATH", str(BASE_DIR.parent / "model_service" / "models" / "thresholds.json"))

# System versions
POLICY_VERSION = "1.0.0"
MODEL_VERSION = "satark_fusion_v1.0.0"

# Server configuration
HOST = os.getenv("SATARK_HOST", "0.0.0.0")
PORT = int(os.getenv("SATARK_PORT", "8000"))
DEBUG = os.getenv("SATARK_DEBUG", "false").lower() == "true"

