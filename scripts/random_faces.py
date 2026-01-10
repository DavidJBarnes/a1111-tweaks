import gradio as gr
import json
import os
import random as stdlib_random

from modules import scripts
from modules.processing import StableDiffusionProcessing


class RandomFacesScript(scripts.Script):
    # Use a separate Random instance that won't be affected by A1111's seeding
    rng = stdlib_random.Random()

    def __init__(self):
        super().__init__()
        self.face_pool = []
        self.available_faces = []
        self.last_selected_face = None
        self.config_file = os.path.join(scripts.basedir(), "random_faces_config.json")
        self.load_config()
        self.refresh_available_faces()

    def title(self):
        return "a1111 tweaks - Random Faces"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.face_pool = data.get('face_pool', [])
            except:
                self.face_pool = []

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump({'face_pool': self.face_pool}, f)

    def refresh_available_faces(self):
        faces_dir = os.path.join(os.path.dirname(scripts.basedir()), "models", "faceswaplab", "faces")
        if os.path.exists(faces_dir):
            self.available_faces = ["None"] + [f for f in os.listdir(faces_dir) if f.endswith('.safetensors')]
        else:
            # Try alternate path
            alt_faces_dir = os.path.expanduser("~/stable-diffusion-webui/models/faceswaplab/faces")
            if os.path.exists(alt_faces_dir):
                self.available_faces = ["None"] + [f for f in os.listdir(alt_faces_dir) if f.endswith('.safetensors')]
            else:
                self.available_faces = ["None"]

    def ui(self, is_img2img):
        with gr.Accordion("a1111 tweaks - Random Faces", open=False):
            with gr.Column():
                enabled = gr.Checkbox(label="Enable Random Face Selection", value=False)

                with gr.Row():
                    face_dropdown = gr.Dropdown(
                        label="Select Face to Add",
                        choices=self.available_faces,
                        value=self.available_faces[0] if self.available_faces else None
                    )
                    refresh_btn = gr.Button("🔄", scale=0)

                with gr.Row():
                    add_btn = gr.Button("Add to Pool")
                    remove_btn = gr.Button("Remove Selected")
                    clear_btn = gr.Button("Clear All")

                remove_index = gr.Number(label="Index to Remove (0-based)", value=0, precision=0)

                pool_display = gr.Textbox(
                    label="Current Face Pool",
                    value="\n".join(
                        [f"{i}: {face}" for i, face in enumerate(self.face_pool)]) if self.face_pool else "Empty",
                    interactive=False,
                    lines=5
                )

                def add_face(face):
                    if face and face != "None" and face not in self.face_pool:
                        self.face_pool.append(face)
                        self.save_config()
                    return "\n".join(
                        [f"{i}: {face}" for i, face in enumerate(self.face_pool)]) if self.face_pool else "Empty"

                def remove_face(idx):
                    idx = int(idx)
                    if 0 <= idx < len(self.face_pool):
                        self.face_pool.pop(idx)
                        self.save_config()
                    return "\n".join(
                        [f"{i}: {face}" for i, face in enumerate(self.face_pool)]) if self.face_pool else "Empty"

                def clear_all():
                    self.face_pool = []
                    self.save_config()
                    return "Empty"

                def refresh_faces():
                    self.refresh_available_faces()
                    return gr.Dropdown(choices=self.available_faces)

                add_btn.click(fn=add_face, inputs=[face_dropdown], outputs=[pool_display])
                remove_btn.click(fn=remove_face, inputs=[remove_index], outputs=[pool_display])
                clear_btn.click(fn=clear_all, inputs=[], outputs=[pool_display])
                refresh_btn.click(fn=refresh_faces, inputs=[], outputs=[face_dropdown])

        return [enabled]

    def before_process(self, p, enabled):
        if not enabled:
            return

        if not self.face_pool:
            print("[Random Faces] No faces in pool!")
            return

        # Filter out "None"
        valid_faces = [f for f in self.face_pool if f != "None"]

        if not valid_faces:
            print("[Random Faces] Only 'None' in pool, skipping")
            return

        # Use our own RNG instance - NOT affected by A1111's seed manipulation
        selected_face = self.rng.choice(valid_faces)

        # Store for later retrieval
        self.last_selected_face = selected_face

        # FaceSwapLab stores the face checkpoint at index 31 (after ControlNet installation)
        FACESWAPLAB_FACE_INDEX = 31

        if hasattr(p, 'script_args') and len(p.script_args) > FACESWAPLAB_FACE_INDEX:
            args_list = list(p.script_args)
            args_list[FACESWAPLAB_FACE_INDEX] = selected_face
            p.script_args = tuple(args_list)
            print(f"[Random Faces] Set face checkpoint to: {selected_face}")
        else:
            print(
                f"[Random Faces] Warning: Could not set face checkpoint (script_args length: {len(p.script_args) if hasattr(p, 'script_args') else 0})")

    def process(self, p, enabled):
        pass

    def postprocess(self, p, processed, enabled):
        """Add selected face info to generation parameters"""
        if enabled and self.last_selected_face:
            if hasattr(processed, 'infotexts') and processed.infotexts:
                for i in range(len(processed.infotexts)):
                    processed.infotexts[i] += f", Random Face: {self.last_selected_face}"