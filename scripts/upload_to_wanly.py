import io
import json
import os
import uuid

import gradio as gr
import requests
from modules import scripts, script_callbacks

# Module-level storage so the on_image_saved callback can write to it
_last_image = None
_last_filename = None


def _on_image_saved(params):
    """Called after ALL postprocessing (including FaceSwapLab) and saving."""
    global _last_image, _last_filename
    _last_image = params.image
    _last_filename = os.path.basename(params.filename)


script_callbacks.on_image_saved(_on_image_saved)


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


def upload_image_to_wanly(image, filename, api_url=None, api_key=None):
    """Upload a PIL Image to the wanly API."""
    if api_url is None or api_key is None:
        config = load_wanly_config()
        if api_url is None:
            api_url = config.get("api_url", "")
        if api_key is None:
            api_key = config.get("api_key", "")

    api_url = api_url.rstrip("/")
    if not api_url:
        return False, "Error: API URL not set."
    if not api_key:
        return False, "Error: API Key not set."

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
            return True, f"Uploaded: {path}"
        else:
            return False, f"Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Error: {e}"


class UploadToWanlyScript(scripts.Script):
    def __init__(self):
        self.config_file = os.path.join(scripts.basedir(), "upload_to_wanly_config.json")
        self.config = self.load_config()

    def title(self):
        return "Upload to Wanly"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_config(self):
        return load_wanly_config()

    def save_config_to_file(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[Upload to Wanly] Error saving config: {e}")

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("a1111 tweaks - Upload to Wanly", open=False):
                api_url = gr.Textbox(
                    label="API URL",
                    value=self.config.get("api_url", ""),
                    placeholder="http://api.wanly22.com:8001",
                )
                api_key = gr.Textbox(
                    label="API Key",
                    value=self.config.get("api_key", ""),
                    type="password",
                )
                save_btn = gr.Button("Save Settings", variant="secondary")
                upload_btn = gr.Button("Upload Last Image", variant="primary")
                status_box = gr.Textbox(label="Status", interactive=False, lines=2)

                def save_settings(url, key):
                    self.config["api_url"] = url.rstrip("/")
                    self.config["api_key"] = key
                    self.save_config_to_file()
                    return "Settings saved."

                def upload_last(url, key):
                    if _last_image is None:
                        return "Error: No image available. Generate an image first."
                    success, message = upload_image_to_wanly(
                        _last_image,
                        _last_filename or f"{uuid.uuid4().hex}.png",
                        api_url=url,
                        api_key=key,
                    )
                    return message

                save_btn.click(
                    fn=save_settings,
                    inputs=[api_url, api_key],
                    outputs=[status_box],
                )
                upload_btn.click(
                    fn=upload_last,
                    inputs=[api_url, api_key],
                    outputs=[status_box],
                )

        return []