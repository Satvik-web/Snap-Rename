import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
        QLabel, QLineEdit, QCheckBox, QStackedWidget, QSpinBox, QComboBox,
        QAbstractItemView, QFrame, QRadioButton, QButtonGroup, QListWidget, 
        QMessageBox, QDialog, QTabWidget, QInputDialog, QSplitter, QFileIconProvider
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QUrl, QFileInfo
    from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor, QFont, QPixmap, QDrag, QIcon, QDesktopServices
except ImportError:
    print("PyQt6 is required. Please install it using: pip install PyQt6")
    sys.exit(1)

from engine import (
    RenameEngine, CleanOp, AdvancedReplaceOp, PrefixSuffixOp, 
    NumberingOp, SmartMetadataOp, NormalReplaceOp
)
import utils

STYLE_SHEET = """
QMainWindow, QDialog {
    background-color: #1a1a24;
}
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #e0e0e0;
}
QFrame#sidebar, QFrame#tool_settings_pane {
    background-color: #1e1d29;
    border: none;
}
QFrame#file_pane {
    background-color: #1a1a24;
}
QFrame#preview_pane {
    background-color: #1a1a24;
    border-left: 1px solid #2f2e3e;
    border-right: 1px solid #2f2e3e;
}

QSplitter::handle {
    background: #2f2e3e;
    width: 2px;
}

/* Sidebar Buttons */
QPushButton.NavBtn {
    background-color: transparent;
    color: #a1a1bc;
    border: none;
    border-radius: 8px;
    padding: 12px 15px;
    text-align: left;
    font-size: 14px;
    font-weight: 600;
}
QPushButton.NavBtn:hover {
    background-color: #2e2d3e;
    color: #ffffff;
}
QPushButton.NavBtn:checked {
    background-color: #4a47a3;
    color: #ffffff;
}

/* Headings */
QLabel.TitleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #ffffff;
}
QLabel.SubtitleLabel {
    font-size: 13px;
    color: #8c8c9e;
}

/* Action Buttons */
QPushButton.ActionBtn {
    background-color: #383842;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}
QPushButton.ActionBtn:hover {
    background-color: #4a4a58;
}

QPushButton.BlockBtn {
    background-color: #4a47a3;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton.BlockBtn:hover {
    background-color: #6a67c3;
}

QPushButton#applyBtn, QPushButton#sortBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f5576c, stop:1 #f093fb);
    color: white;
    font-weight: bold;
    font-size: 16px;
    border-radius: 12px;
    padding: 14px 24px;
}
QPushButton#applyBtn:hover, QPushButton#sortBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6b80, stop:1 #ffaafd);
}

QLineEdit, QSpinBox, QComboBox {
    background-color: #2a2939;
    border: 1px solid #3c3c46;
    border-radius: 8px;
    padding: 10px;
    color: #ffffff;
    font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #f093fb;
}

QListWidget {
    background-color: #2a2939;
    border: 1px solid #3c3c46;
    border-radius: 8px;
    padding: 5px;
}

QTableWidget {
    background-color: #1a1a24;
    border: none;
    gridline-color: transparent;
    selection-background-color: #4a47a3;
    selection-color: #ffffff;
    padding: 0px;
    font-size: 13px;
}
QTableWidget::item {
    border-bottom: 1px solid #2f2e3e;
    padding: 4px;
}
QHeaderView::section {
    background-color: #1a1a24;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #3c3c46;
    font-size: 12px;
    font-weight: bold;
    color: #8c8c9e;
}
"""

class FlowLayout(QHBoxLayout):
    def __init__(self, *widgets):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        for w in widgets: self.addWidget(w)
        self.addStretch()

class FileTable(QTableWidget):
    filesDropped = pyqtSignal(list)
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        # MacOS Finder layout
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Name", "Date Modified", "Size", "Kind"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self._start_drag()
        super().mouseMoveEvent(event)

    def _start_drag(self):
        items = self.selectedItems()
        if not items: return
        
        # Collect unique rows
        rows = list(set(item.row() for item in items))
        urls = []
        for row in rows:
            path_str = self.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if path_str:
                urls.append(QUrl.fromLocalFile(path_str))
        
        if not urls: return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setUrls(urls)
        drag.setMimeData(mime)
        
        # Use icon of first item as drag pixmap
        icon = QFileIconProvider().icon(QFileInfo(urls[0].toLocalFile()))
        drag.setPixmap(icon.pixmap(32, 32))
        
        drag.exec(Qt.DropAction.CopyAction)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        files = [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
        if files: self.filesDropped.emit(files)

class OptionCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("OptionCard { background-color: #252433; border-radius: 12px; padding: 10px; }")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

class InteractivePreviewLabel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #17161f; border: 1px dashed #4a47a3; border-radius: 6px; padding: 10px;")
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(10, 10, 10, 10)
        self.lbl = QLabel("Live Example: file.ext ➔ file.ext")
        self.lbl.setStyleSheet("color: #a1a1bc; font-size: 14px; font-weight: bold;")
        self.lbl.setWordWrap(True)
        lyt.addWidget(self.lbl)

    def setText(self, text):
        self.lbl.setText(text)

class MainWindow(QMainWindow):
    def __init__(self, directory=None):
        super().__init__()
        self.setWindowTitle("Snap Rename")
        self.resize(1300, 850)
        self.setStyleSheet(STYLE_SHEET)

        self.engine = RenameEngine()
        self.loaded_files = []
        self.active_operations = []
        self.workspace = None

        self.init_ui()
        self.set_window_icon()

        if directory:
            QTimer.singleShot(0, lambda: self.load_directory(directory))
        else:
            # Trigger directory selection slightly safely post-loop
            QTimer.singleShot(0, self.change_workspace)

    def set_window_icon(self):
        if os.path.exists("logo.png"):
            self.setWindowIcon(QIcon("logo.png"))

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 4-Pane Core Layout via QSplitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # PANE 1: Sidebar (Tools)
        self._build_sidebar()
        
        # PANE 2: File Table (Finder View)
        self._build_file_pane()
        
        # PANE 3: File Preview (Get Info View)
        self._build_preview_pane()
        
        # PANE 4: Active Tool Settings (Configurations)
        self._build_tool_settings_pane()

        main_layout.addWidget(self.splitter)

        self.update_clean_preview()
        self.update_smart_ui()
        self.update_normal_ui()
        self.update_ps_ui()
        self.update_num_ui()
        self.combo_meta_preset.setCurrentText("Audio / Songs")

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        # Let's constraint it to be like a finder sidebar
        sidebar.setMinimumWidth(200)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 20, 10, 20)
        side_layout.setSpacing(5)
        
        # Logo Section
        if os.path.exists("logo.png"):
            logo_lbl = QLabel()
            logo_pix = QPixmap("logo.png").scaled(112, 112, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(logo_pix)
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_lbl.setStyleSheet("margin-bottom: 5px;")
            side_layout.addWidget(logo_lbl)
        
        title = QLabel("Snap Rename")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(title)

        lbl = QLabel("TOOLS")
        lbl.setStyleSheet("color: #6a6a7c; font-weight: bold; font-size: 11px; padding-left: 5px; padding-bottom: 5px;")
        side_layout.addWidget(lbl)

        self.nav_btns = []
        tools = [
            ("Enhanced Clean Filename", 0),
            ("Smart Find & Replace", 1),
            ("Normal Find & Replace", 2),
            ("Prefix / Suffix", 3),
            ("Sequential Numbering", 4),
            ("Extended Smart Metadata", 5)
        ]

        self.btn_group = QButtonGroup(self)
        for text, idx in tools:
            btn = QPushButton(text.replace("&", "&&")) # Qt uses & for mnemonics, need to double it to show literal &
            btn.setProperty("class", "NavBtn")
            btn.setCheckable(True)
            if idx == 0: btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=idx: self.nav_clicked(i))
            self.btn_group.addButton(btn)
            self.nav_btns.append(btn)
            side_layout.addWidget(btn)

        side_layout.addStretch()
        
        pipeline_lbl = QLabel("ACTIVE PIPELINE")
        pipeline_lbl.setStyleSheet("color: #6a6a7c; font-weight: bold; font-size: 11px; padding-left: 5px; padding-bottom: 5px;")
        side_layout.addWidget(pipeline_lbl)

        self.op_list_widget = QListWidget()
        self.op_list_widget.setFixedHeight(120)
        side_layout.addWidget(self.op_list_widget)

        btn_rem_op = QPushButton("Remove Step")
        btn_rem_op.setProperty("class", "ActionBtn")
        btn_rem_op.clicked.connect(self.remove_operation)
        side_layout.addWidget(btn_rem_op)

        # Append to Splitter
        self.splitter.addWidget(sidebar)

    def _build_file_pane(self):
        file_pane = QFrame()
        file_pane.setObjectName("file_pane")
        file_pane.setMinimumWidth(400)
        lyt = QVBoxLayout(file_pane)
        lyt.setContentsMargins(10, 10, 10, 10)
        
        # Toolbar inside files
        list_header_lyt = QHBoxLayout()
        list_header_lyt.setContentsMargins(0, 0, 0, 5)
        
        btn_workspace = QPushButton("Directory...")
        btn_workspace.setProperty("class", "ActionBtn")
        btn_workspace.clicked.connect(self.change_workspace)
        list_header_lyt.addWidget(btn_workspace)
        
        self.lbl_workspace = QLabel("No workspace selected")
        self.lbl_workspace.setStyleSheet("color: #a1a1bc; padding-left: 10px; font-weight: bold;")
        list_header_lyt.addWidget(self.lbl_workspace)
        list_header_lyt.addStretch()
        
        list_header_lyt.addWidget(QLabel("Sort by:"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Alphabetical", "Date Added", "Date Modified", "Size", "Extension"])
        self.combo_sort.setFixedWidth(160)
        self.combo_sort.currentTextChanged.connect(self.handle_sort_change)  # BUG FIX: was never connected
        list_header_lyt.addWidget(self.combo_sort)
        
        self.btn_toggle_preview = QPushButton("Hide Preview")
        self.btn_toggle_preview.setCheckable(True)
        self.btn_toggle_preview.setChecked(True)
        self.btn_toggle_preview.setFixedWidth(120)
        self.btn_toggle_preview.setProperty("class", "ActionBtn")
        self.btn_toggle_preview.clicked.connect(self.toggle_preview_pane)
        list_header_lyt.addWidget(self.btn_toggle_preview)
        
        lyt.addLayout(list_header_lyt)

        self.table = FileTable()
        self.table.filesDropped.connect(self.handle_files_dropped)
        self.table.itemSelectionChanged.connect(self.update_file_preview)
        self.table.itemDoubleClicked.connect(self.open_file)
        self.table.itemSelectionChanged.connect(self.refresh_all_previews)
        lyt.addWidget(self.table)
        
        bottom_box = QHBoxLayout()
        btn_clear = QPushButton("Clear Selection")
        btn_clear.setProperty("class", "ActionBtn")
        btn_clear.clicked.connect(self.clear_files)

        btn_undo = QPushButton("Undo Last Rename")
        btn_undo.setObjectName("undoBtn")
        btn_undo.clicked.connect(self.undo_action)
        
        bottom_box.addWidget(btn_clear)
        bottom_box.addStretch()
        bottom_box.addWidget(btn_undo)
        
        lyt.addLayout(bottom_box)
        
        self.splitter.addWidget(file_pane)

    def _build_preview_pane(self):
        self.preview_pane = QFrame()
        self.preview_pane.setObjectName("preview_pane")
        self.preview_pane.setMinimumWidth(250)
        lyt = QVBoxLayout(self.preview_pane)
        lyt.setContentsMargins(20, 30, 20, 20)
        lyt.setSpacing(15)
        
        self.lbl_art = QLabel()
        self.lbl_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_art.setMinimumHeight(150)
        self.lbl_art.setStyleSheet("background-color: #23222f; border-radius: 12px;")
        lyt.addWidget(self.lbl_art)
        
        self.lbl_preview_title = QLabel("No Selection")
        self.lbl_preview_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.lbl_preview_title.setWordWrap(True)
        lyt.addWidget(self.lbl_preview_title)
        
        self.lbl_preview_subtitle = QLabel("Select a file to preview properties")
        self.lbl_preview_subtitle.setStyleSheet("font-size: 13px; color: #a1a1bc;")
        lyt.addWidget(self.lbl_preview_subtitle)
        
        lbl_info = QLabel("Information")
        lbl_info.setProperty("class", "SubtitleLabel")
        lyt.addWidget(lbl_info)
        
        info_card = QFrame()
        info_card.setStyleSheet("background-color: #252433; border-radius: 8px;")
        info_lyt = QVBoxLayout(info_card)
        info_lyt.setContentsMargins(15, 15, 15, 15)
        info_lyt.setSpacing(8)
        
        self.lbl_preview_created = QLabel("Created: --")
        self.lbl_preview_modified = QLabel("Modified: --")
        self.lbl_preview_kind = QLabel("Kind: --")
        self.lbl_preview_size = QLabel("Size: --")
        
        for lb in [self.lbl_preview_created, self.lbl_preview_modified, self.lbl_preview_kind, self.lbl_preview_size]:
            lb.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            info_lyt.addWidget(lb)
            
        lyt.addWidget(info_card)
        lyt.addStretch()
        
        self.splitter.addWidget(self.preview_pane)

    def _build_tool_settings_pane(self):
        tool_pane = QFrame()
        tool_pane.setObjectName("tool_settings_pane")
        tool_pane.setMinimumWidth(300)
        lyt = QVBoxLayout(tool_pane)
        lyt.setContentsMargins(20, 30, 20, 20)
        
        self.title_lbl = QLabel("Enhanced Clean Filename")
        self.title_lbl.setProperty("class", "TitleLabel")
        lyt.addWidget(self.title_lbl)
        
        self.op_stack = QStackedWidget()
        
        # 0: Enhanced Clean
        page_clean = OptionCard()
        v_clean = QVBoxLayout()
        self.chk_clean_extra_spaces = QCheckBox("Remove Extra Spaces")
        self.chk_clean_dup_words = QCheckBox("Remove Duplicate Words")
        self.chk_clean_special = QCheckBox("Remove Special Characters")
        self.chk_clean_nums = QCheckBox("Remove All Numbers")
        self.chk_clean_letters = QCheckBox("Remove All Letters")
        for w in [self.chk_clean_extra_spaces, self.chk_clean_dup_words, self.chk_clean_special, self.chk_clean_nums, self.chk_clean_letters]:
            v_clean.addWidget(w)
        page_clean.layout.addLayout(v_clean)
        
        self.combo_clean_norm = QComboBox()
        self.combo_clean_norm.addItems(["None", "Spaces", "Dashes", "Underscores"])
        page_clean.layout.addWidget(QLabel("Normalize format to:"))
        page_clean.layout.addWidget(self.combo_clean_norm)
        self.combo_clean_case = QComboBox()
        self.combo_clean_case.addItems(["None", "Capitalize First Letters", "Uppercase", "Lowercase"])
        page_clean.layout.addWidget(QLabel("Change casing to:"))
        page_clean.layout.addWidget(self.combo_clean_case)
        
        self.clean_ip = InteractivePreviewLabel()
        page_clean.layout.addWidget(self.clean_ip)
        page_clean.layout.addStretch()
        
        self.chk_clean_extra_spaces.toggled.connect(self.update_clean_preview)
        self.chk_clean_dup_words.toggled.connect(self.update_clean_preview)
        self.chk_clean_special.toggled.connect(self.update_clean_preview)
        self.chk_clean_nums.toggled.connect(self.update_clean_preview)
        self.chk_clean_letters.toggled.connect(self.update_clean_preview)
        self.combo_clean_norm.currentTextChanged.connect(self.update_clean_preview)
        self.combo_clean_case.currentTextChanged.connect(self.update_clean_preview)
        self.op_stack.addWidget(page_clean)
        
        # 1: Smart Regex Replace
        page_smart = OptionCard()
        self.combo_find = QComboBox()
        self.combo_find.addItems(["Numbers", "Letters", "Spaces", "Special Characters", "Dates", "Brackets / Parentheses", "Consecutive Spaces", "Underscores / Dashes", "File Extension", "Non-ASCII Characters", "Leading/Trailing Spaces", "Leading Numbers", "Trailing Numbers", "Leading/Trailing Underscores", "Capitalize First Letter", "Uppercase All Letters", "Lowercase All Letters", "Swap Words", "Character Position", "Custom Exact", "Custom Regex"])
        page_smart.layout.addWidget(QLabel("Find Pattern: "))
        page_smart.layout.addWidget(self.combo_find)
        self.inp_find_custom = QLineEdit()
        self.inp_find_custom.setPlaceholderText("Custom match...")
        self.inp_find_custom.hide()
        page_smart.layout.addWidget(self.inp_find_custom)
        
        # Character Position input — shown only when 'Character Position' is selected
        self.lbl_pos = QLabel("Insert after character position (1-based):")
        self.lbl_pos.hide()
        self.spin_char_pos = QSpinBox()
        self.spin_char_pos.setRange(1, 999)
        self.spin_char_pos.setValue(1)
        self.spin_char_pos.hide()
        page_smart.layout.addWidget(self.lbl_pos)
        page_smart.layout.addWidget(self.spin_char_pos)
        
        self.combo_act = QComboBox()
        self.combo_act.addItems(["Remove", "Replace With", "Insert Before", "Insert After", "Standardize", "Extract"])
        page_smart.layout.addWidget(QLabel("Action: "))
        page_smart.layout.addWidget(self.combo_act)
        self.inp_act_custom = QLineEdit()
        self.inp_act_custom.setPlaceholderText("Replacement text...")
        self.inp_act_custom.hide()
        page_smart.layout.addWidget(self.inp_act_custom)
        
        self.smart_ip = InteractivePreviewLabel()
        page_smart.layout.addWidget(self.smart_ip)
        page_smart.layout.addStretch()
        
        self.combo_find.currentTextChanged.connect(self.update_smart_ui)
        self.combo_act.currentTextChanged.connect(self.update_smart_ui)
        self.inp_find_custom.textChanged.connect(self.update_smart_ui)
        self.inp_act_custom.textChanged.connect(self.update_smart_ui)
        self.spin_char_pos.valueChanged.connect(self.update_smart_ui)
        self.op_stack.addWidget(page_smart)

        # 2: Normal Replace
        page_nreplace = OptionCard()
        page_nreplace.layout.addWidget(QLabel("Find: "))
        self.inp_n_find = QLineEdit()
        self.inp_n_find.setPlaceholderText("Exact phrase to find")
        page_nreplace.layout.addWidget(self.inp_n_find)
        page_nreplace.layout.addWidget(QLabel("Replace With: "))
        self.inp_n_rep = QLineEdit()
        self.inp_n_rep.setPlaceholderText("Leave empty to delete")
        page_nreplace.layout.addWidget(self.inp_n_rep)
        self.chk_n_case = QCheckBox("Case Sensitive")
        page_nreplace.layout.addWidget(self.chk_n_case)
        self.n_ip = InteractivePreviewLabel()
        page_nreplace.layout.addWidget(self.n_ip)
        page_nreplace.layout.addStretch()
        self.inp_n_find.textChanged.connect(self.update_normal_ui)
        self.inp_n_rep.textChanged.connect(self.update_normal_ui)
        self.chk_n_case.toggled.connect(self.update_normal_ui)
        self.op_stack.addWidget(page_nreplace)

        # 3: Prefix/Suffix
        page_presuf = OptionCard()
        page_presuf.layout.addWidget(QLabel("Prefix Add: "))
        self.inp_prefix = QLineEdit()
        self.inp_prefix.setPlaceholderText("Prefix")
        page_presuf.layout.addWidget(self.inp_prefix)
        page_presuf.layout.addWidget(QLabel("Suffix Add: "))
        self.inp_suffix = QLineEdit()
        self.inp_suffix.setPlaceholderText("Suffix")
        page_presuf.layout.addWidget(self.inp_suffix)
        self.ps_ip = InteractivePreviewLabel()
        page_presuf.layout.addWidget(self.ps_ip)
        page_presuf.layout.addStretch()
        self.inp_prefix.textChanged.connect(self.update_ps_ui)
        self.inp_suffix.textChanged.connect(self.update_ps_ui)
        self.op_stack.addWidget(page_presuf)

        # 4: Numbering
        page_num = OptionCard()
        self.radio_suffix = QRadioButton("At End")
        self.radio_prefix = QRadioButton("At Front")
        self.radio_suffix.setChecked(True)
        num_pos = QHBoxLayout()
        num_pos.addWidget(self.radio_prefix)
        num_pos.addWidget(self.radio_suffix)
        page_num.layout.addWidget(QLabel("Placement: "))
        page_num.layout.addLayout(num_pos)
        
        self.inp_num_base = QLineEdit()
        self.inp_num_base.setPlaceholderText("Base Name (blank keeps orig)")
        page_num.layout.addWidget(QLabel("Base Name:"))
        page_num.layout.addWidget(self.inp_num_base)
        
        s_lyt = QHBoxLayout()
        self.spin_start = QSpinBox()
        self.spin_start.setRange(0, 1000000)
        self.spin_start.setValue(1)
        self.spin_pad = QSpinBox()
        self.spin_pad.setRange(1, 10)
        self.spin_pad.setValue(2)
        s_lyt.addWidget(QLabel("Start:"))
        s_lyt.addWidget(self.spin_start)
        s_lyt.addWidget(QLabel("Pad:"))
        s_lyt.addWidget(self.spin_pad)
        page_num.layout.addLayout(s_lyt)
        
        self.num_ip = InteractivePreviewLabel()
        page_num.layout.addWidget(self.num_ip)
        page_num.layout.addStretch()
        self.inp_num_base.textChanged.connect(self.update_num_ui)
        self.spin_start.valueChanged.connect(self.update_num_ui)
        self.spin_pad.valueChanged.connect(self.update_num_ui)
        self.radio_prefix.toggled.connect(self.update_num_ui)
        self.op_stack.addWidget(page_num)

        # 5: Extended Smart Metadata
        page_meta = OptionCard()
        self.combo_meta_preset = QComboBox()
        self.combo_meta_preset.addItems(["All Files", "Images", "Audio / Songs", "Videos", "Movies", "TV Shows", "Podcasts", "Books / PDFs", "Scanned Documents"])
        page_meta.layout.addWidget(QLabel("Preset Category:"))
        page_meta.layout.addWidget(self.combo_meta_preset)
        self.inp_template = QLineEdit()
        self.inp_template.setPlaceholderText("Template syntax")
        page_meta.layout.addWidget(self.inp_template)
        
        self.lbl_meta_tags = QLabel("Tags: {type}, {created}, {modified}, {size_kb}, {exif_date}, {camera}, {resolution}, {artist}, {album}, {track}, {title}, {year}, {genre}, {duration}, {codec}, {show}, {season}, {episode}, {author}, {original}")
        self.lbl_meta_tags.setStyleSheet("color: #a1a1bc; font-size: 11px;")
        self.lbl_meta_tags.setWordWrap(True)
        page_meta.layout.addWidget(self.lbl_meta_tags)
        
        self.meta_ip = InteractivePreviewLabel()
        page_meta.layout.addWidget(self.meta_ip)
        page_meta.layout.addStretch()
        
        self.combo_meta_preset.currentTextChanged.connect(self.update_meta_preset_ui)
        self.inp_template.textChanged.connect(self.update_meta_preview)
        
        self.op_stack.addWidget(page_meta)

        lyt.addWidget(self.op_stack)
        btn_add_op = QPushButton("+ Add to Pipeline")
        btn_add_op.setProperty("class", "ActionBtn")
        btn_add_op.clicked.connect(self.add_operation)
        lyt.addWidget(btn_add_op)
        
        lyt.addStretch()
        
        # Apply button sits identically on the right side logic pane globally
        btn_apply = QPushButton("Apply Active Renames")
        btn_apply.setObjectName("applyBtn")
        btn_apply.clicked.connect(self.apply_action)
        lyt.addWidget(btn_apply)
        
        self.splitter.addWidget(tool_pane)
        # Ratio layout: Sidebar(15%), Table(50%), Preview(20%), Tools(15%)
        self.splitter.setSizes([200, 500, 250, 300])

    def toggle_preview_pane(self):
        visible = self.btn_toggle_preview.isChecked()
        self.preview_pane.setVisible(visible)
        self.btn_toggle_preview.setText("Hide Preview" if visible else "Show Preview")

    def change_workspace(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Workspace Folder")
        if folder:
            self.load_directory(folder)

    def load_directory(self, folder):
        self.workspace = folder
        self.lbl_workspace.setText(folder)
        paths = [Path(folder) / f for f in os.listdir(folder) 
                 if (Path(folder) / f).is_file() and f != ".DS_Store"]
        self.loaded_files.clear()
        self._add_paths_recursive(paths)
        self.handle_sort_change(self.combo_sort.currentText())

    def open_file(self, item):
        path_str = self.table.item(item.row(), 0).data(Qt.ItemDataRole.UserRole)
        if path_str:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path_str))

    def refresh_all_previews(self):
        """Refresh all tool live-preview labels whenever file selection changes."""
        self.update_clean_preview()
        self.update_smart_ui()
        self.update_normal_ui()
        self.update_ps_ui()
        self.update_num_ui()
        self.update_meta_preview()

    def update_file_preview(self):
        items = self.table.selectedItems()
        if not items:
            self.lbl_preview_title.setText("No Selection")
            self.lbl_preview_subtitle.setText("--")
            self.lbl_preview_created.setText("Created: --")
            self.lbl_preview_modified.setText("Modified: --")
            self.lbl_preview_size.setText("Size: --")
            self.lbl_preview_kind.setText("Kind: --")
            return
            
        row = items[0].row()
        name_item = self.table.item(row, 0)
        if not name_item: return
        
        # BUG FIX: Use the stored original path from UserRole, not workspace+display_name
        # After a rename, the display name is the new name and workspace lookup breaks
        path_str = name_item.data(Qt.ItemDataRole.UserRole)
        if not path_str: return
        p = Path(path_str)
        if not p.exists(): return
        
        meta = utils.extract_metadata(p)
        self.lbl_preview_title.setText(p.name)
        
        # System Icon
        icon = QFileIconProvider().icon(QFileInfo(str(p)))
        pix = icon.pixmap(128, 128)
        self.lbl_art.setPixmap(pix)
        
        size_str = utils.format_size(meta.get('size_bytes', 0))
        self.lbl_preview_subtitle.setText(f"{meta.get('type', 'File')} - {size_str}")
        self.lbl_preview_created.setText(f"Created       {meta.get('created', '--')}")
        self.lbl_preview_modified.setText(f"Modified      {meta.get('modified', '--')}")
        self.lbl_preview_size.setText(f"Size             {size_str}")
        self.lbl_preview_kind.setText(f"Kind            {meta.get('type', 'Unknown Extension')}")
        
    def handle_sort_change(self, text):
        if self.loaded_files:
            self.engine.set_files(self.loaded_files.copy())
            self.engine.sort_files(text)
            self.loaded_files = self.engine.files.copy()
            self.trigger_preview()

    def _get_demo_path(self, fallback="Track01.mp3"):
        # Use topmost selected file, fall back to first loaded, then fallback string
        selected = self.table.selectedItems()
        if selected:
            top_row = min(item.row() for item in selected)
            path_str = self.table.item(top_row, 0).data(Qt.ItemDataRole.UserRole)
            if path_str:
                return Path(path_str)
        if self.loaded_files:
            return Path(self.loaded_files[0])
        return Path(fallback)

    def update_clean_preview(self):
        demo = self._get_demo_path("  IMG__Vacation 2026!.jpg ")
        es = self.chk_clean_extra_spaces.isChecked()
        dw = self.chk_clean_dup_words.isChecked()
        sc = self.chk_clean_special.isChecked()
        rn = self.chk_clean_nums.isChecked()
        rl = self.chk_clean_letters.isChecked()
        norm = self.combo_clean_norm.currentText()
        case = self.combo_clean_case.currentText()
        op = CleanOp(rm_extra_spaces=es, rm_dup_words=dw, rm_special=sc, rm_nums=rn, rm_letters=rl, 
                     normalize_sep=norm if norm != "None" else None, casing=case if case != "None" else None)
        new_name = op.apply(demo, demo.name, 0, 1)
        color = "#10b981" if new_name != demo.name else "#a1a1bc"
        self.clean_ip.setText(f"Live Example: {demo.name} ➔ <span style='color:{color}'>{new_name}</span>")

    def update_smart_ui(self):
        f_txt = self.combo_find.currentText()
        a_txt = self.combo_act.currentText()
        
        is_char_pos = (f_txt == "Character Position")
        self.lbl_pos.setVisible(is_char_pos)
        self.spin_char_pos.setVisible(is_char_pos)
        self.inp_find_custom.setVisible(not is_char_pos and f_txt in ["Custom Exact", "Custom Regex"])
        
        if is_char_pos:
            # Force action combo to insert-related options
            if a_txt not in ["Insert (Stem Only)", "Insert (with Extension)"]:
                self.combo_act.blockSignals(True)
                if "Insert (Stem Only)" not in [self.combo_act.itemText(i) for i in range(self.combo_act.count())]:
                    self.combo_act.addItem("Insert (Stem Only)")
                    self.combo_act.addItem("Insert (with Extension)")
                self.combo_act.setCurrentText("Insert (Stem Only)")
                self.combo_act.blockSignals(False)
                a_txt = "Insert (Stem Only)"
            self.inp_act_custom.setVisible(True)
            self.inp_act_custom.setPlaceholderText("Text to insert at position...")
        else:
            # Remove position-specific actions if they exist
            for extra in ["Insert (Stem Only)", "Insert (with Extension)"]:
                idx_e = self.combo_act.findText(extra)
                if idx_e >= 0: self.combo_act.removeItem(idx_e)
            needs_rep = a_txt in ["Replace With", "Insert Before", "Insert After"]
            if f_txt in ["Capitalize First Letter", "Uppercase All Letters", "Lowercase All Letters", "Swap Words"]:
                self.combo_act.blockSignals(True)
                self.combo_act.setCurrentText("Standardize")
                self.combo_act.blockSignals(False)
                self.inp_act_custom.setVisible(False)
            else:
                self.inp_act_custom.setVisible(needs_rep)
                self.inp_act_custom.setPlaceholderText("Replacement text...")
        
        demo = self._get_demo_path("Photo.png" if is_char_pos else "IMG_2026-04-03.jpg")
        try:
            op = AdvancedReplaceOp(
                find_type=f_txt, action_type=self.combo_act.currentText(),
                find_custom=str(self.spin_char_pos.value()) if is_char_pos else self.inp_find_custom.text(),
                replace_custom=self.inp_act_custom.text()
            )
            new_name = op.apply(demo, demo.name, 0, 1)
            color = "#10b981" if new_name != demo.name else "#a1a1bc"
            self.smart_ip.setText(f"Live Example: {demo.name} ➔ <span style='color:{color}'>{new_name}</span>")
        except ValueError as e:
            self.smart_ip.setText(f"<span style='color:#ff6b6b'>⚠ {str(e)}</span>")
        except Exception:
            self.smart_ip.setText("<span style='color:#a1a1bc'>Live Example: —</span>")

    def update_normal_ui(self):
        demo = self._get_demo_path("My Holiday Photo.jpg")
        op = NormalReplaceOp(find_text=self.inp_n_find.text(), replace_text=self.inp_n_rep.text(), case_sensitive=self.chk_n_case.isChecked())
        new_name = op.apply(demo, demo.name, 0, 1)
        color = "#10b981" if new_name != demo.name else "#a1a1bc"
        self.n_ip.setText(f"Live Example: {demo.name} ➔ <span style='color:{color}'>{new_name}</span>")

    def update_ps_ui(self):
        demo = self._get_demo_path("Document.pdf")
        op = PrefixSuffixOp(self.inp_prefix.text(), self.inp_suffix.text())
        new_name = op.apply(demo, demo.name, 0, 1)
        color = "#10b981" if new_name != demo.name else "#a1a1bc"
        self.ps_ip.setText(f"Live Example: {demo.name} ➔ <span style='color:{color}'>{new_name}</span>")

    def update_num_ui(self):
        demo = self._get_demo_path("File.txt")
        op = NumberingOp(start=self.spin_start.value(), padding=self.spin_pad.value(), position="prefix" if self.radio_prefix.isChecked() else "suffix", base_name=self.inp_num_base.text())
        new_name = op.apply(demo, demo.name, 0, 1)
        color = "#10b981" if new_name != demo.name else "#a1a1bc"
        self.num_ip.setText(f"Live Example: {demo.name} ➔ <span style='color:{color}'>{new_name}</span>")

    def update_meta_preset_ui(self, txt):
        mapping = {
            "Audio / Songs": ("{artist}_{album}_{track} - {title}", [".mp3", ".flac", ".wav", ".m4a", ".aac"]),
            "Images": ("{original}_{camera}_{resolution}", [".jpg", ".jpeg", ".png", ".tiff"]),
            "Videos": ("{original}_{resolution}_{codec}", [".mp4", ".mov", ".mkv", ".avi"]),
            "Movies": ("{title} ({year}) {resolution}", [".mp4", ".mov", ".mkv", ".avi"]),
            "TV Shows": ("{show} {season}{episode} - {title}", [".mp4", ".mkv"]),
            "Podcasts": ("{title} - E{track} - {year}", [".mp3", ".aac"]),
            "Books / PDFs": ("{author} - {title} ({year})", [".pdf", ".epub", ".mobi"]),
            "Scanned Documents": ("Scan_{original}_{created}", [".pdf", ".tiff"]),
            "All Files": ("{original}_{modified}", ["*"])
        }
        tpl, exts = mapping.get(txt, ("", ["*"]))
        self.inp_template.setText(tpl)
        self._current_meta_target_extensions = exts
        self.update_meta_preview()

    def update_meta_preview(self):
        demo = self._get_demo_path("Track01.mp3")
        op = SmartMetadataOp(template=self.inp_template.text(), target_extensions=getattr(self, '_current_meta_target_extensions', ["*"]))
        new_name = op.apply(demo, demo.name, 0, 1)
        color = "#10b981" if new_name != demo.name else "#a1a1bc"
        self.meta_ip.setText(f"Live Example: {demo.name} ➔ <span style='color:{color}'>{new_name}</span>")

    def nav_clicked(self, idx):
        self.op_stack.setCurrentIndex(idx)
        titles = ["Enhanced Clean Filename", "Smart Find & Replace", "Normal Find & Replace", "Prefix / Suffix", "Sequential Numbering", "Extended Smart Metadata"]
        self.title_lbl.setText(titles[idx])

    def add_operation(self):
        idx = self.op_stack.currentIndex()
        op = None
        desc = ""
        
        if idx == 0:
            op = CleanOp(rm_extra_spaces=self.chk_clean_extra_spaces.isChecked(), rm_dup_words=self.chk_clean_dup_words.isChecked(), rm_special=self.chk_clean_special.isChecked(), rm_nums=self.chk_clean_nums.isChecked(), rm_letters=self.chk_clean_letters.isChecked(), normalize_sep=self.combo_clean_norm.currentText() if self.combo_clean_norm.currentText() != "None" else None, casing=self.combo_clean_case.currentText() if self.combo_clean_case.currentText() != "None" else None)
            desc = "Enhanced Clean Pipeline"
        elif idx == 1:
            f_txt = self.combo_find.currentText()
            a_txt = self.combo_act.currentText()
            
            if f_txt == "Character Position":
                pos = self.spin_char_pos.value()
                insert_text = self.inp_act_custom.text()
                
                # Ask about extension if action is stem-only but user might want ext included
                if a_txt == "Insert (Stem Only)":
                    reply = QMessageBox.question(self, "Affect Extension?",
                        "Should the character position insert affect the file extension too?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        a_txt = "Insert (with Extension)"
                
                op = AdvancedReplaceOp(find_type="Character Position", action_type=a_txt,
                                       find_custom=str(pos), replace_custom=insert_text)
                desc = f"Insert '{insert_text}' at pos {pos}"
            else:
                op = AdvancedReplaceOp(find_type=f_txt, action_type=a_txt,
                                       find_custom=self.inp_find_custom.text(),
                                       replace_custom=self.inp_act_custom.text())
                desc = f"Smart: {a_txt} {f_txt}"
        elif idx == 2:
            op = NormalReplaceOp(find_text=self.inp_n_find.text(), replace_text=self.inp_n_rep.text(), case_sensitive=self.chk_n_case.isChecked())
            desc = f"Normal Replace ('{self.inp_n_find.text()}')"
        elif idx == 3:
            p = self.inp_prefix.text()
            s = self.inp_suffix.text()
            if not p and not s: return
            op = PrefixSuffixOp(p, s)
            desc = f"Prefix/Suffix"
        elif idx == 4:
            pos = "prefix" if self.radio_prefix.isChecked() else "suffix"
            op = NumberingOp(start=self.spin_start.value(), padding=self.spin_pad.value(), position=pos, base_name=self.inp_num_base.text())
            desc = f"Numbering ({pos.capitalize()})"
        elif idx == 5:
            op = SmartMetadataOp(template=self.inp_template.text(), target_extensions=getattr(self, '_current_meta_target_extensions', ["*"]))
            desc = f"Meta ({self.combo_meta_preset.currentText()})"

        if op:
            self.active_operations.append(op)
            self.op_list_widget.addItem(desc)
            self.trigger_preview()

    def remove_operation(self):
        row = self.op_list_widget.currentRow()
        if row >= 0:
            self.op_list_widget.takeItem(row)
            self.active_operations.pop(row)
            self.trigger_preview()

    def _add_paths_recursive(self, paths: list[Path]):
        for p in paths:
            if p.is_file() and p.name != ".DS_Store":
                if p not in self.loaded_files: self.loaded_files.append(p)
            elif p.is_dir():
                for sub in p.iterdir(): self._add_paths_recursive([sub])
                    
    def handle_files_dropped(self, paths: list[Path]):
        if not self.workspace:
            QMessageBox.warning(self, "No Workspace", "Please select a workspace folder first.")
            return

        import shutil
        copied_any = False
        for p in paths:
            if p.parent == Path(self.workspace):
                # Already in workspace, just ensure it's in list (should be)
                if p not in self.loaded_files: self.loaded_files.append(p)
                continue
            
            target = Path(self.workspace) / p.name
            if target.exists():
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Question)
                msg.setWindowTitle("File Conflict")
                msg.setText(f"The file '{p.name}' already exists in the workspace.")
                btn_replace = msg.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
                btn_keep_both = msg.addButton("Keep Both", QMessageBox.ButtonRole.ActionRole)
                msg.addButton(QMessageBox.StandardButton.Cancel)
                msg.exec()
                
                if msg.clickedButton() == btn_replace:
                    shutil.copy2(p, target)
                    copied_any = True
                elif msg.clickedButton() == btn_keep_both:
                    stem = target.stem
                    suffix = target.suffix
                    counter = 1
                    while (Path(self.workspace) / f"{stem} copy {counter}{suffix}").exists():
                        counter += 1
                    target = Path(self.workspace) / f"{stem} copy {counter}{suffix}"
                    shutil.copy2(p, target)
                    copied_any = True
            else:
                shutil.copy2(p, target)
                copied_any = True
        
        if copied_any:
            # Refresh workspace
            self.loaded_files.clear()
            for f in os.listdir(self.workspace):
                f_path = Path(self.workspace) / f
                if f_path.is_file() and f != ".DS_Store":
                    self.loaded_files.append(f_path)
            self.handle_sort_change(self.combo_sort.currentText())  # BUG FIX: removed redundant double-sort below
        self.trigger_preview()

    def clear_files(self):
        self.loaded_files.clear()
        self.trigger_preview()
        
    def trigger_preview(self):
        self.engine.set_files(self.loaded_files.copy())
        self.engine.set_operations(self.active_operations)
        results = self.engine.preview()
        self.table.setRowCount(0)
        for row_idx, (orig_path, new_name, status) in enumerate(results):
            self.table.insertRow(row_idx)
            
            meta = utils.extract_metadata(orig_path)
            
            display_name = new_name if new_name != orig_path.name else orig_path.name
            name_item = QTableWidgetItem(display_name)
            name_item.setData(Qt.ItemDataRole.UserRole, str(orig_path))
            
            mod_item = QTableWidgetItem(meta.get('modified', ''))
            size_item = QTableWidgetItem(utils.format_size(meta.get('size_bytes', 0)))
            kind_item = QTableWidgetItem(meta.get('type', 'File'))
            
            for item in [mod_item, size_item, kind_item]:
                item.setForeground(QColor("#d1d1e0"))
            
            if new_name != orig_path.name:
                name_item.setForeground(QColor("#ff3b30"))
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
            else:
                name_item.setForeground(QColor("#d1d1e0"))
            
            self.table.setItem(row_idx, 0, name_item)
            self.table.setItem(row_idx, 1, mod_item)
            self.table.setItem(row_idx, 2, size_item)
            self.table.setItem(row_idx, 3, kind_item)

    def apply_action(self):
        if not self.loaded_files: return QMessageBox.information(self, "No Files", "Please add files first.")
        if not self.active_operations: return QMessageBox.information(self, "No Operations", "Please add at least one operation to the pipeline.")

        selected_rows = {item.row() for item in self.table.selectedItems()}
        target_results = None
        
        if selected_rows:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Apply Changes")
            msgBox.setText("Rename only selected files or all files in folder?")
            btn_sel = msgBox.addButton("Selected Only", QMessageBox.ButtonRole.AcceptRole)
            btn_all = msgBox.addButton("All Files", QMessageBox.ButtonRole.AcceptRole)
            btn_cncl = msgBox.addButton(QMessageBox.StandardButton.Cancel)
            msgBox.exec()
            
            if msgBox.clickedButton() == btn_cncl: return
            elif msgBox.clickedButton() == btn_sel:
                full_results = self.engine.preview()
                target_results = [full_results[i] for i in sorted(list(selected_rows))]
            else: target_results = self.engine.preview()
        else:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Confirm Rename")
            msgBox.setText(f"Are you sure you want to rename all files in the Workspace?")
            msgBox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if msgBox.exec() == QMessageBox.StandardButton.Yes: target_results = self.engine.preview()
            else: return
        
        if target_results:
            try:
                success, errors = self.engine.apply(target_results)
                self.loaded_files = self.engine.files.copy()
                err_msg = f"\nFailed to rename {errors} files (Check permissions or lock files)." if errors > 0 else ""
                QMessageBox.information(self, "Success", f"Successfully renamed {success} files.{err_msg}")
                # Clear pipeline after success
                self.active_operations.clear()
                self.op_list_widget.clear()
                self.trigger_preview()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def undo_action(self):
        reply = QMessageBox.question(self, 'Confirm Undo', 'Revert the last batch?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, errors = self.engine.undo()
            self.loaded_files = self.engine.files.copy()
            if success == 0 and errors == 0: QMessageBox.information(self, "Undo Complete", "No history found or nothing reverted.")
            else:
                msg = f"Successfully reverted {success} names."
                if errors > 0: msg += f"\nFailed to revert {errors} names."
                QMessageBox.information(self, "Undo Complete", msg)
            self.trigger_preview()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="snap-rename",
        description="Snap Rename — Batch File Renaming Tool",
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Launch the graphical GUI (requires PyQt6)",
    )
    parser.add_argument(
        "-d", "--directory", default=None, metavar="PATH",
        help="Folder to open on launch (TUI mode)",
    )
    parser.add_argument(
        "--uninstall-menu", action="store_true",
        help="Remove Snap Rename from the OS right-click context menu",
    )
    args = parser.parse_args()

    # ── Handle context menu install/uninstall ────────────────────
    from install_context_menu import uninstall as cm_uninstall

    if args.uninstall_menu:
        ok, msg = cm_uninstall()
        print(msg)
        sys.exit(0)

    if args.gui:
        # ── PyQt6 GUI mode ──────────────────────────────────────
        app = QApplication(sys.argv)
        window = MainWindow(directory=args.directory)
        window.show()
        sys.exit(app.exec())
    else:
        # ── Terminal UI mode (default) ───────────────────────────
        from tui import run_tui
        run_tui(directory=args.directory)

