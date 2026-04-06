import io
import json
import os

import requests
import gradio as gr
from modules import scripts
from PIL import Image

IMAGES_PER_PAGE = 10
BASE_DIR = os.path.expanduser("~/StabilityMatrix-linux-x64/Data/Images/Text2Img")
IMAGE_EXTENSIONS = ("*.png", "*.jpg", "*.jpeg", "*.webp")


def load_wanly_config():
    """Load wanly upload config from JSON."""
    config_file = os.path.join(scripts.basedir(), "upload_to_wanly_config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"api_url": "", "api_key": ""}


def upload_image_to_wanly(image, filename):
    """Upload a PIL Image to the wanly API."""
    config = load_wanly_config()
    api_url = config.get("api_url", "").rstrip("/")
    api_key = config.get("api_key", "")

    if not api_url:
        return "Error: API URL not set."
    if not api_key:
        return "Error: API Key not set."

    try:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        resp = requests.post(
            f"{api_url}/images/upload",
            params={"filename": filename},
            headers={"X-API-Key": api_key},
            files={"file": (filename, buf, "image/png")},
            timeout=60,
        )
        if resp.status_code == 200:
            path = resp.json().get("path", "")
            return f"Uploaded: {path}"
        else:
            return f"Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Error: {e}"


def scan_all_images():
    """Scan Text2Img directory recursively for images, sorted newest first."""
    if not os.path.isdir(BASE_DIR):
        return []
    files = []
    for ext in IMAGE_EXTENSIONS:
        files.extend([f for f in __import__('glob').glob(os.path.join(BASE_DIR, "**", ext), recursive=True)])
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    return files


def load_image_page(page):
    """Return (image_list, page_info_text) for the given page number (0-based)."""
    all_images = scan_all_images()
    total = len(all_images)
    if total == 0:
        return [], "No images found."
    start = page * IMAGES_PER_PAGE
    end = start + IMAGES_PER_PAGE
    page_files = all_images[start:end]
    images = []
    for f in page_files:
        try:
            images.append(Image.open(f))
        except Exception:
            pass
    info = f"Showing {start + 1}-{min(end, total)} of {total} images (page {page + 1})"
    return images, info


class GalleryScript(scripts.Script):
    def title(self):
        return "Gallery"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("a1111 tweaks - Gallery", open=False):
                gallery = gr.Gallery(
                    label="Recent Images",
                    value=[],
                    columns=10,
                    rows=1,
                    height=220,
                    object_fit="contain",
                )
                page_info = gr.Textbox(
                    label="Page Info",
                    value="Click Refresh to load images.",
                    interactive=False,
                )
                selected_index = gr.State(value=None)

                with gr.Row():
                    prev_btn = gr.Button("<< Prev", variant="secondary")
                    refresh_btn = gr.Button("Refresh", variant="primary")
                    next_btn = gr.Button("Next >>", variant="secondary")

                with gr.Row():
                    upload_btn = gr.Button("Upload Selected to Wanly", variant="primary")
                upload_status = gr.Textbox(label="Upload Status", interactive=False, lines=1)

                current_page = gr.State(value=0)

                def go_page(page):
                    images, info = load_image_page(page)
                    return images, info, page

                def go_prev(page):
                    new_page = max(0, page - 1)
                    return go_page(new_page)

                def go_next(page):
                    new_page = page + 1
                    return go_page(new_page)

                def do_refresh():
                    return go_page(0)

                prev_btn.click(fn=go_prev, inputs=[current_page], outputs=[gallery, page_info, current_page])
                next_btn.click(fn=go_next, inputs=[current_page], outputs=[gallery, page_info, current_page])
                refresh_btn.click(fn=do_refresh, inputs=[], outputs=[gallery, page_info, current_page])

                def on_select(evt: gr.SelectData):
                    return evt.index

                gallery.select(
                    fn=on_select,
                    inputs=[],
                    outputs=[selected_index],
                )

                def upload_selected(page, idx):
                    if idx is None:
                        return "No image selected. Click an image first."
                    all_images = scan_all_images()
                    start = page * IMAGES_PER_PAGE
                    real_idx = start + idx
                    if real_idx >= len(all_images):
                        return "Image no longer available."
                    filepath = all_images[real_idx]
                    try:
                        img = Image.open(filepath)
                        filename = os.path.basename(filepath)
                        return upload_image_to_wanly(img, filename)
                    except Exception as e:
                        return f"Error: {e}"

                upload_btn.click(
                    fn=upload_selected,
                    inputs=[current_page, selected_index],
                    outputs=[upload_status],
                )

        return []