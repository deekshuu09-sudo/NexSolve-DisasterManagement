"""Validation Utilities for NexSolve P5 Benchmark & Scientific Evaluation.

Provides:
- Chronological temporal train/test splitter
- Location-group K-fold cross-validator
- District-group K-fold cross-validator
- Metric calculator (ROC-AUC, PR-AUC, Precision, Recall, F1, Brier score, Confusion matrix, ECE)
- Baseline production model evaluator
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_score,
    recall_score, f1_score, brier_score_loss, confusion_matrix
)
from sklearn.model_selection import GroupKFold

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"

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

EXCLUDED_FEATURES = [
    "distance_to_nearest_event_km", "soilSat"
]

FEATURE_SETS = {
    "Model_A_Production_Baseline": PROD_FEATURES,
    "Model_B_Terrain_Enhanced": PROD_FEATURES + TERRAIN_FEATURES,
    "Model_C_Terrain_Historical_Inventory": PROD_FEATURES + TERRAIN_FEATURES + INVENTORY_FEATURES
}


def calculate_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error (ECE) across binned probability forecasts."""
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


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """Compute comprehensive evaluation metrics for classification and calibration."""
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
        },
        "positive_count": int(np.sum(y_true == 1)),
        "control_count": int(np.sum(y_true == 0)),
        "total_samples": int(len(y_true))
    }


def split_chronological(df: pd.DataFrame, cutoff_year: int = 2023) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset chronologically into train (year <= cutoff_year) and test (year > cutoff_year)."""
    df_copy = df.copy()
    df_copy["year"] = pd.to_datetime(df_copy["date"]).dt.year
    
    train_df = df_copy[df_copy["year"] <= cutoff_year].copy()
    test_df = df_copy[df_copy["year"] > cutoff_year].copy()
    
    return train_df, test_df


def get_group_kfold_splits(df: pd.DataFrame, group_col: str, n_splits: int = 5) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Generate GroupKFold train/test index splits, verifying zero group overlap between train and test."""
    gkf = GroupKFold(n_splits=n_splits)
    groups = df[group_col].values
    
    splits = []
    for train_idx, test_idx in gkf.split(df, groups=groups):
        train_groups = set(groups[train_idx])
        test_groups = set(groups[test_idx])
        overlap = train_groups.intersection(test_groups)
        assert len(overlap) == 0, f"Group overlap detected for column {group_col}!"
        splits.append((train_idx, test_idx))
        
    return splits
