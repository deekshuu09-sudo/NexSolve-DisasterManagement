#!/usr/bin/env python3
"""
NexSolve P5 Model Benchmarking & Scientific Validation Script.
Evaluates Production RF Baseline vs Experimental Feature Sets across:
1. Chronological Holdout (Train <=2023, Test >=2024)
2. Location-Group 5-Fold CV (Overlap = 0)
3. District-Group 5-Fold CV (Overlap = 0)
4. Event-Aware Group 5-Fold CV (Overlap = 0)
"""

import hashlib
import json
import pickle
from pathlib import Path
import sys
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"
MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_results.csv"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_model_benchmark_report.md"

from backend.validation.validation_utils import (
    compute_metrics, split_chronological, get_group_kfold_splits,
    FEATURE_SETS, PROD_FEATURES
)

def verify_model_hash() -> str:
    with open(MODEL_PATH, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    assert sha == "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1", f"Model SHA mismatch: {sha}"
    return sha

def load_production_model():
    with open(MODEL_PATH, "rb") as f:
        obj = pickle.load(f)
    if isinstance(obj, dict) and "model" in obj:
        return obj["model"]
    return obj

def run_benchmarks():
    print("=" * 80)
    print("NEXSOLVE P5 BENCHMARK & SCIENTIFIC VALIDATION")
    print("=" * 80)
    
    sha_start = verify_model_hash()
    print(f"Production Model Baseline SHA-256 Verified: {sha_start}")
    
    prod_model_loaded = load_production_model()
    
    df = pd.read_csv(FUSED_DATASET_PATH)
    print(f"Loaded fused dataset: {len(df)} samples, {len(df.columns)} columns")
    
    # Create grouping keys
    df["location_group"] = df["latitude"].astype(str) + "_" + df["longitude"].astype(str)
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df["event_group"] = df["location_group"] + "_" + df["year"].astype(str)
    
    results = []

    # ---------------------------------------------------------
    # 1. EVALUATE PRODUCTION RF BASELINE (7 FEATURES)
    # ---------------------------------------------------------
    print("\n[1/4] Evaluating Loaded Production RF Model Baseline...")
    
    # Chronological Holdout
    train_df, test_df = split_chronological(df, cutoff_year=2023)
    X_test_prod = test_df[PROD_FEATURES].values
    y_test_prod = test_df["landslide"].values
    
    prod_probs = prod_model_loaded.predict_proba(X_test_prod)[:, 1]
    metrics_prod_chrono = compute_metrics(y_test_prod, prod_probs)
    
    results.append({
        "model_id": "Production_RF_Baseline",
        "model_class": "Loaded_RandomForestClassifier",
        "feature_set": "Model_A_Production_Baseline",
        "feature_count": len(PROD_FEATURES),
        "validation_strategy": "Chronological_Holdout",
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "metrics": metrics_prod_chrono
    })
    
    # Location-Group CV for Production Baseline
    loc_splits = get_group_kfold_splits(df, group_col="location_group", n_splits=5)
    loc_probs_list = []
    loc_y_list = []
    
    for train_idx, test_idx in loc_splits:
        X_test_fold = df.iloc[test_idx][PROD_FEATURES].values
        y_test_fold = df.iloc[test_idx]["landslide"].values
        probs_fold = prod_model_loaded.predict_proba(X_test_fold)[:, 1]
        loc_probs_list.append(probs_fold)
        loc_y_list.append(y_test_fold)
        
    all_loc_y = np.concatenate(loc_y_list)
    all_loc_probs = np.concatenate(loc_probs_list)
    metrics_prod_loc = compute_metrics(all_loc_y, all_loc_probs)
    
    results.append({
        "model_id": "Production_RF_Baseline",
        "model_class": "Loaded_RandomForestClassifier",
        "feature_set": "Model_A_Production_Baseline",
        "feature_count": len(PROD_FEATURES),
        "validation_strategy": "Location_Group_5Fold_CV",
        "train_samples": len(df) * 4 // 5,
        "test_samples": len(df),
        "metrics": metrics_prod_loc
    })

    # ---------------------------------------------------------
    # 2. EVALUATE EXPERIMENTAL MODEL CONFIGURATIONS
    # ---------------------------------------------------------
    model_factories = {
        "RandomForestClassifier": lambda: RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
        "HistGradientBoostingClassifier": lambda: HistGradientBoostingClassifier(max_iter=100, random_state=42)
    }
    
    validation_strategies = [
        ("Chronological_Holdout", lambda: ("chrono", split_chronological(df, cutoff_year=2023))),
        ("Location_Group_5Fold_CV", lambda: ("group_cv", ("location_group", get_group_kfold_splits(df, group_col="location_group", n_splits=5)))),
        ("District_Group_5Fold_CV", lambda: ("group_cv", ("district_id", get_group_kfold_splits(df, group_col="district_id", n_splits=5)))),
        ("Event_Aware_5Fold_CV", lambda: ("group_cv", ("event_group", get_group_kfold_splits(df, group_col="event_group", n_splits=5))))
    ]
    
    for fset_name, features in FEATURE_SETS.items():
        print(f"\nEvaluating Feature Set: {fset_name} ({len(features)} features)")
        
        for m_name, m_factory in model_factories.items():
            for v_name, v_builder in validation_strategies:
                v_type, v_data = v_builder()
                
                if v_type == "chrono":
                    tr_df, te_df = v_data
                    X_tr = tr_df[features].values
                    y_tr = tr_df["landslide"].values
                    X_te = te_df[features].values
                    y_te = te_df["landslide"].values
                    
                    clf = m_factory()
                    clf.fit(X_tr, y_tr)
                    probs = clf.predict_proba(X_te)[:, 1]
                    met = compute_metrics(y_te, probs)
                    
                    results.append({
                        "model_id": f"Exp_{m_name}",
                        "model_class": m_name,
                        "feature_set": fset_name,
                        "feature_count": len(features),
                        "validation_strategy": v_name,
                        "train_samples": len(tr_df),
                        "test_samples": len(te_df),
                        "metrics": met
                    })
                    
                elif v_type == "group_cv":
                    group_col, splits = v_data
                    fold_probs = []
                    fold_y = []
                    
                    for train_idx, test_idx in splits:
                        tr_df = df.iloc[train_idx]
                        te_df = df.iloc[test_idx]
                        
                        X_tr = tr_df[features].values
                        y_tr = tr_df["landslide"].values
                        X_te = te_df[features].values
                        y_te = te_df["landslide"].values
                        
                        clf = m_factory()
                        clf.fit(X_tr, y_tr)
                        p_fold = clf.predict_proba(X_te)[:, 1]
                        
                        fold_probs.append(p_fold)
                        fold_y.append(y_te)
                        
                    all_y = np.concatenate(fold_y)
                    all_p = np.concatenate(fold_probs)
                    met = compute_metrics(all_y, all_p)
                    
                    results.append({
                        "model_id": f"Exp_{m_name}",
                        "model_class": m_name,
                        "feature_set": fset_name,
                        "feature_count": len(features),
                        "validation_strategy": v_name,
                        "train_samples": len(df) * 4 // 5,
                        "test_samples": len(df),
                        "metrics": met
                    })

    # Save machine-readable results
    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    flat_rows = []
    for r in results:
        m = r["metrics"]
        flat_rows.append({
            "model_id": r["model_id"],
            "feature_set": r["feature_set"],
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
        
    results_df = pd.DataFrame(flat_rows)
    results_df.to_csv(RESULTS_CSV_PATH, index=False)
    
    print(f"\nSaved benchmark results to {RESULTS_JSON_PATH} and {RESULTS_CSV_PATH}")
    
    # Verify model hash again
    sha_end = verify_model_hash()
    print(f"Final Production Model SHA-256 Verified: {sha_end}")

if __name__ == "__main__":
    run_benchmarks()
