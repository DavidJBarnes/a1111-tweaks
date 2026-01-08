import random
import gradio as gr
import json
import os
from modules import scripts


class RandomFacesScript(scripts.Script):
    def __init__(self):
        self.presets_file = os.path.join(scripts.basedir(), "random_faces_presets.json")
        self.face_pool = self.load_presets()
        self.last_selected_face = None

        # You'll need to update this list with your actual .safetensors files
        # These are examples based on your screenshot
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
        # Default face pool (empty to avoid accidental face swaps)
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

                gr.Markdown("### Current Face Pool")
                pool_display = gr.Textbox(
                    label="Faces that will be randomly selected",
                    value=self.get_face_pool_text(),
                    interactive=False,
                    lines=8
                )

                gr.Markdown("### Add Face to Pool")
                with gr.Row():
                    face_dropdown = gr.Dropdown(
                        choices=self.available_faces,
                        label="Select Face",
                        value=self.available_faces[0] if self.available_faces else None
                    )
                    add_btn = gr.Button("Add to Pool", variant="primary")

                gr.Markdown("### Manage Pool")
                with gr.Row():
                    remove_index = gr.Number(
                        label="Face Number to Remove",
                        value=1,
                        precision=0,
                        minimum=1
                    )
                    remove_btn = gr.Button("Remove Face", variant="secondary")

                with gr.Row():
                    clear_btn = gr.Button("Clear All Faces", variant="stop")
                    refresh_btn = gr.Button("Refresh Available Faces", variant="secondary")

                def add_face(face):
                    if face and face not in self.face_pool:
                        self.face_pool.append(face)
                        self.save_presets()
                    elif face in self.face_pool:
                        return f"⚠️ '{face}' is already in the pool\n\n{self.get_face_pool_text()}"
                    return self.get_face_pool_text()

                def remove_face(index):
                    index = int(index) - 1
                    if 0 <= index < len(self.face_pool):
                        self.face_pool.pop(index)
                        self.save_presets()
                    return self.get_face_pool_text()

                def clear_all():
                    self.face_pool = []
                    self.save_presets()
                    return self.get_face_pool_text()

                def refresh_faces():
                    # Try to dynamically load faces from FaceSwapLab
                    # This is a placeholder - actual implementation depends on FaceSwapLab's structure
                    try:
                        # You may need to import FaceSwapLab modules here
                        # and get the actual list of available faces
                        pass
                    except:
                        pass
                    return face_dropdown.update(choices=self.available_faces)

                add_btn.click(
                    fn=add_face,
                    inputs=[face_dropdown],
                    outputs=[pool_display]
                )

                remove_btn.click(
                    fn=remove_face,
                    inputs=[remove_index],
                    outputs=[pool_display]
                )

                clear_btn.click(
                    fn=clear_all,
                    inputs=[],
                    outputs=[pool_display]
                )

                refresh_btn.click(
                    fn=refresh_faces,
                    inputs=[],
                    outputs=[face_dropdown]
                )

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

        # FaceSwapLab uses alwayson_scripts
        # We need to find the FaceSwapLab script and modify its args
        if hasattr(p, 'script_args') and p.script_args:
            try:
                # FaceSwapLab args are typically in a specific position
                # The face checkpoint is usually one of the early arguments
                # This tries to find and set it
                for i, arg in enumerate(p.script_args):
                    # Look for the face checkpoint field
                    if isinstance(arg, str) and arg.endswith('.safetensors'):
                        p.script_args[i] = selected_face
                        print(f"[Random Faces] Set face checkpoint to: {selected_face}")
                        return

                # If not found by extension, try setting at known positions
                # FaceSwapLab Face 1 checkpoint is typically around index 2-4
                for idx in [2, 3, 4]:
                    if idx < len(p.script_args):
                        p.script_args[idx] = selected_face
                        print(f"[Random Faces] Set face checkpoint at index {idx} to: {selected_face}")
                        return

            except Exception as e:
                print(f"[Random Faces] Error setting face: {e}")

        print(f"[Random Faces] Warning: Could not set face checkpoint")

    def process(self, p, enabled):
        # Moved logic to before_process
        pass

    def postprocess(self, p, processed, enabled):
        if enabled and self.last_selected_face:
            processed.info += f"\nRandom Face: {self.last_selected_face}"