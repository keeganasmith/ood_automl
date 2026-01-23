#!/usr/bin/env python3
"""
Train AutoGluon MultiModal using 2 GPUs.

Example:
  CUDA_VISIBLE_DEVICES=0,1 python train_mm_2gpus.py \
      --train train.csv --valid valid.csv --label label --problem_type classification

Notes:
- For images: your CSV can have a column with image file paths (e.g., "image").
- For text: a column with strings (e.g., "title" or "description").
- For tabular: numeric/categorical columns are fine too.
"""

import argparse
import pandas as pd

from autogluon.multimodal import MultiModalPredictor


def read_data(path: str):
    if path.endswith(".csv"):
        return pd.read_csv(path)
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file type: {path} (use .csv or .parquet)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True, help="Path to train.csv/train.parquet")
    parser.add_argument("--valid", default=None, help="Optional: valid.csv/valid.parquet")
    parser.add_argument("--label", required=True, help="Name of label column")
    parser.add_argument("--save_path", default="AutogluonModels/mm_2gpus", help="Model output dir")

    # Common knobs
    parser.add_argument("--problem_type", default=None, choices=[None, "classification", "regression"])
    parser.add_argument("--time_limit", type=int, default=None, help="Seconds (optional)")
    parser.add_argument("--presets", default="medium_quality", help='e.g. "medium_quality", "high_quality"')

    args = parser.parse_args()

    train_df = read_data(args.train)
    valid_df = read_data(args.valid) if args.valid else None

    predictor = MultiModalPredictor(
        label=args.label,
        problem_type=args.problem_type,   # None lets AutoGluon infer
        path=args.save_path,
    )

    predictor.fit(
        train_data=train_df,
        tuning_data=valid_df,             # if None, AutoGluon will split internally
        presets=args.presets,
        time_limit=args.time_limit,

        # Key line: use 2 GPUs
        hyperparameters={
            "env.num_gpus": 2
        },
    )

    print("\nTraining done.")
    print("Saved to:", args.save_path)


if __name__ == "__main__":
    main()

