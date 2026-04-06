// engine.js — Snap Rename Web Engine
// Mirrors engine.py logic exactly

class CleanOp {
  constructor({ rmExtraSpaces=false, rmDupWords=false, rmSpecial=false, rmNums=false, rmLetters=false, normalizeSep=null, casing=null } = {}) {
    this.rmExtraSpaces = rmExtraSpaces;
    this.rmDupWords = rmDupWords;
    this.rmSpecial = rmSpecial;
    this.rmNums = rmNums;
    this.rmLetters = rmLetters;
    this.normalizeSep = normalizeSep;
    this.casing = casing;
  }
  apply(originalName, currentName, index, total) {
    const ext = extOf(currentName);
    let base = stemOf(currentName);

    if (this.rmNums)    base = base.replace(/\d+/g, '');
    if (this.rmLetters) base = base.replace(/[a-zA-Z]+/g, '');
    if (this.rmSpecial) base = base.replace(/[^\w\s-]/g, '');

    // Strip extra spaces FIRST before normalizing
    if (this.rmExtraSpaces) {
      base = base.replace(/\s{2,}/g, ' ').trim();
      base = base.replace(/_{2,}/g, '_');
      base = base.replace(/-{2,}/g, '-');
    }

    if (this.normalizeSep === 'Underscores') base = base.replace(/[\s-]+/g, '_');
    else if (this.normalizeSep === 'Dashes')  base = base.replace(/[\s_]+/g, '-');
    else if (this.normalizeSep === 'Spaces')  base = base.replace(/[_-]+/g, ' ');

    if (this.rmDupWords) {
      const parts = base.split(/([\s_-]+)/);
      const seen = new Set();
      base = parts.filter(w => {
        if (/^\s*$/.test(w) || !/\w/.test(w)) return true;
        if (seen.has(w.toLowerCase())) return false;
        seen.add(w.toLowerCase()); return true;
      }).join('');
    }

    if (this.casing === 'Capitalize First Letters') base = base.replace(/\b\w/g, c=>c.toUpperCase());
    else if (this.casing === 'Uppercase') base = base.toUpperCase();
    else if (this.casing === 'Lowercase') base = base.toLowerCase();

    return base + ext;
  }
  describe() { return 'Enhanced Clean Pipeline'; }
}

class NormalReplaceOp {
  constructor({ findText='', replaceText='', caseSensitive=false } = {}) {
    this.findText = findText;
    this.replaceText = replaceText;
    this.caseSensitive = caseSensitive;
  }
  apply(originalName, currentName, index, total) {
    if (!this.findText) return currentName;
    const ext = extOf(currentName);
    let base = stemOf(currentName);
    const flags = this.caseSensitive ? 'g' : 'gi';
    base = base.replace(new RegExp(escapeRegex(this.findText), flags), this.replaceText);
    return base + ext;
  }
  describe() { return `Normal Replace ('${this.findText}')`; }
}

class AdvancedReplaceOp {
  constructor({ findType='Numbers', actionType='Remove', findCustom='', replaceCustom='' } = {}) {
    this.findType = findType;
    this.actionType = actionType;
    this.findCustom = findCustom;
    this.replaceCustom = replaceCustom;
  }
  apply(originalName, currentName, index, total) {
    const ext = extOf(currentName);
    let base = stemOf(currentName);

    // Character Position Insert
    if (this.findType === 'Character Position') {
      const pos = parseInt(this.findCustom);
      if (isNaN(pos)) return currentName;
      if (this.actionType === 'Insert (with Extension)') {
        if (pos < 1 || pos > currentName.length) throw new Error(`Position ${pos} is out of range for '${currentName}' (length ${currentName.length}).`);
        return currentName.slice(0, pos) + this.replaceCustom + currentName.slice(pos);
      } else {
        if (pos < 1 || pos > base.length) throw new Error(`Position ${pos} is out of range for stem '${base}' (length ${base.length}).`);
        return base.slice(0, pos) + this.replaceCustom + base.slice(pos) + ext;
      }
    }

    // File Extension
    if (this.findType === 'File Extension') {
      if (this.actionType === 'Remove') return base;
      if (this.actionType === 'Replace With') {
        const newExt = this.replaceCustom.startsWith('.') ? this.replaceCustom : '.' + this.replaceCustom;
        return base + newExt;
      }
      return currentName;
    }

    // Standardize actions
    if (this.actionType === 'Standardize' || this.findType === 'Swap Words') {
      if (this.findType === 'Capitalize First Letter') return base.charAt(0).toUpperCase() + base.slice(1) + ext;
      if (this.findType === 'Uppercase All Letters') return base.toUpperCase() + ext;
      if (this.findType === 'Lowercase All Letters') return base.toLowerCase() + ext;
      if (this.findType === 'Swap Words') {
        const swapped = base.replace(/^([^\s_-]+)([\s_-]+)([^\s_-]+)/, '$3$2$1');
        return swapped + ext;
      }
    }

    let pattern = null;
    switch (this.findType) {
      case 'Numbers':              pattern = /\d+/g; break;
      case 'Letters':              pattern = /[a-zA-Z]+/g; break;
      case 'Spaces':               pattern = / /g; break;
      case 'Special Characters':   pattern = /[^\w\s-]/g; break;
      case 'Dates':                pattern = /\d{4}[-_]?\d{2}[-_]?\d{2}|\d{8}/g; break;
      case 'Brackets / Parentheses': pattern = /\[.*?\]|\(.*?\)|<.*?>|\{.*?\}/g; break;
      case 'Consecutive Spaces':   pattern = / {2,}/g; break;
      case 'Underscores / Dashes': pattern = /[_-]+/g; break;
      case 'Non-ASCII Characters': pattern = /[^\x00-\x7F]+/g; break;
      case 'Leading/Trailing Spaces': pattern = /(^\s+|\s+$)/g; break;
      case 'Leading Numbers':      pattern = /^\d+[\s_-]*/g; break;
      case 'Trailing Numbers':     pattern = /[\s_-]*\d+$/g; break;
      case 'Leading/Trailing Underscores': pattern = /(^_+|_+$)/g; break;
      case 'Custom Regex':         try { pattern = new RegExp(this.findCustom, 'g'); } catch(e) { return currentName; } break;
      case 'Custom Exact':         pattern = new RegExp(escapeRegex(this.findCustom), 'g'); break;
    }

    if (!pattern) return currentName;
    try {
      if (this.actionType === 'Remove') base = base.replace(pattern, '');
      else if (this.actionType === 'Replace With') base = base.replace(pattern, this.replaceCustom);
      else if (this.actionType === 'Insert Before') base = base.replace(pattern, m => this.replaceCustom + m);
      else if (this.actionType === 'Insert After')  base = base.replace(pattern, m => m + this.replaceCustom);
      else if (this.actionType === 'Extract') { const m = base.match(pattern); base = m ? m.join('') : ''; }
      else if (this.actionType === 'Standardize') base = base.replace(pattern, '_');
    } catch(e) {}
    return base + ext;
  }
  describe() { return `Smart: ${this.actionType} ${this.findType}`; }
}

class PrefixSuffixOp {
  constructor({ prefix='', suffix='' } = {}) {
    this.prefix = prefix;
    this.suffix = suffix;
  }
  apply(originalName, currentName, index, total) {
    return this.prefix + stemOf(currentName) + this.suffix + extOf(currentName);
  }
  describe() { return `Prefix/Suffix`; }
}

class NumberingOp {
  constructor({ start=1, padding=2, separator='_', step=1, position='suffix', baseName='' } = {}) {
    this.start = start; this.padding = padding; this.separator = separator;
    this.step = step; this.position = position; this.baseName = baseName;
  }
  apply(originalName, currentName, index, total) {
    const ext = extOf(currentName);
    const base = this.baseName || stemOf(currentName);
    const num = String(this.start + index * this.step).padStart(this.padding, '0');
    return this.position === 'prefix'
      ? `${num}${this.separator}${base}${ext}`
      : `${base}${this.separator}${num}${ext}`;
  }
  describe() { return `Numbering (${this.position})`; }
}

class SmartMetadataOp {
  constructor({ template='', targetExtensions=[] } = {}) {
    this.template = template;
    this.targetExtensions = targetExtensions;
  }
  apply(originalName, currentName, index, total, meta={}) {
    if (!this.template) return currentName;
    const ext = extOf(originalName).toLowerCase();
    if (this.targetExtensions.length && !this.targetExtensions.includes('*') && !this.targetExtensions.includes(ext)) {
      return currentName;
    }
    const base = stemOf(currentName);
    const tags = {
      '{type}': meta.type || 'File',
      '{created}': meta.created || '',
      '{modified}': meta.modified || '',
      '{size_kb}': String(Math.floor((meta.sizeBytes || 0) / 1024)),
      '{exif_date}': meta.exif_date || meta.created || '',
      '{camera}': meta.camera || 'UnknownCamera',
      '{resolution}': meta.resolution || '1080p',
      '{artist}': meta.artist || 'UnknownArtist',
      '{album}': meta.album || 'UnknownAlbum',
      '{track}': meta.track || '00',
      '{title}': meta.title || base,
      '{year}': meta.year || '',
      '{genre}': meta.genre || 'UnknownGenre',
      '{duration}': meta.duration || '',
      '{codec}': meta.codec || 'h264',
      '{show}': meta.show || 'Show',
      '{season}': meta.season || 'S01',
      '{episode}': meta.episode || 'E01',
      '{author}': meta.author || 'UnknownAuthor',
      '{original}': base
    };
    let newBase = this.template;
    for (const [tag, val] of Object.entries(tags)) newBase = newBase.split(tag).join(val);
    newBase = newBase.replace(/\{[a-zA-Z_]+\}/g, '');
    newBase = newBase.replace(/_{2,}/g, '_').replace(/^_+|_+$/g, '');
    return newBase + ext;
  }
  describe() { return `Smart Metadata`; }
}

class RenameEngine {
  constructor() {
    this.files = [];          // Array of FileEntry {name, handle, file, meta}
    this.operations = [];
    this.undoHistory = [];    // Array of batches [{oldName, newHandle, dirHandle}]
  }

  setFiles(files) { this.files = files; }
  setOperations(ops) { this.operations = ops; }

  sortFiles(method) {
    switch (method) {
      case 'Alphabetical':  this.files.sort((a,b) => a.name.localeCompare(b.name)); break;
      case 'Date Added':
      case 'Date Modified': this.files.sort((a,b) => (b.file?.lastModified||0) - (a.file?.lastModified||0)); break;
      case 'Size':          this.files.sort((a,b) => (b.file?.size||0) - (a.file?.size||0)); break;
      case 'Extension':     this.files.sort((a,b) => extOf(a.name).localeCompare(extOf(b.name))); break;
    }
  }

  preview() {
    const results = [];
    const seen = new Set();
    this.files.forEach((entry, idx) => {
      let currentName = entry.name;
      for (const op of this.operations) {
        try {
          currentName = op.apply(entry.name, currentName, idx, this.files.length, entry.meta || {});
        } catch(e) {
          currentName = entry.name; break;
        }
      }
      let finalName = currentName;
      let counter = 1;
      let status = 'Ready';
      while (seen.has(finalName)) {
        status = 'Conflict Resolved';
        finalName = `${stemOf(currentName)}(${counter})${extOf(currentName)}`;
        counter++;
      }
      seen.add(finalName);
      results.push({ entry, newName: finalName, status });
    });
    return results;
  }

  async applyRenames(results, dirHandle) {
    const batch = [];
    let success = 0, errors = 0;
    for (const { entry, newName, status } of results) {
      if (entry.name === newName) continue;
      try {
        // Read old file contents
        const oldFile = await entry.handle.getFile();
        const buffer = await oldFile.arrayBuffer();
        // Write new file
        const newHandle = await dirHandle.getFileHandle(newName, { create: true });
        const writable = await newHandle.createWritable();
        await writable.write(buffer);
        await writable.close();
        // Delete old file
        await dirHandle.removeEntry(entry.name);
        batch.push({ oldName: entry.name, newName, handle: newHandle });
        entry.handle = newHandle;
        entry.name = newName;
        success++;
      } catch(e) {
        console.error('Rename error:', e);
        errors++;
      }
    }
    if (batch.length) this.undoHistory.push({ batch, dirHandle });
    return { success, errors };
  }

  async undo(dirHandle) {
    if (!this.undoHistory.length) return { success: 0, errors: 0 };
    const { batch } = this.undoHistory.pop();
    let success = 0, errors = 0;
    for (const { oldName, newName, handle } of [...batch].reverse()) {
      try {
        const newFile = await handle.getFile();
        const buffer = await newFile.arrayBuffer();
        const oldHandle = await dirHandle.getFileHandle(oldName, { create: true });
        const writable = await oldHandle.createWritable();
        await writable.write(buffer);
        await writable.close();
        await dirHandle.removeEntry(newName);
        // Update in-memory
        const fe = window.snapApp?.loadedFiles.find(f => f.name === newName);
        if (fe) { fe.handle = oldHandle; fe.name = oldName; }
        success++;
      } catch(e) { errors++; }
    }
    return { success, errors };
  }
}

// Helpers
function extOf(filename) {
  const idx = filename.lastIndexOf('.');
  return idx > 0 ? filename.slice(idx) : '';
}
function stemOf(filename) {
  const idx = filename.lastIndexOf('.');
  return idx > 0 ? filename.slice(0, idx) : filename;
}
function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
