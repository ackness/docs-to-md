import os

import openai
import pytest
from docs_to_md.jina import jina_reader

demo_html = """
<html>
    <body>
        <h1>Hello, World!</h1>
        <p>This is a test.</p>
        <a href="https://www.google.com">Google</a>
    </body>
</html>
"""


@pytest.mark.asyncio
async def test_openai_chat():
    client = openai.AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    response = await client.chat.completions.create(
        model="reader-lm",
        stream=False,
        messages=[
            {
                "role": "user",
                "content": demo_html,
            },
        ],
        timeout=120,
    )

    text = response.choices[0].message.content
    assert text is not None


@pytest.mark.asyncio
async def test_jina_api():
    token = os.getenv("JINA_TOKEN")
    assert token is not None
    response = await jina_reader("https://example.com", token)
    assert response is not None
    print(response)
