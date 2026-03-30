import time
import sys
import os
import contextlib

import pandas as pd
from autogluon.tabular import TabularPredictor
from autogluon.multimodal import MultiModalPredictor


def main() -> None:
    train_data = pd.read_csv("/scratch/user/u.ks124812/datasets/HIGGS.csv")

    start_time = time.perf_counter()

    TabularPredictor(label="label").fit(
        train_data=train_data,
        presets="medium_quality"
    )

    end_time = time.perf_counter()

    elapsed = end_time - start_time
    print(f"SCRIPT_TRAIN_TIME_SECONDS={elapsed}", flush=True)


if __name__ == "__main__":
    number_of_times = 1
    if len(sys.argv) > 1:
        number_of_times = int(sys.argv[1])
    for i in range(number_of_times):
        main()
