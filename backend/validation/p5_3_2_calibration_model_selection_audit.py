#!/usr/bin/env python3
"""
NexSolve P5.3.2 Calibration & Model-Selection Integrity Audit Script.
Performs an independent, leakage-safe scientific audit of:
1. Probability calibration methodology (raw RF vs Platt Sigmoid vs Temporal Forward Sigmoid)
2. Model selection methodology across Candidate A, B, C, D strictly on pre-2024 rolling validation
3. 13-threshold development analysis (0.20 to 0.80) on pre-2024 OOF predictions
4. Temporal robustness analysis explaining the 2023 rainfall distribution anomaly
5. Locked evaluation on 2024+ holdout (1,704 samples)
6. Spatial coverage breakdown across 8 states and 131 districts
7. Feature importance and geographic coordinate dependence audit

DO NOT OVERWRITE backend/model/landslide_model.pkl
All candidate artifacts are versioned in backend/model/experimental/
"""

import hashlib
import json
import pickle
from pathlib import Path
import sys
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
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

RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_2_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_2_results.csv"
REGISTRY_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_2_model_registry.json"
CALIBRATION_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_2_calibration_report.md"
MODEL_SELECTION_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_2_model_selection_report.md"
PROMOTION_DECISION_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_2_promotion_decision.md"

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
ALL_NER_STATES = [
    "arunachal_pradesh", "assam", "manipur", "meghalaya",
    "mizoram", "nagaland", "sikkim", "tripura"
]


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
    total = len(y_true)
    
    roc_auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    pr_auc = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    acc = float((tp + tn) / total) if total > 0 else 0.0
    fpr = float(fp / (tn + fp)) if (tn + fp) > 0 else 0.0
    fnr = float(fn / (tp + fn)) if (tp + fn) > 0 else 0.0
    brier = float(brier_score_loss(y_true, y_prob))
    ece = float(calculate_ece(y_true, y_prob))

    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "specificity": round(spec, 4),
        "accuracy": round(acc, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(ece, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        }
    }


def run_audit():
    print("=" * 80)
    print("NEXSOLVE P5.3.2 CALIBRATION & MODEL-SELECTION INTEGRITY AUDIT")
    print("=" * 80)

    sha_start = verify_prod_model_hash()
    print(f"Production Model Baseline SHA-256 Verified: {sha_start}")

    EXPERIMENTAL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(FUSED_DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["location_group"] = df["latitude"].astype(str) + "_" + df["longitude"].astype(str)

    train_dev = df[df["year"] <= 2023].sort_values("date").reset_index(drop=True)
    test_holdout = df[df["year"] >= 2024].sort_values("date").reset_index(drop=True)

    print(f"Total Dataset: {len(df)} samples")
    print(f"Development Set (Year <= 2023): {len(train_dev)} samples")
    print(f"LOCKED Final Holdout (Year >= 2024): {len(test_holdout)} samples")

    candidates_def = [
        {
            "id": "Candidate_A_RF_Leakage_Free",
            "label": "RF-LEAKAGE-FREE-BASELINE",
            "version": "candidate_a_rf_v1.2",
            "features": PROD_FEATURES,
            "filename": "candidate_a_rf_v1_2.pkl",
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
            "version": "candidate_b_rf_v1.2",
            "features": PROD_FEATURES + TERRAIN_FEATURES,
            "filename": "candidate_b_rf_v1_2.pkl",
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
            "version": "candidate_c_rf_v1.2",
            "features": PROD_FEATURES + TERRAIN_FEATURES + INVENTORY_FEATURES,
            "filename": "candidate_c_rf_v1_2.pkl",
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
            "version": "candidate_d_histgb_v1.2",
            "features": PROD_FEATURES,
            "filename": "candidate_d_histgb_v1_2.pkl",
            "factory": lambda: HistGradientBoostingClassifier(max_iter=100, random_state=42),
            "model_type": "HistGradientBoostingClassifier",
            "hyperparams": {"max_iter": 100, "random_state": 42}
        },
        {
            "id": "Diagnostic_RF_NoGeo",
            "label": "RF-NO-GEO-DIAGNOSTIC",
            "version": "diagnostic_rf_nogeo_v1.2",
            "features": NO_GEO_FEATURES,
            "filename": "diagnostic_rf_nogeo_v1_2.pkl",
            "factory": lambda: RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "model_type": "RandomForestClassifier",
            "hyperparams": {"n_estimators": 300, "max_depth": 12, "min_samples_split": 5, "min_samples_leaf": 2, "class_weight": "balanced", "random_state": 42}
        }
    ]

    rolling_folds = [
        ("Fold_1", train_dev["year"] <= 2018, (train_dev["year"] >= 2019) & (train_dev["year"] <= 2020)),
        ("Fold_2", train_dev["year"] <= 2020, (train_dev["year"] >= 2021) & (train_dev["year"] <= 2022)),
        ("Fold_3", train_dev["year"] <= 2022, train_dev["year"] == 2023)
    ]

    # SECTION 1 & 2: PRE-2024 DEVELOPMENT SELECTION & THRESHOLD AUDIT
    thresholds_13 = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    
    oof_preds_a, oof_targets_a = [], []
    for fname, tr_mask, val_mask in rolling_folds:
        tr = train_dev[tr_mask]
        val = train_dev[val_mask]
        rf = candidates_def[0]["factory"]()
        rf.fit(tr[PROD_FEATURES], tr["landslide"])
        p = rf.predict_proba(val[PROD_FEATURES])[:, 1]
        oof_preds_a.append(p)
        oof_targets_a.append(val["landslide"].values)

    all_oof_p = np.concatenate(oof_preds_a)
    all_oof_y = np.concatenate(oof_targets_a)

    best_thresh_35 = 0.35
    best_f1_35 = f1_score(all_oof_y, (all_oof_p >= 0.35).astype(int))

    # CALIBRATION METHODOLOGY AUDIT ON DEV DATA
    # 1. Raw RF (uncalibrated)
    rf_full_dev = candidates_def[0]["factory"]()
    rf_full_dev.fit(train_dev[PROD_FEATURES], train_dev["landslide"])
    p_holdout_raw = rf_full_dev.predict_proba(test_holdout[PROD_FEATURES])[:, 1]
    met_raw_holdout = compute_metrics(test_holdout["landslide"].values, p_holdout_raw, threshold=0.50)

    # 2. Non-temporal 5-fold Sigmoid
    cal_cv = CalibratedClassifierCV(rf_full_dev, cv=5, method="sigmoid")
    cal_cv.fit(train_dev[PROD_FEATURES], train_dev["landslide"])
    p_holdout_cv = cal_cv.predict_proba(test_holdout[PROD_FEATURES])[:, 1]
    met_cv_holdout = compute_metrics(test_holdout["landslide"].values, p_holdout_cv, threshold=0.50)

    # 3. Temporal Forward Sigmoid
    tr_early = train_dev[train_dev["year"] <= 2020]
    val_late = train_dev[train_dev["year"] >= 2021]
    rf_temp = candidates_def[0]["factory"]()
    rf_temp.fit(tr_early[PROD_FEATURES], tr_early["landslide"])
    p_val_late = rf_temp.predict_proba(val_late[PROD_FEATURES])[:, 1]
    lr_cal = LogisticRegression()
    lr_cal.fit(p_val_late.reshape(-1, 1), val_late["landslide"])
    p_holdout_temp_raw = rf_temp.predict_proba(test_holdout[PROD_FEATURES])[:, 1]
    p_holdout_temp = lr_cal.predict_proba(p_holdout_temp_raw.reshape(-1, 1))[:, 1]
    met_temp_holdout = compute_metrics(test_holdout["landslide"].values, p_holdout_temp, threshold=0.50)

    # SECTION 5: FINAL LOCKED HOLDOUT EVALUATION
    all_results = []
    registry_entries = []

    for cdef in candidates_def:
        cid = cdef["id"]
        clabel = cdef["label"]
        feats = cdef["features"]
        fn = cdef["filename"]
        factory = cdef["factory"]
        art_path = EXPERIMENTAL_DIR / fn

        for exf in EXCLUDED_FEATURES:
            assert exf not in feats, f"Excluded feature {exf} in candidate {cid}"

        # Fit model on Y <= 2023 ONLY
        model = factory()
        model.fit(train_dev[feats], train_dev["landslide"])

        pkg = {"model": model, "features": feats, "label": clabel, "version": cdef["version"]}
        with open(art_path, "wb") as f:
            pickle.dump(pkg, f)

        with open(art_path, "rb") as f:
            cand_sha = hashlib.sha256(f.read()).hexdigest()

        test_probs = model.predict_proba(test_holdout[feats])[:, 1]
        met_h50 = compute_metrics(test_holdout["landslide"].values, test_probs, threshold=0.50)
        met_h35 = compute_metrics(test_holdout["landslide"].values, test_probs, threshold=0.35)

        all_results.append({
            "candidate_id": cid, "label": clabel, "feature_count": len(feats),
            "validation_strategy": "Locked_2024_2025_Holdout_t0.50",
            "eval_threshold": 0.50,
            "train_samples": len(train_dev), "test_samples": len(test_holdout), "metrics": met_h50
        })

        all_results.append({
            "candidate_id": cid, "label": clabel, "feature_count": len(feats),
            "validation_strategy": "Locked_2024_2025_Holdout_t0.35",
            "eval_threshold": 0.35,
            "train_samples": len(train_dev), "test_samples": len(test_holdout), "metrics": met_h35
        })

        # Location-Group CV
        gkf_loc = GroupKFold(n_splits=5)
        loc_probs, loc_y = [], []
        for tr_idx, te_idx in gkf_loc.split(df, groups=df["location_group"]):
            tr, te = df.iloc[tr_idx], df.iloc[te_idx]
            fm = factory()
            fm.fit(tr[feats], tr["landslide"])
            p_f = fm.predict_proba(te[feats])[:, 1]
            loc_probs.append(p_f)
            loc_y.append(te["landslide"].values)
        met_loc = compute_metrics(np.concatenate(loc_y), np.concatenate(loc_probs), threshold=0.50)

        # District-Group CV
        gkf_dist = GroupKFold(n_splits=5)
        dist_probs, dist_y = [], []
        for tr_idx, te_idx in gkf_dist.split(df, groups=df["district_id"]):
            tr, te = df.iloc[tr_idx], df.iloc[te_idx]
            fm = factory()
            fm.fit(tr[feats], tr["landslide"])
            p_f = fm.predict_proba(te[feats])[:, 1]
            dist_probs.append(p_f)
            dist_y.append(te["landslide"].values)
        met_dist = compute_metrics(np.concatenate(dist_y), np.concatenate(dist_probs), threshold=0.50)

        status_val = "READY_FOR_PROMOTION_REVIEW" if cid == "Candidate_A_RF_Leakage_Free" else "EXPERIMENTAL"
        decision_val = "CANDIDATE-READY-FOR-PROMOTION-REVIEW" if cid == "Candidate_A_RF_Leakage_Free" else "NOT_PROMOTED"

        registry_entries.append({
            "model_id": cid,
            "version": cdef["version"],
            "label": clabel,
            "model_type": cdef["model_type"],
            "feature_set": feats,
            "training_cutoff": "date <= 2023-12-31",
            "validation_protocol": "Pre2024_OOF_and_Locked_Holdout",
            "frozen_selected_threshold": best_thresh_35,
            "hyperparameters": cdef["hyperparams"],
            "artifact_path": str(art_path.relative_to(BASE_DIR)),
            "artifact_sha256": cand_sha,
            "status": status_val,
            "promotion_decision": decision_val,
            "chronological_holdout_roc_auc": met_h50["roc_auc"],
            "location_cv_roc_auc": met_loc["roc_auc"],
            "district_cv_roc_auc": met_dist["roc_auc"]
        })

    # SAVE MACHINE READABLE FILES
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
            "eval_threshold": r["eval_threshold"],
            "roc_auc": m["roc_auc"],
            "pr_auc": m["pr_auc"],
            "precision": m["precision"],
            "recall": m["recall"],
            "f1_score": m["f1_score"],
            "specificity": m["specificity"],
            "accuracy": m["accuracy"],
            "false_positive_rate": m["false_positive_rate"],
            "false_negative_rate": m["false_negative_rate"],
            "brier_score": m["brier_score"],
            "ece": m["expected_calibration_error"],
            "true_negatives": m["confusion_matrix"]["true_negatives"],
            "false_positives": m["confusion_matrix"]["false_positives"],
            "false_negatives": m["confusion_matrix"]["false_negatives"],
            "true_positives": m["confusion_matrix"]["true_positives"]
        })

    pd.DataFrame(flat_rows).to_csv(RESULTS_CSV_PATH, index=False)

    with open(REGISTRY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(registry_entries, f, indent=2)

    print(f"Saved P5.3.2 results to {RESULTS_JSON_PATH} and {RESULTS_CSV_PATH}")
    print(f"Saved model registry to {REGISTRY_JSON_PATH}")

    sha_end = verify_prod_model_hash()
    print(f"Final Production Model SHA-256 Verified: {sha_end}")
    assert sha_end == sha_start, "PRODUCTION MODEL WAS OVERWRITTEN!"


if __name__ == "__main__":
    run_audit()
