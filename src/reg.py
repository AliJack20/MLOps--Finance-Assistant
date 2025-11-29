import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor

df = pd.read_csv("D:\\Ikhlas University\\Semester 7\\MLOPS\Project_Financial_Advisor\\MLOps--Finance-Assistant\src\\train.csv")
df["week"] = pd.to_datetime(df["week"])
df["week_num"] = df["week"].astype(int) // 10**9

X = df[["week_num", "actual_spending"]]
y = df["predicted_spending_next_week"]

rf_model = ExtraTreesRegressor(
    n_estimators=100,
    min_samples_split=4,
    bootstrap=False,
    random_state=42,
    n_jobs=-1
)

rf_model.fit(X, y)

test_df = pd.read_csv("D:\\Ikhlas University\\Semester 7\\MLOPS\Project_Financial_Advisor\\MLOps--Finance-Assistant\src\\test.csv")
test_df["week"] = pd.to_datetime(test_df["week"])
test_df["week_num"] = test_df["week"].astype(int) // 10**9

X_test = test_df[["week_num", "actual_spending"]]
test_df["predicted_next_week_spending"] = rf_model.predict(X_test)

print(test_df.head())
test_df.to_csv("test_predictions.csv", index=False)
print("Predictions saved to test_predictions.csv")
