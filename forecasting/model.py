"""Simple global weekly forecasting pipeline using Random Forest.

Flow:
1) Load and clean historical prices.
2) Train one global model on all valid series.
3) Forecast each series and save results to price_forecasts.
"""

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from database.database_config import get_connection


DEFAULT_FORECAST_HORIZON = 3
MIN_TRAINING_POINTS = 8
LAGS = (1, 2, 3)

# Keep only high-signal features that are easy to explain.
NUMERIC_FEATURE_COLS = [
    "lag_1",
    "lag_2",
    "lag_3",
    "sample_count_lag_1",
    "days_since_prev_obs",
    "week_of_year",
    "month",
]

CATEGORICAL_FEATURE_COLS = [
    "brand_name",
    "category_name",
    "range_name",
    "format",
    "packaging",
    "site_name",
    "country",
    "store_code",
]

FEATURE_COLS = NUMERIC_FEATURE_COLS + CATEGORICAL_FEATURE_COLS


def _safe_str(value: Any, fallback: str = "Unknown") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _confidence_label(training_points: int, relative_spread: float) -> str:
    # Two simple signals: data quantity + model dispersion.
    if training_points >= 52:
        base = 3
    elif training_points >= 20:
        base = 2
    elif training_points >= 8:
        base = 1
    else:
        base = 0

    if relative_spread <= 0.10:
        spread_bonus = 1
    elif relative_spread <= 0.22:
        spread_bonus = 0
    else:
        spread_bonus = -1

    level_idx = max(0, min(3, base + spread_bonus))
    return ["Very Low", "Low", "Medium", "High"][level_idx]


def _prepare_history(history_df: pd.DataFrame) -> pd.DataFrame:
    cleaned = history_df.copy()
    cleaned["ds"] = pd.to_datetime(cleaned["ds"], errors="coerce")
    cleaned["y"] = pd.to_numeric(cleaned["y"], errors="coerce")
    cleaned["sample_count"] = pd.to_numeric(cleaned.get("sample_count", 1.0), errors="coerce")

    # Policy: ignore invalid or non-positive prices; no missing-week imputation.
    cleaned = cleaned.dropna(subset=["ds", "y"])
    cleaned = cleaned[cleaned["y"] > 0]
    if cleaned.empty:
        return cleaned

    cleaned = cleaned.groupby("ds", as_index=False).agg(
        y=("y", "mean"),
        sample_count=("sample_count", "mean"),
    )
    return cleaned.sort_values("ds").reset_index(drop=True)


def _series_to_training_rows(history_df: pd.DataFrame, static_features: dict[str, str]) -> pd.DataFrame:
    features_df = history_df.copy()
    features_df["week_of_year"] = features_df["ds"].dt.isocalendar().week.astype(int)
    features_df["month"] = features_df["ds"].dt.month.astype(int)
    features_df["days_since_prev_obs"] = features_df["ds"].diff().dt.days.fillna(7).astype(float)

    for lag in LAGS:
        features_df[f"lag_{lag}"] = features_df["y"].shift(lag)

    features_df["sample_count_lag_1"] = features_df["sample_count"].shift(1)

    train_df = features_df.dropna(subset=NUMERIC_FEATURE_COLS + ["y"]).reset_index(drop=True)
    for col in CATEGORICAL_FEATURE_COLS:
        train_df[col] = static_features[col]

    return train_df[FEATURE_COLS + ["y"]]


def _build_model_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURE_COLS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURE_COLS),
        ],
        remainder="drop",
    )

    regressor = RandomForestRegressor(
        n_estimators=400,
        random_state=42,
        min_samples_leaf=2,
        n_jobs=-1,
    )

    return Pipeline(steps=[("preprocessor", preprocessor), ("regressor", regressor)])


def _predict_with_interval(model_pipeline: Pipeline, feature_row: pd.DataFrame):
    pred = max(float(model_pipeline.predict(feature_row)[0]), 0.0)

    preprocessor = model_pipeline.named_steps["preprocessor"]
    regressor = model_pipeline.named_steps["regressor"]
    transformed = preprocessor.transform(feature_row)
    tree_preds = np.array([tree.predict(transformed)[0] for tree in regressor.estimators_], dtype=float)

    low = max(float(np.percentile(tree_preds, 10)), 0.0)
    high = max(float(np.percentile(tree_preds, 90)), 0.0)
    mean_abs = max(abs(float(np.mean(tree_preds))), 1e-6)
    relative_spread = float(np.std(tree_preds, ddof=0) / mean_abs)

    return pred, low, high, relative_spread


def _future_feature_row(
    history_values: list[float],
    sample_count_lag_1: float,
    forecast_date: pd.Timestamp,
    static_features: dict[str, str],
) -> pd.DataFrame:
    row = {
        "lag_1": float(history_values[-1]),
        "lag_2": float(history_values[-2]),
        "lag_3": float(history_values[-3]),
        "sample_count_lag_1": float(sample_count_lag_1),
        "days_since_prev_obs": 7.0,
        "week_of_year": int(forecast_date.isocalendar().week),
        "month": int(forecast_date.month),
        **static_features,
    }
    return pd.DataFrame([row], columns=FEATURE_COLS)


def _load_series_rows(cursor):
    cursor.execute(
        """
        SELECT
            ws.product_format_id,
            ws.website_id,
            ws.store_id,
            ws.week_start::date AS week_start,
            CASE
                WHEN ws.currency = 'EUR' THEN ws.avg_price::FLOAT
                WHEN fx_hist.rate_to_eur IS NOT NULL THEN (ws.avg_price / fx_hist.rate_to_eur)::FLOAT
                ELSE NULL
            END AS price_eur,
            ws.sample_count::FLOAT AS sample_count,
            b.brand_name,
            c.category_name,
            r.range_name,
            pf.format,
            pf.packaging,
            w.site_name,
            w.country,
            COALESCE(s.store_code, 'NO_STORE') AS store_code
        FROM weekly_price_summary ws
        JOIN product_formats pf ON ws.product_format_id = pf.id
        JOIN products p ON pf.product_id = p.id
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        JOIN ranges r ON p.range_id = r.id
        JOIN websites w ON ws.website_id = w.id
        LEFT JOIN stores s ON ws.store_id = s.id
        JOIN product_urls pu ON pu.product_format_id = ws.product_format_id
                           AND pu.website_id = ws.website_id
                           AND pu.store_id IS NOT DISTINCT FROM ws.store_id
                           AND pu.is_active = TRUE
        LEFT JOIN LATERAL (
            SELECT rate_to_eur
            FROM exchange_rates e
            WHERE e.currency = ws.currency
              AND e.date <= ws.week_start
            ORDER BY e.date DESC
            LIMIT 1
        ) fx_hist ON TRUE
        ORDER BY ws.product_format_id, ws.website_id, ws.store_id, ws.week_start
        """
    )
    return cursor.fetchall()


def _group_series(rows):
    grouped = defaultdict(list)
    static_by_series = {}

    for (
        product_format_id,
        website_id,
        store_id,
        week_start,
        price_eur,
        sample_count,
        brand_name,
        category_name,
        range_name,
        format_value,
        packaging_value,
        site_name,
        country,
        store_code,
    ) in rows:
        if price_eur is None or float(price_eur) <= 0:
            continue

        key = (int(product_format_id), int(website_id), store_id)
        grouped[key].append({"ds": week_start, "y": float(price_eur), "sample_count": float(sample_count or 1.0)})

        if key not in static_by_series:
            static_by_series[key] = {
                "brand_name": _safe_str(brand_name),
                "category_name": _safe_str(category_name),
                "range_name": _safe_str(range_name),
                "format": _safe_str(format_value),
                "packaging": _safe_str(packaging_value),
                "site_name": _safe_str(site_name),
                "country": _safe_str(country),
                "store_code": _safe_str(store_code, fallback="NO_STORE"),
            }

    return grouped, static_by_series


def run_random_forest_forecasts(horizon_weeks=DEFAULT_FORECAST_HORIZON):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            rows = _load_series_rows(cursor)
            grouped, static_by_series = _group_series(rows)

            training_frames = []
            series_data = {}
            skipped_low_points = 0
            skipped_no_train_rows = 0

            for key, observations in grouped.items():
                history_df = _prepare_history(pd.DataFrame(observations))
                training_points = len(history_df)

                if training_points < MIN_TRAINING_POINTS:
                    skipped_low_points += 1
                    continue

                static_features = static_by_series.get(key, {col: "Unknown" for col in CATEGORICAL_FEATURE_COLS})
                train_rows = _series_to_training_rows(history_df, static_features)
                if train_rows.empty:
                    skipped_no_train_rows += 1
                    continue

                training_frames.append(train_rows)
                series_data[key] = {
                    "history_df": history_df,
                    "static_features": static_features,
                    "training_points": training_points,
                }

            insert_rows = []
            skipped_forecast = 0

            if training_frames and series_data:
                global_train_df = pd.concat(training_frames, ignore_index=True)
                model_pipeline = _build_model_pipeline()
                model_pipeline.fit(global_train_df[FEATURE_COLS], global_train_df["y"])

                for key, data in series_data.items():
                    history_df = data["history_df"]
                    static_features = data["static_features"]
                    training_points = data["training_points"]
                    product_format_id, website_id, store_id = key
                    history_values = history_df["y"].tolist()
                    history_sample_counts = history_df["sample_count"].fillna(1.0).tolist()
                    if len(history_values) < max(LAGS):
                        skipped_forecast += 1
                        continue

                    last_date = history_df["ds"].iloc[-1]
                    spreads = []
                    series_rows = []

                    for step in range(1, horizon_weeks + 1):
                        forecast_date = last_date + pd.Timedelta(days=7 * step)
                        sample_count_lag_1 = float(history_sample_counts[-1]) if history_sample_counts else 1.0
                        feature_row = _future_feature_row(history_values, sample_count_lag_1, forecast_date, static_features)

                        pred, low, high, spread = _predict_with_interval(model_pipeline, feature_row)
                        spreads.append(spread)
                        series_rows.append((forecast_date, pred, low, high))

                        history_values.append(pred)
                        history_sample_counts.append(sample_count_lag_1)

                    avg_spread = float(np.mean(spreads)) if spreads else float("inf")
                    confidence = _confidence_label(training_points, avg_spread)

                    for forecast_date, pred, low, high in series_rows:
                        insert_rows.append(
                            (
                                product_format_id,
                                website_id,
                                store_id,
                                forecast_date,
                                round(float(pred), 2),
                                round(float(low), 2),
                                round(float(high), 2),
                                confidence,
                                int(training_points),
                            )
                        )

            cursor.execute("DELETE FROM price_forecasts")
            if insert_rows:
                cursor.executemany(
                    """
                    INSERT INTO price_forecasts (
                        product_format_id,
                        website_id,
                        store_id,
                        forecast_date,
                        predicted_price,
                        price_low,
                        price_high,
                        confidence_level,
                        training_points
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    insert_rows,
                )

        conn.commit()

    print(
        "Global Random Forest forecasts saved",
        (
            f"(rows={len(insert_rows)}, series_total={len(grouped)}, trained_series={len(series_data)}, "
            f"skipped_low_points={skipped_low_points}, skipped_no_train_rows={skipped_no_train_rows}, "
            f"skipped_forecast={skipped_forecast}, horizon={horizon_weeks})"
        ),
    )


if __name__ == "__main__":
    run_random_forest_forecasts()