import pandas as pd
import numpy as np
import pickle

from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score
)

# ============================================================
# PATHS
# ============================================================

DATA_PATH = Path(
    "backend/data/training/ml_dataset.csv"
)

MODEL_DIR = Path(
    "backend/model"
)

MODEL_PATH = MODEL_DIR / "landslide_model.pkl"


# ============================================================
# LOAD DATA
# ============================================================

print("Loading dataset...")

df = pd.read_csv(DATA_PATH)

df["date"] = pd.to_datetime(df["date"])

print(f"Dataset rows: {len(df)}")


# ============================================================
# FEATURE ENGINEERING
# ============================================================

# Extract useful seasonal information
df["month"] = df["date"].dt.month

df["month_sin"] = np.sin(
    2 * np.pi * df["month"] / 12
)

df["month_cos"] = np.cos(
    2 * np.pi * df["month"] / 12
)


# Features available to the prediction system
FEATURES = [
    "latitude",
    "longitude",
    "rainfall_1d",
    "rainfall_3d",
    "rainfall_7d",
    "month_sin",
    "month_cos"
]

TARGET = "landslide"


X = df[FEATURES]
y = df[TARGET]


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

# Use chronological splitting to avoid using future events
# to predict earlier events.

df_sorted = df.sort_values("date").reset_index(drop=True)

split_index = int(len(df_sorted) * 0.80)

train_df = df_sorted.iloc[:split_index]
test_df = df_sorted.iloc[split_index:]

X_train = train_df[FEATURES]
y_train = train_df[TARGET]

X_test = test_df[FEATURES]
y_test = test_df[TARGET]

print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))

print("\nTraining class distribution:")
print(y_train.value_counts())

print("\nTesting class distribution:")
print(y_test.value_counts())


# ============================================================
# TRAIN RANDOM FOREST
# ============================================================

print("\nTraining Random Forest...")

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)


# ============================================================
# EVALUATION
# ============================================================

print("\n================================")
print("MODEL EVALUATION")
print("================================")

predictions = model.predict(X_test)

probabilities = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(
    y_test,
    predictions
)

print(f"\nAccuracy: {accuracy:.4f}")

# ROC-AUC requires both classes in test set
if len(np.unique(y_test)) == 2:

    auc = roc_auc_score(
        y_test,
        probabilities
    )

    print(f"ROC-AUC: {auc:.4f}")

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        target_names=[
            "No Landslide",
            "Landslide"
        ]
    )
)

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        predictions
    )
)


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\n================================")
print("FEATURE IMPORTANCE")
print("================================")

importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_
})

importance = importance.sort_values(
    "importance",
    ascending=False
)

print(
    importance.to_string(index=False)
)


# ============================================================
# SAVE MODEL
# ============================================================

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

model_package = {
    "model": model,
    "features": FEATURES
}

with open(
    MODEL_PATH,
    "wb"
) as f:

    pickle.dump(
        model_package,
        f
    )


print("\n================================")
print("MODEL SAVED")
print("================================")

print(MODEL_PATH)