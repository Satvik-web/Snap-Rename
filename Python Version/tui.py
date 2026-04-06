"""
Snap Rename - Terminal UI (tui.py)
Full-featured TUI built with Textual, mirrors the GUI layout.

Usage:
    python3 main.py             # Launch TUI (prompts for folder)
    python3 main.py -d PATH     # Launch TUI with folder pre-loaded
    python3 main.py --gui       # Launch PyQt6 GUI
    python3 tui.py              # Run TUI directly
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Make engine importable when run directly
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from engine import (
    RenameEngine, CleanOp, AdvancedReplaceOp, PrefixSuffixOp,
    NumberingOp, SmartMetadataOp, NormalReplaceOp,
)

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Checkbox, ContentSwitcher, DataTable,
    Footer, Header, Input, Label, ListItem, ListView, Select, Static,
)

# ─────────────────────────────────────────────────────────────────
#  MODAL SCREENS
# ─────────────────────────────────────────────────────────────────

class InputModal(ModalScreen):
    """Single-line text input modal (used for directory path)."""

    DEFAULT_CSS = """
    InputModal {
        align: center middle;
    }
    #modal-box {
        background: #1e1d2e;
        /* Removed double border for cross-platform safety */
        outline: solid #6c63ff;
        width: 70;
        height: auto;
        padding: 2 3;
    }
    #modal-title { color: #6c63ff; text-style: bold; padding-bottom: 1; }
    #modal-hint  { color: #6c6680; margin-bottom: 1; }
    #modal-btns  { margin-top: 1; }
    Button { margin-right: 1; }
    """

    def __init__(self, title: str, hint: str = "", default: str = "") -> None:
        super().__init__()
        self._title = title
        self._hint = hint
        self._default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label(self._title, id="modal-title")
            if self._hint:
                yield Label(self._hint, id="modal-hint")
            yield Input(value=self._default, id="modal-input")
            with Horizontal(id="modal-btns"):
                yield Button("  OK  ", variant="success", id="modal-ok")
                yield Button("Cancel", variant="default", id="modal-cancel")

    @on(Button.Pressed, "#modal-ok")
    def _ok(self) -> None:
        self.dismiss(self.query_one("#modal-input", Input).value)

    @on(Button.Pressed, "#modal-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted)
    def _submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class ConfirmModal(ModalScreen):
    """Yes/No confirmation modal."""

    DEFAULT_CSS = """
    ConfirmModal { align: center middle; }
    #modal-box {
        background: #1e1d2e;
        /* Removed double border for cross-platform safety */
        outline: solid #f5576c;
        width: 60;
        height: auto;
        padding: 2 3;
    }
    #modal-title   { color: #f5576c; text-style: bold; padding-bottom: 1; }
    #modal-message { color: #d0d0e8; margin-bottom: 1; }
    Button { margin-right: 1; }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label(self._title, id="modal-title")
            yield Label(self._message, id="modal-message")
            with Horizontal():
                yield Button("Confirm", variant="error", id="ok")
                yield Button("Cancel", variant="default", id="cancel")

    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(False)


# ─────────────────────────────────────────────────────────────────
#  TOOL PANES (one per tool, shown inside ContentSwitcher)
# ─────────────────────────────────────────────────────────────────

# --- Smart Find & Replace pattern / action lists -----------------

FIND_PATTERNS = [
    ("1.  Numbers",                    "Numbers"),
    ("2.  Letters",                    "Letters"),
    ("3.  Spaces",                     "Spaces"),
    ("4.  Special Characters",         "Special Characters"),
    ("5.  Dates",                      "Dates"),
    ("6.  Brackets / Parentheses",     "Brackets / Parentheses"),
    ("7.  Consecutive Spaces",         "Consecutive Spaces"),
    ("8.  Underscores / Dashes",       "Underscores / Dashes"),
    ("9.  File Extension",             "File Extension"),
    ("10. Non-ASCII Characters",       "Non-ASCII Characters"),
    ("11. Leading/Trailing Spaces",    "Leading/Trailing Spaces"),
    ("12. Leading Numbers",            "Leading Numbers"),
    ("13. Trailing Numbers",           "Trailing Numbers"),
    ("14. Leading/Trailing Underscores","Leading/Trailing Underscores"),
    ("15. Capitalize First Letter",    "Capitalize First Letter"),
    ("16. Uppercase All Letters",      "Uppercase All Letters"),
    ("17. Lowercase All Letters",      "Lowercase All Letters"),
    ("18. Swap Words",                 "Swap Words"),
    ("19. Character Position",         "Character Position"),
    ("20. Custom Exact",               "Custom Exact"),
    ("21. Custom Regex",               "Custom Regex"),
]

ACTIONS = [
    ("Remove",               "Remove"),
    ("Replace With",         "Replace With"),
    ("Insert Before",        "Insert Before"),
    ("Insert After",         "Insert After"),
    ("Standardize",          "Standardize"),
    ("Extract",              "Extract"),
    ("Insert (Stem Only)",   "Insert (Stem Only)"),
    ("Insert (with Ext.)",   "Insert (with Extension)"),
]

METADATA_PRESETS = [
    ("-- Choose preset --",        ""),
    ("Audio / Songs",              "{artist}_{album}_{track} - {title}"),
    ("Images",                     "{original}_{camera}_{resolution}"),
    ("Videos",                     "{original}_{resolution}_{codec}"),
    ("Movies",                     "{title} ({year}) {resolution}"),
    ("TV Shows",                   "{show} {season}{episode} - {title}"),
    ("Podcasts",                   "{title} - E{track} - {year}"),
    ("Books / PDFs",               "{author} - {title} ({year})"),
    ("Scanned Documents",          "Scan_{original}_{created}"),
    ("All Files",                  "{original}_{modified}"),
]


class CleanPane(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Remove options:", classes="field-label")
        yield Checkbox("Remove Extra Spaces",      id="cl-spaces")
        yield Checkbox("Remove Duplicate Words",   id="cl-dups")
        yield Checkbox("Remove Special Characters",id="cl-special")
        yield Checkbox("Remove All Numbers",       id="cl-nums")
        yield Checkbox("Remove All Letters",       id="cl-letters")
        yield Label("Normalize separators:", classes="field-label")
        yield Select(
            [("None","None"),("Underscores","Underscores"),
             ("Dashes","Dashes"),("Spaces","Spaces")],
            value="None", id="cl-normalize", allow_blank=False,
        )
        yield Label("Change casing:", classes="field-label")
        yield Select(
            [("None","None"),("Capitalize First Letters","Capitalize First Letters"),
             ("Uppercase","Uppercase"),("Lowercase","Lowercase")],
            value="None", id="cl-casing", allow_blank=False,
        )

    def build_op(self) -> CleanOp:
        norm = self.query_one("#cl-normalize", Select).value
        cas  = self.query_one("#cl-casing",    Select).value
        return CleanOp(
            rm_extra_spaces=self.query_one("#cl-spaces",  Checkbox).value,
            rm_dup_words   =self.query_one("#cl-dups",    Checkbox).value,
            rm_special     =self.query_one("#cl-special", Checkbox).value,
            rm_nums        =self.query_one("#cl-nums",    Checkbox).value,
            rm_letters     =self.query_one("#cl-letters", Checkbox).value,
            normalize_sep  =norm if norm != "None" else None,
            casing         =cas  if cas  != "None" else None,
        )

    def label(self) -> str:
        parts = []
        if self.query_one("#cl-spaces",  Checkbox).value: parts.append("No-spaces")
        if self.query_one("#cl-dups",    Checkbox).value: parts.append("No-dups")
        if self.query_one("#cl-special", Checkbox).value: parts.append("No-special")
        if self.query_one("#cl-nums",    Checkbox).value: parts.append("No-nums")
        if self.query_one("#cl-letters", Checkbox).value: parts.append("No-letters")
        norm = self.query_one("#cl-normalize", Select).value
        cas  = self.query_one("#cl-casing",    Select).value
        if norm != "None": parts.append(norm)
        if cas  != "None": parts.append(cas)
        return "Clean: " + (", ".join(parts) if parts else "none")


class SmartPane(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Find Pattern (21 built-in + custom):", classes="field-label")
        yield Select(FIND_PATTERNS, value="Numbers", id="sm-pattern", allow_blank=False)
        yield Label("Action:", classes="field-label")
        yield Select(ACTIONS, value="Remove", id="sm-action", allow_blank=False)
        yield Label("Custom Find Pattern  (for Custom Exact / Regex / Char Position):", classes="field-label")
        yield Input(placeholder='e.g.  [0-9]+  or  3  (for char position)', id="sm-find")
        yield Label("Replacement / Insert Text:", classes="field-label")
        yield Input(placeholder='e.g. NUM  or  _   (leave blank to delete)', id="sm-replace")

    def build_op(self) -> AdvancedReplaceOp:
        pattern = self.query_one("#sm-pattern", Select).value
        action  = self.query_one("#sm-action",  Select).value
        find    = self.query_one("#sm-find",    Input).value
        replace = self.query_one("#sm-replace", Input).value
        return AdvancedReplaceOp(
            find_type=pattern, action_type=action,
            find_custom=find, replace_custom=replace,
        )

    def label(self) -> str:
        pattern = self.query_one("#sm-pattern", Select).value
        action  = self.query_one("#sm-action",  Select).value
        return f"Smart: {pattern} → {action}"


class NormalPane(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Find text:", classes="field-label")
        yield Input(placeholder="Exact text to search for", id="nm-find")
        yield Label("Replace with (blank = delete):", classes="field-label")
        yield Input(placeholder="Replacement text", id="nm-replace")
        yield Checkbox("Case Sensitive", id="nm-case")

    def build_op(self) -> NormalReplaceOp:
        return NormalReplaceOp(
            find_text    =self.query_one("#nm-find",    Input).value,
            replace_text =self.query_one("#nm-replace", Input).value,
            case_sensitive=self.query_one("#nm-case",   Checkbox).value,
        )

    def label(self) -> str:
        f = self.query_one("#nm-find", Input).value
        r = self.query_one("#nm-replace", Input).value
        return f"Replace: '{f}' → '{r}'"


class PreSufPane(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Prefix  (added before the stem):", classes="field-label")
        yield Input(placeholder="e.g.  2024_", id="ps-prefix")
        yield Label("Suffix  (added after the stem, before extension):", classes="field-label")
        yield Input(placeholder="e.g.  _final", id="ps-suffix")

    def build_op(self) -> PrefixSuffixOp:
        return PrefixSuffixOp(
            prefix=self.query_one("#ps-prefix", Input).value,
            suffix=self.query_one("#ps-suffix", Input).value,
        )

    def label(self) -> str:
        p = self.query_one("#ps-prefix", Input).value
        s = self.query_one("#ps-suffix", Input).value
        return f"Prefix/Suffix: '{p}...{s}'"


class NumberPane(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Placement:", classes="field-label")
        yield Select(
            [("At Front (prefix)", "prefix"), ("At End (suffix)", "suffix")],
            value="suffix", id="nb-pos", allow_blank=False,
        )
        yield Label("Base Name (optional — replaces stem):", classes="field-label")
        yield Input(placeholder="e.g.  Photo  →  Photo_001.jpg", id="nb-base")
        yield Label("Start number:", classes="field-label")
        yield Input(value="1",  id="nb-start", placeholder="1")
        yield Label("Pad width (digits):", classes="field-label")
        yield Input(value="3",  id="nb-pad",   placeholder="3")
        yield Label("Separator:", classes="field-label")
        yield Input(value="_",  id="nb-sep",   placeholder="_")

    def build_op(self) -> NumberingOp:
        try:   start = int(self.query_one("#nb-start", Input).value)
        except ValueError: start = 1
        try:   pad   = int(self.query_one("#nb-pad",   Input).value)
        except ValueError: pad = 3
        return NumberingOp(
            start    =start,
            padding  =pad,
            separator=self.query_one("#nb-sep",  Input).value or "_",
            position =self.query_one("#nb-pos",  Select).value,
            base_name=self.query_one("#nb-base", Input).value,
        )

    def label(self) -> str:
        pos   = self.query_one("#nb-pos",   Select).value
        start = self.query_one("#nb-start", Input).value
        return f"Number: {pos} from {start}"


class MetaPane(ScrollableContainer):
    def compose(self) -> ComposeResult:
        yield Label("Preset category:", classes="field-label")
        yield Select(METADATA_PRESETS, value="", id="mt-preset", allow_blank=False)
        yield Label("Template (edit freely):", classes="field-label")
        yield Input(placeholder="{original}_{modified}", id="mt-tpl")
        yield Static(
            " Available tags:\n"
            "  {original}  {type}  {created}  {modified}  {size_kb}\n"
            "  {year}  {title}  {artist}  {album}  {track}\n"
            "  {genre}  {duration}  {show}  {season}  {episode}\n"
            "  {author}  {camera}  {resolution}  {exif_date}  {codec}",
            id="mt-hint",
        )

    @on(Select.Changed, "#mt-preset")
    def _preset_changed(self, event: Select.Changed) -> None:
        if event.value:
            self.query_one("#mt-tpl", Input).value = event.value

    def build_op(self) -> SmartMetadataOp:
        return SmartMetadataOp(
            template=self.query_one("#mt-tpl", Input).value,
            target_extensions=["*"],
        )

    def label(self) -> str:
        tpl = self.query_one("#mt-tpl", Input).value
        return f"Metadata: {tpl[:25]}..." if len(tpl) > 25 else f"Metadata: {tpl}"


# ─────────────────────────────────────────────────────────────────
#  MAIN TUI APPLICATION
# ─────────────────────────────────────────────────────────────────

_TOOL_ORDER = ["clean", "smart", "normal", "presuf", "number", "meta"]

_TOOL_NAMES = {
    "clean":  "Enhanced Clean",
    "smart":  "Smart Find & Replace",
    "normal": "Normal Find & Replace",
    "presuf": "Prefix / Suffix",
    "number": "Sequential Numbering",
    "meta":   "Smart Metadata",
}

_LI_TO_TOOL = {
    "li-clean":  "clean",
    "li-smart":  "smart",
    "li-normal": "normal",
    "li-presuf": "presuf",
    "li-number": "number",
    "li-meta":   "meta",
}


class SnapRenameTUI(App):
    """Snap Rename - Terminal UI."""

    TITLE = "Snap Rename"
    SUB_TITLE = "Batch File Renaming | satvik-web"

    CSS = """
    /* ── Root ── */
    Screen {
        background: #0d0c1a;
        color: #d0d0e8;
        layers: base overlay;
    }

    /* ── Main layout ── */
    #main-area {
        height: 1fr;
    }

    /* ── Sidebar ── */
    #sidebar {
        width: 26;
        background: #13122a;
        /* Removed border for cross-platform safety */
        padding: 0 1;
    }

    /* ── File table panel ── */
    #file-table-panel {
        background: #0d0c1a;
        padding: 0 1;
    }

    /* ── Settings panel ── */
    #settings-panel {
        width: 42;
        background: #13122a;
        /* Removed border for cross-platform safety */
        padding: 0 1;
    }

    /* ── Labels ── */
    .section-label {
        color: #6c63ff;
        text-style: bold;
        padding: 1 0 0 0;
    }
    .panel-title {
        color: #ffffff;
        text-style: bold;
        background: #1e1d30;
        padding: 0 1;
    }
    .field-label {
        color: #8888aa;
        padding: 1 0 0 0;
    }

    /* ── Live preview box ── */
    #live-preview {
        background: #0a0918;
        /* Removed border for cross-platform safety */
        color: #a8ff78;
        padding: 1;
        min-height: 5;
        margin: 1 0;
    }

    /* ── Status bar ── */
    #status-bar {
        height: 3;
        background: #13122a;
        /* Removed border for cross-platform safety */
        padding: 0 2;
        align: left middle;
    }
    #status-text   { color: #d0d0e8; width: 1fr; }
    #shortcuts-hint{ color: #4a47a3; }

    /* ── Buttons ── */
    #btn-add { margin: 1 0 0 0; width: 100%; }
    #btn-rm  { margin: 0 0 1 0; width: 100%; }
    #table-btns { height: 3; dock: bottom; }
    #btn-tbl-add   { width: 1fr; margin-right: 1; }
    #btn-tbl-apply { width: 1fr; }

    /* ── ContentSwitcher ── */
    ContentSwitcher { height: auto; border: none; }

    /* ── Disable all default borders/outlines to prevent ? on Windows ── */
    * { border: none; outline: none; }
    Button, Checkbox, Input, Select, DataTable, ListView, ListItem {
        border: none;
        outline: none;
    }
    DataTable > .datatable--header { border: none; }
    ListItem.--highlight { border: none; outline: none; }

    /* ── Header ──  */
    Header { background: #1e1d30; color: #6c63ff; }
    Header.-tall  { height: 2; }

    /* ── Metadata hint ── */
    #mt-hint {
        color: #55547a;
        background: #0d0c1a;
        /* Removed border for cross-platform safety */
        padding: 1;
        margin-top: 1;
    }

    /* ── DataTable ── */
    DataTable { height: 1fr; }
    DataTable > .datatable--header { background: #1e1d30; color: #6c63ff; }
    DataTable > .datatable--cursor { background: #2e2c50; }

    /* ── ListView ── */
    ListView { height: auto; max-height: 12; }
    ListView > ListItem.--highlight { background: #4a47a3; color: #fff; }

    /* ── Checkbox / Input / Select ── */
    Input, Select  { margin: 0 0 0 0; }
    Checkbox       { margin: 0; }

    #footer-bar {
        height: 1;
        background: #1e1d30;
        color: #d0d0e8;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("d", "set_directory",  "Dir",      show=True),
        Binding("a", "apply_renames",  "Apply",    show=True),
        Binding("u", "undo_renames",   "Undo",     show=True),
        Binding("p", "add_pipeline",   "+Pipeline",show=True),
        Binding("c", "clear_pipeline", "Clear",    show=True),
        Binding("q", "quit",           "Quit",     show=True),
        Binding("1", "tool_1", show=False),
        Binding("2", "tool_2", show=False),
        Binding("3", "tool_3", show=False),
        Binding("4", "tool_4", show=False),
        Binding("5", "tool_5", show=False),
        Binding("6", "tool_6", show=False),
        Binding("r", "remove_step",    "Rm Step",  show=False),
    ]

    # ── Reactive state ──
    current_tool: reactive[str] = reactive("clean")

    def __init__(self, initial_dir: Optional[str] = None) -> None:
        super().__init__()
        self.engine          = RenameEngine()
        self._pipeline_ops:    list = []
        self._pipeline_labels: list[str] = []
        self.initial_dir = Path(initial_dir) if initial_dir else None

    # ─────────────── compose ──────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-area"):

            # ── SIDEBAR ──────────────────────────────────────────
            with Vertical(id="sidebar"):
                yield Label("TOOLS", classes="section-label")
                yield ListView(
                    ListItem(Label("1  Enhanced Clean"),      id="li-clean"),
                    ListItem(Label("2  Smart Find & Replace"), id="li-smart"),
                    ListItem(Label("3  Normal Find & Replace"), id="li-normal"),
                    ListItem(Label("4  Prefix / Suffix"),       id="li-presuf"),
                    ListItem(Label("5  Sequential Numbering"), id="li-number"),
                    ListItem(Label("6  Smart Metadata"),       id="li-meta"),
                    id="tool-list",
                )
                yield Label("PIPELINE", classes="section-label")
                yield ListView(id="pipeline-list")
                yield Button("Remove Step", id="btn-rm", variant="error")

            # ── FILE TABLE ───────────────────────────────────────
            with Vertical(id="file-table-panel"):
                yield Label(" FILES ", classes="panel-title")
                yield DataTable(
                    id="file-table",
                    zebra_stripes=True,
                    cursor_type="row",
                    show_cursor=True,
                )
                with Horizontal(id="table-btns"):
                    yield Button("+ Pipeline [p]", id="btn-tbl-add",   variant="success")
                    yield Button("Apply Renames [a]", id="btn-tbl-apply", variant="error")

            # ── SETTINGS + PREVIEW ───────────────────────────────
            with Vertical(id="settings-panel"):
                yield Label(" SETTINGS ", id="tool-title", classes="panel-title")
                with ContentSwitcher(initial="pane-clean", id="switcher"):
                    yield CleanPane( id="pane-clean")
                    yield SmartPane( id="pane-smart")
                    yield NormalPane(id="pane-normal")
                    yield PreSufPane(id="pane-presuf")
                    yield NumberPane(id="pane-number")
                    yield MetaPane(  id="pane-meta")
                yield Label("LIVE PREVIEW", classes="section-label")
                yield Static("Load a folder to see preview.", id="live-preview")
                yield Button("+ Add to Pipeline  [p]", id="btn-add", variant="success")

        # ── STATUS BAR ───────────────────────────────────────────
        with Horizontal(id="status-bar"):
            yield Label("No folder loaded - press 'd' to open a directory.", id="status-text")
            yield Label("1-6: tools | d: dir | a: apply | u: undo | p: +pipe | c: clear | r: rm step | q: quit", id="shortcuts-hint")

        yield Static(
            " d: dir  a: apply  u: undo  p: +pipe  c: clear  r: rm  q: quit",
            id="footer-bar"
        )

    # ─────────────── on_mount ─────────────────────────────────────

    def on_mount(self) -> None:
        t = self.query_one("#file-table", DataTable)
        t.add_columns("  #", "Filename  (bold red = pending rename)", "Size", "Created", "Modified", "Status")
        self.query_one("#tool-list", ListView).index = 0

        if self.initial_dir:
            self.load_directory(self.initial_dir)
        else:
            self.call_after_refresh(self.action_set_directory)

    # ─────────────── directory handling ───────────────────────────

    def action_set_directory(self) -> None:
        default = str(self.initial_dir or Path.home())
        self.push_screen(
            InputModal("Open Directory", "Enter the full path to your folder:", default),
            self._dir_chosen,
        )

    def _dir_chosen(self, path: Optional[str]) -> None:
        if path and path.strip():
            self.load_directory(Path(path.strip()))

    def load_directory(self, folder: Path) -> None:
        if not folder.exists() or not folder.is_dir():
            self._status(f"[red]Error: '{folder}' is not a valid directory.[/red]")
            return
        files = sorted(
            [p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")],
            key=lambda p: p.name.lower(),
        )
        self.engine.set_files(files)
        self.initial_dir = folder
        self._refresh_table()
        self._status(
            f"{len(files)} files loaded from "
            f"{folder.name}"
        )
        self._update_preview()

    # ─────────────── file table ───────────────────────────────────

    @staticmethod
    def _trunc(text: str, n: int = 34) -> str:
        """Truncate text to n chars, appending '...' if clipped."""
        return text if len(text) <= n else text[:n - 1] + "..."

    @staticmethod
    def _fmt_size(b: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.0f} {unit}" if unit == "B" else f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"

    @staticmethod
    def _fmt_date(ts: float) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(ts).strftime("%d/%m/%y")

    def _refresh_table(self) -> None:
        t = self.query_one("#file-table", DataTable)
        t.clear()
        if not self.engine.files:
            return
        self.engine.set_operations(self._pipeline_ops)
        try:
            previews = self.engine.preview()
        except Exception:
            previews = [(f, f.name, "Error") for f in self.engine.files]

        for i, (orig_path, new_name, status) in enumerate(previews, 1):
            orig    = orig_path.name
            changed = orig != new_name

            # File metadata
            try:
                st       = orig_path.stat()
                size_col = f"[dim]{self._fmt_size(st.st_size)}[/dim]"
                cre_col  = f"[dim]{self._fmt_date(st.st_birthtime if hasattr(st, 'st_birthtime') else st.st_ctime)}[/dim]"
                mod_col  = f"[dim]{self._fmt_date(st.st_mtime)}[/dim]"
            except Exception:
                size_col = cre_col = mod_col = "[dim]--[/dim]"

            if status == "File Missing":
                name_col = f"[red]{self._trunc(orig)}[/red]"
                sts_col  = "! missing"
            elif "Conflict" in status:
                name_col = f"[yellow]{self._trunc(new_name)}[/yellow]"
                sts_col  = "! conflict"
            elif changed:
                # Pending rename → bold red shows NEW name
                name_col = f"[bold red]{self._trunc(new_name)}[/bold red]"
                sts_col  = "->"
            else:
                name_col = f"[white]{self._trunc(orig)}[/white]"
                sts_col  = "."

            t.add_row(str(i), name_col, size_col, cre_col, mod_col, sts_col, key=str(i))

    # ─────────────── live preview ─────────────────────────────────

    def _update_preview(self) -> None:
        pw = self.query_one("#live-preview", Static)
        if not self.engine.files:
            pw.update("Load a folder to see preview.")
            return
        try:
            pane   = self.query_one(f"#pane-{self.current_tool}")
            tmp_op = pane.build_op()
            ops    = self._pipeline_ops + [tmp_op]
        except Exception:
            ops = self._pipeline_ops

        f       = self.engine.files[0]
        current = f.name
        for op in ops:
            try:
                current = op.apply(f, current, 0, len(self.engine.files))
            except Exception:
                pass

        if current == f.name:
            pw.update(f"{f.name}\n(no change with current settings)")
        else:
            pw.update(
                f"{f.name}\n"
                f"->  {current}"
            )

    # ─────────────── tool selection ───────────────────────────────

    def watch_current_tool(self, tool: str) -> None:
        self.query_one("#switcher", ContentSwitcher).current = f"pane-{tool}"
        self.query_one("#tool-title", Label).update(f" {_TOOL_NAMES.get(tool, tool)} ")
        self._update_preview()

    @on(ListView.Selected, "#tool-list")
    def _tool_list_selected(self, event: ListView.Selected) -> None:
        tid = _LI_TO_TOOL.get(event.item.id)
        if tid:
            self.current_tool = tid

    def _sel_tool(self, idx: int) -> None:
        tool = _TOOL_ORDER[idx]
        self.current_tool = tool
        self.query_one("#tool-list", ListView).index = idx

    def action_tool_1(self) -> None: self._sel_tool(0)
    def action_tool_2(self) -> None: self._sel_tool(1)
    def action_tool_3(self) -> None: self._sel_tool(2)
    def action_tool_4(self) -> None: self._sel_tool(3)
    def action_tool_5(self) -> None: self._sel_tool(4)
    def action_tool_6(self) -> None: self._sel_tool(5)

    # ─────────────── reactive refresh on any input change ─────────

    @on(Input.Changed)
    def _input_changed(self, _: Input.Changed) -> None:
        self._update_preview()

    @on(Checkbox.Changed)
    def _checkbox_changed(self, _: Checkbox.Changed) -> None:
        self._update_preview()

    @on(Select.Changed)
    def _select_changed(self, _: Select.Changed) -> None:
        self._update_preview()

    # ─────────────── pipeline management ─────────────────────────

    def action_add_pipeline(self) -> None:
        self._do_add()

    @on(Button.Pressed, "#btn-add")
    def _btn_add(self) -> None:
        self._do_add()

    @on(Button.Pressed, "#btn-tbl-add")
    def _btn_tbl_add(self) -> None:
        self._do_add()

    @on(Button.Pressed, "#btn-tbl-apply")
    def _btn_tbl_apply(self) -> None:
        self.action_apply_renames()

    def _do_add(self) -> None:
        try:
            pane  = self.query_one(f"#pane-{self.current_tool}")
            op    = pane.build_op()
            label = pane.label()
        except Exception as exc:
            self._status(f"[red]Error: {exc}[/red]")
            return

        self._pipeline_ops.append(op)
        self._pipeline_labels.append(label)
        n = len(self._pipeline_ops)
        self.query_one("#pipeline-list", ListView).append(
            ListItem(Label(f"{n}. {label}"))
        )
        self.engine.set_operations(self._pipeline_ops)
        self._refresh_table()
        self._status(
            f"Added: {label} | "
            f"Pipeline: {n} step(s)"
        )

    def action_remove_step(self) -> None:
        self._do_remove()

    @on(Button.Pressed, "#btn-rm")
    def _btn_rm(self) -> None:
        self._do_remove()

    def _do_remove(self) -> None:
        pl  = self.query_one("#pipeline-list", ListView)
        idx = pl.index

        if not self._pipeline_ops:
            self._status("[dim]Pipeline is already empty.[/dim]")
            return

        if idx is not None and 0 <= idx < len(self._pipeline_ops):
            removed = self._pipeline_labels.pop(idx)
            self._pipeline_ops.pop(idx)
        else:
            removed = self._pipeline_labels.pop()
            self._pipeline_ops.pop()

        pl.clear()
        for i, lbl in enumerate(self._pipeline_labels, 1):
            pl.append(ListItem(Label(f"{i}. {lbl}")))

        self.engine.set_operations(self._pipeline_ops)
        self._refresh_table()
        self._status(f"Removed [bold]{removed}[/bold]")

    def action_clear_pipeline(self) -> None:
        self._pipeline_ops.clear()
        self._pipeline_labels.clear()
        self.query_one("#pipeline-list", ListView).clear()
        self.engine.set_operations([])
        self._refresh_table()
        self._status("[dim]Pipeline cleared.[/dim]")

    # ─────────────── apply renames ────────────────────────────────

    def action_apply_renames(self) -> None:
        if not self.engine.files:
            self._status("[red]No files loaded.[/red]"); return
        if not self._pipeline_ops:
            self._status("[red]Pipeline is empty — add operations first.[/red]"); return

        preview   = self.engine.preview()
        n_changes = sum(1 for p, n, _ in preview if p.name != n)

        self.push_screen(
            ConfirmModal(
                "Apply Renames",
                f"Apply {len(self._pipeline_ops)} pipeline step(s) to "
                f"{len(preview)} files?\n{n_changes} file(s) will be renamed."
            ),
            self._apply_confirmed,
        )

    def _apply_confirmed(self, ok: Optional[bool]) -> None:
        if not ok:
            return
        success, errors = self.engine.apply()
        self.action_clear_pipeline()
        if self.initial_dir:
            self.load_directory(self.initial_dir)
        msg = f"[bold green]✓ Renamed {success} file(s).[/bold green]"
        if errors:
            msg += f"  [bold red]{errors} error(s).[/bold red]"
        self._status(msg)

    # ─────────────── undo ─────────────────────────────────────────

    def action_undo_renames(self) -> None:
        self.push_screen(
            ConfirmModal("Undo Last Rename", "Revert the most recent batch rename?"),
            self._undo_confirmed,
        )

    def _undo_confirmed(self, ok: Optional[bool]) -> None:
        if not ok:
            return
        success, errors = self.engine.undo()
        if self.initial_dir:
            self.load_directory(self.initial_dir)
        if success == 0 and errors == 0:
            self._status("[dim]Nothing to undo.[/dim]")
        else:
            msg = f"[bold green]✓ Reverted {success} file(s).[/bold green]"
            if errors:
                msg += f"  [bold red]{errors} failed.[/bold red]"
            self._status(msg)

    # ─────────────── helpers ──────────────────────────────────────

    def _status(self, text: str) -> None:
        self.query_one("#status-text", Label).update(text)


# ─────────────────────────────────────────────────────────────────
#  Entry point (when run directly: python3 tui.py)
# ─────────────────────────────────────────────────────────────────

def run_tui(directory: Optional[str] = None) -> None:
    SnapRenameTUI(initial_dir=directory).run()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Snap Rename TUI")
    p.add_argument("-d", "--directory", default=None, metavar="PATH",
                   help="Folder to open on launch")
    args = p.parse_args()
    run_tui(directory=args.directory)
