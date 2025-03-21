# Kindle2Notion

A Python utility to export Kindle highlights and notes to a Notion database.

## Setup

1. Clone this repository
2. Create a `.env` file with your Notion API credentials (see `.env.example`)
3. Install the package:
    ```
    pip install -e .
    ```

## Usage

### Local Usage

Run the script locally:

```bash
python -m kindle2notion
```

By default, it will look for a file named "My Clippings.txt" in the current directory.

### Command Line Options

```bash
# Specify a different clippings file
python -m kindle2notion "path/to/My Clippings.txt"

# Disable location information
python -m kindle2notion --enable_location=False

# Disable highlight date
python -m kindle2notion --enable_highlight_date=False

# Disable book covers
python -m kindle2notion --enable_book_cover=False

# Use separate blocks for each highlight (slower but more organized)
python -m kindle2notion --separate_blocks=True
```

### GitHub Action

This repository includes a GitHub Action that can be triggered manually to sync your Kindle highlights to Notion:

1. Fork this repository
2. Add your "My Clippings.txt" file to the repository
3. Add your Notion API credentials as GitHub Secrets:
    - `NOTION_API_AUTH_TOKEN`
    - `NOTION_DATABASE_ID`
4. Run the "Sync Kindle Highlights to Notion" workflow from the Actions tab

## Required Notion Database Structure

Your Notion database should have the following properties:

-   Title (title): The book title
-   Author (rich text): The book's author
-   Highlights (number): Count of highlights and notes
-   Last Highlighted (date): Date of the most recent highlight
-   Last Synced (date): Date when the highlights were last synced

## License

MIT
