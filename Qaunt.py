import requests
from bs4 import BeautifulSoup
import json
import re

BASE_URL = "https://www.notion.so"  # Might be updated if the help center domain changes
HELP_CENTER_URL = "https://www.notion.so/help"  # The main help center page


def get_help_articles(url):
    """
    Scrape the help center main page to find all article links.
    Returns a list of full URLs to each help article.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    article_links = []

    # This selector is just an example.
    # Inspect the Notion help center page to adjust the exact tag/class/attribute.
    # For example, if articles are in <a class="help-article-link" href="...">
    # you would use something like soup.select('a.help-article-link').

    for link_tag in soup.select("a"):
        href = link_tag.get("href", "")

        # We only want to keep links that lead to actual help articles
        # and exclude Notion Academy or anything else.
        # This filter logic can be adjusted:
        if "/help/" in href and "academy" not in href.lower():
            # Some links might be relative, so ensure they're absolute:
            if href.startswith("http"):
                article_links.append(href)
            else:
                article_links.append(BASE_URL + href)

    # Remove duplicates in case of repeated links
    article_links = list(set(article_links))
    return article_links


def scrape_article(url):
    """
    Scrape the content of a single help article given its URL.
    Return a string or a structured representation of the content.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the main article content. Again, the exact selectors
    # will depend on the real HTML structure.
    # This is a placeholder structure:
    article_container = soup.find("div", {"class": "help-article-container"})
    if not article_container:
        # Fallback: if the structure is different, just get the body or some default
        article_container = soup.find("body")

        # Extract text in headings, paragraphs, bullet lists, etc.
    # Let's keep them in a list of blocks for chunking.
    content_blocks = []

    # Collect headings (e.g., h1, h2, h3, etc.)
    for heading in article_container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = heading.get_text(strip=True)
        if text:
            content_blocks.append(text)

    # Collect paragraphs
    for p in article_container.find_all("p"):
        text = p.get_text(strip=True)
        if text:
            content_blocks.append(text)

    # Collect bullet list items
    # Instead of collecting each <li> as an individual block,
    # we could group them by their parent <ul> or <ol> if we want to keep a single bullet list together.
    for ul in article_container.find_all("ul"):
        # We'll build a single string out of the bullet list
        bullet_list_text = []
        for li in ul.find_all("li"):
            bullet_text = li.get_text(strip=True)
            if bullet_text:
                # prefix bullet
                bullet_list_text.append(f"• {bullet_text}")
        if bullet_list_text:
            # Join them by newlines or your preferred delimiter
            content_blocks.append("\n".join(bullet_list_text))

    # Combine all blocks into a single list for chunking
    return content_blocks


def chunk_text_blocks(text_blocks, max_length=750):
    """
    Given a list of text blocks (e.g. headings, paragraphs, bullet lists),
    merge them into chunks ~<= max_length chars each, without splitting
    any single block across two chunks.
    """
    chunks = []
    current_chunk = ""

    for block in text_blocks:
        # If adding this block to the current chunk goes beyond max_length,
        # we start a new chunk. (But if block itself is longer than max_length,
        # we keep it whole anyway to avoid splitting mid-block.)

        # If we are empty, just start with the block
        if not current_chunk:
            current_chunk = block
        else:
            # Potential new chunk length if we add this block
            if len(current_chunk) + len(block) + 1 < max_length:
                # +1 for a space or newline
                current_chunk += "\n" + block
            else:
                # Push the current chunk to chunks array
                chunks.append(current_chunk)
                # Start a new chunk
                current_chunk = block

    # Append the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def main():
    # 1) Get all article links
    article_urls = get_help_articles(HELP_CENTER_URL)

    # 2) Scrape each article and chunk
    all_chunks = []
    for url in article_urls:
        try:
            text_blocks = scrape_article(url)
            # 3) Chunk the text blocks
            chunks_for_article = chunk_text_blocks(text_blocks, max_length=750)

            # For clarity, store them with some reference to the article
            for i, chunk in enumerate(chunks_for_article):
                all_chunks.append({
                    "url": url,
                    "chunk_index": i,
                    "text": chunk
                })
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # 4) Output to JSON
    with open("notion_help_chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
