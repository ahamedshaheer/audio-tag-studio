import os
import re
import time
import base64
import mutagen
from mutagen.id3 import (
    ID3, TIT2, TPE1, TALB, TPE2, TCON, TYER, TDRC, TRCK, COMM, APIC, ID3NoHeaderError
)
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis


def clean_text(text: str, keyword: str, case_sensitive: bool = False, clean_brackets: bool = True) -> str:
    if not text or not keyword:
        return text

    flags = 0 if case_sensitive else re.IGNORECASE
    escaped_kw = re.escape(keyword)

    # 1. Remove keyword
    cleaned = re.sub(escaped_kw, "", text, flags=flags)

    if clean_brackets:
        # 2. Clean empty or orphaned brackets/parentheses
        cleaned = re.sub(r"\(\s*\)", "", cleaned)
        cleaned = re.sub(r"\[\s*\]", "", cleaned)
        cleaned = re.sub(r"\{\s*\}", "", cleaned)

        # 3. Clean leading and trailing hyphens, pipes, underscores
        cleaned = re.sub(r"\s*[-_\|]+\s*$", "", cleaned)
        cleaned = re.sub(r"^\s*[-_\|]+\s*", "", cleaned)

    # 4. Collapse multiple spaces into one and strip edges
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def read_tags(filepath: str) -> dict:
    info = {
        "filepath": filepath,
        "filename": os.path.basename(filepath),
        "title": "",
        "artist": "",
        "album": "",
        "album_artist": "",
        "genre": "",
        "year": "",
        "track_number": "",
        "comment": "",
        "duration": 0,
        "format": os.path.splitext(filepath)[1].lower().lstrip("."),
        "has_cover": False,
        "cover_data_uri": None,
        "error": None
    }

    if not os.path.isfile(filepath):
        info["error"] = "File not found"
        return info

    try:
        audio = mutagen.File(filepath)
        if audio is None:
            info["error"] = "Unsupported audio format"
            return info

        if hasattr(audio, "info") and hasattr(audio.info, "length"):
            info["duration"] = round(audio.info.length)

        ext = os.path.splitext(filepath)[1].lower()

        # MP3 ID3
        if ext == ".mp3" or isinstance(audio, mutagen.mp3.MP3):
            try:
                id3 = ID3(filepath)
            except ID3NoHeaderError:
                id3 = ID3()

            if "TIT2" in id3:
                info["title"] = str(id3["TIT2"])
            if "TPE1" in id3:
                info["artist"] = str(id3["TPE1"])
            if "TALB" in id3:
                info["album"] = str(id3["TALB"])
            if "TPE2" in id3:
                info["album_artist"] = str(id3["TPE2"])
            if "TCON" in id3:
                info["genre"] = str(id3["TCON"])
            if "TYER" in id3:
                info["year"] = str(id3["TYER"])
            elif "TDRC" in id3:
                info["year"] = str(id3["TDRC"])
            if "TRCK" in id3:
                info["track_number"] = str(id3["TRCK"])

            for key in id3.keys():
                if key.startswith("COMM"):
                    info["comment"] = str(id3[key].text[0]) if id3[key].text else ""
                    break

            for key in id3.keys():
                if key.startswith("APIC"):
                    apic = id3[key]
                    mime = apic.mime or "image/jpeg"
                    b64 = base64.b64encode(apic.data).decode("ascii")
                    info["cover_data_uri"] = f"data:{mime};base64,{b64}"
                    info["has_cover"] = True
                    break

        # FLAC
        elif ext == ".flac" or isinstance(audio, FLAC):
            flac = audio
            info["title"] = flac.get("title", [""])[0]
            info["artist"] = flac.get("artist", [""])[0]
            info["album"] = flac.get("album", [""])[0]
            info["album_artist"] = flac.get("albumartist", [""])[0]
            info["genre"] = flac.get("genre", [""])[0]
            info["year"] = flac.get("date", [""])[0]
            info["track_number"] = flac.get("tracknumber", [""])[0]
            info["comment"] = flac.get("comment", [""])[0]

            if flac.pictures:
                pic = flac.pictures[0]
                mime = pic.mime or "image/jpeg"
                b64 = base64.b64encode(pic.data).decode("ascii")
                info["cover_data_uri"] = f"data:{mime};base64,{b64}"
                info["has_cover"] = True

        # MP4 / M4A
        elif ext in [".m4a", ".mp4"] or isinstance(audio, MP4):
            mp4 = audio
            tags = mp4.tags or {}
            info["title"] = tags.get("\xa9nam", [""])[0]
            info["artist"] = tags.get("\xa9ART", [""])[0]
            info["album"] = tags.get("\xa9alb", [""])[0]
            info["album_artist"] = tags.get("aART", [""])[0]
            info["genre"] = tags.get("\xa9gen", [""])[0]
            info["year"] = tags.get("\xa9day", [""])[0]
            if "trkn" in tags:
                info["track_number"] = str(tags["trkn"][0][0])
            info["comment"] = tags.get("\xa9cmt", [""])[0]

            covers = tags.get("covr", [])
            if covers:
                cover = covers[0]
                mime = "image/png" if cover.imageformat == MP4Cover.FORMAT_PNG else "image/jpeg"
                b64 = base64.b64encode(bytes(cover)).decode("ascii")
                info["cover_data_uri"] = f"data:{mime};base64,{b64}"
                info["has_cover"] = True

        # OGG Vorbis
        elif ext == ".ogg" or isinstance(audio, OggVorbis):
            ogg = audio
            info["title"] = ogg.get("title", [""])[0]
            info["artist"] = ogg.get("artist", [""])[0]
            info["album"] = ogg.get("album", [""])[0]
            info["album_artist"] = ogg.get("albumartist", [""])[0]
            info["genre"] = ogg.get("genre", [""])[0]
            info["year"] = ogg.get("date", [""])[0]
            info["track_number"] = ogg.get("tracknumber", [""])[0]
            info["comment"] = ogg.get("comment", [""])[0]

        if not info["title"]:
            info["title"] = os.path.splitext(os.path.basename(filepath))[0]

    except Exception as e:
        info["error"] = str(e)

    return info


def write_tags(filepath: str, tags: dict) -> bool:
    """
    Saves tags with maximum compatibility for Windows Explorer, Windows Media Player,
    MediaMonkey, Groove, VLC, iTunes, Foobar2000, and car stereos.
    Uses UTF-16 with BOM (encoding=1) in ID3v2.3 and simultaneously synchronizes ID3v1.
    """
    try:
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".mp3":
            # Remove any conflicting APEv2 tag which overrides ID3 in some players
            try:
                from mutagen.apev2 import APEv2
                APEv2(filepath).delete()
            except Exception:
                pass

            try:
                id3 = ID3(filepath)
            except ID3NoHeaderError:
                id3 = ID3()

            # ID3v2.3 UTF-16 with BOM (encoding=1) is the standard required by Windows Explorer and WMP
            enc = 1

            if "title" in tags:
                id3["TIT2"] = TIT2(encoding=enc, text=[str(tags["title"])])
            if "artist" in tags:
                id3["TPE1"] = TPE1(encoding=enc, text=[str(tags["artist"])])
            if "album" in tags:
                id3["TALB"] = TALB(encoding=enc, text=[str(tags["album"])])
            if "album_artist" in tags:
                id3["TPE2"] = TPE2(encoding=enc, text=[str(tags["album_artist"])])
            if "genre" in tags:
                id3["TCON"] = TCON(encoding=enc, text=[str(tags["genre"])])

            if "year" in tags and str(tags["year"]).strip():
                yr_str = str(tags["year"]).strip()[:4]
                # ID3v2.3 uses TYER; ID3v2.4 uses TDRC. Write both for total player compatibility!
                id3["TYER"] = TYER(encoding=enc, text=[yr_str])
                id3["TDRC"] = TDRC(encoding=enc, text=[str(tags["year"])])

            if "track_number" in tags and str(tags["track_number"]).strip():
                id3["TRCK"] = TRCK(encoding=enc, text=[str(tags["track_number"]).strip()])

            if "comment" in tags:
                id3["COMM::eng"] = COMM(encoding=enc, lang="eng", desc="", text=[str(tags["comment"])])

            # Force save ID3v2.3 AND ID3v1 (v1=2 guarantees ID3v1 is synchronized for legacy players)
            id3.save(filepath, v1=2, v2_version=3)

            # Touch file timestamp so Windows Explorer and players immediately refresh their cache
            try:
                os.utime(filepath, None)
            except Exception:
                pass

            return True

        elif ext == ".flac":
            flac = FLAC(filepath)
            if "title" in tags:
                flac["title"] = [str(tags["title"])]
            if "artist" in tags:
                flac["artist"] = [str(tags["artist"])]
            if "album" in tags:
                flac["album"] = [str(tags["album"])]
            if "album_artist" in tags:
                flac["albumartist"] = [str(tags["album_artist"])]
            if "genre" in tags:
                flac["genre"] = [str(tags["genre"])]
            if "year" in tags and str(tags["year"]).strip():
                flac["date"] = [str(tags["year"]).strip()]
            if "track_number" in tags and str(tags["track_number"]).strip():
                flac["tracknumber"] = [str(tags["track_number"]).strip()]
            if "comment" in tags:
                flac["comment"] = [str(tags["comment"])]
            flac.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass
            return True

        elif ext in [".m4a", ".mp4"]:
            mp4 = MP4(filepath)
            if mp4.tags is None:
                mp4.add_tags()
            tags_map = mp4.tags
            if "title" in tags:
                tags_map["\xa9nam"] = [str(tags["title"])]
            if "artist" in tags:
                tags_map["\xa9ART"] = [str(tags["artist"])]
            if "album" in tags:
                tags_map["\xa9alb"] = [str(tags["album"])]
            if "album_artist" in tags:
                tags_map["aART"] = [str(tags["album_artist"])]
            if "genre" in tags:
                tags_map["\xa9gen"] = [str(tags["genre"])]
            if "year" in tags and str(tags["year"]).strip():
                tags_map["\xa9day"] = [str(tags["year"]).strip()]
            if "track_number" in tags and str(tags["track_number"]).strip():
                try:
                    num = int(tags["track_number"])
                    tags_map["trkn"] = [(num, 0)]
                except ValueError:
                    pass
            if "comment" in tags:
                tags_map["\xa9cmt"] = [str(tags["comment"])]
            mp4.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass
            return True

        elif ext == ".ogg":
            ogg = OggVorbis(filepath)
            if "title" in tags:
                ogg["title"] = [str(tags["title"])]
            if "artist" in tags:
                ogg["artist"] = [str(tags["artist"])]
            if "album" in tags:
                ogg["album"] = [str(tags["album"])]
            if "album_artist" in tags:
                ogg["albumartist"] = [str(tags["album_artist"])]
            if "genre" in tags:
                ogg["genre"] = [str(tags["genre"])]
            if "year" in tags and str(tags["year"]).strip():
                ogg["date"] = [str(tags["year"]).strip()]
            if "track_number" in tags and str(tags["track_number"]).strip():
                ogg["tracknumber"] = [str(tags["track_number"]).strip()]
            if "comment" in tags:
                ogg["comment"] = [str(tags["comment"])]
            ogg.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass
            return True

    except Exception as e:
        print(f"Error writing tags to {filepath}: {e}")
        return False

    return False


def embed_cover_art(filepath: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> bool:
    try:
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".mp3":
            try:
                id3 = ID3(filepath)
            except ID3NoHeaderError:
                id3 = ID3()

            # Remove existing APIC
            for key in list(id3.keys()):
                if key.startswith("APIC"):
                    del id3[key]

            # Standard front cover (type 3)
            id3.add(APIC(
                encoding=0,  # 0 or 3
                mime=mime_type,
                type=3,  # 3 is Front Cover
                desc="Cover",
                data=image_bytes
            ))
            id3.save(filepath, v1=2, v2_version=3)
            try:
                os.utime(filepath, None)
            except Exception:
                pass
            return True

        elif ext == ".flac":
            flac = FLAC(filepath)
            flac.clear_pictures()
            pic = Picture()
            pic.type = 3
            pic.mime = mime_type
            pic.desc = "Cover"
            pic.data = image_bytes
            flac.add_picture(pic)
            flac.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass
            return True

        elif ext in [".m4a", ".mp4"]:
            mp4 = MP4(filepath)
            if mp4.tags is None:
                mp4.add_tags()
            fmt = MP4Cover.FORMAT_PNG if "png" in mime_type.lower() else MP4Cover.FORMAT_JPEG
            mp4.tags["covr"] = [MP4Cover(image_bytes, imageformat=fmt)]
            mp4.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass
            return True

    except Exception as e:
        print(f"Error embedding cover into {filepath}: {e}")
        return False

    return False


def remove_keyword_from_file(filepath: str, keyword: str, case_sensitive: bool = False, clean_brackets: bool = True) -> dict:
    current = read_tags(filepath)
    if current.get("error"):
        return current

    updated = {
        "title": clean_text(current.get("title", ""), keyword, case_sensitive, clean_brackets),
        "artist": clean_text(current.get("artist", ""), keyword, case_sensitive, clean_brackets),
        "album": clean_text(current.get("album", ""), keyword, case_sensitive, clean_brackets),
        "album_artist": clean_text(current.get("album_artist", ""), keyword, case_sensitive, clean_brackets),
        "genre": clean_text(current.get("genre", ""), keyword, case_sensitive, clean_brackets),
        "year": current.get("year", ""),
        "track_number": current.get("track_number", ""),
        "comment": clean_text(current.get("comment", ""), keyword, case_sensitive, clean_brackets),
    }

    write_tags(filepath, updated)
    return read_tags(filepath)
