import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

def generate_data_drift_report(train, test, output_path="data_drift_report.html"):
    """
    Generates an Evidently Data Drift report comparing train and test datasets.

    Args:
        train_path (str): Path to the training CSV file.
        test_path (str): Path to the testing CSV file.
        output_path (str): Path to save the HTML report (default: data_drift_report.html)
    """
    # Load data
    train_df = train
    test_df = test

    # Drop unnecessary columns (adjust names as needed)
    if 'price_doc' in train_df.columns:
        train_df = train_df.drop('price_doc', axis=1)
    if 'row ID' in test_df.columns:
        test_df = test_df.drop('row ID', axis=1)

    # Generate report
    report = Report([DataDriftPreset()])
    eval = report.run(reference_data=train_df, current_data=test_df)
    eval.save_html(output_path)
    print(f"✅ Data drift report saved to: {output_path}")


def main():
    train_path = r"D:\Ikhlas University\Semester 7\MLOPS\Project_Financial_Advisor\MLOps--Finance-Assistant\train.csv"
    test_path  = r"D:\Ikhlas University\Semester 7\MLOPS\Project_Financial_Advisor\MLOps--Finance-Assistant\test.csv"

    generate_data_drift_report(train_path, test_path)


if __name__ == "__main__":
    main()
