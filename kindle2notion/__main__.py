import json
import os

import click
import notional
from dotenv import load_dotenv

from kindle2notion.exporting import export_to_notion
from kindle2notion.parsing import parse_raw_clippings_text
from kindle2notion.reading import read_raw_clippings


@click.command()
@click.argument("clippings_file", default="My Clippings.txt")
@click.option(
    "--enable_location",
    default=True,
    help='Set to False if you don\'t want to see the "Location" and "Page" information in Notion.'
)
@click.option(
    "--enable_highlight_date",
    default=True,
    help='Set to False if you don\'t want to see the "Date Added" information in Notion.',
)
@click.option(
    "--enable_book_cover",
    default=True,
    help="Set to False if you don't want to store the book cover in Notion.",
)
@click.option(
    "--separate_blocks",
    default=False,
    help='Set to True to separate each clipping into a separate quote block. Enabling this option significantly decreases upload speed.'
)

def main(
    clippings_file,
    enable_location,
    enable_highlight_date,
    enable_book_cover,
    separate_blocks
):
    # Load environment variables from .env file
    load_dotenv()

    # Get Notion credentials from environment variables
    notion_api_auth_token = os.environ.get("NOTION_API_AUTH_TOKEN")
    notion_database_id = os.environ.get("NOTION_DATABASE_ID")

    if not notion_api_auth_token or not notion_database_id:
        print("Error: NOTION_API_AUTH_TOKEN and NOTION_DATABASE_ID environment variables must be set")
        return

    notion = notional.connect(auth=notion_api_auth_token)
    db = notion.databases.retrieve(notion_database_id)

    if db:
        print("Notion page is found. Analyzing clippings file...")

        # Open the clippings text file and load it into all_clippings
        all_clippings = read_raw_clippings(clippings_file)

        # Parse all_clippings file and format the content to be sent to the Notion DB into all_books
        all_books = parse_raw_clippings_text(all_clippings)

        # Export all the contents in all_books into the Notion DB.
        export_to_notion(
            all_books,
            enable_location,
            enable_highlight_date,
            enable_book_cover,
            separate_blocks,
            notion_api_auth_token,
            notion_database_id
        )

        with open("my_kindle_clippings.json", "w") as out_file:
            json.dump(all_books, out_file, indent=4)

        print("Transfer complete... Exiting script...")
    else:
        print(
            "Notion page not found! Please check whether the Notion database ID is assigned properly."
        )


if __name__ == "__main__":
    main()