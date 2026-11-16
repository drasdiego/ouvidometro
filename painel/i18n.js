(function () {
  'use strict';
  var CHAVE = 'ouvidometro-idioma';
  var HTML_LANG = { pt: 'pt-BR', en: 'en' };
  var LOCALE = { pt: 'pt-BR', en: 'en-US' };
  var MESES = {
    pt: ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'],
    en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  };
  var dict = {
    'lang.grupo': { pt: 'Idioma', en: 'Language' },
  };
  var ouvintes = [];
  var faltando = [];
  var lang = 'pt';
  var pronto = false;

  function normaliza(v) {
    if (typeof v !== 'string') return null;
    v = v.trim().toLowerCase();
    if (v === 'pt' || v === 'pt-br') return 'pt';
    if (v === 'en' || v === 'en-us' || v === 'en-gb') return 'en';
    return null;
  }
  function daUrl() {
    try { return normaliza(new URLSearchParams(window.location.search).get('lang')); } catch (e) { return null; }
  }
  function salvo() {
    try { return normaliza(window.localStorage.getItem(CHAVE)); } catch (e) { return null; }
  }
  function guardar(l) {
    try { window.localStorage.setItem(CHAVE, l); } catch (e) {}
  }
  function atualizaUrl() {
    try {
      var u = new URL(window.location.href);
      u.searchParams.set('lang', lang);
      window.history.replaceState(window.history.state, '', u.toString());
    } catch (e) {}
  }

  lang = daUrl() || salvo() || 'pt';
  document.documentElement.setAttribute('lang', HTML_LANG[lang]);

  function t(chave) {
    var e = dict[chave];
    if (!e) { if (faltando.indexOf(chave) < 0) faltando.push(chave); return chave; }
    var v = e[lang];
    if (v === undefined) v = e.pt;
    if (typeof v === 'function') return v.apply(null, Array.prototype.slice.call(arguments, 1));
    return v;
  }
  function add(d) { for (var k in d) if (Object.prototype.hasOwnProperty.call(d, k)) dict[k] = d[k]; }

  function mes(m) {
    var n = +m.slice(5) - 1;
    return lang === 'en' ? MESES.en[n] + ' ' + m.slice(0, 4) : MESES.pt[n] + '/' + m.slice(0, 4);
  }
  function data(iso) {
    var p = iso.split('-');
    if (lang === 'en') {
      return new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])));
    }
    return p[2] + '/' + p[1] + '/' + p[0];
  }

  function comLang(href) {
    var h = href.split('#');
    var base = h[0].replace(/([?&])lang=[^&]*(&|$)/, function (m, a, b) { return b ? a : ''; }).replace(/[?&]$/, '');
    return base + (base.indexOf('?') >= 0 ? '&' : '?') + 'lang=' + lang + (h.length > 1 ? '#' + h.slice(1).join('#') : '');
  }

  function aplicar(raiz) {
    var r = raiz || document;
    document.documentElement.setAttribute('lang', HTML_LANG[lang]);
    r.querySelectorAll('[data-i18n]').forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
    r.querySelectorAll('[data-i18n-html]').forEach(function (el) { el.innerHTML = t(el.getAttribute('data-i18n-html')); });
    r.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (par) {
        var i = par.indexOf('=');
        if (i > 0) el.setAttribute(par.slice(0, i), t(par.slice(i + 1)));
      });
    });
    r.querySelectorAll('a[data-keep-lang]').forEach(function (a) {
      if (!a.dataset.href0) a.dataset.href0 = a.getAttribute('href');
      a.setAttribute('href', comLang(a.dataset.href0));
    });
    r.querySelectorAll('.lang').forEach(function (g) {
      g.setAttribute('aria-label', t('lang.grupo'));
      g.querySelectorAll('button[lang]').forEach(function (b) {
        var on = b.getAttribute('lang') === lang;
        b.classList.toggle('on', on);
        if (on) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
      });
    });
  }

  function definir(l) {
    l = normaliza(l);
    if (!l || l === lang) return;
    lang = l;
    guardar(l);
    atualizaUrl();
    aplicar();
    ouvintes.slice().forEach(function (fn) { try { fn(lang); } catch (e) { if (window.console) console.error(e); } });
  }

  function iniciar() {
    if (pronto) return;
    pronto = true;
    document.querySelectorAll('.lang button[lang]').forEach(function (b) {
      b.addEventListener('click', function () { definir(b.getAttribute('lang')); });
    });
    aplicar();
  }

  window.OuvI18n = {
    add: add,
    t: t,
    iniciar: iniciar,
    aplicar: aplicar,
    definir: definir,
    aoMudar: function (fn) { ouvintes.push(fn); },
    mes: mes,
    data: data,
    faltando: faltando,
    get lang() { return lang; },
    get locale() { return LOCALE[lang]; },
  };
})();
