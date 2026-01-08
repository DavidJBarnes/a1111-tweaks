import random
import gradio as gr
import json
import os
from modules import scripts


class RandomFacesScript(scripts.Script):
    def __init__(self):
        self.presets_file = os.path.join(scripts.basedir(), "random_faces_presets.json")
        self.face_pool = self.load_presets()

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

                seed_based = gr.Checkbox(
                    label="Use seed for randomization (reproducible)",
                    value=False
                )

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

        return [enabled, seed_based]

    def process(self, p, enabled, seed_based):
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

        # Use seed for reproducibility if requested
        if seed_based:
            random.seed(p.seed)

        # Select a random face from the pool
        selected_face = random.choice(valid_faces)

        # FaceSwapLab stores face selection in different ways depending on version
        # Try multiple approaches to set the face

        # Approach 1: Direct attribute (common in some versions)
        if hasattr(p, 'faceswaplab_face'):
            p.faceswaplab_face = selected_face

        # Approach 2: Via alwayson_scripts (more common)
        if hasattr(p, 'script_args'):
            # Find FaceSwapLab in script_args and update it
            # This part may need adjustment based on FaceSwapLab's exact structure
            for i, arg in enumerate(p.script_args):
                if isinstance(arg, dict) and 'face' in str(arg).lower():
                    p.script_args[i] = selected_face

        print(f"[Random Faces] Selected face: {selected_face}")

    def postprocess(self, p, processed, enabled, seed_based):
        if enabled:
            # Try to get the face that was used
            selected_face = "Unknown"
            if hasattr(p, 'faceswaplab_face'):
                selected_face = p.faceswaplab_face

            processed.info += f"\nRandom Face: {selected_face}"