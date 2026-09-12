#!/usr/bin/env python3
"""
NexSolve P5.2 Leakage-Free Model Promotion Study Script.
Evaluates Candidate Models trained strictly on Y <= 2023 data against Y >= 2024 holdout
and 5-Fold Group-Structured Cross-Validation splits.

DO NOT OVERWRITE backend/model/landslide_model.pkl
All candidates are stored in backend/model/experimental/
"""

import hashlib
import json
import pickle
from pathlib import Path
import sys
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score,
    recall_score, f1_score, brier_score_loss, confusion_matrix
)
from sklearn.model_selection import GroupKFold

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"
PROD_MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
EXPERIMENTAL_DIR = BASE_DIR / "backend" / "model" / "experimental"
RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_results.csv"
REGISTRY_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_model_registry.json"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_model_promotion_report.md"

PROD_FEATURES = [
    "latitude", "longitude", "rainfall_1d", "rainfall_3d",
    "rainfall_7d", "month_sin", "month_cos"
]

TERRAIN_FEATURES = [
    "elevation_m", "slope_deg", "aspect_deg", "curvature",
    "district_mean_slope", "district_p90_slope"
]

INVENTORY_FEATURES = [
    "historical_event_count", "event_density_per_sqkm"
]

NO_GEO_FEATURES = [
    "rainfall_1d", "rainfall_3d", "rainfall_7d", "month_sin", "month_cos"
]

EXCLUDED_FEATURES = ["distance_to_nearest_event_km", "soilSat"]


def verify_prod_model_hash() -> str:
    with open(PROD_MODEL_PATH, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    expected = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"
    assert sha == expected, f"Production Model SHA mismatch: expected {expected}, got {sha}"
    return sha


def calculate_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_samples = len(y_true)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        if i == n_bins - 1:
            in_bin = (y_prob >= bin_lower) & (y_prob <= bin_upper)
        else:
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            
        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = np.mean(y_true[in_bin])
            bin_conf = np.mean(y_prob[in_bin])
            ece += (bin_size / n_samples) * abs(bin_acc - bin_conf)

    return float(ece)


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    
    roc_auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    pr_auc = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true, y_prob))
    ece = float(calculate_ece(y_true, y_prob))

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(ece, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    }


def run_promotion_study():
    print("=" * 80)
    print("NEXSOLVE P5.2 LEAKAGE-FREE MODEL PROMOTION STUDY")
    print("=" * 80)

    sha_initial = verify_prod_model_hash()
    print(f"Production Model Baseline SHA-256 Verified: {sha_initial}")

    EXPERIMENTAL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(FUSED_DATASET_PATH)
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["location_group"] = df["latitude"].astype(str) + "_" + df["longitude"].astype(str)

    train_df = df[df["year"] <= 2023].copy()
    test_df = df[df["year"] > 2023].copy()

    print(f"Dataset Total Samples: {len(df)}")
    print(f"Train Set (Year <= 2023): {len(train_df)} samples (Pos: {(train_df['landslide']==1).sum()}, Neg: {(train_df['landslide']==0).sum()})")
    print(f"Test Set (Year >= 2024): {len(test_df)} samples (Pos: {(test_df['landslide']==1).sum()}, Neg: {(test_df['landslide']==0).sum()})")

    candidates_def = [
        {
            "id": "Candidate_A_RF_Leakage_Free",
            "label": "RF-LEAKAGE-FREE-BASELINE",
            "features": PROD_FEATURES,
            "filename": "candidate_a_rf_leakage_free.pkl",
            "factory": lambda: RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "model_type": "RandomForestClassifier",
            "hyperparams": {"n_estimators": 300, "max_depth": 12, "min_samples_split": 5, "min_samples_leaf": 2, "class_weight": "balanced", "random_state": 42}
        },
        {
            "id": "Candidate_B_RF_Terrain",
            "label": "RF-TERRAIN-ENHANCED",
            "features": PROD_FEATURES + TERRAIN_FEATURES,
            "filename": "candidate_b_rf_terrain.pkl",
            "factory": lambda: RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "model_type": "RandomForestClassifier",
            "hyperparams": {"n_estimators": 300, "max_depth": 12, "min_samples_split": 5, "min_samples_leaf": 2, "class_weight": "balanced", "random_state": 42}
        },
        {
            "id": "Candidate_C_RF_Inventory",
            "label": "RF-TERRAIN-INVENTORY-ENHANCED",
            "features": PROD_FEATURES + TERRAIN_FEATURES + INVENTORY_FEATURES,
            "filename": "candidate_c_rf_inventory.pkl",
            "factory": lambda: RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "model_type": "RandomForestClassifier",
            "hyperparams": {"n_estimators": 300, "max_depth": 12, "min_samples_split": 5, "min_samples_leaf": 2, "class_weight": "balanced", "random_state": 42}
        },
        {
            "id": "Candidate_D_HistGB_Prod",
            "label": "HistGB-LEAKAGE-FREE-BASELINE",
            "features": PROD_FEATURES,
            "filename": "candidate_d_histgb_baseline.pkl",
            "factory": lambda: HistGradientBoostingClassifier(max_iter=100, random_state=42),
            "model_type": "HistGradientBoostingClassifier",
            "hyperparams": {"max_iter": 100, "random_state": 42}
        },
        {
            "id": "Diagnostic_RF_NoGeo",
            "label": "RF-NO-GEO-DIAGNOSTIC",
            "features": NO_GEO_FEATURES,
            "filename": "diagnostic_rf_nogeo.pkl",
            "factory": lambda: RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "model_type": "RandomForestClassifier",
            "hyperparams": {"n_estimators": 300, "max_depth": 12, "min_samples_split": 5, "min_samples_leaf": 2, "class_weight": "balanced", "random_state": 42}
        }
    ]

    all_results = []
    registry_entries = []

    for cdef in candidates_def:
        cid = cdef["id"]
        clabel = cdef["label"]
        feats = cdef["features"]
        fn = cdef["filename"]
        factory = cdef["factory"]
        art_path = EXPERIMENTAL_DIR / fn

        # Enforce feature safety check
        for exf in EXCLUDED_FEATURES:
            assert exf not in feats, f"Excluded feature {exf} found in candidate {cid}"

        # 1. Fit Candidate on Y <= 2023 Train Set ONLY
        model = factory()
        model.fit(train_df[feats], train_df["landslide"])

        # Save candidate artifact
        pkg = {"model": model, "features": feats, "label": clabel}
        with open(art_path, "wb") as f:
            pickle.dump(pkg, f)

        with open(art_path, "rb") as f:
            cand_sha = hashlib.sha256(f.read()).hexdigest()

        # Chronological Holdout Evaluation (Y >= 2024 Test Set)
        test_probs = model.predict_proba(test_df[feats])[:, 1]
        metrics_chrono = compute_metrics(test_df["landslide"].values, test_probs)

        all_results.append({
            "candidate_id": cid,
            "label": clabel,
            "feature_count": len(feats),
            "validation_strategy": "Chronological_Holdout",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "metrics": metrics_chrono
        })

        # Location-Group 5-Fold CV
        gkf_loc = GroupKFold(n_splits=5)
        loc_probs_list, loc_y_list = [], []
        for tr_idx, te_idx in gkf_loc.split(df, groups=df["location_group"]):
            tr, te = df.iloc[tr_idx], df.iloc[te_idx]
            fold_model = factory()
            fold_model.fit(tr[feats], tr["landslide"])
            p_fold = fold_model.predict_proba(te[feats])[:, 1]
            loc_probs_list.append(p_fold)
            loc_y_list.append(te["landslide"].values)
        all_loc_y = np.concatenate(loc_y_list)
        all_loc_probs = np.concatenate(loc_probs_list)
        metrics_loc = compute_metrics(all_loc_y, all_loc_probs)

        all_results.append({
            "candidate_id": cid,
            "label": clabel,
            "feature_count": len(feats),
            "validation_strategy": "Location_Group_5Fold_CV",
            "train_samples": len(df) * 4 // 5,
            "test_samples": len(df),
            "metrics": metrics_loc
        })

        # District-Group 5-Fold CV
        gkf_dist = GroupKFold(n_splits=5)
        dist_probs_list, dist_y_list = [], []
        for tr_idx, te_idx in gkf_dist.split(df, groups=df["district_id"]):
            tr, te = df.iloc[tr_idx], df.iloc[te_idx]
            fold_model = factory()
            fold_model.fit(tr[feats], tr["landslide"])
            p_fold = fold_model.predict_proba(te[feats])[:, 1]
            dist_probs_list.append(p_fold)
            dist_y_list.append(te["landslide"].values)
        all_dist_y = np.concatenate(dist_y_list)
        all_dist_probs = np.concatenate(dist_probs_list)
        metrics_dist = compute_metrics(all_dist_y, all_dist_probs)

        all_results.append({
            "candidate_id": cid,
            "label": clabel,
            "feature_count": len(feats),
            "validation_strategy": "District_Group_5Fold_CV",
            "train_samples": len(df) * 4 // 5,
            "test_samples": len(df),
            "metrics": metrics_dist
        })

        # Register Candidate
        status_val = "READY_FOR_PROMOTION_REVIEW" if cid == "Candidate_A_RF_Leakage_Free" else "EXPERIMENTAL"
        decision_val = "CANDIDATE-READY-FOR-PROMOTION-REVIEW" if cid == "Candidate_A_RF_Leakage_Free" else "NOT_PROMOTED"

        registry_entries.append({
            "model_id": cid,
            "label": clabel,
            "model_type": cdef["model_type"],
            "feature_set": feats,
            "training_cutoff": "date <= 2023-12-31",
            "validation_protocol": "Chronological_Holdout_and_GroupKFold",
            "hyperparameters": cdef["hyperparams"],
            "artifact_path": str(art_path.relative_to(BASE_DIR)),
            "artifact_sha256": cand_sha,
            "status": status_val,
            "promotion_decision": decision_val,
            "chronological_roc_auc": metrics_chrono["roc_auc"],
            "location_cv_roc_auc": metrics_loc["roc_auc"],
            "district_cv_roc_auc": metrics_dist["roc_auc"]
        })

    # Save JSON and CSV results
    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    flat_rows = []
    for r in all_results:
        m = r["metrics"]
        flat_rows.append({
            "candidate_id": r["candidate_id"],
            "label": r["label"],
            "feature_count": r["feature_count"],
            "validation_strategy": r["validation_strategy"],
            "roc_auc": m["roc_auc"],
            "pr_auc": m["pr_auc"],
            "precision": m["precision"],
            "recall": m["recall"],
            "f1_score": m["f1_score"],
            "brier_score": m["brier_score"],
            "ece": m["expected_calibration_error"],
            "true_negatives": m["confusion_matrix"]["true_negatives"],
            "false_positives": m["confusion_matrix"]["false_positives"],
            "false_negatives": m["confusion_matrix"]["false_negatives"],
            "true_positives": m["confusion_matrix"]["true_positives"]
        })

    pd.DataFrame(flat_rows).to_csv(RESULTS_CSV_PATH, index=False)

    # Save Registry
    with open(REGISTRY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(registry_entries, f, indent=2)

    print(f"\nSaved machine-readable results to {RESULTS_JSON_PATH} and {RESULTS_CSV_PATH}")
    print(f"Saved candidate model registry to {REGISTRY_JSON_PATH}")

    sha_final = verify_prod_model_hash()
    print(f"Final Production Model SHA-256 Verified: {sha_final}")
    assert sha_final == sha_initial, "PRODUCTION MODEL WAS OVERWRITTEN!"


if __name__ == "__main__":
    run_promotion_study()
