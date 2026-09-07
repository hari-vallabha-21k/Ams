"""Report rendering: CSV and a dependency-free PDF writer.

The PDF writer emits a simple paginated table using the standard Helvetica
font, which every PDF reader has built in - enough for an access report and
far lighter than pulling in a rendering engine.
"""

import csv
import io
from datetime import datetime

PAGE_WIDTH, PAGE_HEIGHT = 842, 595  # A4 landscape, in points
MARGIN = 32
LINE_HEIGHT = 14
FONT_SIZE = 8
HEADER_SIZE = 14


def to_csv(headers: list[str], rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    return buffer.getvalue()


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _truncate(value, width: int) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


def to_pdf(title: str, headers: list[str], rows: list[list], subtitle: str | None = None) -> bytes:
    columns = max(1, len(headers))
    usable = PAGE_WIDTH - 2 * MARGIN
    col_width = usable / columns
    chars_per_col = max(6, int(col_width / (FONT_SIZE * 0.55)))
    rows_per_page = int((PAGE_HEIGHT - 2 * MARGIN - 60) / LINE_HEIGHT)
    chunks = [rows[i : i + rows_per_page] for i in range(0, len(rows), rows_per_page)] or [[]]

    pages: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        parts = ["BT", f"/F1 {HEADER_SIZE} Tf", f"1 0 0 1 {MARGIN} {PAGE_HEIGHT - MARGIN} Tm",
                 f"({_escape(title)}) Tj", "ET"]
        caption = subtitle or f"Generated {datetime.utcnow():%d/%m/%Y %H:%M} UTC"
        parts += ["BT", f"/F1 {FONT_SIZE} Tf",
                  f"1 0 0 1 {MARGIN} {PAGE_HEIGHT - MARGIN - 16} Tm",
                  f"({_escape(caption)} - page {index} of {len(chunks)}) Tj", "ET"]

        y = PAGE_HEIGHT - MARGIN - 40
        parts += ["BT", f"/F1 {FONT_SIZE} Tf"]
        for column, header in enumerate(headers):
            x = MARGIN + column * col_width
            parts += [f"1 0 0 1 {x:.1f} {y} Tm", f"({_escape(_truncate(header.upper(), chars_per_col))}) Tj"]
        parts.append("ET")
        parts.append(f"{MARGIN} {y - 4} m {PAGE_WIDTH - MARGIN} {y - 4} l S")

        for row_index, row in enumerate(chunk):
            row_y = y - LINE_HEIGHT * (row_index + 1)
            parts += ["BT", f"/F1 {FONT_SIZE} Tf"]
            for column in range(columns):
                value = row[column] if column < len(row) else ""
                x = MARGIN + column * col_width
                parts += [
                    f"1 0 0 1 {x:.1f} {row_y:.1f} Tm",
                    f"({_escape(_truncate(value, chars_per_col))}) Tj",
                ]
            parts.append("ET")
        pages.append("\n".join(parts))

    return _assemble(pages)


def _assemble(pages: list[str]) -> bytes:
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []
    for content in pages:
        data = content.encode("latin-1", "replace")
        content_ids.append(add(b"<< /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"))
        page_ids.append(0)  # placeholder, filled once the pages object id is known

    pages_id = len(objects) + len(pages) + 1
    for position, content_id in enumerate(content_ids):
        page_ids[position] = add(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_obj = add(f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode())
    catalog_id = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)
