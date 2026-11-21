// खबर संसार — interactions: category filter, nav links, install prompt, offline support
(function () {
  'use strict';

  // Base path derived from the manifest link (works on home + article pages).
  const manifestLink = document.querySelector('link[rel="manifest"]');
  const BASE = manifestLink
    ? manifestLink.getAttribute('href').replace(/manifest\.webmanifest$/, '')
    : '';

  const menuBtn = document.getElementById('menuBtn');
  const nav = document.getElementById('nav');
  const tabs = document.getElementById('tabs');
  const grid = document.getElementById('cardGrid');

  function closeMenu() {
    if (nav && nav.classList.contains('open')) nav.classList.remove('open');
  }

  if (menuBtn && nav) {
    menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      nav.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
      if (!nav.contains(e.target) && e.target !== menuBtn) closeMenu();
    });
  }

  // ---- Category filtering (shared by tabs and header nav) ----
  function setFilter(filter) {
    if (!tabs || !grid) return;
    tabs.querySelectorAll('.tab').forEach((t) => {
      t.classList.toggle('active', t.dataset.filter === filter);
    });
    grid.querySelectorAll('.card').forEach((card) => {
      card.style.display = (filter === 'सभी' || card.dataset.category === filter) ? '' : 'none';
    });
  }

  function scrollToTabs() {
    const target = document.getElementById('tabs') || document.querySelector('.section-head');
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  if (tabs && grid) {
    tabs.addEventListener('click', (e) => {
      const tab = e.target.closest('.tab');
      if (!tab) return;
      setFilter(tab.dataset.filter);
      history.replaceState(null, '', '?cat=' + encodeURIComponent(tab.dataset.filter) + '#tabs');
    });

    // Apply filter from URL on load (e.g. after clicking a nav link from an article).
    const cat = new URLSearchParams(location.search).get('cat');
    if (cat) {
      setFilter(cat);
      setTimeout(scrollToTabs, 120);
    }
  }

  // Header nav category links → filter + scroll to tabs.
  document.querySelectorAll('[data-cat]').forEach((link) => {
    link.addEventListener('click', (e) => {
      const cat = link.dataset.cat;
      closeMenu();
      if (tabs && grid) {
        e.preventDefault();
        setFilter(cat);
        scrollToTabs();
        history.replaceState(null, '', '?cat=' + encodeURIComponent(cat) + '#tabs');
      } else {
        // On article pages go back to home with the chosen category.
        e.preventDefault();
        location.href = BASE + 'index.html?cat=' + encodeURIComponent(cat) + '#tabs';
      }
    });
  });

  // ---- Install (PWA) ----
  const installBtn = document.getElementById('installBtn');
  const hint = document.getElementById('installHint');
  const hintText = document.getElementById('installHintText');
  const hintClose = document.getElementById('installHintClose');
  let deferredPrompt = null;

  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

  function showHint() {
    if (!hint) return;
    if (hintText) {
      hintText.textContent = isIOS
        ? 'ऐप लगाने के लिए शेयर बटन (□↑) दबाएँ → “Add to Home Screen” चुनें।'
        : 'ऐप लगाने के लिए ब्राउज़र मेन्यू (⋮) → “Add to Home screen” / “Install app” दबाएँ।';
    }
    hint.hidden = false;
    clearTimeout(showHint._t);
    showHint._t = setTimeout(hideHint, 9000);
  }
  function hideHint() {
    if (hint) hint.hidden = true;
  }

  if (hintClose) hintClose.addEventListener('click', hideHint);

  if (installBtn) {
    // Hide if already running as an installed app.
    if (window.matchMedia('(display-mode: standalone)').matches || navigator.standalone) {
      installBtn.style.display = 'none';
    }
    installBtn.addEventListener('click', async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        try { await deferredPrompt.userChoice; } catch (_) {}
        deferredPrompt = null;
      } else {
        showHint();
      }
    });
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
  });

  // ---- Offline / faster loads ----
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register(BASE + 'sw.js').catch(() => {});
    });
  }
})();
