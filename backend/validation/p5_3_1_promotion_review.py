#!/usr/bin/env python3
"""
NexSolve P5.3.1 Final Leakage-Safe Model Promotion Review Correction Script.
Enforces strict temporal locking of the 2024+ final holdout:
1. Internal pre-2024 rolling temporal validation (Fold 1: <=2018 vs 2019-20, Fold 2: <=2020 vs 2021-22, Fold 3: <=2022 vs 2023)
   used exclusively for threshold selection, calibration fitting, and internal model selection.
2. Locked evaluation on 2024+ final holdout (1,704 samples) performed AFTER freezing all decisions.
3. Verification that backend/model/landslide_model.pkl is UNCHANGED.
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

RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_results.csv"
REGISTRY_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_model_registry.json"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_promotion_review_report.md"
CALIBRATION_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_calibration_report.md"
THRESHOLD_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_threshold_analysis.csv"
STATE_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_state_performance.csv"
DISTRICT_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_district_performance.csv"

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


def run_promotion_review_correction():
    print("=" * 80)
    print("NEXSOLVE P5.3.1 FINAL LEAKAGE-SAFE PROMOTION REVIEW CORRECTION")
    print("=" * 80)

    sha_start = verify_prod_model_hash()
    print(f"Production Model Baseline SHA-256 Verified: {sha_start}")

    EXPERIMENTAL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(FUSED_DATASET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["location_group"] = df["latitude"].astype(str) + "_" + df["longitude"].astype(str)

    # 1. TEMPORAL PARTITIONING
    train_dev = df[df["year"] <= 2023].sort_values("date").reset_index(drop=True)
    test_holdout = df[df["year"] >= 2024].sort_values("date").reset_index(drop=True)

    print(f"Total Dataset: {len(df)} samples")
    print(f"Development Set (Year <= 2023): {len(train_dev)} samples")
    print(f"LOCKED Final Holdout (Year >= 2024): {len(test_holdout)} samples")

    # Strict leakage assertion: confirm zero test_holdout overlap in train_dev
    assert len(train_dev[train_dev["year"] >= 2024]) == 0, "TEST SAMPLES DETECTED IN DEV SET!"

    candidates_def = [
        {
            "id": "Candidate_A_RF_Leakage_Free",
            "label": "RF-LEAKAGE-FREE-BASELINE",
            "version": "candidate_a_rf_v1.1",
            "features": PROD_FEATURES,
            "filename": "candidate_a_rf_v1_1.pkl",
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
            "version": "candidate_b_rf_v1.1",
            "features": PROD_FEATURES + TERRAIN_FEATURES,
            "filename": "candidate_b_rf_v1_1.pkl",
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
            "version": "candidate_c_rf_v1.1",
            "features": PROD_FEATURES + TERRAIN_FEATURES + INVENTORY_FEATURES,
            "filename": "candidate_c_rf_v1_1.pkl",
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
            "version": "candidate_d_histgb_v1.1",
            "features": PROD_FEATURES,
            "filename": "candidate_d_histgb_v1_1.pkl",
            "factory": lambda: HistGradientBoostingClassifier(max_iter=100, random_state=42),
            "model_type": "HistGradientBoostingClassifier",
            "hyperparams": {"max_iter": 100, "random_state": 42}
        },
        {
            "id": "Diagnostic_RF_NoGeo",
            "label": "RF-NO-GEO-DIAGNOSTIC",
            "version": "diagnostic_rf_nogeo_v1.1",
            "features": NO_GEO_FEATURES,
            "filename": "diagnostic_rf_nogeo_v1_1.pkl",
            "factory": lambda: RandomForestClassifier(
                n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
                class_weight="balanced", random_state=42, n_jobs=-1
            ),
            "model_type": "RandomForestClassifier",
            "hyperparams": {"n_estimators": 300, "max_depth": 12, "min_samples_split": 5, "min_samples_leaf": 2, "class_weight": "balanced", "random_state": 42}
        }
    ]

    # 2. INTERNAL PRE-2024 ROLLING TEMPORAL VALIDATION & THRESHOLD / CALIBRATION SELECTION
    rolling_folds = [
        ("Fold_1", train_dev["year"] <= 2018, (train_dev["year"] >= 2019) & (train_dev["year"] <= 2020)),
        ("Fold_2", train_dev["year"] <= 2020, (train_dev["year"] >= 2021) & (train_dev["year"] <= 2022)),
        ("Fold_3", train_dev["year"] <= 2022, train_dev["year"] == 2023)
    ]

    print("\n--- PHASE 1: PRE-2024 INTERNAL ROLLING VALIDATION ---")
    val_preds_cand_a = []
    val_targets_cand_a = []

    for fname, tr_mask, val_mask in rolling_folds:
        tr_data = train_dev[tr_mask]
        val_data = train_dev[val_mask]
        rf = RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1)
        rf.fit(tr_data[PROD_FEATURES], tr_data["landslide"])
        p_val = rf.predict_proba(val_data[PROD_FEATURES])[:, 1]
        val_preds_cand_a.append(p_val)
        val_targets_cand_a.append(val_data["landslide"].values)
        auc_fold = roc_auc_score(val_data["landslide"], p_val)
        print(f"Internal {fname} (Train n={len(tr_data)}, Val n={len(val_data)}) | Val ROC-AUC: {auc_fold:.4f}")

    all_val_preds_a = np.concatenate(val_preds_cand_a)
    all_val_targets_a = np.concatenate(val_targets_cand_a)

    # Evaluate Candidate Thresholds ONLY on internal pre-2024 predictions
    thresholds = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
    best_thresh_internal = 0.50
    best_f1_internal = 0.0
    thresh_eval_rows = []

    for t in thresholds:
        preds_t = (all_val_preds_a >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(all_val_targets_a, preds_t, labels=[0, 1]).ravel()
        prec = precision_score(all_val_targets_a, preds_t, zero_division=0)
        rec = recall_score(all_val_targets_a, preds_t, zero_division=0)
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        fpr = fp / (tn + fp) if (tn + fp) > 0 else 0.0
        fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = f1_score(all_val_targets_a, preds_t, zero_division=0)

        if f1 > best_f1_internal:
            best_f1_internal = f1
            best_thresh_internal = t

        if t <= 0.30:
            band = "GREEN_PROTOTYPE (Low Risk Band — High Sensitivity)"
        elif t <= 0.50:
            band = "YELLOW_PROTOTYPE (Balanced Operations Band)"
        elif t <= 0.70:
            band = "ORANGE_PROTOTYPE (Elevated Risk Band)"
        else:
            band = "RED_PROTOTYPE (High Confidence Alert Band)"

        thresh_eval_rows.append({
            "threshold": t,
            "stage": "INTERNAL_PRE2024_DEVELOPMENT",
            "prototype_risk_band": band,
            "disclaimer": "prototype decision-support thresholds requiring domain/expert validation",
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "specificity": round(spec, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "f1_score": round(f1, 4),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        })

    print(f"\nFROZEN THRESHOLD SELECTED FROM PRE-2024 INTERNAL VALIDATION: {best_thresh_internal:.2f} (Internal F1: {best_f1_internal:.4f})")

    # Fit Calibration Model STRICTLY on Pre-2024 Development Data
    rf_base_pre2024 = RandomForestClassifier(
        n_estimators=300, max_depth=12, min_samples_split=5, min_samples_leaf=2,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    cal_model_frozen = CalibratedClassifierCV(rf_base_pre2024, cv=5, method="sigmoid")
    cal_model_frozen.fit(train_dev[PROD_FEATURES], train_dev["landslide"])

    # 3. FIT CANDIDATES ON FULL PRE-2024 DEV SET & EVALUATE ON LOCKED 2024+ HOLDOUT
    print("\n--- PHASE 2: EVALUATING FROZEN CANDIDATES ON LOCKED 2024+ HOLDOUT ---")
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

        # Final Evaluation on LOCKED 2024+ Holdout
        test_probs = model.predict_proba(test_holdout[feats])[:, 1]
        met_holdout = compute_metrics(test_holdout["landslide"].values, test_probs, threshold=0.50)
        met_holdout_sel_thresh = compute_metrics(test_holdout["landslide"].values, test_probs, threshold=best_thresh_internal)

        all_results.append({
            "candidate_id": cid, "label": clabel, "feature_count": len(feats),
            "validation_strategy": "Locked_2024_2025_Holdout_DefaultThresh",
            "eval_threshold": 0.50,
            "train_samples": len(train_dev), "test_samples": len(test_holdout), "metrics": met_holdout
        })

        all_results.append({
            "candidate_id": cid, "label": clabel, "feature_count": len(feats),
            "validation_strategy": "Locked_2024_2025_Holdout_SelectedThresh",
            "eval_threshold": best_thresh_internal,
            "train_samples": len(train_dev), "test_samples": len(test_holdout), "metrics": met_holdout_sel_thresh
        })

        # Internal Rolling Fold Results for Candidate Reporting
        for fname, tr_mask, val_mask in rolling_folds:
            tr_d = train_dev[tr_mask]
            val_d = train_dev[val_mask]
            m_f = factory()
            m_f.fit(tr_d[feats], tr_d["landslide"])
            p_f = m_f.predict_proba(val_d[feats])[:, 1]
            met_f = compute_metrics(val_d["landslide"].values, p_f, threshold=0.50)
            all_results.append({
                "candidate_id": cid, "label": clabel, "feature_count": len(feats),
                "validation_strategy": f"Internal_Rolling_{fname}",
                "eval_threshold": 0.50,
                "train_samples": len(tr_d), "test_samples": len(val_d), "metrics": met_f
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
        all_results.append({
            "candidate_id": cid, "label": clabel, "feature_count": len(feats),
            "validation_strategy": "Location_Group_5Fold_CV",
            "eval_threshold": 0.50,
            "train_samples": len(df) * 4 // 5, "test_samples": len(df), "metrics": met_loc
        })

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
        all_results.append({
            "candidate_id": cid, "label": clabel, "feature_count": len(feats),
            "validation_strategy": "District_Group_5Fold_CV",
            "eval_threshold": 0.50,
            "train_samples": len(df) * 4 // 5, "test_samples": len(df), "metrics": met_dist
        })

        status_val = "READY_FOR_PROMOTION_REVIEW" if cid == "Candidate_A_RF_Leakage_Free" else "EXPERIMENTAL"
        decision_val = "CANDIDATE-READY-FOR-PROMOTION-REVIEW" if cid == "Candidate_A_RF_Leakage_Free" else "NOT_PROMOTED"

        registry_entries.append({
            "model_id": cid,
            "version": cdef["version"],
            "label": clabel,
            "model_type": cdef["model_type"],
            "feature_set": feats,
            "training_cutoff": "date <= 2023-12-31",
            "validation_protocol": "Strict_Internal_Rolling_and_Locked_Holdout",
            "frozen_selected_threshold": best_thresh_internal,
            "hyperparameters": cdef["hyperparams"],
            "artifact_path": str(art_path.relative_to(BASE_DIR)),
            "artifact_sha256": cand_sha,
            "status": status_val,
            "promotion_decision": decision_val,
            "chronological_holdout_roc_auc": met_holdout["roc_auc"],
            "location_cv_roc_auc": met_loc["roc_auc"],
            "district_cv_roc_auc": met_dist["roc_auc"]
        })

    # Evaluate Frozen Thresholds on LOCKED Holdout for reporting
    cand_a_model = candidates_def[0]["factory"]()
    cand_a_model.fit(train_dev[PROD_FEATURES], train_dev["landslide"])
    test_probs_a = cand_a_model.predict_proba(test_holdout[PROD_FEATURES])[:, 1]

    for t in thresholds:
        preds_t = (test_probs_a >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(test_holdout["landslide"], preds_t, labels=[0, 1]).ravel()
        prec = precision_score(test_holdout["landslide"], preds_t, zero_division=0)
        rec = recall_score(test_holdout["landslide"], preds_t, zero_division=0)
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        fpr = fp / (tn + fp) if (tn + fp) > 0 else 0.0
        fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = f1_score(test_holdout["landslide"], preds_t, zero_division=0)

        if t <= 0.30:
            band = "GREEN_PROTOTYPE (Low Risk Band — High Sensitivity)"
        elif t <= 0.50:
            band = "YELLOW_PROTOTYPE (Balanced Operations Band)"
        elif t <= 0.70:
            band = "ORANGE_PROTOTYPE (Elevated Risk Band)"
        else:
            band = "RED_PROTOTYPE (High Confidence Alert Band)"

        thresh_eval_rows.append({
            "threshold": t,
            "stage": "LOCKED_2024_2025_HOLDOUT_EVALUATION",
            "prototype_risk_band": band,
            "disclaimer": "prototype decision-support thresholds requiring domain/expert validation",
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "specificity": round(spec, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "f1_score": round(f1, 4),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        })

    pd.DataFrame(thresh_eval_rows).to_csv(THRESHOLD_CSV_PATH, index=False)

    # Evaluate Frozen Calibration Model on LOCKED Holdout
    cal_probs_holdout = cal_model_frozen.predict_proba(test_holdout[PROD_FEATURES])[:, 1]
    met_cal_holdout = compute_metrics(test_holdout["landslide"].values, cal_probs_holdout, threshold=0.50)

    # 4. STATE-WISE PERFORMANCE ON LOCKED HOLDOUT
    state_rows = []
    for state in ALL_NER_STATES:
        st_df = test_holdout[test_holdout["state_id"] == state]
        n_total = len(st_df)
        n_pos = (st_df["landslide"] == 1).sum() if n_total > 0 else 0
        n_neg = (st_df["landslide"] == 0).sum() if n_total > 0 else 0

        if n_total == 0:
            state_rows.append({
                "state_id": state, "total_samples": 0, "positive_count": 0, "control_count": 0,
                "status": "NO_TEST_SAMPLES", "roc_auc": "N/A", "pr_auc": "N/A",
                "recall": "N/A", "precision": "N/A", "f1_score": "N/A"
            })
            continue

        p_st = test_probs_a[test_holdout["state_id"] == state]
        pr_st = (p_st >= 0.50).astype(int)

        if n_pos > 0 and n_neg > 0 and n_total >= 10:
            s_auc = round(float(roc_auc_score(st_df["landslide"], p_st)), 4)
            s_pr_auc = round(float(average_precision_score(st_df["landslide"], p_st)), 4)
            s_prec = round(float(precision_score(st_df["landslide"], pr_st, zero_division=0)), 4)
            s_rec = round(float(recall_score(st_df["landslide"], pr_st, zero_division=0)), 4)
            s_f1 = round(float(f1_score(st_df["landslide"], pr_st, zero_division=0)), 4)
            s_status = "EVALUATED"
        else:
            s_auc = "N/A"
            s_pr_auc = "N/A"
            s_prec = round(float(precision_score(st_df["landslide"], pr_st, zero_division=0)), 4) if n_pos > 0 else "N/A"
            s_rec = round(float(recall_score(st_df["landslide"], pr_st, zero_division=0)), 4) if n_pos > 0 else "N/A"
            s_f1 = round(float(f1_score(st_df["landslide"], pr_st, zero_division=0)), 4) if n_pos > 0 else "N/A"
            s_status = "INSUFFICIENT_SUPPORT"

        state_rows.append({
            "state_id": state, "total_samples": n_total, "positive_count": n_pos, "control_count": n_neg,
            "status": s_status, "roc_auc": s_auc, "pr_auc": s_pr_auc,
            "recall": s_rec, "precision": s_prec, "f1_score": s_f1
        })

    pd.DataFrame(state_rows).to_csv(STATE_CSV_PATH, index=False)

    # 5. DISTRICT-WISE PERFORMANCE ON LOCKED HOLDOUT
    eval_districts = df["district_id"].unique()
    dist_rows = []
    for dist in eval_districts:
        d_df = test_holdout[test_holdout["district_id"] == dist]
        n_total = len(d_df)
        n_pos = (d_df["landslide"] == 1).sum() if n_total > 0 else 0
        n_neg = (d_df["landslide"] == 0).sum() if n_total > 0 else 0

        if n_total == 0:
            dist_rows.append({
                "district_id": dist, "state_id": df[df["district_id"]==dist]["state_id"].iloc[0],
                "total_samples": 0, "positive_count": 0, "control_count": 0, "status": "NO_TEST_SAMPLES",
                "roc_auc": "N/A", "f1_score": "N/A"
            })
            continue

        p_dist = test_probs_a[test_holdout["district_id"] == dist]
        pr_dist = (p_dist >= 0.50).astype(int)

        if n_pos > 0 and n_neg > 0 and n_total >= 6:
            d_auc = round(float(roc_auc_score(d_df["landslide"], p_dist)), 4)
            d_f1 = round(float(f1_score(d_df["landslide"], pr_dist, zero_division=0)), 4)
            d_status = "EVALUATED"
        else:
            d_auc = "N/A"
            d_f1 = round(float(f1_score(d_df["landslide"], pr_dist, zero_division=0)), 4) if n_pos > 0 else "N/A"
            d_status = "INSUFFICIENT_SUPPORT"

        dist_rows.append({
            "district_id": dist, "state_id": d_df["state_id"].iloc[0],
            "total_samples": n_total, "positive_count": n_pos, "control_count": n_neg,
            "status": d_status, "roc_auc": d_auc, "f1_score": d_f1
        })

    pd.DataFrame(dist_rows).to_csv(DISTRICT_CSV_PATH, index=False)

    # 6. SAVE RESULTS JSON & CSV
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

    print(f"\nSaved P5.3.1 results to {RESULTS_JSON_PATH} and {RESULTS_CSV_PATH}")
    print(f"Saved threshold analysis to {THRESHOLD_CSV_PATH}")
    print(f"Saved state performance to {STATE_CSV_PATH}")
    print(f"Saved district performance to {DISTRICT_CSV_PATH}")
    print(f"Saved model registry to {REGISTRY_JSON_PATH}")

    sha_end = verify_prod_model_hash()
    print(f"Final Production Model SHA-256 Verified: {sha_end}")
    assert sha_end == sha_start, "PRODUCTION MODEL WAS OVERWRITTEN!"


if __name__ == "__main__":
    run_promotion_review_correction()
