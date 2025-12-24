// menu
document.addEventListener('DOMContentLoaded', function () {
  const sidebar   = document.getElementById('sidebarNav');
  const openBtn   = document.getElementById('openSidebar');
  const closeBtn  = document.getElementById('closeSidebar');

  // --- Open Sidebar ---
  if (openBtn && sidebar) {
    openBtn.addEventListener('click', () => {
      sidebar.classList.add('active');
    });
  }

  // --- Close Sidebar ---
  if (closeBtn && sidebar) {
    closeBtn.addEventListener('click', () => {
      sidebar.classList.remove('active');
    });
  }

  // --- Dropdown Toggle ---
  document.querySelectorAll('.dropdown-toggle').forEach(title => {
    const content = title.nextElementSibling;

    if (!content || !content.classList.contains('dropdown-content')) return;

    // Initialize collapsed
    content.style.overflow = 'hidden';
    content.style.maxHeight = '0px';
    content.classList.remove('show');

    title.setAttribute('role', 'button');
    title.setAttribute('aria-expanded', 'false');
    title.style.userSelect = 'none';

    title.addEventListener('click', function () {
      const isOpen = title.classList.toggle('active');
      title.setAttribute('aria-expanded', String(isOpen));

      if (isOpen) {
        // open
        content.classList.add('show');
        content.style.maxHeight = content.scrollHeight + 'px';
      } else {
        // close
        content.style.maxHeight = '0px';
        content.addEventListener('transitionend', function handler () {
          if (content.style.maxHeight === '0px') {
            content.classList.remove('show');
          }
          content.removeEventListener('transitionend', handler);
        });
      }
    });

    // Optional: keyboard accessibility
    title.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        title.click();
      }
    });
  });
});

// ___________________________________________________________



