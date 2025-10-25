from fastapi import FastAPI
import boto3, os, joblib, tempfile

app = FastAPI(title="MLOps API on AWS")

S3_BUCKET = os.getenv("S3_BUCKET")
MODEL_PATH = os.getenv("MODEL_PATH")

def load_model_from_s3():
    s3 = boto3.client("s3",
                      aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                      aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                      region_name=os.getenv("AWS_REGION"))
    tmp = tempfile.NamedTemporaryFile(delete=False)
    s3.download_file(S3_BUCKET, "models/latest_model.pkl", tmp.name)
    model = joblib.load(tmp.name)
    return model

model = load_model_from_s3()

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/predict")
def predict():
    sample = [[5.1, 3.5, 1.4, 0.2]]
    pred = model.predict(sample)
    return {"prediction": pred.tolist()}
