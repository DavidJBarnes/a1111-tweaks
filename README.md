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

## Contributing

Feel free to submit issues, feature requests, or pull requests!

## License

See LICENSE file for details.

## Credits

Created for the Automatic1111 Stable Diffusion WebUI community.

---

**Note**: This extension modifies the width and height parameters for each generation. Make sure this doesn't conflict with other extensions that also modify these parameters.