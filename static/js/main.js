// Drag & drop, file name display, spinner overlay
document.addEventListener('DOMContentLoaded', () => {
  const dz = document.getElementById('dropzone');
  const input = document.getElementById('resume');
  const name = document.getElementById('file-name');
  const form = document.getElementById('upload-form');
  const overlay = document.getElementById('overlay');

  if (dz && input) {
    dz.addEventListener('click', () => input.click());
    ['dragenter','dragover'].forEach(ev =>
      dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('drag'); }));
    ['dragleave','drop'].forEach(ev =>
      dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('drag'); }));
    dz.addEventListener('drop', e => {
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        name.textContent = e.dataTransfer.files[0].name;
      }
    });
    input.addEventListener('change', () => {
      if (input.files[0]) name.textContent = input.files[0].name;
    });
  }

  if (form && overlay) {
    form.addEventListener('submit', (e) => {
      if (!input.files || !input.files[0]) {
        e.preventDefault();
        alert('Please upload a resume (PDF or DOCX).');
        return;
      }
      overlay.classList.add('show');
    });
  }
});
