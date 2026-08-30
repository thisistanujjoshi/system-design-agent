from common import client

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=50,
    messages=[{"role": "user", "content": "Reply with exactly: API key works."}],
)

print(response.content[0].text)
