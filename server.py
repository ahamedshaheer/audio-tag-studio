import os
import sys
import shutil
import subprocess
import webbrowser
import threading
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

import tag_manager
import cover_lookup

app = Flask(__name__, template_folder="templates")
ap = app  # Fallback alias for 'gunicorn server:ap'
application = app  # Standard WSGI fallback alias
app.config["MAX_CONTENT_LENGTH"] = 800 * 1024 * 1024  # 800 MB max

UPLOAD_FOLDER = os.path.normpath(os.path.join(os.path.dirname(__file__), "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SUPPORTED_EXTS = {".mp3", ".flac", ".m4a", ".mp4", ".ogg", ".wav"}


@app.route("/")
def index():
    user_home = os.path.expanduser("~").replace("\\", "/")
    common_folders = {
        "music": f"{user_home}/Music",
        "downloads": f"{user_home}/Downloads",
        "desktop": f"{user_home}/Desktop"
    }
    return render_template("index.html", common_folders=common_folders)


@app.route("/api/scan", methods=["POST"])
def scan_directory():
    data = request.get_json() or {}
    folder_raw = data.get("folder", "").strip().strip('"').strip("'")

    if not folder_raw:
        # Default to User Music folder if empty
        folder_raw = os.path.join(os.path.expanduser("~"), "Music")

    folder_norm = os.path.normpath(folder_raw)

    if not os.path.isdir(folder_norm):
        return jsonify({"error": f"Folder not found: '{folder_norm}'"}), 400

    tracks = []
    for root, _, files in os.walk(folder_norm):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTS:
                full_path = os.path.normpath(os.path.join(root, f))
                info = tag_manager.read_tags(full_path)
                info["is_local"] = True
                info["is_uploaded"] = False
                tracks.append(info)

    return jsonify({"tracks": tracks, "count": len(tracks), "folder": folder_norm})


@app.route("/api/upload", methods=["POST"])
def upload_files():
    """Uploads audio files selected via browser file picker, folder picker, or drag-and-drop."""
    if "files" not in request.files:
        return jsonify({"error": "No files received"}), 400

    files = request.files.getlist("files")
    tracks = []

    for f in files:
        if f.filename:
            # Handle possible nested paths from webkitdirectory
            basename = os.path.basename(f.filename)
            safe_name = secure_filename(basename)
            if not safe_name:
                safe_name = f"song_{len(tracks) + 1}.mp3"

            ext = os.path.splitext(safe_name)[1].lower()
            if ext in SUPPORTED_EXTS:
                save_path = os.path.normpath(os.path.join(UPLOAD_FOLDER, safe_name))
                f.save(save_path)
                info = tag_manager.read_tags(save_path)
                info["is_uploaded"] = True
                info["is_local"] = False
                tracks.append(info)

    return jsonify({"tracks": tracks, "count": len(tracks)})


@app.route("/api/save-tags", methods=["POST"])
def save_tags():
    data = request.get_json() or {}
    filepath = data.get("filepath")
    tags = data.get("tags", {})

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": f"File not found on disk: {filepath}"}), 404

    success = tag_manager.write_tags(filepath, tags)
    if success:
        updated = tag_manager.read_tags(filepath)
        norm_fp = os.path.normcase(os.path.abspath(filepath))
        norm_up = os.path.normcase(os.path.abspath(UPLOAD_FOLDER))
        is_uploaded = norm_fp.startswith(norm_up)
        updated["is_uploaded"] = is_uploaded
        updated["is_local"] = not is_uploaded
        return jsonify({"success": True, "track": updated})
    else:
        return jsonify({"error": "Failed to write tags to file"}), 500


@app.route("/api/remove-keyword", methods=["POST"])
def remove_keyword():
    data = request.get_json() or {}
    filepaths = data.get("filepaths", [])
    keyword = data.get("keyword", "")
    case_sensitive = data.get("case_sensitive", False)
    clean_brackets = data.get("clean_brackets", True)

    if not keyword:
        return jsonify({"error": "No keyword provided"}), 400

    updated_tracks = []
    for fp in filepaths:
        if os.path.exists(fp):
            updated = tag_manager.remove_keyword_from_file(
                fp, keyword, case_sensitive=case_sensitive, clean_brackets=clean_brackets
            )
            norm_fp = os.path.normcase(os.path.abspath(fp))
            norm_up = os.path.normcase(os.path.abspath(UPLOAD_FOLDER))
            is_uploaded = norm_fp.startswith(norm_up)
            updated["is_uploaded"] = is_uploaded
            updated["is_local"] = not is_uploaded
            updated_tracks.append(updated)

    return jsonify({"success": True, "updated_tracks": updated_tracks, "count": len(updated_tracks)})


@app.route("/api/search-cover", methods=["POST"])
def search_cover():
    data = request.get_json() or {}
    query = data.get("query", "")
    artist = data.get("artist", "")
    album = data.get("album", "")
    title = data.get("title", "")

    results = cover_lookup.search_online_covers(query=query, artist=artist, album=album, title=title)
    return jsonify({"results": results})


@app.route("/api/apply-cover", methods=["POST"])
def apply_cover():
    data = request.get_json() or {}
    filepath = data.get("filepath")
    image_url = data.get("image_url")

    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Audio file not found"}), 404
    if not image_url:
        return jsonify({"error": "No image URL provided"}), 400

    try:
        img_bytes, mime = cover_lookup.download_cover_bytes(image_url)
        success = tag_manager.embed_cover_art(filepath, img_bytes, mime)
        if success:
            updated = tag_manager.read_tags(filepath)
            norm_fp = os.path.normcase(os.path.abspath(filepath))
            norm_up = os.path.normcase(os.path.abspath(UPLOAD_FOLDER))
            is_uploaded = norm_fp.startswith(norm_up)
            updated["is_uploaded"] = is_uploaded
            updated["is_local"] = not is_uploaded
            return jsonify({
                "success": True,
                "cover_data_uri": updated.get("cover_data_uri"),
                "has_cover": updated.get("has_cover"),
                "track": updated
            })
        else:
            return jsonify({"error": "Failed to embed cover"}), 500
    except Exception as e:
        return jsonify({"error": f"Error downloading/applying cover: {str(e)}"}), 500


def open_folder_in_file_manager(folder_path):
    norm = os.path.abspath(os.path.normpath(folder_path))
    if sys.platform.startswith("win"):
        if hasattr(os, "startfile"):
            os.startfile(norm)
        else:
            subprocess.Popen(["explorer.exe", norm])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", norm])
    else:  # Linux / Unix
        try:
            subprocess.Popen(["xdg-open", norm])
        except Exception:
            pass


def reveal_file_in_file_manager(filepath):
    norm = os.path.abspath(os.path.normpath(filepath))
    if sys.platform.startswith("win"):
        try:
            subprocess.Popen(["explorer.exe", f"/select,{norm}"])
        except Exception:
            open_folder_in_file_manager(os.path.dirname(norm))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", norm])
    else:  # Linux
        try:
            open_folder_in_file_manager(os.path.dirname(norm))
        except Exception:
            pass


@app.route("/api/open-in-explorer", methods=["POST"])
def open_in_explorer():
    data = request.get_json() or {}
    filepath = data.get("filepath", "").strip()
    if not filepath:
        return jsonify({"error": "No file path provided"}), 400

    norm = os.path.abspath(os.path.normpath(filepath))
    if not os.path.exists(norm):
        return jsonify({"error": f"File not found on disk: {norm}"}), 404

    try:
        if os.path.isfile(norm):
            reveal_file_in_file_manager(norm)
        else:
            open_folder_in_file_manager(norm)
        return jsonify({"success": True, "path": norm})
    except Exception as e:
        return jsonify({"error": f"Could not open file manager: {str(e)}"}), 500


@app.route("/api/open-uploads-folder", methods=["POST"])
def open_uploads_folder():
    """Opens the folder containing all cleaned songs in the system file manager."""
    try:
        norm = os.path.abspath(os.path.normpath(UPLOAD_FOLDER))
        os.makedirs(norm, exist_ok=True)
        open_folder_in_file_manager(norm)
        return jsonify({"success": True, "folder": norm})
    except Exception as e:
        return jsonify({"error": f"Failed to open folder: {str(e)}"}), 500


@app.route("/api/export-all", methods=["POST"])
def export_all():
    """Copies all cleaned songs to a destination folder chosen by the user."""
    data = request.get_json() or {}
    target_dir = data.get("target_folder", "").strip().strip('"').strip("'")
    filepaths = data.get("filepaths", [])

    if not target_dir:
        return jsonify({"error": "Please provide a target folder path"}), 400

    os.makedirs(target_dir, exist_ok=True)
    copied = 0
    for src in filepaths:
        if os.path.isfile(src):
            dest = os.path.join(target_dir, os.path.basename(src))
            shutil.copy2(src, dest)
            copied += 1

    return jsonify({"success": True, "copied": copied, "target_folder": target_dir})


@app.route("/api/download", methods=["GET"])
def download_file():
    filepath = request.args.get("path")
    if filepath and os.path.isfile(filepath):
        return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
    return "File not found", 404


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    print("\n=======================================================")
    print(f"[*] Audio Tag Studio running at: http://{host}:{port}")
    print("=======================================================\n")
    if host == "127.0.0.1":
        threading.Timer(1.2, open_browser).start()
    app.run(host=host, port=port, debug=False)
