# AGENTS.md

## What This Is

An Automatic1111 (A1111) Stable Diffusion WebUI extension with 5 scripts + 1 shared module in `scripts/`. No build system, no tests, no CI. Scripts are loaded directly by A1111 at startup.

## Scripts

| Script | Purpose |
|--------|---------|
| `random_dimensions.py` | Randomly picks width/height from user-defined pairs before each generation |
| `random_faces.py` | Randomly selects a FaceSwapLab face checkpoint and injects it into `p.script_args[31]` |
| `random_styles.py` | Randomly picks an SDXL style prompt and sets `p.styles` |
| `upload_to_wanly.py` | Uploads the last generated image to a custom API (wanly22.com) via button click, plus an "auto-upload every completed image" checkbox |
| `gallery.py` | Paginated browser of recent images from `~/StabilityMatrix-linux-x64/Data/Images/Text2Img/`, with per-image upload to wanly |
| `wanly_upload.py` | **Shared helper** — the hardcoded `API_URL`, config load/save, `upload_image_to_wanly()`, `is_grid_image()`, and the background auto-upload worker. Imported by `upload_to_wanly.py` and `gallery.py`. |

## Architecture Notes

- All scripts extend `scripts.Script` and return `scripts.AlwaysVisible` from `show()` to appear in both txt2img and img2img tabs.
- `wanly_upload.py` is the only cross-script dependency — it is a plain module, not a Script subclass. Consumers import it as `from scripts.wanly_upload import ...` (works because A1111 puts the extension root on `sys.path` and `scripts/` is a namespace package).
- Auto-upload flow: `ui()` returns the checkbox → `process()` stashes it plus the active `p` in module globals → `on_image_saved` enqueues the file path → a daemon worker thread in `wanly_upload.py` does the HTTP POST.
- Config/preset files are JSON stored alongside scripts using `scripts.basedir()`. These are **not** in `.gitignore` — do not commit user config files.
- Testing requires running inside an actual A1111 instance. There is no test harness.

## Gotchas

- **`random_faces.py` uses its own `Random()` instance** (`stdlib_random.Random()`) — do not replace with bare `random.choice()` or A1111's seed will make face selection deterministic.
- **`random_faces.py` hardcodes index 31** for FaceSwapLab's checkpoint in `p.script_args`. This is fragile and may break with A1111 or FaceSwapLab updates.
- **`upload_to_wanly.py` uses `script_callbacks.on_image_saved`** at module level to capture the last generated image. The callback fires after all postprocessing.
- **A1111's "generate forever" is client-side only** (`javascript/contextMenus.js` re-clicks the Generate button on a `setInterval`). There is no Python-visible flag, so auto-upload deliberately fires on *every* completed render rather than trying to detect that mode.
- **`on_image_saved` also fires for grids**, and grids are saved *last* — always run payloads through `is_grid_image()` before treating one as "the generated image".
- **Auto-upload is gated on `params.p is _active_p`**, not just the checkbox. Without the identity check, a stale flag would auto-upload unrelated saves from the Extras tab or PNG Info.
- **Never upload synchronously from `on_image_saved`** — it runs on the generation thread, so a blocking POST stalls the next generate-forever iteration. Queue the file path (not the PIL image) so long runs don't accumulate decoded images in RAM.
- **The endpoint is hardcoded** as `API_URL` in `wanly_upload.py`; only the API key is user-configurable. `save_wanly_config()` filters keys against `DEFAULT_CONFIG`, so the old `api_url` entry is dropped from existing config files on the next save.
- **The worker reads the API key from the config file**, not the UI textbox it can't see, so auto-upload requires clicking Save Settings first. After `MAX_CONSECUTIVE_FAILURES` it pauses itself; Save Settings or re-ticking the checkbox clears that.
- **`wanly_upload.py` is executed twice** — once by A1111's script loader (it globs `scripts/*.py`) and once via `import`. Harmless only because it registers no callbacks and starts no threads at import time. Keep it that way.
- The `process()` hook runs before generation; `before_process()` runs even earlier. `random_faces.py` uses `before_process()` because it needs to modify script args before other scripts read them.

## Conventions

- UI accordions use the prefix `a1111 tweaks -` in their titles.
- Console logging uses `[Script Name]` prefix format. The wanly scripts share the single `LOG_PREFIX` (`[Wanly Upload]`) exported by `wanly_upload.py` so one grep catches both files.
- Log the success path, not just failures — a silent console must never be ambiguous between "working" and "never fired".
- Gradio closure functions inside `ui()` handle all button callbacks.
- New scripts should follow the same pattern: `scripts.Script` subclass, `AlwaysVisible`, JSON config via `scripts.basedir()`.

## See Also

- `claude.md` — detailed development context, A1111 API reference, testing checklist
