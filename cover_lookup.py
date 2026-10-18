import re
import requests


def search_online_covers(query: str = "", artist: str = "", album: str = "", title: str = "", limit: int = 12) -> list:
    results = []
    seen_urls = set()

    # Formulate search queries
    search_queries = []
    if query and query.strip():
        search_queries.append(query.strip())
    
    if artist and album:
        search_queries.append(f"{artist} {album}")
    if artist and title:
        search_queries.append(f"{artist} {title}")
    if album:
        search_queries.append(album)
    if title:
        search_queries.append(title)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. Query iTunes Search API (Albums & Songs)
    for q in search_queries[:3]:
        try:
            # Query for album releases
            resp = requests.get(
                "https://itunes.apple.com/search",
                params={"term": q, "entity": "album", "limit": limit},
                headers=headers,
                timeout=6
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    art_100 = item.get("artworkUrl100", "")
                    if not art_100:
                        continue
                    
                    # Convert to ultra high-res (1000x1000 or 1400x1400)
                    high_res = re.sub(r"100x100bb\.", "1200x1200bb.", art_100)
                    thumb = re.sub(r"100x100bb\.", "300x300bb.", art_100)

                    if high_res in seen_urls:
                        continue
                    seen_urls.add(high_res)

                    results.append({
                        "source": "Apple Music / iTunes",
                        "artist": item.get("artistName", "Unknown Artist"),
                        "album": item.get("collectionName", "Unknown Album"),
                        "title": item.get("collectionName", ""),
                        "year": (item.get("releaseDate") or "")[:4],
                        "artwork_url": high_res,
                        "thumbnail_url": thumb,
                        "track_count": item.get("trackCount", 1)
                    })

            # Also query for song tracks if needed
            if len(results) < 5:
                resp_song = requests.get(
                    "https://itunes.apple.com/search",
                    params={"term": q, "entity": "song", "limit": 6},
                    headers=headers,
                    timeout=6
                )
                if resp_song.status_code == 200:
                    data = resp_song.json()
                    for item in data.get("results", []):
                        art_100 = item.get("artworkUrl100", "")
                        if not art_100:
                            continue
                        high_res = re.sub(r"100x100bb\.", "1200x1200bb.", art_100)
                        thumb = re.sub(r"100x100bb\.", "300x300bb.", art_100)

                        if high_res in seen_urls:
                            continue
                        seen_urls.add(high_res)

                        results.append({
                            "source": "Apple Music (Track)",
                            "artist": item.get("artistName", "Unknown Artist"),
                            "album": item.get("collectionName", "Single / Track"),
                            "title": item.get("trackName", ""),
                            "year": (item.get("releaseDate") or "")[:4],
                            "artwork_url": high_res,
                            "thumbnail_url": thumb,
                            "track_count": 1
                        })

        except Exception as e:
            print(f"Error querying iTunes for '{q}': {e}")

        if len(results) >= limit:
            break

    # 2. Fallback / supplement: Deezer Public API
    if len(results) < 4 and search_queries:
        try:
            d_query = search_queries[0]
            d_resp = requests.get(
                "https://api.deezer.com/search",
                params={"q": d_query, "limit": 6},
                headers=headers,
                timeout=6
            )
            if d_resp.status_code == 200:
                data = d_resp.json()
                for item in data.get("data", []):
                    album_obj = item.get("album", {})
                    cover_xl = album_obj.get("cover_xl") or album_obj.get("cover_big") or album_obj.get("cover_medium")
                    thumb = album_obj.get("cover_medium") or cover_xl
                    if cover_xl and cover_xl not in seen_urls:
                        seen_urls.add(cover_xl)
                        results.append({
                            "source": "Deezer",
                            "artist": item.get("artist", {}).get("name", "Unknown Artist"),
                            "album": album_obj.get("title", "Unknown Album"),
                            "title": item.get("title", ""),
                            "year": "",
                            "artwork_url": cover_xl,
                            "thumbnail_url": thumb,
                            "track_count": 1
                        })
        except Exception as e:
            print(f"Deezer search error: {e}")

    return results


def download_cover_bytes(image_url: str) -> tuple[bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    resp = requests.get(image_url, headers=headers, timeout=15)
    resp.raise_for_status()
    
    content_type = resp.headers.get("Content-Type", "")
    mime = "image/jpeg"
    if "png" in content_type or image_url.lower().endswith(".png"):
        mime = "image/png"
    elif "webp" in content_type or image_url.lower().endswith(".webp"):
        mime = "image/webp"

    return resp.content, mime
