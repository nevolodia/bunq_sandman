api_key = "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"

from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = api_key
)

completion = client.chat.completions.create(
  model="meta/llama-3.1-8b-instruct",
  messages=[{"role":"user","content":"what is 5 multiplied by 25?"}],
  temperature=0.2,
  top_p=0.7,
  max_tokens=1024,
  stream=True
)

for chunk in completion:
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")