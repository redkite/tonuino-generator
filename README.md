# Tonuino Organizer

A Python CLI application to organize MP3 files from input folders (albums/podcasts) into a standardized output directory structure with fixed naming patterns.
The target naming pattern matches the requirements for a set of mp3s compatible with the TonUINO project.
More info on TonUINO can be found at https://github.com/tonuino/TonUINO-TNG

## Features

- Organizes MP3 files into folders with two-digit prefixes (01_, 02_, etc., followed by underscore)
- Renames files to three-digit numbers (001.mp3, 002.mp3, ..., 255.mp3)
- Supports two input types:
  - **Static albums**: Fixed set of MP3 files
  - **RSS podcasts**: Download and update from RSS feeds
- Maintains alphanumeric order from input
- Human-readable progress indicators using Rich
- Headless CLI operation

## Installation

### Option 1: Virtual Environment with Editable Install (Recommended)

1. Create a virtual environment:
```bash
python3 -m venv venv
```

2. Activate the virtual environment:
```bash
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

3. Install the package in editable mode:
```bash
pip install -e .
```

This installs the package and all dependencies. You can then use the `tonuino-organize` command.

### Option 2: Virtual Environment - Run Directly (No Installation)

1. Create and activate a virtual environment (see Option 1, steps 1-2)

2. Install only dependencies:
```bash
pip install -r requirements.txt
```

3. Run directly using Python module:
```bash
python -m tonuino_organizer.cli
```

Or create an alias in your shell:
```bash
alias tonuino-organize="python -m tonuino_organizer.cli"
```

### Option 3: System-wide Installation (Not Recommended)

Install directly to your system Python (not recommended):
```bash
pip install .
```

## Usage

### Basic Usage

Process all albums/podcasts in the default input directory:
```bash
tonuino-organize
```

### Custom Input/Output Paths

Specify custom input and output directories:
```bash
tonuino-organize --input ~/my/music/input --output ~/my/music/output
```

### Update RSS Feeds

Update podcasts and download new episodes from RSS feeds:
```bash
tonuino-organize --update
```

## Folder Structure

### Input Structure

The input directory should contain folders that start with exactly two digits followed by an underscore:
```
~/data/tonuino/input/
├── 01_MyAlbum/
│   ├── description.yaml
│   ├── song1.mp3
│   ├── song2.mp3
│   └── ...
├── 15_Podcast/
│   ├── description.yaml
│   ├── episode_001.mp3
│   └── ...
└── ...
```

### Description Files

Each album/podcast folder must contain a `description.yaml` file.

#### Static Album Example
```yaml
type: static
```

#### RSS Podcast Example
```yaml
type: rss
feed_url: https://example.com/podcast/feed.xml
# Optional: minimum duration in seconds (default: 60.0)
# Files shorter than this will be discarded and not re-downloaded
min_duration: 60
```

### Output Structure

Files are organized by their two-digit prefix:
```
~/data/tonuino/output/
├── 01/
│   ├── 001.mp3
│   ├── 002.mp3
│   └── ...
├── 15/
│   ├── 001.mp3
│   ├── 002.mp3
│   └── ...
└── ...
```

## How It Works

1. Scans the input directory for folders starting with exactly two digits followed by underscore (e.g., `01_`, `15_`)
2. Reads `description.yaml` from each folder
3. For static albums: finds all MP3 files (recursively)
4. For RSS podcasts:
   - If `--update` flag is used: fetches RSS feed and downloads new episodes
   - Processes all MP3 files in the folder (both new and existing)
5. Sorts MP3 files alphanumerically
6. Copies files to output directory:
   - Creates folder named with the two-digit prefix
   - Renames files to 001.mp3, 002.mp3, etc.
   - Maintains the sorted order

## File Naming Rules

- Input folders must start with exactly two digits followed by an underscore (e.g., `01_Album`, `15_Podcast`)
  - Valid: `01_MyAlbum`, `15_Podcast`, `99_Test`
  - Invalid: `1_Album` (single digit), `001_Album` (three digits), `01Album` (missing underscore)
- MP3 files are sorted alphanumerically (natural sort)
- Output files are renamed to three-digit numbers: `001.mp3`, `002.mp3`, ..., `255.mp3`
- Maximum of 255 files per album/podcast

## RSS Podcast Behavior

- When `--update` is used, the tool:
  - Fetches the RSS feed
  - Identifies new episodes (not previously downloaded)
  - Downloads new episodes to the input folder
  - Checks duration: files shorter than `min_duration` (default: 60 seconds) are discarded
  - Tracks downloaded URLs in `.downloaded_files` file
  - Tracks rejected (too short) URLs in `.rejected_files` file
- Old episodes remain in the input folder even if removed from the RSS feed
- Episodes are processed in RSS feed order (usually newest first)
- Rejected URLs are never re-downloaded in future runs
- You can configure a custom `min_duration` in `description.yaml` (optional, default: 60 seconds)

## Examples

### Example 1: Static Album

Input folder: `01_ClassicalMusic`
```yaml
# description.yaml
type: static
```

Files:
- `Beethoven_Symphony5.mp3`
- `Mozart_Requiem.mp3`
- `Bach_WellTemperedClavier.mp3`

Output folder: `01/`
- `001.mp3` (Beethoven_Symphony5.mp3, sorted)
- `002.mp3` (Bach_WellTemperedClavier.mp3)
- `003.mp3` (Mozart_Requiem.mp3)

### Example 2: RSS Podcast

Input folder: `15_MyPodcast`
```yaml
# description.yaml
type: rss
feed_url: https://example.com/feed.xml
# Optional: minimum duration in seconds (default: 60)
min_duration: 120  # Only keep files longer than 2 minutes
```

Command:
```bash
tonuino-organize --update
```

This will:
1. Fetch the RSS feed
2. Download any new episodes
3. Process all MP3 files (new + existing) into `15/001.mp3`, `15/002.mp3`, etc.

## Requirements

- Python 3.7+
- click
- feedparser
- requests
- pyyaml
- rich
- mutagen (for MP3 duration checking)

## Development

1. Set up a virtual environment (see Installation section above)

2. Install in development mode:
```bash
pip install -e .
```

3. Install test dependencies:
```bash
pip install -r requirements.txt
```

4. Run tests:
```bash
# Run all tests
pytest tests/

# Run tests with verbose output
pytest tests/ -v

# Run a specific test file
pytest tests/test_utils.py

# Run tests with coverage (if pytest-cov is installed)
pytest tests/ --cov=tonuino_organizer
```

5. Run the application directly without installation:
```bash
# In virtual environment, after installing dependencies:
python -m tonuino_organizer.cli --help
```

### Test Coverage

The project includes comprehensive unit tests for:
- `utils.py` - Path expansion, file sorting, validation, prefix extraction
- `config.py` - Configuration management
- `description.py` - YAML parsing and validation
- `file_organizer.py` - File organization logic
- `album_handler.py` - Static album processing
- `podcast_handler.py` - RSS feed processing (with mocks)

