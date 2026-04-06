import os
import shutil
import json
import re
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
import utils

class RenameOperation(ABC):
    @abstractmethod
    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        pass

class CleanOp(RenameOperation):
    def __init__(self, rm_extra_spaces=False, rm_dup_words=False, rm_special=False, 
                 rm_nums=False, rm_letters=False, normalize_sep=None, casing=None):
        self.rm_extra_spaces = rm_extra_spaces
        self.rm_dup_words = rm_dup_words
        self.rm_special = rm_special
        self.rm_nums = rm_nums
        self.rm_letters = rm_letters
        self.normalize_sep = normalize_sep
        self.casing = casing

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        base = Path(current_name).stem
        ext = Path(current_name).suffix

        if self.rm_nums: base = re.sub(r'\d+', '', base)
        if self.rm_letters: base = re.sub(r'[a-zA-Z]+', '', base)
        if self.rm_special: base = re.sub(r'[^\w\s-]', '', base)
            
        if self.rm_extra_spaces:  # BUG FIX: Strip extra spaces FIRST before normalizing separators
            base = re.sub(r'\s{2,}', ' ', base).strip()
            base = re.sub(r'_{2,}', '_', base)
            base = re.sub(r'-{2,}', '-', base)

        if self.normalize_sep == "Underscores": base = re.sub(r'[\s-]+', '_', base)
        elif self.normalize_sep == "Dashes": base = re.sub(r'[\s_]+', '-', base)
        elif self.normalize_sep == "Spaces": base = re.sub(r'[_-]+', ' ', base)

        if self.rm_dup_words:
            words = re.split(r'([\s_-]+)', base)
            seen = set()
            new_words = []
            for w in words:
                if w.strip() == "" or not re.match(r'[\w]+', w):
                    new_words.append(w)
                else:
                    if w.lower() not in seen:
                        seen.add(w.lower())
                        new_words.append(w)
            base = "".join(new_words)

        if self.casing == "Capitalize First Letters": base = base.title()
        elif self.casing == "Uppercase": base = base.upper()
        elif self.casing == "Lowercase": base = base.lower()

        return f"{base}{ext}"

class NormalReplaceOp(RenameOperation):
    def __init__(self, find_text: str, replace_text: str, case_sensitive: bool = False):
        self.find_text = find_text
        self.replace_text = replace_text
        self.case_sensitive = case_sensitive

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        base = Path(current_name).stem
        ext = Path(current_name).suffix
        if not self.find_text: return current_name
            
        if self.case_sensitive:
            base = base.replace(self.find_text, self.replace_text)
        else:
            pattern = re.compile(re.escape(self.find_text), re.IGNORECASE)
            base = pattern.sub(self.replace_text, base)
            
        return f"{base}{ext}"

class AdvancedReplaceOp(RenameOperation):
    def __init__(self, find_type: str, action_type: str, find_custom: str = "", replace_custom: str = ""):
        self.find_type = find_type
        self.action_type = action_type
        self.find_custom = find_custom
        self.replace_custom = replace_custom

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        base = Path(current_name).stem
        ext = Path(current_name).suffix

        # --- Character Position Insert ---
        if self.find_type == "Character Position":
            try:
                pos = int(self.find_custom)  # 1-based position
            except (ValueError, TypeError):
                return current_name  # No valid position yet
            
            insert_text = self.replace_custom
            
            # Decide whether to work on full name or just stem
            if self.action_type == "Insert (with Extension)":
                target = current_name
                if pos < 1 or pos > len(target):
                    raise ValueError(f"Position {pos} is out of range for '{current_name}' (length {len(target)}).")
                return target[:pos] + insert_text + target[pos:]
            else:  # Default: Insert (stem only, keep extension)
                if pos < 1 or pos > len(base):
                    raise ValueError(f"Position {pos} is out of range for stem '{base}' (length {len(base)}).")
                return base[:pos] + insert_text + base[pos:] + ext

        if self.find_type == "File Extension":
            if self.action_type == "Remove": return base
            elif self.action_type == "Replace With":
                new_ext = self.replace_custom if self.replace_custom.startswith('.') else f".{self.replace_custom}"
                return f"{base}{new_ext}"
            return current_name

        if self.action_type == "Standardize" or self.action_type == "Swap Words":
            if self.find_type == "Capitalize First Letter": return f"{base.capitalize()}{ext}"
            elif self.find_type == "Uppercase All Letters": return f"{base.upper()}{ext}"
            elif self.find_type == "Lowercase All Letters": return f"{base.lower()}{ext}"
            elif self.action_type == "Swap Words" or self.find_type == "Swap Words":
                swapped = re.sub(r'^([^\s_-]+)([\s_-]+)([^\s_-]+)', r'\3\2\1', base)
                return f"{swapped}{ext}"

        pattern = None
        if self.find_type == "Numbers": pattern = r'\d+'
        elif self.find_type == "Letters": pattern = r'[a-zA-Z]+'
        elif self.find_type == "Spaces": pattern = r' '
        elif self.find_type == "Special Characters": pattern = r'[^\w\s-]'
        elif self.find_type == "Dates": pattern = r'\d{4}[-_]?\d{2}[-_]?\d{2}|\d{8}'
        elif self.find_type == "Brackets / Parentheses": pattern = r'\[(.*?)\]|\((.*?)\)|<(.*?)>|\{(.*?)\}'
        elif self.find_type == "Consecutive Spaces": pattern = r' {2,}'
        elif self.find_type == "Underscores / Dashes": pattern = r'[_-]+'
        elif self.find_type == "Non-ASCII Characters": pattern = r'[^\x00-\x7F]+'
        elif self.find_type == "Leading/Trailing Spaces": pattern = r'(^\s+|\s+$)'
        elif self.find_type == "Leading Numbers": pattern = r'^\d+[\s_-]*'
        elif self.find_type == "Trailing Numbers": pattern = r'[\s_-]*\d+$'
        elif self.find_type == "Leading/Trailing Underscores": pattern = r'(^_+|_+$)'
        elif self.find_type == "Custom Regex": pattern = self.find_custom
        elif self.find_type == "Custom Exact": pattern = re.escape(self.find_custom)

        if not pattern: return current_name

        try:
            if self.action_type == "Remove":
                if self.find_type == "Brackets / Parentheses":
                    base = re.sub(r'\[.*?\]|\(.*?\)|<.*?>|\{.*?\}', "", base)
                else:
                    base = re.sub(pattern, "", base)
            elif self.action_type == "Replace With":
                if self.find_type == "Brackets / Parentheses":
                    def _rep_func(m):
                        inner = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ""
                        rc = self.replace_custom
                        if len(rc) >= 2:
                            half = len(rc) // 2
                            return f"{rc[:half]}{inner}{rc[half:]}"
                        elif len(rc) == 1:
                            return f"{rc}{inner}{rc}"
                        return inner
                    base = re.sub(pattern, _rep_func, base)
                else:
                    base = re.sub(pattern, self.replace_custom, base)
            elif self.action_type == "Insert Before":
                base = re.sub(f'({pattern})', f'{self.replace_custom}\\1', base)
            elif self.action_type == "Insert After":
                base = re.sub(f'({pattern})', f'\\1{self.replace_custom}', base)
            elif self.action_type == "Extract":
                matches = re.findall(pattern, base)
                base = "".join(matches)
            elif self.action_type == "Standardize":
                if "Spaces" in self.find_type or "Underscores / Dashes" in self.find_type:
                    base = re.sub(pattern, "_", base)
        except re.error:
            pass 
        return f"{base}{ext}"

class PrefixSuffixOp(RenameOperation):
    def __init__(self, prefix: str = "", suffix: str = ""):
        self.prefix = prefix
        self.suffix = suffix

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        base = Path(current_name).stem
        ext = Path(current_name).suffix
        return f"{self.prefix}{base}{self.suffix}{ext}"

class NumberingOp(RenameOperation):
    def __init__(self, start: int = 1, padding: int = 3, separator: str = "_", step: int = 1, position: str = "suffix", base_name: str = ""):
        self.start = start
        self.padding = padding
        self.separator = separator
        self.step = step
        self.position = position
        self.base_name = base_name

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        base = Path(current_name).stem
        ext = Path(current_name).suffix
        number = self.start + (index * self.step)
        num_str = str(number).zfill(self.padding)
        
        target_base = self.base_name if self.base_name else base
        if self.position == "prefix": return f"{num_str}{self.separator}{target_base}{ext}"
        else: return f"{target_base}{self.separator}{num_str}{ext}"

class BaseNameOp(RenameOperation):
    def __init__(self, base_name: str):
        self.base_name = base_name

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        ext = Path(current_name).suffix
        return f"{self.base_name}{ext}"

class SmartMetadataOp(RenameOperation):
    def __init__(self, template: str, target_extensions: list = None):
        self.template = template
        self.target_extensions = target_extensions if target_extensions else []

    def apply(self, original_path: Path, current_name: str, index: int, total: int) -> str:
        if not self.template: return current_name
        ext = original_path.suffix.lower()
        if self.target_extensions and ext not in self.target_extensions and "*" not in self.target_extensions:
            return current_name 
            
        meta = utils.extract_metadata(original_path)
        base = Path(current_name).stem
        
        tags = {
            "{type}": meta.get("type", "File"),
            "{created}": meta.get("created", ""),
            "{modified}": meta.get("modified", ""),
            "{size_kb}": str(meta.get("size_bytes", 0) // 1024),
            "{exif_date}": meta.get("exif_date", ""),
            "{camera}": meta.get("camera", "UnknownCamera"),
            "{resolution}": meta.get("resolution", ""),
            "{artist}": meta.get("artist", "UnknownArtist"),
            "{album}": meta.get("album", "UnknownAlbum"),
            "{track}": meta.get("track", "01"),
            "{title}": meta.get("title", base),
            "{year}": meta.get("year", ""),
            "{genre}": meta.get("genre", ""),
            "{duration}": meta.get("duration", ""),
            "{codec}": meta.get("codec", ""),
            "{show}": meta.get("show", "Show"),
            "{season}": meta.get("season", "S01"),
            "{episode}": meta.get("episode", "E01"),
            "{author}": meta.get("author", "UnknownAuthor"),
            "{original}": base
        }
        
        new_base = self.template
        for tag, val in tags.items():
            new_base = new_base.replace(tag, str(val))
            
        new_base = re.sub(r'\{[a-zA-Z_]+\}', '', new_base)
        new_base = re.sub(r'_{2,}', '_', new_base).strip('_')
        new_base = re.sub(r'-{2,}', '-', new_base).strip('-')
        
        return f"{new_base}{ext}"



class RenameEngine:
    def __init__(self):
        self.files: list[Path] = []
        self.operations: list[RenameOperation] = []
        self.undo_file = Path.home() / ".snap_undo_log.json"
        self.smart_sorter = None
        self.custom_sort_lambda = None

    def set_files(self, files: list[Path]):
        self.files = files

    def set_operations(self, operations: list[RenameOperation]):
        self.operations = operations


    def sort_files(self, method: str):
        if not self.files: return
        if method == "Date Created" or method == "Date Added":
            self.files.sort(key=lambda p: os.path.getctime(p) if p.exists() else 0)
        elif method == "Date Modified":
            self.files.sort(key=lambda p: os.path.getmtime(p) if p.exists() else 0)
        elif method == "Size":
            self.files.sort(key=lambda p: os.path.getsize(p) if p.exists() else 0)
        elif method == "Alphabetical":
            self.files.sort(key=lambda p: p.name)
        elif method == "Extension":
            self.files.sort(key=lambda p: p.suffix.lower())


    def preview(self) -> list[tuple[Path, str, str]]:
        results = []
        seen_names = set()
        
        for idx, path in enumerate(self.files):
            if not path.exists():
                results.append((path, path.name, "File Missing"))
                continue
                
            current_name = path.name
            for op in self.operations:
                try:
                    current_name = op.apply(path, current_name, idx, len(self.files))
                except ValueError:
                    # Position out of range: keep original name; flag it
                    current_name = path.name
                    break

            status = "Ready"
            final_name = current_name
            counter = 1
            while final_name in seen_names:
                status = "Conflict Resolved"
                stem = Path(current_name).stem
                suffix = Path(current_name).suffix
                final_name = f"{stem}({counter}){suffix}"
                counter += 1
                
            seen_names.add(final_name)
            results.append((path, final_name, status))

        return results

    def _save_undo(self, batch_id: str, history: list):
        log = {}
        if self.undo_file.exists():
            try:
                with open(self.undo_file, 'r', encoding='utf-8') as f:
                    log = json.load(f)
                    if not isinstance(log, dict): log = {}
            except:
                pass
        
        log[batch_id] = history
        with open(self.undo_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, indent=4)

    def apply(self, target_results=None) -> tuple[int, int]:
        results = target_results if target_results else self.preview()
        success = 0
        errors = 0
        history = []
        batch_id = datetime.now().isoformat()

        for original_path, new_name, status in results:
            if status == "File Missing" or original_path.name == new_name: continue
            new_path = original_path.parent / new_name
            try:
                if not new_path.exists():
                    shutil.move(str(original_path), str(new_path))
                    history.append({"original": str(original_path), "new": str(new_path)})
                    idx = self.files.index(original_path)
                    self.files[idx] = new_path
                    success += 1
                else: errors += 1
            except Exception:
                errors += 1

        if history: self._save_undo(batch_id, history)
        return success, errors

    def undo(self) -> tuple[int, int]:
        if not self.undo_file.exists(): return 0, 0
        try:
            with open(self.undo_file, 'r', encoding='utf-8') as f:
                log = json.load(f)
                if not isinstance(log, dict): return 0, 0
        except:
            return 0, 0
            
        if not log: return 0, 0
        latest_batch_id = list(log.keys())[-1]
        history = log[latest_batch_id]
        success, errors = 0, 0
        
        for entry in reversed(history):
            old_path = Path(entry["new"])
            reverted_path = Path(entry["original"])
            try:
                if old_path.exists() and not reverted_path.exists():
                    shutil.move(str(old_path), str(reverted_path))
                    success += 1
                    if old_path in self.files:
                        idx = self.files.index(old_path)
                        self.files[idx] = reverted_path
                else: errors += 1
            except: errors += 1
                
        del log[latest_batch_id]
        with open(self.undo_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, indent=4)
        return success, errors
