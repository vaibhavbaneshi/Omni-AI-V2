from time import time

import requests
import json
import time

url = "http://localhost:11434/api/generate"

payload = {
    "model": "llama3",
    "prompt": """

    System: You are a senior AI tutor. Explain concepts in a simple and engaging way, using examples and analogies to help students understand complex topics. Your goal is to make learning enjoyable and accessible for everyone.

    User: Explain what vector databases are and how they work.

""" * 5000,
    "stream": True
}

start_time = time.time()

response = requests.post(url, json=payload, stream=True)

full_response = ""

for line in response.iter_lines():
    if line:
        chunk = json.loads(line.decode('utf-8'))

        token = chunk.get("response", "")
        print(token, end="", flush=True)
        full_response += token

end_time = time.time()
print("\n")
print("=" * 50)

elapsed = end_time - start_time

print(f"Total Time: {elapsed:.2f} seconds")
print(f"Characters Generated: {len(full_response)}")
print(f"Characters per Second: {len(full_response) / elapsed:.2f}")
