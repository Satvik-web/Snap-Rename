// app.js — Snap Rename Web App
'use strict';

window.snapApp = null;

// ─── Custom Modal System ──────────────────────────────────────────
function showModal({ icon='💬', title='', message='', okText='OK', okClass='modal-btn-ok' } = {}) {
  return new Promise(resolve => {
    document.getElementById('modal-icon').textContent = icon;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    const actions = document.getElementById('modal-actions');
    actions.innerHTML = '';
    const btnOk = document.createElement('button');
    btnOk.textContent = okText;
    btnOk.className = okClass;
    btnOk.onclick = () => { document.getElementById('modal-overlay').classList.add('hidden'); resolve(true); };
    actions.appendChild(btnOk);
    document.getElementById('modal-overlay').classList.remove('hidden');
    setTimeout(() => btnOk.focus(), 50);
  });
}

function showConfirm({ icon='❓', title='', message='', okText='OK', cancelText='Cancel', okClass='modal-btn-ok' } = {}) {
  return new Promise(resolve => {
    document.getElementById('modal-icon').textContent = icon;
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    const actions = document.getElementById('modal-actions');
    actions.innerHTML = '';
    const btnCancel = document.createElement('button');
    btnCancel.textContent = cancelText;
    btnCancel.className = 'modal-btn-cancel';
    btnCancel.onclick = () => { document.getElementById('modal-overlay').classList.add('hidden'); resolve(false); };
    const btnOk = document.createElement('button');
    btnOk.textContent = okText;
    btnOk.className = okClass;
    btnOk.onclick = () => { document.getElementById('modal-overlay').classList.add('hidden'); resolve(true); };
    actions.appendChild(btnCancel);
    actions.appendChild(btnOk);
    document.getElementById('modal-overlay').classList.remove('hidden');
    setTimeout(() => btnOk.focus(), 50);
    const overlay = document.getElementById('modal-overlay');
    const closeHandler = e => {
      if (e.target === overlay) {
        overlay.classList.add('hidden');
        overlay.removeEventListener('click', closeHandler);
        resolve(false);
      }
    };
    overlay.addEventListener('click', closeHandler);
  });
}

// ────────────────────────────────────────────────────────────────────
class SnapRenameApp {
  constructor() {
    this.engine = new RenameEngine();
    this.loadedFiles = [];
    this.dirHandle = null;
    this.activeOperations = [];
    this.previewResults = [];
    this._bindUI();
    window.snapApp = this;
  }

  // ─── UI Binding ─────────────────────────────────────────────────
  _bindUI() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => this._navClicked(parseInt(btn.dataset.idx)));
    });
    document.getElementById('btn-workspace').addEventListener('click', () => this.pickWorkspace());
    document.getElementById('combo-sort').addEventListener('change', e => this.handleSortChange(e.target.value));
    document.getElementById('btn-toggle-preview').addEventListener('click', () => this.togglePreview());
    document.getElementById('btn-add-op').addEventListener('click', () => this.addOperation());
    document.getElementById('btn-rem-op').addEventListener('click', () => this.removeOperation());
    document.getElementById('btn-apply').addEventListener('click', () => this.applyAction());
    document.getElementById('btn-clear').addEventListener('click', () => this.clearFiles());
    document.getElementById('btn-undo').addEventListener('click', () => this.undoAction());

    const livePreviewInputs = [
      'chk-clean-spaces','chk-clean-dups','chk-clean-special','chk-clean-nums','chk-clean-letters',
      'combo-clean-norm','combo-clean-case',
      'combo-find','combo-act','inp-find-custom','inp-act-custom','spin-char-pos',
      'inp-n-find','inp-n-rep','chk-n-case',
      'inp-prefix','inp-suffix',
      'spin-start','spin-pad','radio-prefix','radio-suffix','inp-num-base',
      'inp-template','combo-meta-preset'
    ];
    livePreviewInputs.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', () => this.updateAllPreviews());
      if (el) el.addEventListener('change', () => this.updateAllPreviews());
    });

    document.getElementById('combo-find').addEventListener('change', () => this._updateSmartUI());
    document.getElementById('combo-act').addEventListener('change', () => this._updateSmartUI());
    document.getElementById('combo-meta-preset').addEventListener('change', e => this._metaPresetChanged(e.target.value));

    document.getElementById('file-table-body').addEventListener('click', e => {
      const row = e.target.closest('tr');
      if (!row) return;
      if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
        document.querySelectorAll('#file-table-body tr.selected').forEach(r => r.classList.remove('selected'));
      }
      row.classList.toggle('selected');
      this._updatePreviewPane();
      this.updateAllPreviews();
    });

    document.getElementById('file-table-body').addEventListener('dblclick', async e => {
      const row = e.target.closest('tr');
      if (!row) return;
      const idx = parseInt(row.dataset.idx);
      const entry = this.loadedFiles[idx];
      if (entry?.file) {
        const url = URL.createObjectURL(entry.file);
        window.open(url, '_blank');
      }
    });

    const tableArea = document.getElementById('file-pane');
    tableArea.addEventListener('dragover', e => { e.preventDefault(); tableArea.classList.add('drag-over'); });
    tableArea.addEventListener('dragleave', () => tableArea.classList.remove('drag-over'));
    tableArea.addEventListener('drop', e => {
      e.preventDefault();
      tableArea.classList.remove('drag-over');
      this._handleExternalDrop(e.dataTransfer.files);
    });

    this._updateSmartUI();
    this.updateAllPreviews();
    this._metaPresetChanged('Audio / Songs');
  }

  // ─── Navigation ─────────────────────────────────────────────────
  _navClicked(idx) {
    document.querySelectorAll('.nav-btn').forEach((btn, i) => btn.classList.toggle('active', i === idx));
    document.querySelectorAll('.tool-page').forEach((pg, i) => pg.classList.toggle('hidden', i !== idx));
    const titles = ['Enhanced Clean Filename','Smart Find & Replace','Normal Find & Replace','Prefix / Suffix','Sequential Numbering','Extended Smart Metadata'];
    document.getElementById('tool-title').textContent = titles[idx];
  }

  // ─── Workspace ──────────────────────────────────────────────────
  async pickWorkspace() {
    try {
      const handle = await window.showDirectoryPicker({ mode: 'readwrite' });
      this.dirHandle = handle;
      document.getElementById('lbl-workspace').textContent = handle.name;
      this.loadedFiles = [];
      for await (const [name, fh] of handle.entries()) {
        if (fh.kind === 'file' && !name.startsWith('.')) {
          const file = await fh.getFile();
          const entry = { name, handle: fh, file, meta: null };
          entry.meta = await extractMeta(entry);
          this.loadedFiles.push(entry);
        }
      }
      this.handleSortChange(document.getElementById('combo-sort').value);
      this.triggerPreview();
    } catch(e) {
      if (e.name !== 'AbortError') console.error(e);
    }
  }

  // ─── Drop external files ────────────────────────────────────────
  async _handleExternalDrop(fileList) {
    if (!this.dirHandle) {
      await showModal({ icon: '📂', title: 'No Workspace', message: 'Please select a workspace folder first using the Directory button.' });
      return;
    }
    for (const file of fileList) {
      let existingHandle = null;
      try { existingHandle = await this.dirHandle.getFileHandle(file.name); } catch {}
      let targetName = file.name;
      if (existingHandle) {
        const choice = await showConfirm({
          icon: '⚠️', title: 'File Already Exists',
          message: `"${file.name}" already exists in this folder.\nReplace it, or keep both?`,
          okText: 'Replace', cancelText: 'Keep Both'
        });
        if (!choice) {
          const stem = stemOf(file.name), ext = extOf(file.name);
          let counter = 1;
          while (true) {
            targetName = `${stem} copy ${counter}${ext}`;
            try { await this.dirHandle.getFileHandle(targetName); counter++; } catch { break; }
          }
        }
      }
      const newHandle = await this.dirHandle.getFileHandle(targetName, { create: true });
      const buffer = await file.arrayBuffer();
      const writable = await newHandle.createWritable();
      await writable.write(buffer);
      await writable.close();
      const newFile = await newHandle.getFile();
      const entry = { name: targetName, handle: newHandle, file: newFile, meta: null };
      entry.meta = await extractMeta(entry);
      const existing = this.loadedFiles.findIndex(f => f.name === targetName);
      if (existing >= 0) this.loadedFiles[existing] = entry;
      else this.loadedFiles.push(entry);
    }
    this.handleSortChange(document.getElementById('combo-sort').value);
    this.triggerPreview();
  }

  // ─── Sort ───────────────────────────────────────────────────────
  handleSortChange(method) {
    this.engine.setFiles([...this.loadedFiles]);
    this.engine.sortFiles(method);
    this.loadedFiles = [...this.engine.files];
    this.triggerPreview();
  }

  // ─── Preview Pane ───────────────────────────────────────────────
  _getSelectedEntry() {
    const sel = document.querySelector('#file-table-body tr.selected');
    if (!sel) return null;
    return this.loadedFiles[parseInt(sel.dataset.idx)] || null;
  }

  _updatePreviewPane() {
    const entry = this._getSelectedEntry();
    const icon = document.getElementById('preview-icon');
    const title = document.getElementById('preview-title');
    const subtitle = document.getElementById('preview-subtitle');
    const created = document.getElementById('preview-created');
    const modified = document.getElementById('preview-modified');
    const size = document.getElementById('preview-size');
    const kind = document.getElementById('preview-kind');

    if (!entry) {
      icon.textContent = '📁';
      title.textContent = 'No Selection';
      subtitle.textContent = 'Select a file to see info';
      created.textContent = 'Created  --';
      modified.textContent = 'Modified  --';
      size.textContent = 'Size  --';
      kind.textContent = 'Kind  --';
      return;
    }

    const meta = entry.meta || {};
    const sizeStr = formatSize(meta.sizeBytes || entry.file?.size || 0);
    icon.textContent = getFileEmoji(entry.name);
    title.textContent = entry.name;
    subtitle.textContent = `${meta.type || 'File'} — ${sizeStr}`;
    created.textContent  = `Created      ${meta.created || '--'}`;
    modified.textContent = `Modified     ${meta.modified || '--'}`;
    size.textContent     = `Size            ${sizeStr}`;
    kind.textContent     = `Kind            ${meta.type || 'File'}`;
  }

  togglePreview() {
    const pane = document.getElementById('preview-pane');
    const btn = document.getElementById('btn-toggle-preview');
    const hidden = pane.classList.toggle('hidden');
    btn.textContent = hidden ? 'Show Preview' : 'Hide Preview';
  }

  // ─── File Table ─────────────────────────────────────────────────
  triggerPreview() {
    this.engine.setFiles([...this.loadedFiles]);
    this.engine.setOperations(this.activeOperations.map(a => a.op));
    this.previewResults = this.engine.preview();

    const tbody = document.getElementById('file-table-body');
    tbody.innerHTML = '';
    this.previewResults.forEach(({ entry, newName }, idx) => {
      const meta = entry.meta || {};
      const changed = newName !== entry.name;
      const tr = document.createElement('tr');
      tr.dataset.idx = idx;
      tr.innerHTML = `
        <td class="${changed ? 'name-changed' : ''}">${escapeHtml(newName)}</td>
        <td>${meta.modified || '--'}</td>
        <td>${formatSize(meta.sizeBytes || entry.file?.size || 0)}</td>
        <td>${meta.type || 'File'}</td>
      `;
      tbody.appendChild(tr);
    });
    this.updateAllPreviews();
  }

  // ─── Live Preview Demo Entry ─────────────────────────────────────
  _getDemoEntry(fallbackName = 'Track01.mp3') {
    const rows = [...document.querySelectorAll('#file-table-body tr.selected')];
    if (rows.length) {
      const topIdx = Math.min(...rows.map(r => parseInt(r.dataset.idx)));
      const entry = this.loadedFiles[topIdx];
      if (entry) return entry;
    }
    if (this.loadedFiles.length) return this.loadedFiles[0];
    return { name: fallbackName, meta: {} };
  }

  // ─── Live Previews ───────────────────────────────────────────────
  updateAllPreviews() {
    this._updateCleanPreview();
    this._updateSmartUI();
    this._updateNormalPreview();
    this._updatePsPreview();
    this._updateNumPreview();
    this._updateMetaPreview();
  }

  _setPreviewText(id, original, result) {
    const el = document.getElementById(id);
    if (!el) return;
    const color = result !== original ? '#10b981' : '#a1a1bc';
    el.innerHTML = `Live Example: ${escapeHtml(original)} ➔ <span style="color:${color}">${escapeHtml(result)}</span>`;
  }

  _setPreviewError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<span style="color:#ff6b6b">⚠ ${escapeHtml(msg)}</span>`;
  }

  _updateCleanPreview() {
    const demo = this._getDemoEntry('  IMG__Vacation 2026!.jpg ');
    const op = new CleanOp({
      rmExtraSpaces: document.getElementById('chk-clean-spaces').checked,
      rmDupWords: document.getElementById('chk-clean-dups').checked,
      rmSpecial: document.getElementById('chk-clean-special').checked,
      rmNums: document.getElementById('chk-clean-nums').checked,
      rmLetters: document.getElementById('chk-clean-letters').checked,
      normalizeSep: document.getElementById('combo-clean-norm').value || null,
      casing: document.getElementById('combo-clean-case').value || null
    });
    const result = op.apply(demo.name, demo.name, 0, 1);
    this._setPreviewText('clean-preview', demo.name, result);
  }

  _updateSmartUI() {
    const fTxt = document.getElementById('combo-find').value;
    const aTxt = document.getElementById('combo-act').value;
    const isCharPos = fTxt === 'Character Position';

    document.getElementById('char-pos-group').classList.toggle('hidden', !isCharPos);
    document.getElementById('inp-find-custom').classList.toggle('hidden', isCharPos || !['Custom Exact','Custom Regex'].includes(fTxt));
    document.getElementById('inp-act-custom').classList.toggle('hidden', !isCharPos && !['Replace With','Insert Before','Insert After','Insert (Stem Only)','Insert (with Extension)'].includes(aTxt));
    if (isCharPos) document.getElementById('inp-act-custom').classList.remove('hidden');

    const demo = this._getDemoEntry('Photo.png');
    try {
      const op = new AdvancedReplaceOp({
        findType: fTxt, actionType: aTxt,
        findCustom: isCharPos ? document.getElementById('spin-char-pos').value : document.getElementById('inp-find-custom').value,
        replaceCustom: document.getElementById('inp-act-custom').value
      });
      const result = op.apply(demo.name, demo.name, 0, 1);
      this._setPreviewText('smart-preview', demo.name, result);
    } catch(e) {
      this._setPreviewError('smart-preview', e.message);
    }
  }

  _updateNormalPreview() {
    const demo = this._getDemoEntry('My Holiday Photo.jpg');
    const op = new NormalReplaceOp({
      findText: document.getElementById('inp-n-find').value,
      replaceText: document.getElementById('inp-n-rep').value,
      caseSensitive: document.getElementById('chk-n-case').checked
    });
    this._setPreviewText('normal-preview', demo.name, op.apply(demo.name, demo.name, 0, 1));
  }

  _updatePsPreview() {
    const demo = this._getDemoEntry('Document.pdf');
    const op = new PrefixSuffixOp({
      prefix: document.getElementById('inp-prefix').value,
      suffix: document.getElementById('inp-suffix').value
    });
    this._setPreviewText('ps-preview', demo.name, op.apply(demo.name, demo.name, 0, 1));
  }

  _updateNumPreview() {
    const demo = this._getDemoEntry('File.txt');
    const op = new NumberingOp({
      start: parseInt(document.getElementById('spin-start').value) || 1,
      padding: parseInt(document.getElementById('spin-pad').value) || 2,
      position: document.getElementById('radio-prefix').checked ? 'prefix' : 'suffix',
      baseName: document.getElementById('inp-num-base').value
    });
    this._setPreviewText('num-preview', demo.name, op.apply(demo.name, demo.name, 0, 1));
  }

  _updateMetaPreview() {
    const demo = this._getDemoEntry('Track01.mp3');
    const exts = this._currentMetaExtensions || ['*'];
    const op = new SmartMetadataOp({ template: document.getElementById('inp-template').value, targetExtensions: exts });
    try {
      const result = op.apply(demo.name, demo.name, 0, 1, demo.meta || {});
      this._setPreviewText('meta-preview', demo.name, result);
    } catch(e) {
      this._setPreviewError('meta-preview', e.message);
    }
  }

  _metaPresetChanged(txt) {
    const mapping = {
      'Audio / Songs':     ['{artist}_{album}_{track} - {title}', ['.mp3','.flac','.wav','.m4a','.aac']],
      'Images':            ['{original}_{camera}_{resolution}',   ['.jpg','.jpeg','.png','.tiff']],
      'Videos':            ['{original}_{resolution}_{codec}',    ['.mp4','.mov','.mkv','.avi']],
      'Movies':            ['{title} ({year}) {resolution}',      ['.mp4','.mov','.mkv','.avi']],
      'TV Shows':          ['{show} {season}{episode} - {title}', ['.mp4','.mkv']],
      'Podcasts':          ['{title} - E{track} - {year}',        ['.mp3','.aac']],
      'Books / PDFs':      ['{author} - {title} ({year})',        ['.pdf','.epub','.mobi']],
      'Scanned Documents': ['Scan_{original}_{created}',          ['.pdf','.tiff']],
      'All Files':         ['{original}_{modified}',              ['*']]
    };
    const [tpl, exts] = mapping[txt] || ['', ['*']];
    document.getElementById('inp-template').value = tpl;
    this._currentMetaExtensions = exts;
    this._updateMetaPreview();
  }

  // ─── Pipeline ───────────────────────────────────────────────────
  async addOperation() {
    const activeIdx = [...document.querySelectorAll('.nav-btn')].findIndex(b => b.classList.contains('active'));
    let op = null, desc = '';

    switch (activeIdx) {
      case 0: {
        op = new CleanOp({
          rmExtraSpaces: document.getElementById('chk-clean-spaces').checked,
          rmDupWords:    document.getElementById('chk-clean-dups').checked,
          rmSpecial:     document.getElementById('chk-clean-special').checked,
          rmNums:        document.getElementById('chk-clean-nums').checked,
          rmLetters:     document.getElementById('chk-clean-letters').checked,
          normalizeSep:  document.getElementById('combo-clean-norm').value || null,
          casing:        document.getElementById('combo-clean-case').value || null
        });
        desc = 'Enhanced Clean Pipeline';
        break;
      }
      case 1: {
        const fTxt = document.getElementById('combo-find').value;
        const aTxt = document.getElementById('combo-act').value;
        const isCharPos = fTxt === 'Character Position';
        if (isCharPos) {
          const pos = document.getElementById('spin-char-pos').value;
          const insertTxt = document.getElementById('inp-act-custom').value;
          const withExt = await showConfirm({
            icon: '🔤', title: 'Affect Extension?',
            message: 'Should the character position insert also affect the file extension?',
            okText: 'Yes (Full Name)', cancelText: 'No (Stem Only)'
          });
          op = new AdvancedReplaceOp({ findType: 'Character Position', actionType: withExt ? 'Insert (with Extension)' : 'Insert (Stem Only)', findCustom: pos, replaceCustom: insertTxt });
          desc = `Insert '${insertTxt}' at pos ${pos}`;
        } else {
          op = new AdvancedReplaceOp({ findType: fTxt, actionType: aTxt, findCustom: document.getElementById('inp-find-custom').value, replaceCustom: document.getElementById('inp-act-custom').value });
          desc = `Smart: ${aTxt} ${fTxt}`;
        }
        break;
      }
      case 2: {
        op = new NormalReplaceOp({ findText: document.getElementById('inp-n-find').value, replaceText: document.getElementById('inp-n-rep').value, caseSensitive: document.getElementById('chk-n-case').checked });
        desc = `Normal Replace ('${document.getElementById('inp-n-find').value}')`;
        break;
      }
      case 3: {
        const p = document.getElementById('inp-prefix').value, s = document.getElementById('inp-suffix').value;
        if (!p && !s) return;
        op = new PrefixSuffixOp({ prefix: p, suffix: s });
        desc = 'Prefix/Suffix';
        break;
      }
      case 4: {
        op = new NumberingOp({ start: parseInt(document.getElementById('spin-start').value)||1, padding: parseInt(document.getElementById('spin-pad').value)||2, position: document.getElementById('radio-prefix').checked ? 'prefix' : 'suffix', baseName: document.getElementById('inp-num-base').value });
        desc = 'Numbering';
        break;
      }
      case 5: {
        op = new SmartMetadataOp({ template: document.getElementById('inp-template').value, targetExtensions: this._currentMetaExtensions || ['*'] });
        desc = `Meta (${document.getElementById('combo-meta-preset').value})`;
        break;
      }
    }
    if (!op) return;
    this.activeOperations.push({ op, desc });
    const li = document.createElement('li');
    li.textContent = desc;
    document.getElementById('op-list').appendChild(li);
    this.triggerPreview();
  }

  removeOperation() {
    const list = document.getElementById('op-list');
    const selected = list.querySelector('li.selected');
    if (selected) {
      const idx = [...list.children].indexOf(selected);
      this.activeOperations.splice(idx, 1);
      selected.remove();
    } else if (list.lastChild) {
      this.activeOperations.pop();
      list.lastChild.remove();
    }
    this.triggerPreview();
  }

  // ─── Apply ──────────────────────────────────────────────────────
  async applyAction() {
    if (!this.loadedFiles.length) {
      await showModal({ icon: '📂', title: 'No Files Loaded', message: 'Please select a workspace folder first using the Directory button.' });
      return;
    }
    if (!this.activeOperations.length) {
      await showModal({ icon: '⚙️', title: 'Empty Pipeline', message: 'Please add at least one rename operation to the pipeline first.' });
      return;
    }
    if (!this.dirHandle) {
      await showModal({ icon: '📂', title: 'No Workspace', message: 'No workspace directory handle found. Please re-select the folder.' });
      return;
    }

    const selectedRows = [...document.querySelectorAll('#file-table-body tr.selected')];
    let targetResults = this.previewResults;

    if (selectedRows.length && selectedRows.length < this.loadedFiles.length) {
      const choice = await showConfirm({
        icon: '📋', title: 'Rename Selection?',
        message: `Rename only the ${selectedRows.length} selected file(s), or apply to all ${this.loadedFiles.length} files?`,
        okText: 'Selected Only', cancelText: 'All Files'
      });
      if (choice) {
        const indices = new Set(selectedRows.map(r => parseInt(r.dataset.idx)));
        targetResults = this.previewResults.filter((_, i) => indices.has(i));
      }
    } else {
      const go = await showConfirm({
        icon: '✏️', title: 'Confirm Rename',
        message: `This will rename all ${this.loadedFiles.length} file(s) in the workspace. This cannot be undone without using the Undo button.`,
        okText: 'Rename All', cancelText: 'Cancel', okClass: 'modal-btn-danger'
      });
      if (!go) return;
    }

    const { success, errors } = await this.engine.applyRenames(targetResults, this.dirHandle);
    this.loadedFiles = [...this.engine.files];

    const msg = `Successfully renamed ${success} file(s).${errors ? `\n${errors} file(s) failed.` : ''}`;
    await showModal({ icon: errors ? '⚠️' : '✅', title: errors ? 'Rename Finished with Errors' : 'Rename Complete', message: msg });

    this.activeOperations = [];
    document.getElementById('op-list').innerHTML = '';
    this.triggerPreview();
  }

  async undoAction() {
    if (!this.dirHandle) {
      await showModal({ icon: '📂', title: 'No Workspace', message: 'No workspace selected. Please pick a folder first.' });
      return;
    }
    const go = await showConfirm({
      icon: '↩️', title: 'Undo Last Rename',
      message: 'Revert all file renames from the last batch operation?',
      okText: 'Undo', cancelText: 'Cancel'
    });
    if (!go) return;
    const { success, errors } = await this.engine.undo(this.dirHandle);
    this.loadedFiles = [...this.engine.files];
    if (success === 0 && errors === 0) {
      await showModal({ icon: 'ℹ️', title: 'Nothing to Undo', message: 'There are no renames to revert.' });
    } else {
      await showModal({ icon: errors ? '⚠️' : '✅', title: 'Undo Complete', message: `Reverted ${success} file(s).${errors ? `\n${errors} failed.` : ''}` });
    }
    this.triggerPreview();
  }

  clearFiles() {
    this.loadedFiles = [];
    this.dirHandle = null;
    document.getElementById('lbl-workspace').textContent = 'No workspace selected';
    this.triggerPreview();
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ─── Bootstrap ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('op-list').addEventListener('click', e => {
    if (e.target.tagName === 'LI') {
      document.querySelectorAll('#op-list li').forEach(l => l.classList.remove('selected'));
      e.target.classList.add('selected');
    }
  });
  window._app = new SnapRenameApp();
});
