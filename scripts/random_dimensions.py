import random
import gradio as gr
import json
import os
from modules import scripts
from modules.processing import process_images


class RandomDimensionsScript(scripts.Script):
    def __init__(self):
        self.presets_file = os.path.join(scripts.basedir(), "random_dimensions_presets.json")
        self.dimension_pairs = self.load_presets()

    def title(self):
        return "Random Dimensions"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_presets(self):
        """Load saved dimension pairs from file"""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default presets
        return [
            {"width": 512, "height": 512},
            {"width": 768, "height": 512},
            {"width": 512, "height": 768},
        ]

    def save_presets(self):
        """Save dimension pairs to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.dimension_pairs, f, indent=2)
        except Exception as e:
            print(f"[Random Dimensions] Error saving presets: {e}")

    def get_preset_list_text(self):
        """Format dimension pairs for display"""
        if not self.dimension_pairs:
            return "No dimension pairs saved"
        return "\n".join([f"{i + 1}. {pair['width']}x{pair['height']}"
                          for i, pair in enumerate(self.dimension_pairs)])

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("a1111 tweaks - Random Dimensions", open=False):
                enabled = gr.Checkbox(label="Enable Random Dimensions", value=False)

                gr.Markdown("### Saved Dimension Pairs")
                preset_display = gr.Textbox(
                    label="Current Pairs",
                    value=self.get_preset_list_text(),
                    interactive=False,
                    lines=5
                )

                gr.Markdown("### Add New Pair")
                with gr.Row():
                    new_width = gr.Number(label="Width", value=512, precision=0)
                    new_height = gr.Number(label="Height", value=512, precision=0)
                    add_btn = gr.Button("Add Pair", variant="primary")

                gr.Markdown("### Remove Pair")
                with gr.Row():
                    remove_index = gr.Number(
                        label="Pair Number to Remove",
                        value=1,
                        precision=0,
                        minimum=1
                    )
                    remove_btn = gr.Button("Remove Pair", variant="secondary")

                clear_btn = gr.Button("Clear All Pairs", variant="stop")

                def add_pair(width, height):
                    self.dimension_pairs.append({"width": int(width), "height": int(height)})
                    self.save_presets()
                    return self.get_preset_list_text()

                def remove_pair(index):
                    index = int(index) - 1
                    if 0 <= index < len(self.dimension_pairs):
                        self.dimension_pairs.pop(index)
                        self.save_presets()
                    return self.get_preset_list_text()

                def clear_all():
                    self.dimension_pairs = []
                    self.save_presets()
                    return self.get_preset_list_text()

                add_btn.click(
                    fn=add_pair,
                    inputs=[new_width, new_height],
                    outputs=[preset_display]
                )

                remove_btn.click(
                    fn=remove_pair,
                    inputs=[remove_index],
                    outputs=[preset_display]
                )

                clear_btn.click(
                    fn=clear_all,
                    inputs=[],
                    outputs=[preset_display]
                )

        return [enabled]

    def process(self, p, enabled):
        if not enabled:
            return

        if not self.dimension_pairs:
            print("[Random Dimensions] No dimension pairs available!")
            return

        # Select a random dimension pair
        selected_pair = random.choice(self.dimension_pairs)
        p.width = selected_pair["width"]
        p.height = selected_pair["height"]

        print(f"[Random Dimensions] Set dimensions to: {p.width}x{p.height}")

    def postprocess(self, p, processed, enabled):
        if enabled:
            processed.info += f"\nRandom Dimensions: {p.width}x{p.height}"