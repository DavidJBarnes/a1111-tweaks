# A1111 Random Dimensions Extension - Development Context

## Project Overview

This is an extension for Automatic1111 Stable Diffusion WebUI that randomizes image dimensions by selecting from user-defined width/height pairs.

## Project Structure

```
a1111-tweaks/
├── scripts/
│   ├── random_dimensions.py          # Main extension script
│   └── random_dimensions_presets.json # Auto-generated presets storage
├── README.md                          # User documentation
├── LICENSE                            # Project license
└── claude.md                          # This file - development context
```

## Core Functionality

### What It Does
- Allows users to define and save specific width/height dimension pairs
- Randomly selects one pair before each image generation
- Persists saved pairs across sessions using JSON storage
- Optionally uses the generation seed for reproducible randomization

### Key Components

1. **Preset Management**
   - Saved to `random_dimensions_presets.json` in the scripts directory
   - Loaded on extension initialization
   - Format: `[{"width": 512, "height": 768}, ...]`

2. **UI Elements**
   - Enable/disable checkbox
   - Seed-based randomization option
   - Display of current dimension pairs
   - Add new pair controls (width/height inputs + button)
   - Remove pair controls (index input + button)
   - Clear all button

3. **Generation Hook**
   - Intercepts the `process()` phase before image generation
   - Modifies `p.width` and `p.height` parameters
   - Adds selected dimensions to generation metadata

## A1111 Extension Architecture

### Script Types
- Uses `scripts.AlwaysVisible` to appear in all tabs (txt2img and img2img)

### Key Methods

1. **`title()`** - Returns extension name shown in UI
2. **`show(is_img2img)`** - Controls where extension appears
3. **`ui(is_img2img)`** - Builds Gradio UI components
4. **`process(p, ...)`** - Runs before generation, modifies parameters
5. **`postprocess(p, processed, ...)`** - Runs after generation, adds metadata

### Important Objects

- **`p`** - Processing object containing generation parameters
  - `p.width` - Image width
  - `p.height` - Image height
  - `p.seed` - Generation seed
- **`processed`** - Result object after generation
  - `processed.info` - Generation metadata string

## Technical Implementation Details

### File I/O
- Uses `scripts.basedir()` to get the extension's base directory
- JSON file stored in same directory as the script
- Graceful fallback to default presets if file doesn't exist

### Random Selection
- Uses Python's `random.choice()` for selection
- Optional `random.seed()` call for reproducible results based on generation seed

### UI Updates
- Gradio buttons use `.click()` events to trigger updates
- Functions return updated text for the preset display textbox
- All changes immediately saved to JSON file

## Default Presets

If no presets file exists, starts with:
- 512x512 (square)
- 768x512 (landscape)
- 512x768 (portrait)

## Dependencies

- `random` - Standard Python library
- `gradio` - UI framework (included with A1111)
- `json` - Standard Python library
- `os` - Standard Python library
- `modules.scripts` - A1111 extension framework
- `modules.processing` - A1111 processing utilities

## Usage Flow

1. User adds dimension pairs via UI
2. Pairs saved to JSON file
3. User enables extension
4. On generation:
   - Extension loads saved pairs
   - Randomly selects one pair (optionally using seed)
   - Overrides p.width and p.height
   - Generation proceeds with new dimensions
5. Dimensions added to image metadata

## Extension Points for Future Development

### Potential Features
- Import/export preset collections
- Named preset groups (e.g., "portrait pack", "landscape pack")
- Aspect ratio presets (e.g., "16:9", "4:3")
- Weighted random selection (some pairs more likely than others)
- Batch generation with sequential pair usage
- Integration with dynamic prompts
- UI preset for common resolutions (HD, 4K, etc.)

### Code Locations for Features
- **New UI elements**: Add to `ui()` method
- **Generation logic**: Modify `process()` method
- **Preset management**: Extend load/save methods
- **New storage format**: Update `load_presets()` and `save_presets()`

## Common Modifications

### Adding a New UI Control
```python
# In ui() method:
new_control = gr.Checkbox(label="New Feature", value=False)
# Add to return statement
return [enabled, seed_based, new_control]
# Add parameter to process() and postprocess()
```

### Changing Selection Logic
```python
# In process() method, replace:
selected_pair = random.choice(self.dimension_pairs)
# With custom logic
```

### Adding Preset Validation
```python
# In add_pair() function:
if width < 64 or height < 64:
    return "Error: Minimum dimension is 64px"
if width % 8 != 0 or height % 8 != 0:
    return "Error: Dimensions must be multiples of 8"
```

## Testing Checklist

- [ ] Extension loads without errors
- [ ] UI appears in txt2img tab
- [ ] UI appears in img2img tab
- [ ] Can add dimension pairs
- [ ] Can remove dimension pairs
- [ ] Can clear all pairs
- [ ] Presets persist after WebUI restart
- [ ] Random selection works
- [ ] Seed-based randomization is reproducible
- [ ] Dimensions appear in generation info
- [ ] Works with various samplers
- [ ] No conflicts with other extensions

## Known Limitations

- No validation for extremely large dimensions (GPU memory limits)
- Single preset file (no multiple collections)
- No preview of how dimensions look
- Pair list doesn't auto-refresh on external file changes
- No undo functionality for pair removal

## Debug Information

The extension prints to console:
```
[Random Dimensions] Set dimensions to: {width}x{height}
```

Check A1111 console for:
- Extension loading errors
- File I/O errors
- Selected dimensions for each generation

## File Locations

**Extension file**: `stable-diffusion-webui/extensions/a1111-tweaks/scripts/random_dimensions.py`

**Presets file**: `stable-diffusion-webui/extensions/a1111-tweaks/scripts/random_dimensions_presets.json`

## Quick Reference Commands

### Install Extension
```bash
cd stable-diffusion-webui/extensions/
git clone [repository-url] a1111-tweaks
# Restart WebUI
```

### Manual Installation
```bash
mkdir -p stable-diffusion-webui/extensions/a1111-tweaks/scripts
# Copy random_dimensions.py to scripts folder
# Restart WebUI
```

### Check Presets File
```bash
cat stable-diffusion-webui/extensions/a1111-tweaks/scripts/random_dimensions_presets.json
```

## Development Notes

- Always test with WebUI restart, not just UI reload
- Gradio state management can be tricky - use closure functions for UI updates
- A1111 extension API is minimally documented - check other extensions for examples
- Keep preset file format simple for manual editing if needed
- Consider backwards compatibility when changing preset file format