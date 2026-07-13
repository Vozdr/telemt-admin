from __future__ import annotations

import base64
import io

import qrcode
import qrcode.image.svg


def domain_hex(domain: str) -> str:
    return domain.encode("utf-8").hex()


def make_link(secret: str, host: str, port: int, tls_domain: str) -> str:
    sni_domain = tls_domain or host
    return f"tg://proxy?server={host}&port={port}&secret=ee{secret}{domain_hex(sni_domain)}"


def make_qr_data_uri(link: str) -> str:
    img = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    return "data:image/svg+xml;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
