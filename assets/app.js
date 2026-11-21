// छोटे इंटरैक्शन: मोबाइल मेन्यू, कैटेगरी फ़िल्टर, खोज
document.addEventListener('DOMContentLoaded', function () {
  const btn = document.getElementById('menuBtn');
  const nav = document.getElementById('nav');
  if (btn && nav) btn.addEventListener('click', () => nav.classList.toggle('open'));

  const tabs = document.getElementById('tabs');
  const grid = document.getElementById('cardGrid');
  if (tabs && grid) {
    tabs.addEventListener('click', function (e) {
      const tab = e.target.closest('.tab');
      if (!tab) return;
      tabs.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const filter = tab.dataset.filter;
      grid.querySelectorAll('.card').forEach(card => {
        card.style.display = (filter === 'सभी' || card.dataset.category === filter) ? '' : 'none';
      });
    });
  }
});
