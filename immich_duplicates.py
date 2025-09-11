#!/usr/bin/env

from itertools import groupby
from operator import attrgetter
from tabnanny import verbose
from typing import Generator
import json
import os
import requests


class Asset(dict):

    def __gt__(self, other: "Asset"):
        """
        Prefer assets that are in the external library.

        If they both are, prefer assets that are favourited.
        """
        if self.in_external_lib and not other.in_external_lib:
            return True
        elif not self.in_external_lib and other.in_external_lib:
            return False
        elif self.in_external_lib and other.in_external_lib:
            return self.get("isFavorite", False) and not other.get("isFavorite", False)
        else:
            return False

    @property
    def file_size(self) -> int:
        return self["exifInfo"]["fileSizeInByte"]

    @property
    def orig_name(self) -> str:
        return self["originalFileName"]
    
    @property
    def orig_path(self) -> str:
        return self["originalPath"]

    @property
    def in_external_lib(self) -> bool:
        ext_lib_path = "/volume1/photo/Photos"
        return self.orig_path.startswith(ext_lib_path)


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


def get_all_assets(url: str, verbose: bool = False) -> list:
    """
    Fetches all assets from the Immich server and returns a list of dictionaries.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": os.environ["IMMICH_API_KEY"],
    }

    all_assets = []
    page = 1

    while True:
        if verbose:
            print(f"fetching page {page} ...", end="")
        payload = json.dumps({"page": page, "withExif": True, "size": 1_000})
        response = requests.request(
            "POST", f"{url}/api/search/metadata", headers=headers, data=payload
        )
        response.raise_for_status()
        data = response.json()
        if not data["assets"]["items"]:
            break
        else:
            if verbose:
                print(f"first id: {data['assets']['items']}")
            all_assets.extend(data["assets"]["items"])
        page += 1

    return all_assets


def sort_groupby(iterable, key):
    """
    Sort and group an iterable by a key function.
    """
    yield from groupby(sorted(iterable, key=key), key=key)


def groups_larger_than_n(iterable, n, key):
    """
    Yield groups from an iterable that are larger than n, grouped by a key function.
    """
    for _, group in sort_groupby(iterable, key=key):
        group = tuple(group)
        if len(group) > n:
            yield group


def matching_file_size_orig_name(assets: list[dict]) -> Generator[tuple, None, None]:
    """
    Yield groups of assets that have the same file size and original file name.
    """
    assets = (Asset(a) for a in assets)
    for group in groups_larger_than_n(assets, n=1, key=attrgetter("file_size")):
        for matches in groups_larger_than_n(group, n=1, key=attrgetter("orig_name")):
            yield matches


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Delete Immich duplicate phone uploads"
    )
    parser.add_argument(
        "--url", type=str, required=True, help="The base URL of the Immich server"
    )
    parser.add_argument(
        "--check-manual",
        help="Check for assets with the same file size and original file name",
        action="store_true",
        default=False,
        dest="check_manual",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only list duplicates without deleting"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Verbose output", default=False
    )
    args = parser.parse_args()

    ids_to_delete = list(phone_upload_duplicate_ids(args.url))
    print(f"Duplicate API found {len(ids_to_delete)} duplicate phone uploads to delete")

    if args.check_manual:
        print("Checking for assets with same file size and original file name")
        print("Fetching asset metadata...")
        manual_check_ids_to_delete = []
        all_assets = get_all_assets(args.url)

        if args.verbose:
            print("would delete:")

        for group in matching_file_size_orig_name(all_assets):

            for asset in sorted(group)[:-1]:  # keep the last asset

                if args.verbose:
                    print(f"{asset['id']} {asset['originalFileName']}")

                manual_check_ids_to_delete.append(asset["id"])

        ids_to_delete.extend(manual_check_ids_to_delete)

        print(
            f"Found {len(manual_check_ids_to_delete)} dupes with the same file size and original filename"
        )

    if args.dry_run:
        print("Dry run, not deleting")
    
    elif ids_to_delete:
        delete_ids(args.url, ids_to_delete)
        print(f"Deleted {len(ids_to_delete)} duplicates")
    
    else:
        print("No duplicates to delete")
