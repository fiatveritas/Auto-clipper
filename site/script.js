/* Auto-Clipper landing — tiny vanilla JS */
(function () {
  'use strict';

  // Year in footer
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();

  // Mobile nav
  var nav = document.getElementById('nav');
  var burger = document.getElementById('navBurger');
  if (burger && nav) {
    burger.addEventListener('click', function () {
      var isOpen = nav.classList.toggle('open');
      burger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    // Close on link click (mobile)
    nav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (window.innerWidth <= 680) {
          nav.classList.remove('open');
          burger.setAttribute('aria-expanded', 'false');
        }
      });
    });
  }

  // Scroll reveal (only if IntersectionObserver + motion allowed)
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if ('IntersectionObserver' in window && !prefersReduced) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -60px 0px', threshold: 0.05 });
    document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll('.reveal').forEach(function (el) { el.classList.add('in'); });
  }

  // Bento hover spotlight (mouse x/y → CSS vars)
  document.querySelectorAll('.bento__item').forEach(function (card) {
    card.addEventListener('mousemove', function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty('--mx', ((e.clientX - r.left) / r.width) * 100 + '%');
      card.style.setProperty('--my', ((e.clientY - r.top) / r.height) * 100 + '%');
    });
  });

  // YOLO confidence counter — climbs synced with the 4s loop
  (function () {
    var conf = document.querySelector('.yolo__conf');
    if (!conf || prefersReduced) return;
    var start = parseInt(conf.getAttribute('data-start'), 10) || 60;
    var end = parseInt(conf.getAttribute('data-end'), 10) || 94;
    var LOOP_MS = 4000;
    // The enemy box is visible roughly from 22% to 96% of the loop.
    // Map that window to the counter climbing from start → end.
    var FROM = 0.22, TO = 0.60;
    function tick() {
      var t = (performance.now() % LOOP_MS) / LOOP_MS;
      var v;
      if (t < FROM) v = start;
      else if (t > TO) v = end;
      else v = Math.round(start + (end - start) * ((t - FROM) / (TO - FROM)));
      conf.textContent = v;
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  })();

  // Install v2 — OS tabs + autodetect
  (function () {
    var tabs = document.querySelectorAll('.install2__tab');
    var panels = document.querySelectorAll('.install2__panel');
    if (!tabs.length) return;

    function activate(os) {
      tabs.forEach(function (t) {
        t.classList.toggle('is-active', t.getAttribute('data-os') === os);
      });
      panels.forEach(function (p) {
        p.classList.toggle('is-active', p.getAttribute('data-panel') === os);
      });
    }

    // Autodetect platform
    var ua = (navigator.userAgent || '').toLowerCase();
    var plat = (navigator.platform || '').toLowerCase();
    var detected = 'mac';
    if (/win/.test(plat) || /windows/.test(ua)) detected = 'win';
    else if (/linux/.test(plat) || /linux/.test(ua)) detected = 'linux';
    else if (/mac/.test(plat) || /darwin/.test(ua) || /iphone|ipad/.test(ua)) detected = 'mac';
    activate(detected);

    tabs.forEach(function (t) {
      t.addEventListener('click', function () {
        activate(t.getAttribute('data-os'));
      });
    });

    // Highlight the detected-OS download card with a "recommended" badge
    var dlCards = document.querySelectorAll('.dl__card');
    dlCards.forEach(function (card) {
      if (card.getAttribute('data-os') === detected) {
        card.classList.add('dl__card--recommended');
      }
    });
  })();

  // Copy-to-clipboard for install snippets
  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var pre = btn.parentElement;
      // Clone pre and strip the copy button before extracting text
      var text = pre.innerText.replace(/^\s*Copy\s*/, '').trim();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(success, fallback);
      } else {
        fallback();
      }
      function success() {
        btn.classList.add('copied');
        var orig = btn.textContent;
        btn.textContent = 'Copied';
        setTimeout(function () {
          btn.classList.remove('copied');
          btn.textContent = orig;
        }, 1600);
      }
      function fallback() {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); success(); } catch (_) {}
        document.body.removeChild(ta);
      }
    });
  });
})();
