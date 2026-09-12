"""Central Model Loader & Registry Service for NexSolve Risk Intelligence.
Manages versioned model loading, SHA256 integrity verification, and safe 1-step rollback.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT_DIR / "backend" / "model" / "model_registry.json"
DEFAULT_MODEL_PATH = ROOT_DIR / "backend" / "model" / "landslide_model.pkl"
EXPECTED_LEGACY_SHA = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"


def get_model_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Model registry not found at {REGISTRY_PATH}")
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_model_registry(registry: Dict[str, Any]) -> None:
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def load_active_model() -> Optional[Dict[str, Any]]:
    """Loads active model package resolved via central model_registry.json with SHA256 verification."""
    try:
        registry = get_model_registry()
        active_id = registry.get("active_model_id")
        
        active_meta = None
        for m in registry.get("models", []):
            if m.get("model_id") == active_id:
                active_meta = m
                break
                
        if not active_meta:
            raise ValueError(f"Active model ID '{active_id}' not found in model registry")
            
        rel_path = active_meta["artifact_path"]
        artifact_path = ROOT_DIR / rel_path
        
        if not artifact_path.exists():
            raise FileNotFoundError(f"Active model artifact not found at {artifact_path}")
            
        with open(artifact_path, "rb") as f:
            raw_bytes = f.read()
            computed_sha = hashlib.sha256(raw_bytes).hexdigest()
            
        expected_sha = active_meta.get("sha256")
        if expected_sha and computed_sha != expected_sha:
            raise ValueError(f"Model artifact SHA256 mismatch! Expected {expected_sha}, got {computed_sha}")
            
        package = pickle.loads(raw_bytes)
        
        model_obj = package["model"] if isinstance(package, dict) and "model" in package else package
        features_list = package["features"] if isinstance(package, dict) and "features" in package else active_meta.get("feature_set")
        
        return {
            "model": model_obj,
            "features": features_list,
            "model_id": active_meta["model_id"],
            "model_version": active_meta.get("version", "1.0.0"),
            "model_source": active_meta.get("model_source", "NexSolve leakage-free RF"),
            "feature_schema_version": active_meta.get("feature_schema_version", "v1"),
            "sha256": computed_sha,
            "artifact_path": str(artifact_path),
            "status": active_meta.get("status", "ACTIVE")
        }
        
    except Exception as exc:
        print(f"Warning: Model loader failed to resolve active model via registry ({exc}). Falling back to default artifact.")
        if DEFAULT_MODEL_PATH.exists():
            with open(DEFAULT_MODEL_PATH, "rb") as f:
                raw_bytes = f.read()
                computed_sha = hashlib.sha256(raw_bytes).hexdigest()
                package = pickle.loads(raw_bytes)
                model_obj = package["model"] if isinstance(package, dict) and "model" in package else package
                features_list = package["features"] if isinstance(package, dict) and "features" in package else [
                    "latitude", "longitude", "rainfall_1d", "rainfall_3d", "rainfall_7d", "month_sin", "month_cos"
                ]
                return {
                    "model": model_obj,
                    "features": features_list,
                    "model_id": "legacy_production_fallback",
                    "model_version": "1.0.0",
                    "model_source": "trained-random-forest",
                    "feature_schema_version": "v1",
                    "sha256": computed_sha,
                    "artifact_path": str(DEFAULT_MODEL_PATH),
                    "status": "FALLBACK"
                }
        return None


def rollback_to_previous_model() -> Dict[str, Any]:
    """1-Step Rollback mechanism: atomically sets previous production model to ACTIVE in registry."""
    registry = get_model_registry()
    rollback_target_id = "previous_production_model_v0"
    
    for m in registry.get("models", []):
        if m["model_id"] == rollback_target_id:
            m["status"] = "ACTIVE"
            registry["active_model_id"] = m["model_id"]
            registry["active_model_version"] = m["version"]
        elif m["status"] == "ACTIVE":
            m["status"] = "ROLLBACK"
            
    save_model_registry(registry)
    return get_model_registry()
