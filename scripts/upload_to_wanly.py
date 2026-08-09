import os
import uuid

import gradio as gr
from modules import scripts, script_callbacks

from scripts.wanly_upload import (
    API_URL,
    auto_upload_status,
    is_grid_image,
    load_wanly_config,
    queue_auto_upload,
    reset_auto_upload,
    save_wanly_config,
    upload_image_to_wanly,
)

# Module-level storage so the on_image_saved callback can write to it
_last_image = None
_last_filename = None

# Set from process() so the callback knows whether the generation that produced
# this image had auto-upload enabled. Comparing against the active `p` keeps
# unrelated saves (Extras tab, PNG Info) from being picked up by a stale flag.
_auto_enabled = False
_active_p = None


def _on_image_saved(params):
    """Called after ALL postprocessing (including FaceSwapLab) and saving."""
    global _last_image, _last_filename
    try:
        if is_grid_image(params):
            return

        _last_image = params.image
        _last_filename = os.path.basename(params.filename)

        p = getattr(params, "p", None)
        if _auto_enabled and p is not None and p is _active_p:
            queue_auto_upload(params.filename)
    except Exception as e:
        print(f"[Upload to Wanly] Error handling saved image: {e}")


script_callbacks.on_image_saved(_on_image_saved)


class UploadToWanlyScript(scripts.Script):
    def __init__(self):
        self.config = load_wanly_config()

    def title(self):
        return "Upload to Wanly"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("a1111 tweaks - Upload to Wanly", open=False):
                gr.Markdown(f"Uploading to `{API_URL}`")
                api_key = gr.Textbox(
                    label="API Key",
                    value=self.config.get("api_key", ""),
                    type="password",
                )
                save_btn = gr.Button("Save Settings", variant="secondary")
                upload_btn = gr.Button("Upload Last Image", variant="primary")
                status_box = gr.Textbox(label="Status", interactive=False, lines=2)

                auto_upload = gr.Checkbox(
                    label="Auto-upload every completed image",
                    value=bool(self.config.get("auto_upload", False)),
                )
                gr.Markdown(
                    "Uploads run in the background using the **saved** API key - "
                    "click Save Settings after changing it. Pairs with A1111's "
                    "generate forever (right-click Generate)."
                )
                auto_status = gr.Textbox(
                    label="Auto-upload Status",
                    value=auto_upload_status(),
                    interactive=False,
                    lines=3,
                )
                refresh_btn = gr.Button("Refresh Auto-upload Status", variant="secondary")

                def save_settings(key, auto):
                    config = load_wanly_config()
                    config["api_key"] = key
                    config["auto_upload"] = bool(auto)
                    self.config = config
                    reset_auto_upload()
                    if not save_wanly_config(config):
                        return "Error saving settings - see console.", auto_upload_status()
                    return "Settings saved.", auto_upload_status()

                def upload_last(key):
                    if _last_image is None:
                        return "Error: No image available. Generate an image first."
                    success, message = upload_image_to_wanly(
                        _last_image,
                        _last_filename or f"{uuid.uuid4().hex}.png",
                        api_key=key,
                    )
                    return message

                def on_auto_toggle(auto):
                    # Re-enabling clears a paused circuit breaker so the user can
                    # fix settings and carry on without a restart.
                    if auto:
                        reset_auto_upload()
                    return auto_upload_status()

                save_btn.click(
                    fn=save_settings,
                    inputs=[api_key, auto_upload],
                    outputs=[status_box, auto_status],
                )
                upload_btn.click(
                    fn=upload_last,
                    inputs=[api_key],
                    outputs=[status_box],
                )
                auto_upload.change(
                    fn=on_auto_toggle,
                    inputs=[auto_upload],
                    outputs=[auto_status],
                )
                refresh_btn.click(
                    fn=auto_upload_status,
                    inputs=[],
                    outputs=[auto_status],
                )

        return [auto_upload]

    def process(self, p, auto_upload=False):
        global _auto_enabled, _active_p
        _auto_enabled = bool(auto_upload)
        _active_p = p

    def postprocess(self, p, processed, auto_upload=False):
        global _active_p
        if _active_p is p:
            _active_p = None
