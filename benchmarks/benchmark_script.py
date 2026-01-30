import time
import sys

import pandas as pd
from autogluon.tabular import TabularPredictor


def main() -> None:
    train_data = pd.read_csv("./backend/sample_datasets/adult.tsv", sep="\t")

    start_time = time.perf_counter()
    TabularPredictor(label="target").fit(train_data=train_data, presets="medium_quality", num_gpus=0, ag_args_fit={'num_gpus': 0})
    end_time = time.perf_counter()

    elapsed = end_time - start_time
    print(f"SCRIPT_TRAIN_TIME_SECONDS={elapsed}")


if __name__ == "__main__":
    number_of_times = 1;
    if(len(sys.argv) > 1):
        number_of_times = int(sys.argv[1])
    for i in range(0, number_of_times):
        main()
