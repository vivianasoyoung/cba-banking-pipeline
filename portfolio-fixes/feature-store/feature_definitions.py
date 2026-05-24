"""
feature_definitions.py
----------------------
Feast entity + feature view + feature service for the fraud model.
A FeatureService gives the served model a versioned contract.
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource
from feast.types import Float64, Int64

account = Entity(name="account_id", description="A CBA bank account")

account_features_source = FileSource(
    path="data/account_features.parquet",
    timestamp_field="event_timestamp",
)

account_transaction_features = FeatureView(
    name="account_transaction_features",
    entities=[account],
    ttl=timedelta(days=30),
    schema=[
        Field(name="transaction_count_7d",     dtype=Int64),
        Field(name="total_spend_7d",           dtype=Float64),
        Field(name="avg_transaction_value",    dtype=Float64),
        Field(name="max_transaction_value",    dtype=Float64),
        Field(name="unique_categories",        dtype=Int64),
        Field(name="online_transaction_ratio", dtype=Float64),
        Field(name="night_transaction_ratio", dtype=Float64),
        Field(name="avg_daily_spend",          dtype=Float64),
    ],
    source=account_features_source,
)

# Versioned input contract for the production scoring model.
# Bump the name (v2, v3...) when the model's input list changes.
fraud_model_v1 = FeatureService(
    name="fraud_model_v1",
    features=[
        account_transaction_features[[
            "transaction_count_7d",
            "total_spend_7d",
            "avg_transaction_value",
            "max_transaction_value",
            "unique_categories",
            "online_transaction_ratio",
            "night_transaction_ratio",
            "avg_daily_spend",
        ]],
    ],
)
