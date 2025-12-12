import requests

url = "http://localhost:8000/predict"

flow = [
    80, 6, 15000, 500, 2, 600000, 1200, 1500, 1500, 1500, 0,
    1500, 1500, 1500, 0,
    40000000.0, 35000.0,
    1.2, 0.5, 3.0, 0.5,
    1.0, 0.7, 0.3, 2.8, 0.4,
    1.1, 0.75, 0.35, 3.0, 0.5,
    0, 0, 0, 0,
    200, 200,
    1500, 1500, 1500, 0, 1500,
    200, 200, 0, 500, 500, 0,
    0, 0,
    1500.0, 1500.0, 1500.0,
    0, 0, 0,
    0, 0, 0,
    500, 600000, 2, 1200,
    0, 0, 1, 1500,
    0, 0, 0, 0,
    0, 0, 0, 0, 0, 0
]

payload = {"features": flow}

print("Sending request...")
response = requests.post(url, json=payload)

print("\nServer response:")
print(response.json())
