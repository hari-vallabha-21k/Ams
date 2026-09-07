import base64
from io import BytesIO

import qrcode

from app.config import settings
from app.enums import SubjectType

_PATH_PREFIX = {
    SubjectType.EMPLOYEE: "q",
    SubjectType.VISITOR: "v",
    SubjectType.DELIVERY: "d",
}


def pass_url(subject_type: SubjectType | str, token: str) -> str:
    prefix = _PATH_PREFIX[SubjectType(subject_type)]
    return f"{settings.public_base_url.rstrip('/')}/{prefix}/{token}"


def qr_png_data_uri(payload: str) -> str:
    """Render a QR code as a base64 PNG data URI for display, print or download."""
    img = qrcode.make(payload)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
