import logging
from pathlib import Path

logger = logging.getLogger('kindle2notion')

def read_raw_clippings(clippings_file_path: Path) -> str:
    """
    Read the clippings file and handle various encoding issues.

    Args:
        clippings_file_path: Path to the My Clippings.txt file

    Returns:
        Decoded content of the clippings file
    """
    try:
        if not Path(clippings_file_path).exists():
            raise FileNotFoundError(f"Clippings file not found: {clippings_file_path}")

        # Try multiple encodings if the first one fails
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        raw_clippings_text = None

        for encoding in encodings:
            try:
                with open(clippings_file_path, "r", encoding=encoding) as raw_clippings_file:
                    raw_clippings_text = raw_clippings_file.read()
                logger.info(f"Successfully read file using {encoding} encoding")
                break
            except UnicodeDecodeError:
                logger.warning(f"Failed to decode with {encoding}, trying next encoding")
                continue

        if raw_clippings_text is None:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "Failed to decode file with any encoding")

        # Clean BOM and other characters
        raw_clippings_text = raw_clippings_text.replace('\ufeff', '')

        # Handle ASCII conversion with caution
        raw_clippings_text_decoded = raw_clippings_text.encode(
            "ascii", errors="ignore"
        ).decode()

        return raw_clippings_text_decoded

    except UnicodeDecodeError as e:
        logger.error(f"Error decoding the clippings file: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error reading the clippings file: {str(e)}")
        raise