# AGENTS.md

## What This Is

An Automatic1111 (A1111) Stable Diffusion WebUI extension with 5 scripts + 1 shared module in `scripts/`. No build system, no tests, no CI. Scripts are loaded directly by A1111 at startup.

## Scripts

| Script | Purpose |
|--------|---------|
| `random_dimensions.py` | Randomly picks width/height from user-defined pairs before each generation |
| `random_faces.py` | Randomly selects a FaceSwapLab face checkpoint and injects it into `p.script_args[31]` |
| `random_styles.py` | Randomly picks an SDXL style prompt and sets `p.styles` |
| `upload_to_wanly.py` | Uploads the last generated image to a custom API (wanly22.com) via button click |
| `gallery.py` | Paginated browser of recent images from `~/StabilityMatrix-linux-x64/Data/Images/Text2Img/`, with per-image upload to wanly |
| `wanly_upload.py` | **Shared helper** — `upload_image_to_wanly(image, filename)` and `load_wanly_config()`. Imported by `upload_to_wanly.py` and `gallery.py`. |

## Architecture Notes

- All scripts extend `scripts.Script` and return `scripts.AlwaysVisible` from `show()` to appear in both txt2img and img2img tabs.
- `wanly_upload.py` is the only cross-script dependency — it is a plain module, not a Script subclass.
- Config/preset files are JSON stored alongside scripts using `scripts.basedir()`. These are **not** in `.gitignore` — do not commit user config files.
- Testing requires running inside an actual A1111 instance. There is no test harness.

## Gotchas

- **`random_faces.py` uses its own `Random()` instance** (`stdlib_random.Random()`) — do not replace with bare `random.choice()` or A1111's seed will make face selection deterministic.
- **`random_faces.py` hardcodes index 31** for FaceSwapLab's checkpoint in `p.script_args`. This is fragile and may break with A1111 or FaceSwapLab updates.
- **`upload_to_wanly.py` uses `script_callbacks.on_image_saved`** at module level to capture the last generated image. The callback fires after all postprocessing.
- The `process()` hook runs before generation; `before_process()` runs even earlier. `random_faces.py` uses `before_process()` because it needs to modify script args before other scripts read them.

## Conventions

- UI accordions use the prefix `a1111 tweaks -` in their titles.
- Console logging uses `[Script Name]` prefix format.
- Gradio closure functions inside `ui()` handle all button callbacks.
- New scripts should follow the same pattern: `scripts.Script` subclass, `AlwaysVisible`, JSON config via `scripts.basedir()`.

## See Also

- `claude.md` — detailed development context, A1111 API reference, testing checklist
