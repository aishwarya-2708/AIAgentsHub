# backend/tools/scraper.py
import requests
from bs4 import BeautifulSoup
from config import REQUEST_TIMEOUT, MAX_SCRAPE_CONTENT, WEB_REQUEST_DELAY
import time


def scrape_and_summarize(url):
    """MCTS-driven web scraping with table extraction"""

    max_retries = 2

    result = f"🔍 MCTS Web Scraping\n{'='*60}\n\n"
    result += f"🎯 URL: {url}\n"
    result += f"🤖 MCTS retry algorithm (2 attempts)...\n\n"

    for attempt in range(max_retries):
        try:

            result += f"🔄 Attempt {attempt + 1}/{max_retries}...\n"

            time.sleep(WEB_REQUEST_DELAY)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5"
            }

            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

            response.raise_for_status()

            result += f"✅ Success on attempt {attempt+1}\n\n{'='*60}\n\n"

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
                element.decompose()

            content_found = False

            # -----------------------------
            # Page Title
            # -----------------------------

            title = soup.find("title")

            if title:
                result += f"📌 Title: {title.get_text().strip()}\n\n"

            # -----------------------------
            # Tables
            # -----------------------------

            tables = soup.find_all("table")

            if tables:
                result += f"📊 TABLES FOUND ({len(tables)}):\n{'='*60}\n\n"
                result += extract_tables_formatted(tables)
                result += "\n"

            # -----------------------------
            # Lists
            # -----------------------------

            lists = soup.find_all(["ul", "ol"])

            if lists:
                result += f"\n📋 LISTS AS TABLES\n{'-'*60}\n\n"
                result += extract_lists_as_tables(lists[:3])

            # -----------------------------
            # Structured content
            # -----------------------------

            result += f"\n📄 CONTENT\n{'-'*60}\n\n"

            for heading in soup.find_all(["h1", "h2", "h3"])[:10]:

                heading_text = heading.get_text().strip()

                if not heading_text or len(heading_text) < 3:
                    continue

                content_found = True

                level = heading.name

                if level == "h1":
                    result += f"\n## {heading_text}\n{'='*40}\n"
                elif level == "h2":
                    result += f"\n### {heading_text}\n{'-'*30}\n"
                else:
                    result += f"\n#### {heading_text}\n"

                next_elem = heading.find_next_sibling()

                para_count = 0

                while next_elem and para_count < 2:

                    if next_elem.name == "p":

                        para_text = next_elem.get_text().strip()

                        if para_text and len(para_text) > 20:
                            result += f"\n{para_text}\n"
                            para_count += 1

                    elif next_elem.name in ["h1", "h2", "h3"]:
                        break

                    elif next_elem.name in ["ul", "ol"]:

                        items = next_elem.find_all("li")[:5]

                        for item in items:

                            text = item.get_text().strip()

                            if text:
                                result += f"  • {text}\n"

                        para_count += 1

                    next_elem = next_elem.find_next_sibling()

            # -----------------------------
            # Fallback paragraphs
            # -----------------------------

            if not content_found:

                result += "\n📝 Main Content\n\n"

                paragraphs = soup.find_all("p")

                for p in paragraphs[:15]:

                    text = p.get_text().strip()

                    if text and len(text) > 30:
                        result += f"{text}\n\n"

            # -----------------------------
            # Extract links
            # -----------------------------

            links = soup.find_all("a", href=True)

            valid_links = []

            for link in links:

                href = link.get("href")

                text = link.get_text().strip()

                if href and text and len(text) > 3 and len(text) < 100:

                    if href.startswith("http") or href.startswith("/"):

                        valid_links.append((text, href))

            if valid_links and len(valid_links) <= 10:

                result += f"\n\n🔗 Links Found\n{'-'*40}\n"

                for i, (text, href) in enumerate(valid_links[:10], 1):
                    result += f"{i}. {text}\n   {href}\n"

            # Limit output size

            if len(result) > MAX_SCRAPE_CONTENT:

                result = result[:MAX_SCRAPE_CONTENT] + \
                    f"\n\n... (truncated at {MAX_SCRAPE_CONTENT} chars)"

            return result

        except requests.exceptions.Timeout:

            if attempt < max_retries - 1:
                result += "⚠️ Timeout retrying...\n"
                continue

            return result + f"\n\n❌ Timeout after {max_retries} attempts"

        except requests.exceptions.ConnectionError:

            if attempt < max_retries - 1:
                result += "⚠️ Connection retrying...\n"
                continue

            return result + f"\n\n❌ Connection failed"

        except requests.exceptions.HTTPError as e:

            if attempt < max_retries - 1:
                result += f"⚠️ HTTP {e.response.status_code} retrying...\n"
                continue

            return result + f"\n\n❌ HTTP Error {e.response.status_code}"

        except Exception as e:

            if attempt < max_retries - 1:
                result += "⚠️ Error retrying...\n"
                continue

            return result + f"\n\n❌ Error: {str(e)[:100]}"

    return result + f"\n\n❌ All {max_retries} attempts failed"


# ---------------------------------------------------
# TABLE EXTRACTION
# ---------------------------------------------------

def extract_tables_formatted(tables):

    output = ""

    for idx, table in enumerate(tables[:5], 1):

        output += f"Table {idx}\n"

        rows = table.find_all("tr")

        if not rows:
            continue

        headers = [th.get_text().strip() for th in rows[0].find_all(["th", "td"])]

        rows = rows[1:]

        col_widths = [max(len(h), 15) for h in headers]

        output += "| " + " | ".join(h.ljust(w) for h, w in zip(headers, col_widths)) + " |\n"

        output += "|" + "|".join("-"*(w+2) for w in col_widths) + "|\n"

        for row in rows[:20]:

            cells = [td.get_text().strip() for td in row.find_all(["td", "th"])]

            while len(cells) < len(headers):
                cells.append("")

            cells = cells[:len(headers)]

            output += "| " + " | ".join(c[:w].ljust(w) for c, w in zip(cells, col_widths)) + " |\n"

        output += "\n"

    return output


# ---------------------------------------------------
# LIST TO TABLE
# ---------------------------------------------------

def extract_lists_as_tables(lists):

    output = ""

    for idx, lst in enumerate(lists, 1):

        items = lst.find_all("li")[:15]

        if not items:
            continue

        output += f"List {idx}\n"

        output += "| Item |\n"
        output += "|------|\n"

        for item in items:
            text = item.get_text().strip()
            if text:
                output += f"| {text} |\n"

        output += "\n"

    return output
############################################################################################
