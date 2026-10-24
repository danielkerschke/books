// Reading aids: a sticky bar showing the current section and progress,
// and a section navigator (dropdown on narrow screens, sidebar on wide ones).
(function () {
  var text = document.querySelector('.chapter-text');
  var contents = document.querySelector('.chapter-contents');
  if (!text || !contents) return;

  var head = document.querySelector('.chapter-head');
  var chapterNum = head.querySelector('.chapter-num').textContent;

  // Navigator: reuse the static in-chapter contents list.
  var side = document.createElement('nav');
  side.className = 'toc-side';
  side.id = 'toc-side';
  side.setAttribute('aria-label', 'Sections');
  side.innerHTML = '<p class="label"><a href="index.html">Being and Time</a> · ' + chapterNum + '</p>';
  side.appendChild(contents.querySelector('ol').cloneNode(true));
  var chapterNav = document.querySelector('.chapter-nav');
  if (chapterNav) {
    var links = document.createElement('div');
    links.className = 'chapter-links';
    links.innerHTML = chapterNav.innerHTML;
    side.appendChild(links);
  }

  var bar = document.createElement('div');
  bar.className = 'readbar';
  bar.innerHTML =
    '<div class="readbar-inner">' +
    '<button type="button" class="toggle" aria-controls="toc-side" aria-expanded="false">Sections</button>' +
    '<span class="where"></span>' +
    '</div><div class="progress"></div>';
  document.body.appendChild(bar);
  document.body.appendChild(side);

  var where = bar.querySelector('.where');
  var progress = bar.querySelector('.progress');
  var toggle = bar.querySelector('.toggle');
  var sideLinks = Array.prototype.slice.call(side.querySelectorAll('ol a'));
  var targets = sideLinks.map(function (a) {
    return document.getElementById(a.getAttribute('href').slice(1));
  });

  function setOpen(open) {
    side.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  }
  toggle.addEventListener('click', function () { setOpen(!side.classList.contains('open')); });
  side.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });

  var current = -1;
  function update() {
    var y = window.scrollY;
    var doc = document.documentElement;
    var max = doc.scrollHeight - window.innerHeight;
    progress.style.width = (max > 0 ? Math.min(100, (y / max) * 100) : 0) + '%';

    var showBar = head.getBoundingClientRect().bottom < 0;
    bar.classList.toggle('show', showBar);
    if (!showBar) setOpen(false);

    var idx = -1;
    for (var i = 0; i < targets.length; i++) {
      if (targets[i] && targets[i].getBoundingClientRect().top < 120) idx = i;
    }
    // At the very bottom the last heading may never reach the top; select it anyway.
    if (max > 0 && y >= max - 2) idx = targets.length - 1;
    if (idx !== current) {
      current = idx;
      sideLinks.forEach(function (a, i) { a.classList.toggle('active', i === idx); });
      var label = '';
      if (idx >= 0) {
        label = sideLinks[idx].innerHTML;
        // Subsections: prefix the parent § so the bar reads "§7 › B …"
        if (sideLinks[idx].parentNode.classList.contains('sub')) {
          for (var j = idx - 1; j >= 0; j--) {
            if (!sideLinks[j].parentNode.classList.contains('sub')) {
              label = sideLinks[j].querySelector('.num').outerHTML + '› ' + label;
              break;
            }
          }
        }
      }
      where.innerHTML = label;
      where.title = idx >= 0 ? sideLinks[idx].textContent : '';
    }
  }

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(function () { ticking = false; update(); }); }
  }, { passive: true });
  window.addEventListener('resize', update);
  update();
})();
