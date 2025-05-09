# immich-forward

A small FastAPI service to proxy and transform image requests from an Immich server.

## Features

- Fetch random images of specific people from your Immich instance
- Resize and pad images to specified dimensions
- HEIC image format support
- Return images as JPEG format

## Usage

### Environment Setup

```bash
export IMMICH_API_KEY=your_immich_api_key
```

### Running the Service

```bash
python immich.py --host 0.0.0.0 --port 5678 --immich_url "http://your-immich-server.local"
```

### API Endpoint

```
GET /immich/?names=person1&names=person2&width=600&height=448
```

Parameters:
- `names`: One or more person names to search for (required)
- `width`: Output image width in pixels (default: 600)
- `height`: Output image height in pixels (default: 448)

Returns a JPEG image containing at least one of the specified people, resized and padded to the requested dimensions.

## Dependencies

- FastAPI
- Pillow
- pillow-heif
- requests
- uvicorn
