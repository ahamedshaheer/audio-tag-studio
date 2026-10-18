# Audio Tag Studio & Keyword Cleaner

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-brightgreen.svg)](https://www.python.org/)
[![Platform: Windows | macOS | Linux](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

A lightweight, high-performance audio metadata editor and album art fetcher designed with two hyper-focused core workflows:
1. **Adjust song properties & strip promotional keywords/watermarks across all fields in 1 click.**
2. **Lookup and embed ultra-high-resolution cover art online from official music databases.**

Built to guarantee **100% universal player compatibility** (Windows Media Player, Groove, Apple Music, MediaMonkey, Foobar2000, and car infotainment units).

---

## Key Features

### 1. Song Property Editor & Global Keyword Stripper
* **Comprehensive Metadata Editing**: View and adjust Song Title, Artist, Album, Album Artist, Genre, Release Year, Track Number, and Comments.
* **Global Keyword Remover**: Enter any promotional phrase or watermark (e.g. `[SongsLover.com]`, `320kbps`, `www.site.com`, `(feat. ...)`). One click cleans it across **all metadata fields** simultaneously.
* **Automatic Bracket & Delimiter Cleanup**: Automatically removes orphaned brackets `[]`, `()`, `{}`, double spaces, and dangling hyphens left behind after keyword stripping.
* **Batch or Single-Track**: Clean the currently active track or apply keyword removal across an entire batch of songs at once.

### 2. 1-Click High-Res Online Cover Art Lookup
* **Instant Database Search**: Queries official streaming catalogs (**Apple Music / iTunes** and **Deezer**) with zero API key configuration needed.
* **Ultra High-Definition**: Automatically upgrades artwork thumbnails to crystal-clear 1200×1200 px resolution.
* **Embedded Directly**: Embeds front cover artwork directly into audio container tags (`APIC` frame for MP3, `Picture` block for FLAC, `covr` atom for M4A).

### 3. Maximum Player Compatibility (ID3v2.3 + ID3v1 Synced)
* Writes standard **ID3v2.3 with UTF-16 BOM** encoding alongside synchronized **ID3v1** tags.
* Sets both `TYER` (ID3v2.3) and `TDRC` (ID3v2.4) release year tags for universal reader support.
* Strips legacy conflicting APEv2 tags from MP3s.
* Automatically refreshes file modification timestamps (`os.utime`), forcing Windows Explorer, Groove, and MediaMonkey to immediately invalidate cached metadata and show updated tags.

### 4. Two Flexible Operating Modes
* **Mode A: Direct In-Place Disk Editing (Zero Downloads Needed)**:
  * Type or select your local music folder (e.g. `C:\Music` or `~/Music`) and click **Scan**.
  * All song property adjustments, keyword cleaning, and cover embeds are **written directly to your original audio files on disk**.
* **Mode B: Drag-and-Drop / Uploads**:
  * Drag and drop songs directly into the browser or use the file picker.
  * All processed files are maintained in the dedicated `uploads/` folder.
  * Use **"Open Cleaned Folder"** to reveal them instantly in your file manager, or use **"Export All"** to copy all cleaned songs to any destination folder in one click.

---

## Supported Audio Formats

| Format | Extension | Tagging Standard |
| :--- | :--- | :--- |
| **MP3** | `.mp3` | ID3v2.3 (UTF-16 BOM) + ID3v1 synced, APIC cover art |
| **FLAC** | `.flac` | Vorbis Comments, METADATA_BLOCK_PICTURE |
| **AAC / MP4** | `.m4a`, `.mp4` | MP4 iTunes-style metadata, `covr` atom |
| **OGG Vorbis**| `.ogg` | Ogg Vorbis Comments |
| **WAV** | `.wav` | ID3 chunk tags |

---

## Quick Start

### Prerequisites
* Python 3.8 or higher installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/audio-tag-studio.git
cd audio-tag-studio
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Application

* **Windows**: Double-click `run.bat` or run:
  ```cmd
  python server.py
  ```
* **macOS / Linux**: Run:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```
  *(or `python3 server.py`)*

The app will launch and automatically open **`http://127.0.0.1:5000`** in your default web browser.

---

## Project Structure

```
audio-tag-studio/
├── cover_lookup.py     # High-res artwork query & downloader (Apple Music & Deezer)
├── tag_manager.py      # Audio metadata reader/writer (mutagen, ID3v2.3, FLAC, M4A)
├── server.py           # Flask REST API & cross-platform system integration
├── templates/
│   └── index.html      # Responsive dark-theme interface (Tailwind CSS, FontAwesome)
├── uploads/            # Working directory for uploaded files (.gitkeep included)
├── run.bat             # Windows 1-click batch launcher
├── run.sh              # macOS/Linux bash launcher
├── requirements.txt    # Python package dependencies
├── LICENSE             # MIT Public License
└── README.md           # Documentation
```

---

## License

This project is open-source and released under the [MIT License](LICENSE). You are free to use, modify, and distribute it for personal and commercial purposes.
