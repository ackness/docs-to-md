import logging
import os
import re

import httpx
import openai
import requests
from lxml import html

logger = logging.getLogger("D2M")


async def fetch(url: str, **kwargs) -> str:
    """
    Fetch the html content from the url.
    Args:
        url: url to fetch
        kwargs: httpx.AsyncClient kwargs
    Returns:
        html content
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient(**kwargs) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return ""


async def openai_chat(content: str, base_url: str, api_key: str, model: str) -> str:
    """
    Chat with openai-based model.
    Args:
        content: html content
        base_url: base url of the openai api
        api_key: api key of the openai api
        model: which model to use
    Returns:
        the chat response
    """
    client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model=model,
            stream=False,
            messages=[
                {
                    "role": "user",
                    "content": content,
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(
            f"Failed to fetch result from openai chat ({base_url}) model: {model} error: {e}",
        )
        return ""


async def parse_html_to_markdown_openai(
    html: str,
    *,
    openai_api: str = "http://localhost:11434/v1",
    openai_token: str = "ollama",
    openai_model: str = "reader-lm",
) -> str:
    """
    Parse the html content to markdown content using openai chat.
    Args:
        html: html content
        openai_api: base url of the openai api, default is `http://localhost:11434/v1`
        openai_token: api key of the openai api, default is `ollama`
        openai_model: which model to use, default is `reader-lm`
    Returns:
        markdown content
    """
    content = await openai_chat(html, openai_api, openai_token, openai_model)
    return content


def remove_end_html(url: str) -> str:
    """
    Remove the end html from the url.
    Args:
        url: url to remove the end html
    Returns:
        url without end html
    """
    return re.sub(r"/[^/]+\.html$", "", url)


def get_readthedocs_sub_urls(index_url: str, index_response: str) -> dict[str, str]:
    """
    Parse the readthedocs project and return the sub urls.
    Args:
        index_url: root url of the readthedocs project

    Returns:
        sub urls: a dict of sub urls, {name: url}
    """
    # index may contain *.html, remove it
    if index_url.endswith(".html"):
        index_url = remove_end_html(index_url)

    tree = html.fromstring(index_response)
    sub_urls = tree.xpath('//a[contains(@class, "reference internal")]/@href')
    sub_urls = [requests.compat.urljoin(index_url, url) for url in sub_urls]
    # remove duplicate urls
    sub_urls = list(set(sub_urls))
    # remove urls that are not html
    sub_urls = [url for url in sub_urls if url.endswith(".html")]
    return {
        url.replace(index_url, "").replace(".html", "").replace("/", "_"): url
        for url in sub_urls
    }


def preprocess_readthedocs_html(html_content):
    # parse html
    tree = html.fromstring(html_content)

    # remove script, style and img elements
    for element in tree.xpath("//script | //style | //img"):
        element.getparent().remove(element)

    # remove all class and id attributes
    for element in tree.xpath("//*[@class or @id]"):
        element.attrib.pop("class", None)
        element.attrib.pop("id", None)

    # remove role="navigation" elements
    for element in tree.xpath("//*[@role='navigation']"):
        element.getparent().remove(element)

    # only save articleBody part
    body = tree.xpath("//*[@itemprop='articleBody']")[0]

    # convert processed html to string
    processed_html = html.tostring(body, encoding="unicode", pretty_print=True)

    # simple text cleaning
    processed_html = re.sub(r"\s+", " ", processed_html)
    processed_html = re.sub(r"\n+", "\n", processed_html)

    return processed_html


def save_file(fp: str, s: str):
    make_dirs(os.path.dirname(fp))

    with open(fp, "w", encoding="utf-8") as f:
        f.write(s)


def make_dirs(fp: str):
    if not os.path.exists(fp):
        os.makedirs(fp, exist_ok=True)


def extract_project_name_from_url(url: str) -> str:
    return url.split("/")[2].split(".")[0]
