import random
import gradio as gr
import json
import os
import glob
import time
from modules import scripts, script_callbacks


class RandomFacesScript(scripts.Script):
    def __init__(self):
        self.presets_file = os.path.join(scripts.basedir(), "random_faces_presets.json")
        self.face_pool = self.load_presets()
        self.last_selected_face = None
        # You'll need to update this list with your actual .safetensors files
        self.available_faces = [
            "None",
            "Andrea_all.safetensors",
            "Chelsea_all.safetensors",
            "JennyWade_all.safetensors",
            "Kelly_20251124.safetensors",
            "Kelly__all.safetensors",
            "Kelly__all_but_young.safetensors",
            "Kelly_young.safetensors",
            "Kerry_all.safetensors",
            "Me.safetensors",
            "Udycz_all.safetensors",
            "gena.safetensors",
            "jan.safetensors",
            "katymoore.safetensors",
            "pam_beesly.safetensors"
        ]

    def title(self):
        return "Random FaceSwapLab Faces"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_presets(self):
        """Load saved face pool from file"""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def save_presets(self):
        """Save face pool to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.face_pool, f, indent=2)
        except Exception as e:
            print(f"[Random Faces] Error saving presets: {e}")

    def get_face_pool_text(self):
        """Format face pool for display"""
        if not self.face_pool:
            return "No faces in pool"
        return "\n".join([f"{i + 1}. {face}" for i, face in enumerate(self.face_pool)])

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("a1111 tweaks - Random Faces", open=False):
                enabled = gr.Checkbox(label="Enable Random Face Selection", value=False)
                with gr.Row():
                    face_dropdown = gr.Dropdown(
                        choices=self.available_faces,
                        label="Add face to pool",
                        value="None"
                    )
                    add_btn = gr.Button("Add to Pool", scale=0)
                pool_display = gr.Textbox(
                    label="Current Face Pool",
                    value=self.get_face_pool_text(),
                    interactive=False,
                    lines=5
                )
                with gr.Row():
                    clear_btn = gr.Button("Clear Pool")
                    save_btn = gr.Button("Save Pool")

                def add_face(face):
                    if face and face != "None" and face not in self.face_pool:
                        self.face_pool.append(face)
                    return self.get_face_pool_text()

                def clear_pool():
                    self.face_pool = []
                    return self.get_face_pool_text()

                def save_pool():
                    self.save_presets()
                    return self.get_face_pool_text()

                add_btn.click(fn=add_face, inputs=[face_dropdown], outputs=[pool_display])
                clear_btn.click(fn=clear_pool, outputs=[pool_display])
                save_btn.click(fn=save_pool, outputs=[pool_display])
        return [enabled]

    def before_process(self, p, enabled):
        if not enabled:
            return
        if not self.face_pool:
            print("[Random Faces] No faces in pool!")
            return
        # Filter out "None" if you don't want to randomly disable face swap
        valid_faces = [f for f in self.face_pool if f != "None"]
        if not valid_faces:
            print("[Random Faces] Only 'None' in pool, skipping")
            return
        # Select a random face from the pool
        selected_face = random.choice(valid_faces)
        # Store for later retrieval
        self.last_selected_face = selected_face
        # FaceSwapLab stores the face checkpoint at index 31 (after ControlNet installation)
        # Previously was index 28 before ControlNet added its arguments
        FACESWAPLAB_FACE_INDEX = 31
        if hasattr(p, 'script_args') and len(p.script_args) > FACESWAPLAB_FACE_INDEX:
            args_list = list(p.script_args)
            args_list[FACESWAPLAB_FACE_INDEX] = selected_face
            p.script_args = tuple(args_list)
            print(f"[Random Faces] Set face checkpoint to: {selected_face}")
        else:
            print(f"[Random Faces] Warning: Could not set face checkpoint (script_args too short)")

    def process(self, p, enabled):
        # Moved logic to before_process
        pass

    def get_face_name(self, face_filename):
        """Extract name from face filename (remove .safetensors extension and lowercase)"""
        if not face_filename or face_filename == "None":
            return None
        return face_filename.replace('.safetensors', '').lower()

    def postprocess(self, p, processed, enabled):
        """Add selected face info to generation parameters"""
        if enabled and self.last_selected_face:
            if hasattr(processed, 'infotexts') and processed.infotexts:
                for i in range(len(processed.infotexts)):
                    processed.infotexts[i] += f", Random Face: {self.last_selected_face}"


# Global instance to track last selected face
_random_faces_instance = None


def on_image_saved(params):
    """Called after each image is saved - rename -swapped files"""
    global _random_faces_instance

    filepath = params.filename
    print(f"[Random Faces] on_image_saved called: {filepath}")

    if _random_faces_instance is None:
        print("[Random Faces] No instance, skipping")
        return
    if not _random_faces_instance.last_selected_face:
        print("[Random Faces] No last_selected_face, skipping")
        return

    if not filepath.endswith('-swapped.png'):
        print(f"[Random Faces] Not a swapped file, skipping")
        return

    face_name = _random_faces_instance.get_face_name(_random_faces_instance.last_selected_face)
    if not face_name:
        return

    new_filepath = filepath.replace('-swapped.png', f'-{face_name}.png')
    try:
        os.rename(filepath, new_filepath)
        print(f"[Random Faces] Renamed: {os.path.basename(filepath)} -> {os.path.basename(new_filepath)}")
    except Exception as e:
        print(f"[Random Faces] Error renaming file: {e}")


# Register the callback
script_callbacks.on_image_saved(on_image_saved)

# Hook to capture instance
_original_init = RandomFacesScript.__init__


def _new_init(self, *args, **kwargs):
    global _random_faces_instance
    _original_init(self, *args, **kwargs)
    _random_faces_instance = self


RandomFacesScript.__init__ = _new_init