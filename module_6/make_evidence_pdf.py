from __future__ import annotations

import os
from datetime import datetime

from PIL import Image
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


IMAGES = [
    ("Running Website (http://localhost:8080)", "website.png"),
    ("RabbitMQ Queue (http://localhost:15672 → Queues → tasks_q)", "RabbitMQ.png"),
    ("Docker Containers (docker ps)", "docker_containers.png"),
    ("DockerHub Image Tag (web-v1)", "dockerhub_web_tag.png"),
    ("DockerHub Image Tag (worker-v1)", "dockerhub_worker_tag.png"),
]

DOCKERHUB_LINK = "https://hub.docker.com/r/thinktanck/module_6"


def _fit_image(img_w_px: int, img_h_px: int, max_w: float, max_h: float) -> tuple[float, float]:
    """Return (w, h) in points preserving aspect ratio within max bounds."""
    if img_w_px <= 0 or img_h_px <= 0:
        return max_w, max_h
    scale = min(max_w / img_w_px, max_h / img_h_px)
    return img_w_px * scale, img_h_px * scale


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "evidence.pdf")

    c = canvas.Canvas(out_path, pagesize=LETTER)
    page_w, page_h = LETTER

    # Title page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1 * inch, page_h - 1.25 * inch, "Module 6 – Deployment Evidence")

    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, page_h - 1.60 * inch, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.drawString(1 * inch, page_h - 1.85 * inch, f"DockerHub: {DOCKERHUB_LINK}")

    c.setFont("Helvetica", 11)
    y = page_h - 2.35 * inch
    c.drawString(1 * inch, y, "Included screenshots:")
    y -= 0.25 * inch
    for i, (title, fname) in enumerate(IMAGES, start=1):
        c.drawString(1.15 * inch, y, f"{i}. {title} — {fname}")
        y -= 0.20 * inch

    c.showPage()

    # Image pages
    margin = 0.75 * inch
    caption_gap = 0.25 * inch

    for idx, (title, fname) in enumerate(IMAGES, start=1):
        img_path = os.path.join(here, fname)
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Missing screenshot: {img_path}")

        # Caption
        c.setFont("Helvetica-Bold", 13)
        c.drawString(margin, page_h - margin, f"Figure {idx} – {title}")

        # Load image to get size (px)
        with Image.open(img_path) as im:
            w_px, h_px = im.size

        # Available space below caption
        max_w = page_w - 2 * margin
        max_h = page_h - (margin + 0.35 * inch) - (margin + caption_gap)

        draw_w, draw_h = _fit_image(w_px, h_px, max_w, max_h)

        # Bottom-left origin for image
        x = (page_w - draw_w) / 2
        y = margin

        c.drawImage(img_path, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, anchor="c")
        c.showPage()

    c.save()
    print(f"Created: {out_path}")


if __name__ == "__main__":
    main()