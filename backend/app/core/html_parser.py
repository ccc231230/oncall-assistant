from bs4 import BeautifulSoup


def parse_html(html: str) -> dict:
    """
    Parse SOP HTML document into structured data.
    - Removes all <script> and <style> tags (including their content) via decompose()
    - Extracts title from <title> or <h1>
    - Extracts plain text content from <body>
    - BeautifulSoup automatically decodes HTML entities

    Returns: {"id": ..., "title": ..., "content": ...}
    """
    soup = BeautifulSoup(html, "html.parser")

    # Decompose script and style tags (must be done before get_text)
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Extract title
    title_tag = soup.title
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Untitled"

    # Extract content text
    body = soup.body
    if body:
        content = body.get_text(separator="\n", strip=True)
    else:
        content = soup.get_text(separator="\n", strip=True)

    return {
        "title": title,
        "content": content,
    }
