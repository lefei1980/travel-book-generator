"""Standalone Playwright PDF worker — runs in a separate subprocess to avoid
asyncio event loop conflicts with uvicorn on Windows."""
import sys
import json
from playwright.sync_api import sync_playwright


def main():
    args = json.loads(sys.argv[1])
    html_path = args["html_path"]
    pdf_path = args["pdf_path"]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto(f"file:///{html_path}", wait_until="networkidle")

        try:
            page.wait_for_function("window.mapReady === true", timeout=15000)
        except Exception:
            pass  # proceed anyway

        page.wait_for_timeout(2000)

        page.pdf(
            path=pdf_path,
            format="A4",
            margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
            print_background=True,
        )

        browser.close()

    print(json.dumps({"status": "ok", "pdf_path": pdf_path}))


if __name__ == "__main__":
    main()
