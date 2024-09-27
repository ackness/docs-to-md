import asyncio
import logging
import os

from docs_to_md.jina import jina_reader
from docs_to_md.utils import fetch
from docs_to_md.utils import get_readthedocs_sub_urls
from docs_to_md.utils import make_dirs
from docs_to_md.utils import parse_html_to_markdown_openai
from docs_to_md.utils import preprocess_readthedocs_html
from docs_to_md.utils import remove_end_html
from docs_to_md.utils import save_file
from tqdm import tqdm

logger = logging.getLogger("D2M:PARSER")


def get_fp(target_path, save_name, file_type: str = "md"):
    """
    Get the file path for the saved file.
    """
    save_name = save_name.replace("/", "_")
    save_name = save_name.replace(".html", "")
    return os.path.join(target_path, file_type, f"{save_name}.{file_type}")


async def parse_readthedocs_with_readerlm(
    root_url: str,
    project_name: str,
    target_path: str = "saved",
    api: str = "http://localhost:11434/v1",
    model: str = "reader-lm",
    token: str = None,
):
    """
    Parse the readthedocs project and save the html and md files.
    Args:
        root_url: root url of the readthedocs project
        project_name: name of the project
        target_path: path to save the html and md files
    """
    make_dirs(os.path.join(target_path, project_name))
    target_path = os.path.join(target_path, project_name)

    # handle root url
    logger.info(f"Fetching {root_url}, target path: {target_path}")
    raw_html = await fetch(root_url, timeout=10)
    # root_html = preprocess_readthedocs_html(raw_html)

    root_html = raw_html
    root_md = await parse_html_to_markdown_openai(
        root_html,
        openai_api=api,
        openai_model=model,
        openai_token=token,
    )

    root_html_fp = get_fp(target_path, "index", "html")
    root_md_fp = get_fp(target_path, "index", "md")

    save_file(root_html_fp, root_html)
    save_file(root_md_fp, root_md)
    logger.info(f"Saved root html and md for {root_url}")

    # handle related urls
    sub_urls = get_readthedocs_sub_urls(root_url, raw_html)
    sub_htmls = await asyncio.gather(*[fetch(url) for _, url in sub_urls.items()])
    logger.info(f"Handling {len(sub_urls)} sub htmls, this may take a while...")

    # save clean htmls
    clean_sub_htmls = []
    for html, (name, url) in zip(sub_htmls, sub_urls.items()):
        html_fp = get_fp(target_path, name, "html")
        clean_html = preprocess_readthedocs_html(html)
        clean_sub_htmls.append(clean_html)
        save_file(html_fp, clean_html)

    logger.info(f"Saved {len(sub_htmls)} sub htmls")

    # parse html to md
    tqdm_iter = tqdm(zip(clean_sub_htmls, sub_urls.items()), total=len(sub_urls))
    for html, (name, url) in tqdm_iter:
        tqdm_iter.set_description(f"Processing {name}")
        md = await parse_html_to_markdown_openai(html)
        md_fp = get_fp(target_path, name, "md")
        save_file(md_fp, md)

    logger.info(f"Saved {len(sub_urls)} related md files")


async def jina_job(name: str, url: str, token: str, target_path: str):
    md_result = await jina_reader(url, token)
    save_file(get_fp(target_path, name, "md"), md_result)


async def parse_readthedocs_with_jina(
    root_url: str,
    project_name: str,
    target_path: str,
    token: str,
):
    target_path = os.path.join(target_path, project_name)
    make_dirs(target_path)

    # get sub urls
    index_url = remove_end_html(root_url)
    logger.info(f"Fetching {index_url}")
    index_html = await fetch(index_url)
    sub_urls = get_readthedocs_sub_urls(index_url, index_html)
    sub_urls["index"] = index_url
    logger.info(f"Found {len(sub_urls)} sub urls")

    # dispatch tasks with jina api
    tasks = [jina_job(name, url, token, target_path) for name, url in sub_urls.items()]
    await asyncio.gather(*tasks)
    logger.info(f"Saved {len(sub_urls)} sub urls")


async def parse_readthedocs(
    root_url: str,
    project_name: str,
    target_path: str,
    no_jina: bool = False,
    api: str = "http://localhost:11434/v1",
    token: str = None,
    model: str = "reader-lm",
):
    if not no_jina:
        if token is None or token == "ollama":
            token = None

        logger.info("Using jina to parse readthedocs")
        await parse_readthedocs_with_jina(root_url, project_name, target_path, token)
    else:
        logger.info(
            f"Using openai api, server: {api}, model: {model} to parse readthedocs",
        )
        await parse_readthedocs_with_readerlm(
            root_url,
            project_name,
            target_path,
            api,
            model,
            token,
        )
