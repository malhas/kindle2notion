from datetime import datetime
from typing import Dict, List, Tuple
import time
import logging

import notional
from notional.blocks import Paragraph, Quote
from notional.query import TextCondition
from notional.types import Date, ExternalFile, Number, RichText, Title
from requests import get, RequestException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('kindle2notion')

NO_COVER_IMG = "https://via.placeholder.com/150x200?text=No%20Cover"

# Maximum retries for API calls
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def export_to_notion(
    all_books: Dict,
    enable_location: bool,
    enable_highlight_date: bool,
    enable_book_cover: bool,
    separate_blocks: bool,
    notion_api_auth_token: str,
    notion_database_id: str,
) -> None:
    logger.info("Initiating transfer...")

    for title in all_books:
        each_book = all_books[title]
        author = each_book["author"]
        clippings = each_book["highlights"]
        clippings_count = len(clippings)

        (
            formatted_clippings,
            last_date,
        ) = _prepare_aggregated_text_for_one_book(clippings, enable_location, enable_highlight_date)

        try:
            message = _add_book_to_notion(
                title,
                author,
                clippings_count,
                formatted_clippings,
                last_date,
                notion_api_auth_token,
                notion_database_id,
                enable_book_cover,
                separate_blocks,
            )
            if message != "None to add":
                logger.info(f"✓ {message}")
        except Exception as e:
            logger.error(f"Error processing book '{title}': {str(e)}")


def _prepare_aggregated_text_for_one_book(
        clippings: List, enable_location: bool, enable_highlight_date: bool
) -> Tuple[List[str], str]:
    formatted_clippings = []
    last_date = ""

    for each_clipping in clippings:
        aggregated_text = ""
        text = each_clipping[0]
        page = each_clipping[1]
        location = each_clipping[2]
        date = each_clipping[3]
        is_note = each_clipping[4]

        if is_note:
            aggregated_text += "> " + "NOTE: \n"

        aggregated_text += text + "\n"
        if enable_location:
            if page != "":
                aggregated_text += "Page: " + page + ", "
            if location != "":
                aggregated_text += "Location: " + location
        if enable_highlight_date and (date != ""):
            aggregated_text += ", Date Added: " + date

        aggregated_text = aggregated_text.strip() + "\n\n"
        formatted_clippings.append(aggregated_text)

        # Keep track of the latest date
        if date and (not last_date or datetime.strptime(date, "%A, %d %B %Y %I:%M:%S %p") >
                    datetime.strptime(last_date, "%A, %d %B %Y %I:%M:%S %p")):
            last_date = date

    return formatted_clippings, last_date


def _add_book_to_notion(
    title: str,
    author: str,
    clippings_count: int,
    formatted_clippings: list,
    last_date: str,
    notion_api_auth_token: str,
    notion_database_id: str,
    enable_book_cover: bool,
    separate_blocks: bool,
):
    notion = notional.connect(auth=notion_api_auth_token)

    # Handle case where last_date might be empty
    if last_date:
        try:
            last_date_obj = datetime.strptime(last_date, "%A, %d %B %Y %I:%M:%S %p")
        except ValueError:
            logger.warning(f"Invalid date format for '{title}'. Using current date instead.")
            last_date_obj = datetime.now()
    else:
        last_date_obj = datetime.now()

    # Condition variables
    title_exists = False
    current_clippings_count = 0

    # Track which highlight locations we've already uploaded to avoid duplicates
    existing_locations = set()

    # Retry logic for Notion API calls
    for attempt in range(MAX_RETRIES):
        try:
            query = (
                notion.databases.query(notion_database_id)
                .filter(property="Title", rich_text=TextCondition(equals=title))
                .limit(1)
            )
            data = query.first()
            break
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"API call failed, retrying in {RETRY_DELAY}s... ({str(e)})")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Failed to query Notion API after {MAX_RETRIES} attempts: {str(e)}")
                raise

    if data:
        title_exists = True
        block_id = data.id
        block = notion.pages.retrieve(block_id)

        # Check if Highlights property exists
        if block["Highlights"] is None:
            block["Highlights"] = Number[0]
        elif block["Highlights"] == clippings_count:  # if no change in clippings
            title_and_author = str(block["Title"]) + " (" + str(block["Author"]) + ")"
            logger.info(title_and_author)
            logger.info("-" * len(title_and_author))
            return "None to add.\n"

        # Get existing highlight locations to avoid duplicates
        try:
            existing_content = notion.blocks.children.list(block_id)
            for child in existing_content:
                if hasattr(child, 'paragraph') and child.paragraph:
                    text = child.paragraph.rich_text[0].plain_text if child.paragraph.rich_text else ""
                    for line in text.split("\n"):
                        if "Location: " in line:
                            loc = line.split("Location: ")[1].split(",")[0].strip()
                            existing_locations.add(loc)
                elif hasattr(child, 'quote') and child.quote:
                    text = child.quote.rich_text[0].plain_text if child.quote.rich_text else ""
                    for line in text.split("\n"):
                        if "Location: " in line:
                            loc = line.split("Location: ")[1].split(",")[0].strip()
                            existing_locations.add(loc)
        except Exception as e:
            logger.warning(f"Could not retrieve existing highlights: {str(e)}")

    title_and_author = title + " (" + str(author) + ")"
    logger.info(title_and_author)
    logger.info("-" * len(title_and_author))

    # Filter out clippings that already exist
    new_formatted_clippings = []
    for clipping in formatted_clippings:
        should_add = True
        for line in clipping.split("\n"):
            if "Location: " in line:
                loc = line.split("Location: ")[1].split(",")[0].strip()
                if loc in existing_locations:
                    should_add = False
                    break
        if should_add:
            new_formatted_clippings.append(clipping)

    # If all clippings already exist, nothing to do
    if not new_formatted_clippings:
        return "None to add.\n"

    # Add a new book to the database
    if not title_exists:
        try:
            new_page = notion.pages.create(
                parent=notion.databases.retrieve(notion_database_id),
                properties={
                    "Title": Title[title],
                    "Author": RichText[author],
                    "Highlights": Number[clippings_count],
                    "Last Highlighted": Date[last_date_obj.isoformat()],
                    "Last Synced": Date[datetime.now().isoformat()],
                },
                children=[],
            )

            if separate_blocks:
                for formatted_clipping in new_formatted_clippings:
                    page_content = Quote[formatted_clipping.strip()]
                    notion.blocks.children.append(new_page, page_content)
            else:
                page_content = Paragraph["".join(new_formatted_clippings)]
                notion.blocks.children.append(new_page, page_content)

            block_id = new_page.id

            if enable_book_cover:
                # Fetch a book cover from Google Books if the cover for the page is not set
                if new_page.cover is None:
                    result = _get_book_cover_uri(title, author)

                if result is None:
                    # Set the page cover to a placeholder image
                    cover = ExternalFile[NO_COVER_IMG]
                    logger.warning(
                        "× Book cover couldn't be found. "
                        "Please replace the placeholder image with the original book cover manually."
                    )
                else:
                    # Set the page cover to that of the book
                    cover = ExternalFile[result]
                    logger.info("✓ Added book cover.")

                notion.pages.set(new_page, cover=cover)

        except Exception as e:
            logger.error(f"Error creating new page for '{title}': {str(e)}")
            raise

    else:
        # update a book that already exists in the database
        try:
            page = notion.pages.retrieve(block_id)

            if separate_blocks:
                for formatted_clipping in new_formatted_clippings:
                    page_content = Quote[formatted_clipping.strip()]
                    notion.blocks.children.append(page, page_content)
            else:
                page_content = Paragraph["".join(new_formatted_clippings)]
                notion.blocks.children.append(page, page_content)

            current_clippings_count = int(float(str(page["Highlights"])))
            page["Highlights"] = Number[clippings_count]
            page["Last Highlighted"] = Date[last_date_obj.isoformat()]
            page["Last Synced"] = Date[datetime.now().isoformat()]

        except Exception as e:
            logger.error(f"Error updating existing page for '{title}': {str(e)}")
            raise

    # Logging the changes made
    diff_count = len(new_formatted_clippings)
    message = f"{diff_count} notes/highlights added successfully.\n"

    return message


def _get_book_cover_uri(title: str, author: str):
    if title is None:
        return None

    req_uri = "https://www.googleapis.com/books/v1/volumes?q="
    req_uri += "intitle:" + title

    if author is not None:
        req_uri += "+inauthor:" + author

    try:
        response = get(req_uri, timeout=10).json().get("items", [])
        if len(response) > 0:
            for x in response:
                if x.get("volumeInfo", {}).get("imageLinks", {}).get("thumbnail"):
                    return (
                        x.get("volumeInfo", {})
                        .get("imageLinks", {})
                        .get("thumbnail")
                        .replace("http://", "https://")
                    )
    except (RequestException, ValueError) as e:
        logger.error(f"Error fetching book cover: {str(e)}")

    return None