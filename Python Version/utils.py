import os
from pathlib import Path
from datetime import datetime

def format_size(size_bytes: int) -> str:
    if size_bytes == 0: return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes = size_bytes / 1024.0
        i += 1
    return f"{size_bytes:.1f} {units[i]}"

def _extract_id3v1(mmap_data):
    """Naive ID3v1 parser from the last 128 bytes of an MP3"""
    if len(mmap_data) < 128: return {}
    tag_data = mmap_data[-128:]
    if tag_data[:3] != b'TAG': return {}
    
    try:
        title = tag_data[3:33].decode('ascii', errors='ignore').strip('\x00').strip()
        artist = tag_data[33:63].decode('ascii', errors='ignore').strip('\x00').strip()
        album = tag_data[63:93].decode('ascii', errors='ignore').strip('\x00').strip()
        year = tag_data[93:97].decode('ascii', errors='ignore').strip('\x00').strip()
        
        # ID3v1.1 has track number at byte 126 if byte 125 is 0
        track = ""
        if tag_data[125] == 0 and tag_data[126] != 0:
            track = str(tag_data[126]).zfill(2)
            
        return {
            "title": title, "artist": artist, "album": album, 
            "year": year, "track": track
        }
    except Exception:
        return {}

def extract_metadata(file_path: Path) -> dict:
    """
    Extracts deep metadata using purely Python Standard Libraries (Zero Dependencies).
    Employs byte-level heuristic parsing for ID3, basic EXIF stubs, and OS level fallbacks.
    """
    meta = {}
    
    if not file_path.exists():
        return meta
        
    ext = file_path.suffix.lower()
    meta["type"] = "File"
    if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.gif']: meta["type"] = "Image"
    elif ext in ['.mp3', '.wav', '.flac', '.m4a']: meta["type"] = "Audio"
    elif ext in ['.mp4', '.mkv', '.mov', '.avi']: meta["type"] = "Video"
    elif ext in ['.pdf', '.epub', '.mobi']: meta["type"] = "Book"
    
    # OS level timestamps
    stat = os.stat(file_path)
    meta["size_bytes"] = stat.st_size
    
    try:
        dt_c = datetime.fromtimestamp(stat.st_ctime)
        dt_m = datetime.fromtimestamp(stat.st_mtime)
        meta["created"] = dt_c.strftime("%d/%m/%Y")
        meta["modified"] = dt_m.strftime("%d/%m/%Y")
        meta["exif_date"] = meta["created"] # fallback
        meta["year"] = str(dt_c.year)
    except Exception:
        pass
        
    # Attempt Byte-level parsing where possible
    try:
        if ext == '.mp3':
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 50) # Read start/end
                f.seek(-128, 2)
                end_content = f.read(128)
                
                # Try ID3v1
                tags = _extract_id3v1(end_content)
                if tags:
                    meta.update(tags)
                else:
                    # Naively scan first few kb for ID3v2 frames like TIT2, TPE1
                    if b'ID3' in content:
                        if b'TPE1' in content: # Artist
                            idx = content.find(b'TPE1')
                            meta['artist'] = content[idx+11:idx+31].decode('ascii', errors='ignore').strip('\x00')
                        if b'TIT2' in content: # Title
                            idx = content.find(b'TIT2')
                            meta['title'] = content[idx+11:idx+31].decode('ascii', errors='ignore').strip('\x00')
                            
        elif ext in ['.jpg', '.jpeg']:
             with open(file_path, 'rb') as f:
                 head = f.read(1024)
                 if b'Exif' in head:
                     # Very naive search for datetime text in EXIF
                     date_match = re.search(br'\d{4}:\d{2}:\d{2}', head)
                     if date_match:
                         meta['exif_date'] = date_match.group().decode().replace(':', '')
                     # Dummy Camera
                     if b'Apple' in head or b'iPhone' in head: meta['camera'] = 'iPhone'
                     elif b'Canon' in head: meta['camera'] = 'Canon'
                     
    except Exception:
        pass # Graceful degradation
        
    # Heuristic parsing from Original Filename
    # Ex: "12 - Coldplay - Yellow.mp3" -> track, artist, title
    # Ex: "Breaking Bad S01E05.mkv" -> show, season, episode
    base = file_path.stem
    if meta["type"] == "Video":
        import re
        s_e_match = re.search(r'([A-Za-z\s]+)?[sS](\d{1,2})[eE](\d{1,2})', base)
        if s_e_match:
            meta["show"] = s_e_match.group(1).replace(".", " ").strip() if s_e_match.group(1) else "ShowName"
            meta["season"] = f"S{s_e_match.group(2).zfill(2)}"
            meta["episode"] = f"E{s_e_match.group(3).zfill(2)}"
            
    if meta["type"] == "Audio" and "artist" not in meta:
        parts = [p.strip() for p in base.split('-')]
        if len(parts) >= 2:
            if parts[0].isdigit():
                meta['track'] = parts[0].zfill(2)
                meta['artist'] = parts[1]
                meta['title'] = parts[2] if len(parts) > 2 else ""
            else:
                meta['artist'] = parts[0]
                meta['title'] = parts[1]

    # Fill defaults for anything missing so it doesn't crash template
    defaults = {
        "artist": "UnknownArtist", "album": "UnknownAlbum", "track": "00",
        "title": base, "year": meta.get("created", "01/01/2000").split("/")[-1],  # BUG FIX: parse DD/MM/YYYY correctly
        "genre": "UnknownGenre", "duration": "", "codec": "h264",
        "show": "ShowName", "season": "S01", "episode": "E01",
        "author": "UnknownAuthor", "camera": "UnknownCamera", "resolution": "1080p", "exif_date": meta.get("created", "")
    }
    
    for k, v in defaults.items():
        if k not in meta or not meta[k]:
            meta[k] = v

    return meta
