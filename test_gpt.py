# ...existing code...
from openai import OpenAI
import os

# ...existing code...
client = OpenAI()  # reads OPENAI_API_KEY from env

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Ciao, puoi rispondere in italiano?"}]
)

print(response.choices[0].message["content"])
# ...existing code...