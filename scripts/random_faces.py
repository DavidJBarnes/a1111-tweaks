import random
import gradio as gr
import json
import os
import glob
import time
from modules import scripts
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
    def rename_swapped_files(self, p):
        """Find and rename -swapped files to include face name"""
        if not self.last_selected_face:
            return
        face_name = self.get_face_name(self.last_selected_face)
        if not face_name:
            return
        # Get the output directory
        outdir = p.outpath_samples if hasattr(p, 'outpath_samples') else None
        if not outdir:
            print("[Random Faces] Could not determine output directory")
            return
        # Look for recently created -swapped files (within last 30 seconds)
        current_time = time.time()
        swapped_pattern = os.path.join(outdir, "*-swapped.png")
        swapped_files = glob.glob(swapped_pattern)
        for swapped_file in swapped_files:
            # Only process files created in the last 30 seconds
            file_mtime = os.path.getmtime(swapped_file)
            if current_time - file_mtime > 30:
                continue
            # Build new filename: replace -swapped with -facename
            new_filename = swapped_file.replace('-swapped.png', f'-{face_name}.png')
            try:
                os.rename(swapped_file, new_filename)
                print(f"[Random Faces] Renamed: {os.path.basename(swapped_file)} -> {os.path.basename(new_filename)}")
            except Exception as e:
                print(f"[Random Faces] Error renaming file: {e}")
    def postprocess(self, p, processed, enabled):
        """Add selected face info to generation parameters and rename swapped files"""
        if enabled and self.last_selected_face:
            if hasattr(processed, 'infotexts') and processed.infotexts:
                for i in range(len(processed.infotexts)):
                    processed.infotexts[i] += f", Random Face: {self.last_selected_face}"
            self.rename_swapped_files(p)