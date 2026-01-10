import gradio as gr
import random
import json
import os
import glob
import re

from modules import scripts, script_callbacks
from modules.shared import opts


class RandomFacesScript(scripts.Script):
    def __init__(self):
        super().__init__()
        self.face_pool = []
        self.last_selected_face = None
        self.config_file = os.path.join(scripts.basedir(), "random_faces_config.json")
        self.load_config()

    def title(self):
        return "Random Faces"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_config(self):
        """Load face pool from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.face_pool = data.get('face_pool', [])
            except Exception as e:
                print(f"[Random Faces] Error loading config: {e}")
                self.face_pool = []

    def save_config(self):
        """Save face pool to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'face_pool': self.face_pool}, f, indent=2)
        except Exception as e:
            print(f"[Random Faces] Error saving config: {e}")

    def get_available_faces(self):
        """Get list of available face checkpoints from FaceSwapLab directory"""
        faces_dir = os.path.join(os.path.dirname(scripts.basedir()), "sd-webui-faceswaplab", "faces")
        if not os.path.exists(faces_dir):
            # Try alternate location
            faces_dir = os.path.join(opts.data_path, "models", "faceswaplab", "faces")

        faces = ["None"]  # Option to not swap
        if os.path.exists(faces_dir):
            for f in os.listdir(faces_dir):
                if f.endswith('.safetensors'):
                    faces.append(f)
        return sorted(faces)

    def ui(self, is_img2img):
        with gr.Accordion("Random Faces", open=False):
            enabled = gr.Checkbox(label="Enable Random Faces", value=False)

            available_faces = self.get_available_faces()

            face_pool = gr.CheckboxGroup(
                choices=available_faces,
                value=self.face_pool,
                label="Face Pool (randomly select from checked faces)"
            )

            current_pool = gr.Textbox(
                label="Current Pool",
                value=", ".join(self.face_pool) if self.face_pool else "None selected",
                interactive=False
            )

            def update_pool(selected):
                self.face_pool = selected
                self.save_config()
                return ", ".join(selected) if selected else "None selected"

            face_pool.change(
                fn=update_pool,
                inputs=[face_pool],
                outputs=[current_pool]
            )

        return [enabled]

    def get_face_short_name(self, face_filename):
        """Extract name from face filename for use in renamed files.

        Examples:
            Kelly_young.safetensors -> kelly_young
            Kelly_20251124.safetensors -> kelly_20251124
            Andrea_v2.safetensors -> andrea_v2
            Chelsea_all.safetensors -> chelsea_all
        """
        if not face_filename or face_filename == "None":
            return None

        # Remove .safetensors extension and lowercase
        name = face_filename.replace('.safetensors', '').lower()

        return name

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

    def postprocess(self, p, processed, enabled):
        """Add selected face info to generation parameters and rename swapped files"""
        if not enabled or not self.last_selected_face:
            return

        # Add face info to metadata
        if hasattr(processed, 'infotexts') and processed.infotexts:
            for i in range(len(processed.infotexts)):
                processed.infotexts[i] += f", Random Face: {self.last_selected_face}"

        # Rename swapped files
        self.rename_swapped_files(p, processed)

    def rename_swapped_files(self, p, processed):
        """Find and rename -swapped files to include face name"""
        if not self.last_selected_face:
            return

        short_name = self.get_face_short_name(self.last_selected_face)
        if not short_name:
            return

        # Get the output directory
        outdir = p.outpath_samples if hasattr(p, 'outpath_samples') else None
        if not outdir:
            print("[Random Faces] Could not determine output directory")
            return

        # Look for recently created -swapped files (within last 30 seconds)
        import time
        current_time = time.time()

        # Pattern: *-swapped.png
        swapped_pattern = os.path.join(outdir, "*-swapped.png")
        swapped_files = glob.glob(swapped_pattern)

        for swapped_file in swapped_files:
            # Only process files created in the last 30 seconds
            file_mtime = os.path.getmtime(swapped_file)
            if current_time - file_mtime > 30:
                continue

            # Build new filename: replace -swapped with -facename
            new_filename = swapped_file.replace('-swapped.png', f'-{short_name}.png')

            try:
                os.rename(swapped_file, new_filename)
                print(f"[Random Faces] Renamed: {os.path.basename(swapped_file)} -> {os.path.basename(new_filename)}")
            except Exception as e:
                print(f"[Random Faces] Error renaming file: {e}")