# Random Dimensions Extension for Automatic1111

A simple but powerful extension for Automatic1111 Stable Diffusion WebUI that allows you to define and save specific width/height dimension pairs, then randomly select one for each image generation.

## Features

- **Custom Dimension Pairs**: Define and save your own width/height combinations
- **Persistent Storage**: Pairs are saved to JSON and persist across sessions
- **Easy Management**: Add, remove, or clear dimension pairs through the UI
- **Random Selection**: Each generation randomly picks one of your saved pairs
- **Seed-Based Randomization**: Optional reproducible dimension selection based on generation seed
- **Works Everywhere**: Compatible with both txt2img and img2img

## Installation

1. Navigate to your Automatic1111 extensions folder:
   ```
   cd stable-diffusion-webui/extensions/
   ```

2. Clone or download this repository:
   ```
   git clone https://github.com/yourusername/a1111-tweaks.git
   ```
   
   Or manually create the folder structure:
   ```
   stable-diffusion-webui/extensions/a1111-tweaks/scripts/
   ```

3. Place `random_dimensions.py` in the `scripts` folder

4. Restart the WebUI or click "Reload UI"

## File Structure

```
a1111-tweaks/
├── scripts/
│   ├── random_dimensions.py
│   └── random_dimensions_presets.json (auto-generated)
├── README.md
└── LICENSE
```

## Usage

### Basic Setup

1. Navigate to either txt2img or img2img tab
2. Look for the **"Random Dimensions"** accordion section
3. Check **"Enable Random Dimensions"** to activate the extension

### Managing Dimension Pairs

#### Adding Pairs
1. Enter desired **Width** and **Height** values
2. Click **"Add Pair"**
3. The pair will appear in the "Current Pairs" list

#### Removing Pairs
1. Note the number of the pair you want to remove from the "Current Pairs" list
2. Enter that number in **"Pair Number to Remove"**
3. Click **"Remove Pair"**

#### Clearing All Pairs
- Click **"Clear All Pairs"** to remove all saved dimension pairs

### Example Configuration

Here's a common setup for versatile generation:

- **512x512** - Standard square
- **768x512** - Landscape
- **512x768** - Portrait
- **1024x576** - Widescreen
- **576x1024** - Tall portrait
- **1024x1024** - Large square

Each generation will randomly select one of these pairs.

### Seed-Based Randomization

Enable **"Use seed for randomization (reproducible)"** if you want the same seed to always use the same dimension pair. This is useful for:
- Reproducing exact results
- Testing different settings with consistent dimensions
- Batch processing with predictable dimensions

## How It Works

1. When enabled, the extension intercepts the image generation process
2. Before generation starts, it randomly selects a width/height pair from your saved list
3. The selected dimensions override the UI's width/height settings
4. The chosen dimensions are added to the generation info for reference

## Troubleshooting

### Extension doesn't appear
- Make sure the file is in the correct location: `extensions/a1111-tweaks/scripts/random_dimensions.py`
- Restart the WebUI completely (not just reload UI)
- Check the console for any error messages

### Dimensions not changing
- Verify that "Enable Random Dimensions" is checked
- Make sure you have at least one dimension pair saved
- Check the console output - it will print the selected dimensions

### Presets not saving
- Ensure the WebUI has write permissions in the extensions folder
- Check that `random_dimensions_presets.json` can be created in the `scripts` folder

## Default Dimension Pairs

If no presets file exists, the extension starts with these defaults:
- 512x512
- 768x512
- 512x768

You can modify or remove these as needed.

## Technical Details

- Presets are stored in `random_dimensions_presets.json` in the same folder as the script
- The extension uses the `AlwaysVisible` script type to appear in all tabs
- Dimensions are applied during the `process()` phase before generation begins
- The extension is compatible with all samplers and other extensions

## Upload to Wanly

The `upload_to_wanly.py` script adds an **"a1111 tweaks - Upload to Wanly"** accordion for pushing generated images to a wanly API endpoint.

### Setup

1. Enter your **API Key**
2. Click **Save Settings** — settings are written to `upload_to_wanly_config.json`

The endpoint is hardcoded to `http://api.wanly22.com:8001` (`API_URL` in `scripts/wanly_upload.py`), so the key is the only thing to fill in.

### Manual upload

Click **Upload Last Image** to send the most recent generation. Grid images are ignored, so this always picks the last real image rather than the contact sheet.

### Auto-upload

Tick **"Auto-upload every completed image"** and every image that finishes generating is uploaded automatically. This is what pairs with A1111's **generate forever** (right-click the Generate button): leave it running and each render is uploaded as it lands.

Notes:

- Auto-upload uses the **saved** API key, so click Save Settings before enabling it.
- Uploads happen on a background thread and never block or slow down generation.
- Grid images are skipped; each image in a batch is uploaded individually.
- If five uploads fail in a row (e.g. the API is down), auto-upload pauses itself instead of retrying for the rest of a long run. Fix the settings and click Save Settings, or untick and re-tick the checkbox, to resume.
- **Auto-upload Status** shows counts and the last result; click **Refresh Auto-upload Status** to update it.
- The checkbox state is saved with your settings, so it can be on by default at startup.

### Reading the logs

Every step logs with the `[Wanly Upload]` prefix, so one filter follows the whole path:

```
journalctl -u sd.service -f | grep --line-buffered "Wanly Upload"
```

A healthy run looks like this:

```
[Wanly Upload] Loaded, uploads target http://api.wanly22.com:8001
[Wanly Upload] Auto-upload ARMED
[Wanly Upload] Upload worker started, target http://api.wanly22.com:8001
[Wanly Upload] Queued 00042-1234.png (1 pending)
[Wanly Upload] 00042-1234.png: Uploaded: /path/on/server.png (total 1)
```

`Loaded` appears at startup and confirms the extension imported. `ARMED` is logged only when the checkbox changes state, so generate forever doesn't repeat it every iteration — expect just the `Queued` and `Uploaded` pair per image after that.

When an image is deliberately not uploaded, the reason is always logged:

| Line | Meaning |
|---|---|
| `Skipped grid grid-0001.png` | Batch grid, not a real render — expected with batch count > 1 |
| `Not queued, p not armed on …` | The save came from something other than an armed generation (e.g. Extras tab) |
| `Not queued, no p on …` | Save had no processing object attached (Extras tab, PNG Info) |
| `Not queued, auto-upload is paused: …` | The circuit breaker tripped — see below |
| `Not queued, already uploaded: …` | Duplicate; that path was uploaded already |
| `Error: API Key not set.` | Key wasn't saved — enter it and click Save Settings |

If nothing appears at all after ticking the box, the extension didn't load — check for a traceback above the missing `Loaded` line. Note that A1111's progress bars can cause journald to render nearby lines as `[NNN B blob data]`; pass `-a` to `journalctl` to reveal them.

## Generate Forever Delay

A1111's **generate forever** (right-click the Generate button) fires the next render the instant the previous one finishes. This extension adds a cooldown between iterations.

Set it under **Settings → a1111 tweaks → "Generate forever: seconds to wait between runs"**. The default is **2 seconds**; `0` restores stock back-to-back behaviour.

The delay is re-read on every poll, so changing it takes effect on the *next* gap — no need to stop and restart generate forever, and no UI reload. "Cancel generate forever" works exactly as before.

Nothing blocks the generation thread: the wait happens in the browser (`javascript/generate_forever_delay.js` replaces A1111's `generateOnRepeat`), so queued API jobs and manual Generate clicks are unaffected. The console logs `[Generate Forever Delay]` at startup and each time generate forever is started.

## Gallery

The `gallery.py` script adds an **"a1111 tweaks - Gallery"** accordion that pages through recent images on disk and uploads any selected one to wanly.

## Contributing

Feel free to submit issues, feature requests, or pull requests!

## License

See LICENSE file for details.

## Credits

Created for the Automatic1111 Stable Diffusion WebUI community.

---

**Note**: This extension modifies the width and height parameters for each generation. Make sure this doesn't conflict with other extensions that also modify these parameters.