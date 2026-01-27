import time

import pandas as pd
from autogluon.tabular import TabularPredictor


def main() -> None:
    train_data = pd.read_csv("./backend/sample_datasets/adult.tsv", sep="\t")

    start_time = time.perf_counter()
    TabularPredictor(label="target").fit(train_data)
    end_time = time.perf_counter()

    elapsed = end_time - start_time
    print(f"SCRIPT_TRAIN_TIME_SECONDS={elapsed}")


if __name__ == "__main__":
    main()
