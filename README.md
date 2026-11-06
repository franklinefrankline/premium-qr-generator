# QR Studio

A polished Flask website URL-to-QR generator. QR images are generated in memory with Python's `qrcode` and Pillow; nothing is written to the `generated/` folder or retained between requests.

## Requirements

- Python 3.9 or newer
- pip

## Run locally

Open this folder in VS Code, then run these commands in the integrated terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate the environment again. On systems where `py` is unavailable, use `python` to create the virtual environment.

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Use

Enter a website URL or IP address and choose **Generate QR code**. Scheme-less IP addresses use `http://` by default, while domain names use `https://`; choose HTTP or HTTPS from the protocol menu when needed. An explicit scheme and any custom port are preserved. Invalid IP addresses and ports are rejected. The generated code uses high error correction, a white background, and dark-green modules. Download the PNG or copy the final destination URL.

For ESP32 Access Point mode, connect the phone to the ESP32 hotspot before scanning. For Station mode, connect the phone to the same Wi-Fi router as the ESP32. Local IP addresses are reachable only from a device with network access to the ESP32.

QR previews and downloads are generated on demand. Their signed links expire after one hour. Set a strong `SECRET_KEY` environment variable when running multiple application workers or deploying the app; otherwise a random key is created when the process starts.

## Routes

- `GET /` — generator page
- `POST /generate` — validates a URL and returns its normalized destination, QR image, and download URL as JSON
- `GET /download/<token>` — downloadable PNG with a safe filename

## Test

Run the URL validation, QR payload, preview, and download tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
