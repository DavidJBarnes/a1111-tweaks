import io
import json
import os
import uuid

import gradio as gr
import requests
from modules import scripts


class UploadToWanlyScript(scripts.Script):
    def __init__(self):
        self.config_file = os.path.join(scripts.basedir(), "upload_to_wanly_config.json")
        self.config = self.load_config()
        self.last_image = None
        self.last_filename = None

    def title(self):
        return "Upload to Wanly"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"api_url": "", "api_key": ""}

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
                    # Use form values directly so unsaved edits still work
                    api = url.rstrip("/") if url else self.config.get("api_url", "")
                    secret = key if key else self.config.get("api_key", "")
                    if not api:
                        return "Error: API URL not set."
                    if not secret:
                        return "Error: API Key not set."
                    if self.last_image is None:
                        return "Error: No image available. Generate an image first."
                    try:
                        buf = io.BytesIO()
                        self.last_image.save(buf, format="PNG")
                        buf.seek(0)
                        filename = self.last_filename or f"{uuid.uuid4().hex}.png"
                        resp = requests.post(
                            f"{api}/images/upload",
                            params={"filename": filename},
                            headers={"X-API-Key": secret},
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

    def postprocess(self, p, processed):
        if processed.images:
            self.last_image = processed.images[0]
            # Derive filename from seed
            try:
                seed = processed.all_seeds[0]
                self.last_filename = f"{seed}.png"
            except (IndexError, AttributeError):
                self.last_filename = f"{uuid.uuid4().hex}.png"
