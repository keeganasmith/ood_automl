import pandas as pd

raw_results_dataframe = pd.read_csv("results.csv")
test_dataframe = pd.read_csv("test.csv")

raw_results_dataframe["BeatsPerMinute"] = raw_results_dataframe.pop("prediction")
raw_results_dataframe["id"] = test_dataframe["id"].values
raw_results_dataframe = raw_results_dataframe[["id", "BeatsPerMinute"]]
raw_results_dataframe.to_csv("real_results.csv", index=False)
