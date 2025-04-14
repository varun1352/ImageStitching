# Panorama Section Generator

A robust tool for splitting panoramic images into overlapping sections with consistent coverage and overlap, designed for panorama reconstruction and stitching applications.



## Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-name>

# Create and activate virtual environment
python -m venv ptz_env
source ptz_env/bin/activate  # On Unix/macOS
# or
.\ptz_env\Scripts\activate  # On Windows

# Install dependencies
pip install opencv-python numpy
```

## Usage

```bash
python generate_test_data.py --input <path-to-panorama> --sections <num-sections> --overlap <overlap-percentage>
```

### Arguments

- `--input`, `-i`: Path to the input panoramic image (default: "original.jpg")
- `--sections`, `-s`: Number of sections to split into (default: 10)
- `--overlap`, `-o`: Overlap percentage between sections (default: 40)

### Example

```bash
python generate_test_data.py --input panorama.jpg --sections 10 --overlap 40
```

## Output Structure

```
images/
├── section_00.jpg
├── section_01.jpg
├── ...
├── section_09.jpg
└── metadata.json
```

### Metadata Format

The generated `metadata.json` contains detailed information about the splitting process:

```json
{
  "parameters": {
    "original_image": "panorama.jpg",
    "width": 5000,
    "height": 1000,
    "num_sections": 10,
    "overlap_percent": 40,
    "section_width": 800,
    "overlap_width": 320,
    "step_size": 480
  },
  "images": [
    {
      "filename": "section_00.jpg",
      "position": [0, 0],
      "dimensions": {
        "width": 800,
        "height": 1000
      },
      "overlap": {
        "left": false,
        "right": true,
        "left_pixels": 0,
        "right_pixels": 320
      }
    },
    ...
  ]
}
```

## Example Results

### Original Panorama
![Original Panorama](docs/images/original.jpg)

### Stitching using Metadata
![Split Sections](docs/images/panorama_metadata.jpg)

### Overlap Features (SIFT)
![Overlap Visualization](docs/images/panorama_sift.jpg)

## Technical Details

### Section Width Calculation

The tool uses a mathematical formula to calculate optimal section width:
```
W = w + (n-1)(w - p*w)
```
Where:
- W = total image width
- w = section width
- n = number of sections
- p = overlap percentage

This resolves to:
```
w = W / (1 + (n-1)(1-p))
```

### Overlap Handling

Each section (except edges) has:
- Left overlap with previous section
- Right overlap with next section
- Consistent overlap width based on percentage
- Automatic adjustment for edge cases
