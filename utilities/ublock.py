import shutil
from pathlib import Path
from zipfile import ZipFile

import requests

UBLOCK_DIR = Path(__file__).parent / "ublock"


def download_and_extract_latest_ublock():
    # Get the latest release URL
    response = requests.get(
        "https://github.com/gorhill/uBlock/releases/latest", allow_redirects=True
    )
    latest_version_tag = response.url.split("/")[-1]
    extract_path = UBLOCK_DIR / f"uBlock0_{latest_version_tag}"
    full_path = extract_path / "uBlock0.chromium"

    if full_path.exists():
        return full_path

    # Remove previous versions
    if UBLOCK_DIR.exists():
        shutil.rmtree(UBLOCK_DIR)

    UBLOCK_DIR.mkdir(exist_ok=True, parents=True)

    # Construct the download URL for the Chromium zip file
    download_url = f"https://github.com/gorhill/uBlock/releases/download/{latest_version_tag}/uBlock0_{latest_version_tag}.chromium.zip"

    # Download the zip file
    response = requests.get(download_url)
    zip_path = UBLOCK_DIR / f"uBlock0_{latest_version_tag}.chromium.zip"

    with open(zip_path, "wb") as f:
        f.write(response.content)

    # Extract the zip file
    with ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    # Clean up the zip file
    zip_path.unlink()

    return full_path
