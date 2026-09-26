# AGENTS.md

## What This Is

An Automatic1111 (A1111) Stable Diffusion WebUI extension with 6 scripts + 1 shared module in `scripts/`, plus one browser-side file in `javascript/`. No build system, no tests, no CI. Both directories are loaded directly by A1111 at startup.

## Scripts

| Script | Purpose |
|--------|---------|
| `random_dimensions.py` | Randomly picks width/height from user-defined pairs before each generation |
| `random_faces.py` | Randomly selects a FaceSwapLab face checkpoint and injects it into `p.script_args[31]` |
| `random_styles.py` | Randomly picks an SDXL style prompt and sets `p.styles` |
| `upload_to_wanly.py` | Uploads the last generated image to a custom API (wanly22.com) via button click, plus an "auto-upload every completed image" checkbox |
| `gallery.py` | Paginated browser of recent images from `~/StabilityMatrix-linux-x64/Data/Images/Text2Img/`, with per-image upload to wanly |
| `wanly_upload.py` | **Shared helper** — the hardcoded `API_URL`, config load/save, `upload_image_to_wanly()`, `is_grid_image()`, and the background auto-upload worker. Imported by `upload_to_wanly.py` and `gallery.py`. |
| `generate_forever_delay.py` | Registers the `tweaks_generate_forever_delay` Settings option (seconds, default 2). No `Script` subclass — just an `on_ui_settings` callback; the behaviour lives in the JS below. |
| `javascript/generate_forever_delay.js` | Replaces A1111's global `generateOnRepeat` with a version that waits that many seconds after each render before re-clicking Generate. |

## Architecture Notes

- All scripts extend `scripts.Script` and return `scripts.AlwaysVisible` from `show()` to appear in both txt2img and img2img tabs.
- `wanly_upload.py` is the only cross-script dependency — it is a plain module, not a Script subclass. Consumers import it as `from scripts.wanly_upload import ...` (works because A1111 puts the extension root on `sys.path` and `scripts/` is a namespace package).
- Auto-upload flow: `ui()` returns the checkbox → `process()` tags `p` with a `_wanly_auto_upload` marker attribute → `on_image_saved` checks the marker on `params.p` and enqueues the file path → a daemon worker thread in `wanly_upload.py` does the HTTP POST.
- Config/preset files are JSON stored alongside scripts using `scripts.basedir()`. These are **not** in `.gitignore` — do not commit user config files.
- Testing requires running inside an actual A1111 instance. There is no test harness.

## Gotchas

- **`random_faces.py` uses its own `Random()` instance** (`stdlib_random.Random()`) — do not replace with bare `random.choice()` or A1111's seed will make face selection deterministic.
- **`random_faces.py` hardcodes index 31** for FaceSwapLab's checkpoint in `p.script_args`. This is fragile and may break with A1111 or FaceSwapLab updates.
- **`upload_to_wanly.py` uses `script_callbacks.on_image_saved`** at module level to capture the last generated image. The callback fires after all postprocessing.
- **A1111's "generate forever" is client-side only** (`javascript/contextMenus.js` re-clicks the Generate button on a `setInterval`). There is no Python-visible flag, so auto-upload deliberately fires on *every* completed render rather than trying to detect that mode.
- **`generateOnRepeat` is a top-level `let` in core JS**, i.e. a lexical global, *not* a property of `window` — `window.generateOnRepeat = ...` silently does nothing. Override it with a bare-name assignment from inside a function, and read it through `try`/`catch` since touching an uninitialised lexical global throws `ReferenceError` rather than returning `undefined`.
- **The replacement keeps its timer in `window.generateOnRepeatInterval`** so the stock "Cancel generate forever" context-menu item, which just calls `clearInterval` on it, keeps working. Do not move the handle to a private variable.
- **Don't implement the inter-run wait as `time.sleep()` in `postprocess()`.** It would block the generation thread, so the Interrupt button stays up, the UI reads busy, and queued API jobs stall — the same problem described below for synchronous uploads.
- **Extension `javascript/*.js` loads after core JS** (`list_scripts` walks the webui's own `javascript/` dir first, then extensions), which is what makes the override land. Anything that must survive a different load order belongs in an `onUiLoaded` callback.
- **`on_image_saved` also fires for grids**, and grids are saved *last* — always run payloads through `is_grid_image()` before treating one as "the generated image".
- **Auto-upload is gated on a marker attribute on `p`**, not just the checkbox, so a stale flag can't auto-upload unrelated saves from the Extras tab or PNG Info (those carry no `p` or an unmarked one).
- **Don't gate on `p` identity (`params.p is _active_p`).** That shipped and broke whenever ADetailer was enabled: after its inpaint pass ADetailer calls `p.scripts.before_process(copy(p))` and `p.scripts.process(copy(p))` on *every* script (its `ad_script_names` whitelist only filters its inner img2img, not this call), so the stored `p` became a shallow copy, and FaceSwapLab's later save carried the original — logged as `p mismatch` on every image. A marker attribute survives `copy()`.
- **Never clear the marker in `postprocess()`.** FaceSwapLab adds its swapped image late (watch for `Add swp image to processed` in the log), so the save can land *after* this script's `postprocess` has run — clearing there rejects the very image auto-upload exists to send. This shipped once and produced a silent no-op: armed, generating, uploading nothing.
- **Every path that declines to queue must log why.** The four rejection branches (no `p`, `p` not armed, paused, already uploaded) were originally silent, which made "the gate rejected it" and "the callback never fired" indistinguishable in the log and turned a one-`grep` diagnosis into a code read.
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
