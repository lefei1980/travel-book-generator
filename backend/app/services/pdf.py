import json
import logging
import os
import subprocess
import sys
from app.services.maps import render_trip_html
from app.models import Trip

logger = logging.getLogger(__name__)

PDF_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "pdfs")
WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "_playwright_worker.py")


def generate_pdf(trip: Trip) -> str:
    """Render trip HTML with Leaflet maps, then convert to PDF via Playwright.
    Runs Playwright in a subprocess to avoid asyncio event loop conflicts
    with uvicorn on Windows.
    Returns the path to the generated PDF file."""
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

    html_content = render_trip_html(trip)

    html_path = os.path.join(PDF_OUTPUT_DIR, f"{trip.id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    pdf_path = os.path.join(PDF_OUTPUT_DIR, f"{trip.id}.pdf")

    # Use forward slashes for file:// URL compatibility
    html_url_path = html_path.replace(os.sep, "/")

    args = json.dumps({"html_path": html_url_path, "pdf_path": pdf_path})

    result = subprocess.run(
        [sys.executable, WORKER_SCRIPT, args],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error(f"Playwright worker failed: {result.stderr}")
        raise RuntimeError(f"PDF generation failed: {result.stderr[:500]}")

    # Clean up HTML temp file
    try:
        os.remove(html_path)
    except OSError:
        pass

    logger.info(f"PDF generated: {pdf_path}")
    return pdf_path
