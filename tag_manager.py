import os
import re
import time
import base64
import mutagen
from mutagen.id3 import (
    ID3, TIT1, TIT2, TIT3, TPE1, TALB, TPE2, TPE3, TCON, TYER, TDRC, TRCK,
    COMM, APIC, TPUB, TCOM, TCOP, TENC, ID3NoHeaderError
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
        "subtitle": "",
        "publisher": "",
        "composer": "",
        "conductor": "",
        "copyright": "",
        "encoded_by": "",
        "grouping": "",
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
            if "TIT3" in id3:
                info["subtitle"] = str(id3["TIT3"])
            if "TPUB" in id3:
                info["publisher"] = str(id3["TPUB"])
            if "TCOM" in id3:
                info["composer"] = str(id3["TCOM"])
            if "TPE3" in id3:
                info["conductor"] = str(id3["TPE3"])
            if "TCOP" in id3:
                info["copyright"] = str(id3["TCOP"])
            if "TENC" in id3:
                info["encoded_by"] = str(id3["TENC"])
            if "TIT1" in id3:
                info["grouping"] = str(id3["TIT1"])

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
            info["subtitle"] = flac.get("subtitle", [""])[0]
            info["publisher"] = flac.get("publisher", flac.get("organization", [""]))[0]
            info["composer"] = flac.get("composer", [""])[0]
            info["conductor"] = flac.get("conductor", [""])[0]
            info["copyright"] = flac.get("copyright", [""])[0]
            info["encoded_by"] = flac.get("encodedby", flac.get("encoder", [""]))[0]
            info["grouping"] = flac.get("grouping", [""])[0]

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
            info["subtitle"] = tags.get("\xa9des", [""])[0]
            info["publisher"] = tags.get("\xa9pub", [""])[0]
            info["composer"] = tags.get("\xa9wrt", [""])[0]
            info["conductor"] = tags.get("\xa9con", [""])[0]
            info["copyright"] = tags.get("cprt", [""])[0]
            info["encoded_by"] = tags.get("\xa9enc", tags.get("\xa9too", [""]))[0]
            info["grouping"] = tags.get("\xa9grp", [""])[0]

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
            info["subtitle"] = ogg.get("subtitle", [""])[0]
            info["publisher"] = ogg.get("publisher", ogg.get("organization", [""]))[0]
            info["composer"] = ogg.get("composer", [""])[0]
            info["conductor"] = ogg.get("conductor", [""])[0]
            info["copyright"] = ogg.get("copyright", [""])[0]
            info["encoded_by"] = ogg.get("encodedby", ogg.get("encoder", [""]))[0]
            info["grouping"] = ogg.get("grouping", [""])[0]

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
                val = str(tags["comment"]).strip()
                if val:
                    id3["COMM::eng"] = COMM(encoding=enc, lang="eng", desc="", text=[val])
                else:
                    for k in list(id3.keys()):
                        if k.startswith("COMM"):
                            del id3[k]

            if "subtitle" in tags:
                val = str(tags["subtitle"]).strip()
                if val: id3["TIT3"] = TIT3(encoding=enc, text=[val])
                else: id3.pop("TIT3", None)

            if "publisher" in tags:
                val = str(tags["publisher"]).strip()
                if val: id3["TPUB"] = TPUB(encoding=enc, text=[val])
                else: id3.pop("TPUB", None)

            if "composer" in tags:
                val = str(tags["composer"]).strip()
                if val: id3["TCOM"] = TCOM(encoding=enc, text=[val])
                else: id3.pop("TCOM", None)

            if "conductor" in tags:
                val = str(tags["conductor"]).strip()
                if val: id3["TPE3"] = TPE3(encoding=enc, text=[val])
                else: id3.pop("TPE3", None)

            if "copyright" in tags:
                val = str(tags["copyright"]).strip()
                if val: id3["TCOP"] = TCOP(encoding=enc, text=[val])
                else: id3.pop("TCOP", None)

            if "encoded_by" in tags:
                val = str(tags["encoded_by"]).strip()
                if val: id3["TENC"] = TENC(encoding=enc, text=[val])
                else: id3.pop("TENC", None)

            if "grouping" in tags:
                val = str(tags["grouping"]).strip()
                if val: id3["TIT1"] = TIT1(encoding=enc, text=[val])
                else: id3.pop("TIT1", None)

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
                val = str(tags["comment"]).strip()
                if val: flac["comment"] = [val]
                else: flac.pop("comment", None)

            if "subtitle" in tags:
                val = str(tags["subtitle"]).strip()
                if val: flac["subtitle"] = [val]
                else: flac.pop("subtitle", None)

            if "publisher" in tags:
                val = str(tags["publisher"]).strip()
                if val:
                    flac["publisher"] = [val]
                    flac["organization"] = [val]
                else:
                    flac.pop("publisher", None)
                    flac.pop("organization", None)

            if "composer" in tags:
                val = str(tags["composer"]).strip()
                if val: flac["composer"] = [val]
                else: flac.pop("composer", None)

            if "conductor" in tags:
                val = str(tags["conductor"]).strip()
                if val: flac["conductor"] = [val]
                else: flac.pop("conductor", None)

            if "copyright" in tags:
                val = str(tags["copyright"]).strip()
                if val: flac["copyright"] = [val]
                else: flac.pop("copyright", None)

            if "encoded_by" in tags:
                val = str(tags["encoded_by"]).strip()
                if val: flac["encodedby"] = [val]
                else: flac.pop("encodedby", None)

            if "grouping" in tags:
                val = str(tags["grouping"]).strip()
                if val: flac["grouping"] = [val]
                else: flac.pop("grouping", None)
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
                val = str(tags["comment"]).strip()
                if val: tags_map["\xa9cmt"] = [val]
                else: tags_map.pop("\xa9cmt", None)

            if "subtitle" in tags:
                val = str(tags["subtitle"]).strip()
                if val: tags_map["\xa9des"] = [val]
                else: tags_map.pop("\xa9des", None)

            if "publisher" in tags:
                val = str(tags["publisher"]).strip()
                if val: tags_map["\xa9pub"] = [val]
                else: tags_map.pop("\xa9pub", None)

            if "composer" in tags:
                val = str(tags["composer"]).strip()
                if val: tags_map["\xa9wrt"] = [val]
                else: tags_map.pop("\xa9wrt", None)

            if "conductor" in tags:
                val = str(tags["conductor"]).strip()
                if val: tags_map["\xa9con"] = [val]
                else: tags_map.pop("\xa9con", None)

            if "copyright" in tags:
                val = str(tags["copyright"]).strip()
                if val: tags_map["cprt"] = [val]
                else: tags_map.pop("cprt", None)

            if "encoded_by" in tags:
                val = str(tags["encoded_by"]).strip()
                if val: tags_map["\xa9enc"] = [val]
                else: tags_map.pop("\xa9enc", None)

            if "grouping" in tags:
                val = str(tags["grouping"]).strip()
                if val: tags_map["\xa9grp"] = [val]
                else: tags_map.pop("\xa9grp", None)
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
                val = str(tags["comment"]).strip()
                if val: ogg["comment"] = [val]
                else: ogg.pop("comment", None)

            if "subtitle" in tags:
                val = str(tags["subtitle"]).strip()
                if val: ogg["subtitle"] = [val]
                else: ogg.pop("subtitle", None)

            if "publisher" in tags:
                val = str(tags["publisher"]).strip()
                if val:
                    ogg["publisher"] = [val]
                    ogg["organization"] = [val]
                else:
                    ogg.pop("publisher", None)
                    ogg.pop("organization", None)

            if "composer" in tags:
                val = str(tags["composer"]).strip()
                if val: ogg["composer"] = [val]
                else: ogg.pop("composer", None)

            if "conductor" in tags:
                val = str(tags["conductor"]).strip()
                if val: ogg["conductor"] = [val]
                else: ogg.pop("conductor", None)

            if "copyright" in tags:
                val = str(tags["copyright"]).strip()
                if val: ogg["copyright"] = [val]
                else: ogg.pop("copyright", None)

            if "encoded_by" in tags:
                val = str(tags["encoded_by"]).strip()
                if val: ogg["encodedby"] = [val]
                else: ogg.pop("encodedby", None)

            if "grouping" in tags:
                val = str(tags["grouping"]).strip()
                if val: ogg["grouping"] = [val]
                else: ogg.pop("grouping", None)
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
    """
    Comprehensively scrubs a keyword from EVERY metadata field in the audio file:
    Title, Artist, Album, Subtitle (TIT3), Publisher (TPUB), Composers (TCOM),
    Conductors (TPE3), Copyright (TCOP), Encoded by (TENC), Grouping (TIT1),
    Comments (COMM), URLs (W*), User-defined tags (TXXX), and Lyrics (USLT).
    Any frame whose content becomes empty after keyword removal is completely deleted.
    """
    if not os.path.isfile(filepath) or not keyword:
        return read_tags(filepath)

    ext = os.path.splitext(filepath)[1].lower()
    flags = 0 if case_sensitive else re.IGNORECASE
    escaped_kw = re.escape(keyword.strip())

    try:
        if ext == ".mp3":
            try:
                id3 = ID3(filepath)
            except ID3NoHeaderError:
                return read_tags(filepath)

            keys_to_delete = []

            for key in list(id3.keys()):
                # Keep album cover artwork intact
                if key.startswith("APIC"):
                    continue

                frame = id3[key]

                # 1. Text frames (T* except TXXX)
                if key.startswith("T") and not key.startswith("TXXX"):
                    if hasattr(frame, "text") and isinstance(frame.text, list):
                        new_text = []
                        for s in frame.text:
                            cleaned = clean_text(str(s), keyword, case_sensitive, clean_brackets)
                            if cleaned:
                                new_text.append(cleaned)
                        if new_text:
                            frame.text = new_text
                        else:
                            keys_to_delete.append(key)

                # 2. User-defined text (TXXX)
                elif key.startswith("TXXX"):
                    desc_str = str(getattr(frame, "desc", ""))
                    if re.search(escaped_kw, desc_str, flags=flags):
                        keys_to_delete.append(key)
                    elif hasattr(frame, "text") and isinstance(frame.text, list):
                        new_text = []
                        for s in frame.text:
                            cleaned = clean_text(str(s), keyword, case_sensitive, clean_brackets)
                            if cleaned:
                                new_text.append(cleaned)
                        if new_text:
                            frame.text = new_text
                        else:
                            keys_to_delete.append(key)

                # 3. URL frames (W* and WXXX)
                elif key.startswith("W"):
                    url_val = str(getattr(frame, "url", getattr(frame, "text", "")))
                    desc_val = str(getattr(frame, "desc", ""))
                    if re.search(escaped_kw, url_val, flags=flags) or re.search(escaped_kw, desc_val, flags=flags):
                        keys_to_delete.append(key)

                # 4. Comments (COMM)
                elif key.startswith("COMM"):
                    if hasattr(frame, "text") and isinstance(frame.text, list):
                        new_text = []
                        for s in frame.text:
                            cleaned = clean_text(str(s), keyword, case_sensitive, clean_brackets)
                            if cleaned:
                                new_text.append(cleaned)
                        if new_text:
                            frame.text = new_text
                        else:
                            keys_to_delete.append(key)

                # 5. Lyrics (USLT)
                elif key.startswith("USLT"):
                    text_val = str(getattr(frame, "text", ""))
                    cleaned = clean_text(text_val, keyword, case_sensitive, clean_brackets)
                    if cleaned:
                        frame.text = cleaned
                    else:
                        keys_to_delete.append(key)

            for k in keys_to_delete:
                id3.pop(k, None)

            id3.save(filepath, v1=2, v2_version=3)
            try:
                os.utime(filepath, None)
            except Exception:
                pass

        elif ext == ".flac":
            flac = FLAC(filepath)
            keys_to_delete = []
            for key in list(flac.keys()):
                cleaned_vals = []
                for val in flac[key]:
                    cleaned = clean_text(str(val), keyword, case_sensitive, clean_brackets)
                    if cleaned:
                        cleaned_vals.append(cleaned)
                if cleaned_vals:
                    flac[key] = cleaned_vals
                else:
                    keys_to_delete.append(key)

            for k in keys_to_delete:
                flac.pop(k, None)

            flac.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass

        elif ext in [".m4a", ".mp4"]:
            mp4 = MP4(filepath)
            if mp4.tags:
                keys_to_delete = []
                for key in list(mp4.tags.keys()):
                    if key in ("covr", "trkn", "disk", "tmpo", "cpil", "pgap"):
                        continue
                    val = mp4.tags[key]
                    if isinstance(val, list):
                        cleaned_vals = []
                        for item in val:
                            if isinstance(item, str):
                                cleaned = clean_text(item, keyword, case_sensitive, clean_brackets)
                                if cleaned:
                                    cleaned_vals.append(cleaned)
                            else:
                                cleaned_vals.append(item)
                        if cleaned_vals:
                            mp4.tags[key] = cleaned_vals
                        else:
                            keys_to_delete.append(key)
                    elif isinstance(val, str):
                        cleaned = clean_text(val, keyword, case_sensitive, clean_brackets)
                        if cleaned:
                            mp4.tags[key] = cleaned
                        else:
                            keys_to_delete.append(key)

                for k in keys_to_delete:
                    mp4.tags.pop(k, None)

                mp4.save()
                try:
                    os.utime(filepath, None)
                except Exception:
                    pass

        elif ext == ".ogg":
            ogg = OggVorbis(filepath)
            keys_to_delete = []
            for key in list(ogg.keys()):
                cleaned_vals = []
                for val in ogg[key]:
                    cleaned = clean_text(str(val), keyword, case_sensitive, clean_brackets)
                    if cleaned:
                        cleaned_vals.append(cleaned)
                if cleaned_vals:
                    ogg[key] = cleaned_vals
                else:
                    keys_to_delete.append(key)

            for k in keys_to_delete:
                ogg.pop(k, None)

            ogg.save()
            try:
                os.utime(filepath, None)
            except Exception:
                pass

    except Exception as e:
        print(f"Error removing keyword from {filepath}: {e}")

    return read_tags(filepath)
