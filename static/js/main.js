// ── Auto-dismiss flash messages ──────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s, max-height 0.4s';
      el.style.opacity = '0';
      el.style.maxHeight = '0';
      el.style.padding = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  // Привязка change события к input
  const inputs = [
    { id: 'attachments',         preview: 'uploadPreview'  },
    { id: 'comment_attachments', preview: 'commentPreview' },
  ];
  inputs.forEach(({ id, preview }) => {
    const input = document.getElementById(id);
    if (input) {
      input.addEventListener('change', () => renderPreview(input, preview));
    }
  });
});

// ── Drag & drop ──────────────────────────────────────────
function handleDrop(event, inputId, previewId) {
  event.preventDefault();
  event.currentTarget.classList.remove('drag-over');
  const input = document.getElementById(inputId);
  if (!input) return;
  const dt = new DataTransfer();
  if (input.files) Array.from(input.files).forEach(f => dt.items.add(f));
  Array.from(event.dataTransfer.files).forEach(f => dt.items.add(f));
  input.files = dt.files;
  renderPreview(input, previewId);
}

// ── Рендер превью ────────────────────────────────────────
function renderPreview(input, previewId) {
  const preview = document.getElementById(previewId);
  if (!preview) return;
  preview.innerHTML = '';
  if (!input.files || input.files.length === 0) return;

  Array.from(input.files).forEach((f, i) => {
    const item = document.createElement('div');
    item.className = 'preview-item';

    if (f.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = e => {
        const img = document.createElement('img');
        img.className = 'preview-thumb';
        img.src = e.target.result;
        item.insertBefore(img, item.firstChild);
        const ph = item.querySelector('.preview-thumb-loading');
        if (ph) ph.remove();
      };
      reader.readAsDataURL(f);
      const ph = document.createElement('div');
      ph.className = 'preview-thumb-loading';
      ph.textContent = '🖼';
      item.appendChild(ph);
    } else {
      const icon = document.createElement('span');
      icon.className = 'preview-icon';
      const ext = f.name.split('.').pop().toLowerCase();
      const icons = { pdf:'📕', doc:'📘', docx:'📘', xls:'📗', xlsx:'📗', txt:'📄', log:'📄', csv:'⊞', json:'{}', xml:'</>', md:'M↓' };
      icon.textContent = icons[ext] || '📄';
      item.appendChild(icon);
    }

    const name = document.createElement('span');
    name.className = 'preview-name';
    name.title = f.name;
    name.textContent = f.name;
    item.appendChild(name);

    const size = document.createElement('span');
    size.className = 'preview-size';
    size.textContent = formatSize(f.size);
    item.appendChild(size);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'preview-remove';
    btn.textContent = '✕';
    btn.onclick = () => removeFile(input, i, previewId);
    item.appendChild(btn);

    preview.appendChild(item);
  });
}

// ── Удаление файла ───────────────────────────────────────
function removeFile(input, index, previewId) {
  const dt = new DataTransfer();
  Array.from(input.files)
    .filter((_, i) => i !== index)
    .forEach(f => dt.items.add(f));
  input.files = dt.files;
  renderPreview(input, previewId);
}

// ── Форматирование размера ───────────────────────────────
function formatSize(bytes) {
  if (bytes < 1024)        return bytes + ' Б';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' КБ';
  return (bytes / 1024 / 1024).toFixed(1) + ' МБ';
}