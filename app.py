import base64
import ipaddress
import os
import re
import secrets
from io import BytesIO
from urllib.parse import urlsplit

import qrcode
from qrcode.exceptions import DataOverflowError
from flask import Flask, abort, jsonify, render_template, request, send_file, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024

URL_TOKEN_SALT = "qr-download-v1"
MAX_URL_LENGTH = 2048
HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def normalize_url(value, protocol="auto"):
    """Validate a destination and infer a safe default scheme when needed."""
    if not isinstance(value, str):
        raise ValueError("Enter a valid website URL or IP address.")

    value = value.strip()
    if not value:
        raise ValueError("Enter a website URL or IP address to get started.")
    if len(value) > MAX_URL_LENGTH:
        raise ValueError("That URL is too long. Please use a shorter URL.")
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise ValueError("The URL cannot contain spaces or control characters.")

    if protocol not in ("auto", "http", "https"):
        raise ValueError("Choose automatic protocol detection, HTTP, or HTTPS.")

    has_scheme = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value) is not None
    if not has_scheme:
        try:
            candidate_hostname = urlsplit(f"//{value}").hostname
            ipaddress.ip_address(candidate_hostname or "")
            is_ip_address = True
        except ValueError:
            is_ip_address = False

        scheme = protocol if protocol != "auto" else ("http" if is_ip_address else "https")
        value = f"{scheme}://{value}"

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ValueError("Enter a valid website URL.") from None

    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc or not hostname:
        raise ValueError("Use a website address that starts with http:// or https://.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Website URLs with embedded usernames or passwords are not supported.")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Enter a valid port number.")
    if parsed.netloc.endswith(":"):
        raise ValueError("Enter a valid port number.")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if re.fullmatch(r"[0-9.]+", hostname):
            raise ValueError("Enter a valid IP address.") from None
        try:
            ascii_hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError:
            raise ValueError("Enter a valid website domain.") from None
        domain = ascii_hostname.rstrip(".")
        if not domain or len(domain) > 253:
            raise ValueError("Enter a valid website domain.")
        if domain.lower() != "localhost" and (
            "." not in domain
            or any(not HOST_LABEL.fullmatch(label) for label in domain.split("."))
        ):
            raise ValueError("Enter a valid website domain, such as example.com.")

    return value


def make_qr_code(value):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=16,
        border=4,
    )
    qr.add_data(value)
    qr.make(fit=True)
    return qr


def make_qr_image(value):
    qr = make_qr_code(value)
    image = qr.make_image(fill_color="#064e3b", back_color="#ffffff").convert("RGB")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


def token_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt=URL_TOKEN_SALT)


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify(error="That request is too large. Please use a shorter URL."), 413


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/generate")
def generate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Please enter a website URL or IP address."), 400

    try:
        value = normalize_url(data.get("url"), data.get("protocol", "auto"))
    except ValueError as error:
        return jsonify(error=str(error)), 400

    try:
        image = make_qr_image(value)
    except (DataOverflowError, ValueError):
        return jsonify(error="This URL is too long to fit in a QR code. Please use a shorter link."), 400

    token = token_serializer().dumps(value)
    return jsonify(
        url=value,
        image="data:image/png;base64," + base64.b64encode(image.getvalue()).decode("ascii"),
        download_url=url_for("download_qr", token=token),
    )


def url_from_token(token):
    try:
        return token_serializer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        abort(404)


@app.get("/download/<token>")
def download_qr(token):
    value = url_from_token(token)
    hostname = urlsplit(value).hostname or "website"
    filename = secure_filename(hostname)[:60] or "website"
    return send_file(
        make_qr_image(value),
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{filename}-qr-code.png",
        max_age=0,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
