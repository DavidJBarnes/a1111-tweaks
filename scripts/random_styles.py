import random
import gradio as gr
import json
import os
from modules import scripts


class RandomStylesScript(scripts.Script):
    def __init__(self):
        self.presets_file = os.path.join(scripts.basedir(), "random_styles_presets.json")
        self.style_pool = self.load_presets()

        # Common SDXL styles - expand this list as needed
        self.available_styles = [
            "3D Model", "Abstract", "Advertising", "Alien", "Analog Film", "Anime",
            "Architectural", "Cinematic", "Collage", "Comic Book", "Craft Clay", "Cubist",
            "Digital Art", "Disco", "Dreamscape", "Dystopian", "Enhance", "Fairy Tale",
            "Fantasy Art", "Fighting Game", "Film Noir", "Flat Papercut", "Food Photography",
            "GTA", "Gothic", "Graffiti", "Grunge", "HDR", "Horror", "Hyperrealism",
            "Impressionist", "Isometric Style", "Kirigami", "Legend of Zelda", "Line Art",
            "Long Exposure", "Lowpoly", "Minecraft", "Minimalist", "Monochrome", "Nautical",
            "Neon Noir", "Neon Punk", "Origami", "Paper Mache", "Paper Quilling",
            "Papercut Collage", "Papercut Shadow Box", "Photographic", "Pixel Art", "Pointillism",
            "Pokémon", "Pop Art", "Psychedelic", "RPG Fantasy Game", "Real Estate",
            "Retro Arcade", "Retro Game", "Rococo", "Silhouette", "Space",
            "Stained Glass", "Steampunk", "Surrealist", "Synthwave", "Tilt-Shift",
            "Tribal", "Typography", "Ukiyo-e", "Watercolor", "Zentangle"
        ]

    def title(self):
        return "Random SDXL Styles"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def load_presets(self):
        """Load saved style pool from file"""
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default style pool
        return ["Enhance", "Cinematic", "Photographic"]

    def save_presets(self):
        """Save style pool to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.style_pool, f, indent=2)
        except Exception as e:
            print(f"[Random Styles] Error saving presets: {e}")

    def get_style_pool_text(self):
        """Format style pool for display"""
        if not self.style_pool:
            return "No styles in pool"
        return "\n".join([f"{i + 1}. {style}" for i, style in enumerate(self.style_pool)])

    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("a1111 tweaks - Random Styles", open=False):
                enabled = gr.Checkbox(label="Enable Random Style Selection", value=False)

                seed_based = gr.Checkbox(
                    label="Use seed for randomization (reproducible)",
                    value=False
                )

                gr.Markdown("### Current Style Pool")
                pool_display = gr.Textbox(
                    label="Styles that will be randomly selected",
                    value=self.get_style_pool_text(),
                    interactive=False,
                    lines=8
                )

                gr.Markdown("### Add Style to Pool")
                with gr.Row():
                    style_dropdown = gr.Dropdown(
                        choices=self.available_styles,
                        label="Select Style",
                        value=self.available_styles[0] if self.available_styles else None
                    )
                    add_btn = gr.Button("Add to Pool", variant="primary")

                gr.Markdown("### Remove Style from Pool")
                with gr.Row():
                    remove_index = gr.Number(
                        label="Style Number to Remove",
                        value=1,
                        precision=0,
                        minimum=1
                    )
                    remove_btn = gr.Button("Remove Style", variant="secondary")

                clear_btn = gr.Button("Clear All Styles", variant="stop")

                def add_style(style):
                    if style and style not in self.style_pool:
                        self.style_pool.append(style)
                        self.save_presets()
                    elif style in self.style_pool:
                        return f"⚠️ '{style}' is already in the pool\n\n{self.get_style_pool_text()}"
                    return self.get_style_pool_text()

                def remove_style(index):
                    index = int(index) - 1
                    if 0 <= index < len(self.style_pool):
                        self.style_pool.pop(index)
                        self.save_presets()
                    return self.get_style_pool_text()

                def clear_all():
                    self.style_pool = []
                    self.save_presets()
                    return self.get_style_pool_text()

                add_btn.click(
                    fn=add_style,
                    inputs=[style_dropdown],
                    outputs=[pool_display]
                )

                remove_btn.click(
                    fn=remove_style,
                    inputs=[remove_index],
                    outputs=[pool_display]
                )

                clear_btn.click(
                    fn=clear_all,
                    inputs=[],
                    outputs=[pool_display]
                )

        return [enabled, seed_based]

    def process(self, p, enabled, seed_based):
        if not enabled:
            return

        if not self.style_pool:
            print("[Random Styles] No styles in pool!")
            return

        # Use seed for reproducibility if requested
        if seed_based:
            random.seed(p.seed)

        # Select a random style from the pool
        selected_style = random.choice(self.style_pool)

        # Set the style - this assumes the SDXL Styles extension uses p.styles
        # You may need to adjust this depending on how the styles extension works
        if hasattr(p, 'styles'):
            if isinstance(p.styles, list):
                # Replace existing styles
                p.styles = [selected_style]
            else:
                p.styles = selected_style

        print(f"[Random Styles] Selected style: {selected_style}")

    def postprocess(self, p, processed, enabled, seed_based):
        if enabled and hasattr(p, 'styles'):
            style_info = p.styles if isinstance(p.styles, str) else ", ".join(p.styles)
            processed.info += f"\nRandom Style: {style_info}"