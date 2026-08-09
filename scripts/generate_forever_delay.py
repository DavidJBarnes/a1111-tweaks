"""Exposes the "generate forever" cooldown as a Settings option.

The wait itself is implemented in ``javascript/generate_forever_delay.js`` --
generate forever is client-side only (A1111 re-clicks the Generate button from a
setInterval), so there is nothing on the Python side to pause. This file exists
purely so the delay can be changed from Settings without editing the JS and
reloading the UI; the JS re-reads ``opts`` on every tick.
"""

import gradio as gr
from modules import script_callbacks, shared

LOG_PREFIX = "[Generate Forever Delay]"

OPTION_KEY = "tweaks_generate_forever_delay"
DEFAULT_DELAY = 2.0


def on_ui_settings():
    section = ("a1111_tweaks", "a1111 tweaks")
    shared.opts.add_option(
        OPTION_KEY,
        shared.OptionInfo(
            DEFAULT_DELAY,
            "Generate forever: seconds to wait between runs",
            gr.Slider,
            {"minimum": 0.0, "maximum": 30.0, "step": 0.5},
            section=section,
        ).info("0 restores stock behaviour: the next render starts immediately"),
    )


script_callbacks.on_ui_settings(on_ui_settings)
print(f"{LOG_PREFIX} Loaded, default {DEFAULT_DELAY:g}s between generate-forever runs")
