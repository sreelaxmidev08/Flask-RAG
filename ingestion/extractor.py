from pathlib import Path
from zipfile import BadZipFile, ZipFile

import logging


DEFAULT_OUTPUT_DIR = Path("data/flask_docs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Check that a ZIP member stays inside the extraction directory."""

    try:
        target_path.resolve().relative_to(base_dir.resolve())
        return True
    except ValueError:
        return False


def extract_docs(
    zip_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """
    Safely extract the Flask source ZIP file.

    Returns:
        Path to the extracted Flask source directory.
    """

    # 1. Check that the ZIP exists
    if not zip_path.exists():
        raise FileNotFoundError(
            f"ZIP file not found: {zip_path}"
        )

    # 2. Create the output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Flask's GitHub archive contains a top-level directory
    # matching the ZIP filename.
    extracted_dir = output_dir / zip_path.stem

    # 3. Don't extract again if it already exists
    if extracted_dir.exists():
        logger.info(
            "Documentation already extracted: %s",
            extracted_dir,
        )
        return extracted_dir

    logger.info("Extracting documentation from: %s", zip_path)

    try:
        with ZipFile(zip_path, "r") as zip_file:

            # 4. Validate every path before extracting
            for member in zip_file.infolist():
                target_path = output_dir / member.filename

                if not is_safe_path(output_dir, target_path):
                    raise ValueError(
                        f"Unsafe ZIP path detected: {member.filename}"
                    )

            # 5. Extract only after all paths have passed validation
            zip_file.extractall(output_dir)

    except BadZipFile as error:
        logger.error("Invalid or corrupted ZIP file: %s", zip_path)
        raise ValueError(
            f"Invalid or corrupted ZIP file: {zip_path}"
        ) from error

    except OSError as error:
        logger.error(
            "Failed to extract ZIP file: %s",
            zip_path,
        )
        raise

    logger.info(
        "Successfully extracted documentation to: %s",
        extracted_dir,
    )

    return extracted_dir


if __name__ == "__main__":
    zip_path = Path(
        "data/flask_docs/flask-3.1.3.zip"
    )

    extract_docs(zip_path)