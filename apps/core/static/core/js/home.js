document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.menu-toggle');
  const menu = document.querySelector('#mobile-menu');

  if (toggle && menu) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      menu.hidden = expanded;
    });

    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        toggle.setAttribute('aria-expanded', 'false');
        menu.hidden = true;
      });
    });
  }

  document.querySelectorAll('.nav-dropdown-toggle').forEach((button) => {
    button.addEventListener('click', () => {
      const dropdown = button.closest('.nav-dropdown');
      const panel = dropdown.querySelector('.nav-dropdown-menu');
      const expanded = button.getAttribute('aria-expanded') === 'true';

      document.querySelectorAll('.nav-dropdown').forEach((item) => {
        item.querySelector('.nav-dropdown-toggle').setAttribute('aria-expanded', 'false');
        item.querySelector('.nav-dropdown-menu').hidden = true;
        item.classList.remove('is-open');
      });

      if (!expanded) {
        button.setAttribute('aria-expanded', 'true');
        panel.hidden = false;
        dropdown.classList.add('is-open');
      }
    });
  });
});
