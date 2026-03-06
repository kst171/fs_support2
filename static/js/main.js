// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s, max-height 0.4s';
      el.style.opacity = '0';
      el.style.maxHeight = '0';
      el.style.padding = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
});
