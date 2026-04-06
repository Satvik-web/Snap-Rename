/* utils.js — Snap Rename Web Utilities */

function formatSize(bytes) {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

function formatDate(ts) {
  if (!ts) return '--';
  const d = new Date(ts);
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

function getFileType(filename) {
  const ext = extOf(filename).toLowerCase();
  if (['.jpg','.jpeg','.png','.gif','.tiff','.webp','.svg'].includes(ext)) return 'Image';
  if (['.mp3','.wav','.flac','.m4a','.aac','.ogg'].includes(ext)) return 'Audio';
  if (['.mp4','.mkv','.mov','.avi','.webm'].includes(ext)) return 'Video';
  if (['.pdf','.epub','.mobi'].includes(ext)) return 'Book';
  if (['.doc','.docx','.txt','.md','.rtf'].includes(ext)) return 'Document';
  if (['.zip','.tar','.gz','.7z','.rar'].includes(ext)) return 'Archive';
  if (['.js','.ts','.py','.java','.cpp','.c','.html','.css','.json'].includes(ext)) return 'Code';
  return 'File';
}

function getFileEmoji(filename) {
  const type = getFileType(filename);
  const map = {
    'Image': '🖼️', 'Audio': '🎵', 'Video': '🎬', 'Book': '📖',
    'Document': '📄', 'Archive': '📦', 'Code': '💻', 'File': '📁'
  };
  return map[type] || '📁';
}

async function extractMeta(fileEntry) {
  const file = fileEntry.file;
  const meta = {
    type: getFileType(fileEntry.name),
    sizeBytes: file.size,
    created: formatDate(file.lastModified),  // browsers don't expose creation time
    modified: formatDate(file.lastModified),
    year: String(new Date(file.lastModified).getFullYear()),
    artist: 'UnknownArtist', album: 'UnknownAlbum', track: '00',
    title: stemOf(fileEntry.name), genre: 'UnknownGenre', duration: '',
    codec: 'h264', show: 'Show', season: 'S01', episode: 'E01',
    author: 'UnknownAuthor', camera: 'UnknownCamera', resolution: '1080p',
    exif_date: ''
  };

  // Try heuristic parsing from filename
  const base = stemOf(fileEntry.name);
  if (meta.type === 'Video') {
    const seMatch = base.match(/([A-Za-z\s]+)?[sS](\d{1,2})[eE](\d{1,2})/);
    if (seMatch) {
      meta.show = (seMatch[1] || 'ShowName').replace(/\./g, ' ').trim();
      meta.season = `S${seMatch[2].padStart(2,'0')}`;
      meta.episode = `E${seMatch[3].padStart(2,'0')}`;
    }
  }
  if (meta.type === 'Audio') {
    const parts = base.split('-').map(s => s.trim());
    if (parts.length >= 2) {
      if (/^\d+$/.test(parts[0])) {
        meta.track = parts[0].padStart(2,'0');
        meta.artist = parts[1];
        meta.title = parts[2] || base;
      } else {
        meta.artist = parts[0];
        meta.title = parts[1];
      }
    }
  }
  return meta;
}
