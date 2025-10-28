# ...existing code...
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Ciao, puoi rispondere in italiano?"}]
)

print(response.choices[0].message.content)
# ...existing code...