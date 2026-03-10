"""Download real Olist public datasets into data/raw.

Primary source:
https://github.com/olist/work-at-olist-data/tree/master/datasets
"""

from __future__ import annotations

import pathlib
import sys
from typing import Iterable

import requests


BASE_URLS = [
    "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets",
    "https://raw.githubusercontent.com/WillKoehrsen/Data-Analysis/master/olist_data",
]

DATA_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]


def download_file(url: str, destination: pathlib.Path) -> bool:
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        return False
    destination.write_bytes(response.content)
    return True


def try_download(filename: str, target_dir: pathlib.Path, base_urls: Iterable[str]) -> str:
    destination = target_dir / filename
    for base_url in base_urls:
        url = f"{base_url}/{filename}"
        if download_file(url, destination):
            return url
    raise RuntimeError(f"Failed to download {filename} from all configured sources.")


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    raw_dir = repo_root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(DATA_FILES)} files into: {raw_dir}")
    for filename in DATA_FILES:
        source_url = try_download(filename, raw_dir, BASE_URLS)
        size_mb = (raw_dir / filename).stat().st_size / (1024 * 1024)
        print(f"  ✓ {filename:<45} {size_mb:7.2f} MB  <-  {source_url}")

    print("Download complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
