#!/usr/bin/env python3
"""
Simple AutoGluon MultiModal training script.

Example:
  python train_mm.py --train train.csv --test test.csv --label label --outdir /scratch/user/me/ag_mm_run
"""

import argparse
import os
import pandas as pd

from autogluon.multimodal import MultiModalPredictor


def main():

    # Choose output directory (supports $SCRATCH if set)
    outdir = "$SCRATCH/ood_automl/hello/"
    outdir = os.path.expandvars(outdir)
    os.makedirs(outdir, exist_ok=True)
    train_path = $SCRATCH/datasets/
    # Load data
    train_df = pd.read_csv()
    test_df = pd.read_csv(args.test) if args.test else None

    # Basic sanity checks
    if args.label not in train_df.columns:
        raise ValueError(f"Label column '{args.label}' not found in train CSV columns: {list(train_df.columns)}")

    # Create predictor
    predictor = MultiModalPredictor(
        label=args.label,
        problem_type=args.problem_type,  # can be None to infer
        path=outdir,
    )

    # Train
    predictor.fit(
        train_data=train_df,
        time_limit=args.time_limit,  # e.g. 3600 for 1 hour
        # presets="medium_quality",  # uncomment for a sensible default
    )

    # Evaluate (optional)
    if test_df is not None:
        metrics = predictor.evaluate(test_df)
        print("Evaluation metrics:", metrics)

    # Example predictions (optional)
    preds = predictor.predict(train_df.head(5))
    print("Sample preds:", preds)

    print(f"Saved model artifacts to: {outdir}")


if __name__ == "__main__":
    main()

