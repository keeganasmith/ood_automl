#!/usr/bin/env python3
"""
Parse training time logs and plot mean times with variance error bars.

Works with formats like:

  WEB_UI_TRAIN_TIME_SECONDS=76.4
  SCRIPT_TRAIN_TIME_SECONDS=70.3

Usage:
  python plot_times.py webui.txt script.txt
  python plot_times.py webui.txt script.txt --error std
  python plot_times.py webui.txt script.txt --error sem
  python plot_times.py webui.txt script.txt --error ci95
"""

import argparse
import math
import os
import re
from typing import List, Tuple

import matplotlib.pyplot as plt


# Matches BOTH:
#   WEB_UI_TRAIN_TIME_SECONDS=...
#   SCRIPT_TRAIN_TIME_SECONDS=...
TIME_RE = re.compile(r".*_TRAIN_TIME_SECONDS\s*=\s*([-+]?\d*\.?\d+)")


def parse_times(path: str) -> List[float]:
    """Extract all train time values from a log file."""
    times = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = TIME_RE.search(line)
            if match:
                times.append(float(match.group(1)))

    return times


def mean_and_variance(xs: List[float]) -> Tuple[float, float]:
    """Return mean and population variance."""
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / len(xs)
    return mu, var


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="Log files to parse")
    ap.add_argument(
        "--error",
        choices=["std", "sem", "ci95"],
        default="std",
        help="Error bar type: std (default), sem, or ci95",
    )
    ap.add_argument("--title", default="Average Train Time Comparison")
    ap.add_argument("--output", default="", help="Optional output file (chart.png)")
    args = ap.parse_args()

    labels = []
    means = []
    errors = []

    for path in args.files:
        times = parse_times(path)

        if not times:
            raise SystemExit(f"❌ No training times found in file: {path}")

        mu, var = mean_and_variance(times)
        std = math.sqrt(var)
        n = len(times)

        # Choose error bar style
        if args.error == "std":
            err = std
        elif args.error == "sem":
            err = std / math.sqrt(n)
        else:  # ci95
            err = 1.96 * (std / math.sqrt(n))

        labels.append(os.path.basename(path))
        means.append(mu)
        errors.append(err)

        print(f"\nFile: {path}")
        print(f"  Samples: {n}")
        print(f"  Mean:     {mu:.6f} sec")
        print(f"  Variance: {var:.6f}")
        print(f"  Std Dev:  {std:.6f}")

    # --- Plot bar chart ---
    x = range(len(labels))

    plt.figure()
    plt.bar(
        x,
        means,
        yerr=errors,
        capsize=10,  # fancy horizontal caps
    )

    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Seconds")
    plt.title(args.title)

    # Add mean labels above bars
    for i, val in enumerate(means):
        plt.text(i, val, f"{val:.2f}", ha="center", va="bottom")

    plt.tight_layout()

    if args.output:
        plt.savefig(args.output, dpi=200)
        print(f"\n✅ Saved chart to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()

