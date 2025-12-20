import joblib

scaler = joblib.load("models/scaler.pkl")

print(hasattr(scaler, "feature_names_in_"))
print(scaler.feature_names_in_)