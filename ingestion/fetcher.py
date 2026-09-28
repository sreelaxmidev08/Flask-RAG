from pathlib import Path
import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --------------------------------------------------
# Configuration
# --------------------------------------------------

FLASK_VERSION = "3.1.3"

FLASK_DOCS_URL = (
    f"https://github.com/pallets/flask/archive/refs/tags/"
    f"{FLASK_VERSION}.zip"
)

DEFAULT_OUTPUT_DIR = Path("data/flask_docs")

REQUEST_TIMEOUT = 30


# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# Fetcher
# --------------------------------------------------

def create_session() -> requests.Session:
    """Create an HTTP session with retry support."""

    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def fetch_docs(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """
    Download the pinned Flask source repository.

    Returns:
        Path to the downloaded ZIP file.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / f"flask-{FLASK_VERSION}.zip"

    logger.info("Fetching Flask %s documentation", FLASK_VERSION)
    logger.info("Source: %s", FLASK_DOCS_URL)

    session = create_session()

    try:
        response = session.get(
            FLASK_DOCS_URL,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        if not response.content:
            raise ValueError("Downloaded file is empty")

        zip_path.write_bytes(response.content)

        logger.info(
            "Successfully downloaded Flask %s (%d bytes)",
            FLASK_VERSION,
            len(response.content),
        )

        logger.info("Saved to: %s", zip_path)

        return zip_path

    except requests.RequestException as error:
        logger.error("Failed to download Flask documentation: %s", error)
        raise

    except OSError as error:
        logger.error("Failed to save Flask documentation: %s", error)
        raise

    finally:
        session.close()


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    fetch_docs()
