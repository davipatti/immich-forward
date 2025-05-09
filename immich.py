#!/usr/bin/env python3

from ast import arg
from typing import Annotated, Union
import io
import json
import os
import requests

from fastapi import FastAPI, Query
from fastapi.responses import Response
from PIL import Image, ImageOps
import pillow_heif  # pip install pillow-heif


API_KEY = os.environ.get("IMMICH_API_KEY")


def search_person(name: str) -> requests.Response:
    """
    Search for a person by name.
    """
    return requests.request(
        "GET",
        f"{URL}/api/search/person?name={name}",
        headers={"Accept": "application/json", "x-api-key": API_KEY},
        data={},
    )


def get_person_id(name: str) -> str:
    """
    Get the person ID for a given name.
    """
    response = search_person(name)
    data = response.json()
    if len(data) == 1:
        return data[0]["id"]
    else:
        raise ValueError(f"not exactly one match for {name}\n{data}")


def search_random(person_ids: list[str], n: int = 1) -> requests.Response:
    """
    Search for a random asset that contain person IDs.
    """
    return requests.request(
        "POST",
        f"{URL}/api/search/random",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": API_KEY,
        },
        data=json.dumps(
            {"personIds": person_ids, "type": "IMAGE", "withDeleted": False, "size": n}
        ),
    )


def download_asset(id: str) -> requests.Response:
    """
    Download an asset by ID.
    """
    return requests.request(
        "GET",
        f"{URL}/api/assets/{id}/original",
        headers={
            "Accept": "application/octet-stream",
            "x-api-key": API_KEY,
        },
        data={},
    )


app = FastAPI()


@app.get("/immich/")
def get_immich(
    names: Annotated[Union[list[str], None], Query()],
    width: int = 600,
    height: int = 448,
) -> Response:
    """
    Entry point that fetches a random image that contains at least one of the names
    passed, resizes and pads it according to a width and height and then returns
    it as a Response.

    E.g. http://host:port/immich/?names=frodo&names=bilbo&width=600&height=448
    would return a random image that contains Frodo and Bilbo, resized to 600x448.
    """
    person_ids = [get_person_id(name) for name in names]

    # Fetch a random asset that contains these person_ids
    random = search_random(person_ids=person_ids, n=1)
    data = random.json()[0]
    random_id = data["id"]
    file_format = data["originalFileName"].split(".")[-1].lower()

    download_resp = download_asset(random_id)

    if file_format == "heic":
        heif_file = pillow_heif.open_heif(io.BytesIO(download_resp.content))
        img = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
    else:
        img = Image.open(io.BytesIO(download_resp.content))

    # Pad the image as requested
    padded = ImageOps.pad(img, (width, height))

    # Return the padded image as "image/jpeg" in a response
    # Create a bytes buffer to hold the JPEG image data
    img_byte_arr = io.BytesIO()

    # Save the padded image as JPEG to the buffer
    padded.save(img_byte_arr, format="JPEG")

    # Seek to the beginning of the buffer
    img_byte_arr.seek(0)

    # Return the image as a response
    return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Immich forwarder")
    parser.add_argument("--host", type=str, help="Host to bind to")
    parser.add_argument("--port", type=int, default=5678, help="Port to bind to")
    parser.add_argument("--immich_url", type=str, help="URL of the Immich server")
    args = parser.parse_args()

    URL = args.immich_url

    uvicorn.run(app, host=args.host, port=args.port)
