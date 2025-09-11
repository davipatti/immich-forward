#!/usr/bin/env

import os
import requests
from typing import Generator
import json



def phone_upload_duplicate_ids(url: str) -> Generator[str, None, None]:
    """
    Fetch all duplicates on the server.

    Find duplicates that have a combination of library imports (original path
    starts with /volume1/photo/Photos) and phone uploads, and generate their ids.
    """
    headers = {"Accept": "application/json", "x-api-key": os.environ["IMMICH_API_KEY"]}
    response = requests.request(
        "GET", f"{url}/api/duplicates", headers=headers, data={}
    )

    data = response.json()

    for dupe in data:

        external_lib_assets = [
            asset
            for asset in dupe["assets"]
            if asset["originalPath"].startswith("/volume1/photo/Photos")
        ]

        phone_upload_assets = [
            asset
            for asset in dupe["assets"]
            if asset["originalPath"].startswith("/usr/src/app/upload/upload/")
        ]

        if external_lib_assets and phone_upload_assets:

            for asset in phone_upload_assets:
                yield asset["id"]


def delete_ids(url: str, ids: list[str]) -> None:
    """
    Delete assets by their IDs.

    Args:
        url: The base URL of the Immich server.
        ids: A list of asset IDs to delete.

    Returns:
        The response from the delete request.
    """
    payload = json.dumps({"force": True, "ids": ids})
    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.environ["IMMICH_API_KEY"],
    }
    return requests.request(
        "DELETE", f"{url}/api/assets", headers=headers, data=payload
    )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Delete Immich duplicate phone uploads")
    parser.add_argument(
        "--url", type=str, required=True, help="The base URL of the Immich server"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only list duplicates without deleting"
    )
    args = parser.parse_args()

    ids = list(phone_upload_duplicate_ids(args.url))
    print(f"Found {len(ids)} duplicate phone uploads to delete")
    
    if args.dry_run:
        print("Dry run, not deleting")
    elif ids:
        delete_ids(args.url, ids)
        print("Deleted duplicate phone uploads")
    else:
        print("No duplicate phone uploads to delete")
