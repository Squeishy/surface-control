/*
  Surface Control : interface de la tablette.
  ES5 only. The Surface RT runs Internet Explorer 11, so: no arrow functions, template
  literals, let/const, classes, Promise or fetch. XHR + string templates + event delegation.
*/
(function () {
  'use strict';

  var MONTHS = ['janv.', 'f\u00e9vr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'ao\u00fbt', 'sept.', 'oct.', 'nov.', 'd\u00e9c.'];
  var DASH = '\u2013';
  var DOT = ' \u00b7 ';
  var NB = '\u00a0';
  var MAX_KEYS = 18;
  var ORDER = ['home', 'unity', 'links', 'apps', 'tasks', 'settings'];
  var POWER_TEXT = {
    'system.sleep': 'Le PC va se mettre en veille. Cette tablette se reconnectera \u00e0 son r\u00e9veil.',
    'system.restart': 'Le PC va red\u00e9marrer dans 5 secondes. Le travail non enregistr\u00e9 peut \u00eatre perdu.',
    'system.shutdown': 'Le PC va s\u2019\u00e9teindre dans 5 secondes. Il faudra le rallumer \u00e0 la main.'
  };
  // Short names for the home deck, where space is tight.
  var SHORT = {
    'system.show_desktop': 'Bureau', 'system.task_view': 'Vue des t\u00e2ches', 'system.screenshot': 'Capture',
    'system.snip': 'Capture de zone', 'system.explorer': 'Explorateur', 'system.taskmgr': 'Gestionnaire',
    'system.settings': 'Param\u00e8tres', 'system.monitor_off': '\u00c9teindre \u00e9crans', 'system.abort': 'Annuler l\u2019arr\u00eat',
    'unity.play': 'Unity Play', 'unity.pause': 'Unity Pause', 'unity.step': 'Image suivante', 'unity.refresh': 'Actualiser Unity',
    'unity.save': 'Enregistrer', 'unity.undo': 'Annuler', 'unity.redo': 'R\u00e9tablir', 'unity.build_settings': 'Profils de build',
    'unity.build_run': 'Build & Run', 'unity.focus': 'Afficher Unity'
  };
  // Background presets: a base colour under four drifting colour blobs [x, y, colour].
  var BACKGROUNDS = {
    aurora: { name: 'Aurore', base: '#0b1430', blobs: [['12%', '18%', '#3b82f6'], ['88%', '10%', '#a855f7'], ['80%', '92%', '#ec4899'], ['14%', '92%', '#14b8a6']] },
    sunset: { name: 'Cr\u00e9puscule', base: '#2a0c2c', blobs: [['12%', '15%', '#ff6b6b'], ['88%', '12%', '#fbbf24'], ['82%', '90%', '#f43f8e'], ['15%', '88%', '#7c3aed']] },
    ocean: { name: 'Oc\u00e9an', base: '#03203a', blobs: [['14%', '14%', '#06b6d4'], ['86%', '22%', '#3b82f6'], ['45%', '100%', '#10b981'], ['92%', '92%', '#6366f1']] },
    grape: { name: 'Prune', base: '#1b0b33', blobs: [['18%', '18%', '#8b5cf6'], ['86%', '18%', '#ec4899'], ['72%', '92%', '#6366f1'], ['10%', '86%', '#d946ef']] },
    mint: { name: 'Menthe', base: '#04241f', blobs: [['14%', '18%', '#34d399'], ['86%', '14%', '#22d3ee'], ['80%', '88%', '#a3e635'], ['14%', '88%', '#0d9488']] },
    ember: { name: 'Braise', base: '#220a03', blobs: [['14%', '14%', '#f97316'], ['86%', '20%', '#ef4444'], ['76%', '92%', '#facc15'], ['14%', '86%', '#db2777']] },
    midnight: { name: 'Minuit', base: '#070b16', blobs: [['14%', '14%', '#1e3a8a'], ['86%', '20%', '#4338ca'], ['76%', '92%', '#0e7490'], ['18%', '88%', '#312e81']] }
  };
  var BG_ORDER = ['aurora', 'sunset', 'ocean', 'grape', 'mint', 'ember', 'midnight'];

  // ------------------------------------------------------------------ helpers

  function $(id) { return document.getElementById(id); }
  function now() { return new Date().getTime(); }
  function each(list, fn) { for (var i = 0; i < (list ? list.length : 0); i++) fn(list[i], i); }
  function findBy(list, key, value) {
    for (var i = 0; i < (list ? list.length : 0); i++) if (list[i][key] === value) return list[i];
    return null;
  }
  function indexOf(list, value) {
    for (var i = 0; i < list.length; i++) if (list[i] === value) return i;
    return -1;
  }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function icon(name, cls) {
    return '<svg class="ico' + (cls ? ' ' + cls : '') + '" focusable="false" aria-hidden="true"><use xlink:href="#i-' +
      name + '"></use></svg>';
  }
  function hasClass(el, c) { return (' ' + el.className + ' ').indexOf(' ' + c + ' ') > -1; }
  function addClass(el, c) { if (el && !hasClass(el, c)) el.className = el.className ? el.className + ' ' + c : c; }
  function removeClass(el, c) {
    if (!el) return;
    var s = ' ' + el.className + ' ';
    while (s.indexOf(' ' + c + ' ') > -1) s = s.replace(' ' + c + ' ', ' ');
    el.className = s.replace(/^\s+|\s+$/g, '');
  }
  function toggleClass(el, c, on) { if (on) addClass(el, c); else removeClass(el, c); }
  function withAttr(el, name) {
    if (el && el.correspondingUseElement) el = el.correspondingUseElement; // IE11 <use> event targets
    while (el && el.nodeType === 1) {
      if (el.getAttribute(name) !== null) return el;
      el = el.parentNode;
    }
    return null;
  }
  function setText(el, text) {
    if (el && el._t !== text) { el._t = text; el.textContent = text; }
  }
  function setHTML(el, html) {
    if (el && el._h !== html) { el._h = html; el.innerHTML = html; }
  }
  function setMeter(el, pct) {
    if (!el) return;
    el.firstChild.style.width = clamp(pct, 0, 100) + '%';
    toggleClass(el, 'is-crit', pct >= 95);
    toggleClass(el, 'is-warn', pct >= 85 && pct < 95);
  }
  function dec(n, digits) { return n.toFixed(digits).replace('.', ','); }
  function fmtBytes(n) {
    if (n == null) return DASH;
    var units = ['o', 'Ko', 'Mo', 'Go', 'To'];
    var i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return (n >= 100 || i === 0 ? Math.round(n) : dec(n, 1)) + NB + units[i];
  }
  function fmtRate(n) { return fmtBytes(n) + '/s'; }
  function pct(n) { return Math.round(n) + NB + '%'; }
  function fmtAgo(ts) {
    var s = Math.max(0, (now() + S.offset) / 1000 - ts);
    if (s < 60) return '\u00e0 l\u2019instant';
    if (s < 3600) return 'il y a ' + Math.floor(s / 60) + NB + 'min';
    if (s < 86400) return 'il y a ' + Math.floor(s / 3600) + NB + 'h';
    return 'il y a ' + Math.floor(s / 86400) + NB + 'j';
  }
  function fmtDay(ts) {
    var d = new Date((ts + S.tz) * 1000); // shown in the PC's time zone
    return d.getUTCDate() + ' ' + MONTHS[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
  }
  function shortCpu(name) {
    return String(name || '').replace(/\((R|TM)\)/gi, '').replace(/\s*CPU\s*@.*$/i, '')
      .replace(/\s+(\d+-Core\s+)?Processor\s*$/i, '').replace(/\s+/g, ' ');
  }
  function isWeb(target) { return /^https?:\/\//i.test(target || ''); }
  function isUri(target) { return /^[a-z][a-z0-9+.-]+:/i.test(target || ''); }
  function hexToRgba(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  function deviceName() {
    var ua = navigator.userAgent;
    if (/Windows NT 6\.[23]; ARM/.test(ua) || (/Trident/.test(ua) && /ARM/.test(ua))) return 'Surface RT';
    if (/iPad/.test(ua)) return 'iPad';
    if (/Android/.test(ua)) return 'Tablette Android';
    if (/Trident/.test(ua)) return 'Internet Explorer';
    if (/Edg\//.test(ua)) return 'Navigateur Edge';
    if (/Chrome\//.test(ua)) return 'Navigateur Chrome';
    if (/Firefox\//.test(ua)) return 'Navigateur Firefox';
    if (/Safari\//.test(ua)) return 'Navigateur Safari';
    return 'Navigateur';
  }

  var store = {
    get: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* private mode */ } },
    remove: function (k) { try { window.localStorage.removeItem(k); } catch (e) { /* private mode */ } }
  };

  // Per-device preferences (the theme itself lives on the PC and is shared).
  var DEFAULT_PREFS = { refresh: 2000, confirm: true, scale: 1 };
  function loadPrefs() {
    var p = {};
    try { p = JSON.parse(store.get('sc.prefs') || '{}') || {}; } catch (e) { p = {}; }
    for (var k in DEFAULT_PREFS) if (DEFAULT_PREFS.hasOwnProperty(k) && !p.hasOwnProperty(k)) p[k] = DEFAULT_PREFS[k];
    return p;
  }

  var S = {
    token: store.get('sc.token'),
    prefs: loadPrefs(),
    connected: false,
    everConnected: false,
    latency: 0,
    offset: 0,
    tz: -new Date().getTimezoneOffset() * 60, // replaced by the PC's UTC offset once connected
    rem: 16,
    info: null,
    config: null,
    state: null,
    page: null,
    pointerDown: false,
    badIcons: {},
    volHoldUntil: 0
  };
  function savePrefs() { store.set('sc.prefs', JSON.stringify(S.prefs)); }

  // The UI is designed for 1366x768 and scales (all sizes are rem) to the actual screen.
  function applyScale() {
    var w = window.innerWidth || document.documentElement.clientWidth;
    var h = window.innerHeight || document.documentElement.clientHeight;
    var fit = clamp(Math.min(w / 1366, h / 768), 0.55, 1.2);
    S.rem = Math.round(16 * fit * (S.prefs.scale || 1) * 100) / 100;
    document.documentElement.style.fontSize = S.rem + 'px';
  }

  // ---------------------------------------------------------------------- api

  function request(method, path, body, cb) {
    var xhr = new XMLHttpRequest();
    var started = now();
    xhr.open(method, path + (path.indexOf('?') < 0 ? '?' : '&') + '_=' + started, true);
    xhr.timeout = path === '/api/wallpaper' ? 120000 : 9000; // must be set after open() in IE11
    if (S.token) xhr.setRequestHeader('X-SC-Token', S.token);
    if (body) xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) return;
      var data = null;
      try { data = JSON.parse(xhr.responseText); } catch (e) { data = null; }
      var ms = now() - started;
      if (xhr.status >= 200 && xhr.status < 300) { if (cb) cb(null, data, ms); return; }
      var err = { status: xhr.status, message: (data && data.error) || (xhr.status ? 'Erreur ' + xhr.status : 'Le PC ne r\u00e9pond pas') };
      if (xhr.status === 401) needPairing();
      if (cb) cb(err, data, ms);
    };
    xhr.send(body ? JSON.stringify(body) : null);
  }
  function get(path, cb) { request('GET', path, null, cb); }
  function post(path, body, cb) { request('POST', path, body || {}, cb); }

  function tokenParam() { return S.token ? '&t=' + encodeURIComponent(S.token) : ''; }
  function img(url, fallback) {
    if (S.badIcons[url]) return icon(fallback);
    return '<img src="' + esc(url) + '" alt="" data-fallback="' + fallback + '">';
  }
  function appIcon(app, size) {
    return img('/api/icon?app=' + encodeURIComponent(app.id) + '&s=' + (size || 64) + tokenParam(), 'window');
  }
  function exeIcon(exe, fallback, size) {
    return exe ? img('/api/icon?exe=' + encodeURIComponent(exe) + '&s=' + (size || 64) + tokenParam(), fallback || 'window')
      : icon(fallback || 'window');
  }
  function linkGlyph(link) {
    if (isUri(link.target)) return 'globe';
    return /\.[a-z0-9]{1,5}$/i.test(link.target) ? 'file' : 'folder';
  }
  function linkIcon(link) {
    return isWeb(link.target) ? img('/api/linkicon?id=' + encodeURIComponent(link.id) + tokenParam(), 'globe') : icon(linkGlyph(link));
  }

  // -------------------------------------------------------------------- theme

  var Theme = {
    current: null,
    shown: null,
    blurData: null,
    init: function () {
      var st = document.documentElement.style;
      // ?noblur previews what IE11 (the Surface) renders: the pre-blurred fallback instead of backdrop-filter.
      Theme.backdrop = ('backdropFilter' in st || 'webkitBackdropFilter' in st) && !/[?&]noblur\b/.test(location.search);
      if (Theme.backdrop) addClass(document.documentElement, 'has-blur');
      var cached = null;
      try { cached = JSON.parse(store.get('sc.theme') || 'null'); } catch (e) { cached = null; }
      Theme.apply(cached || { bg: 'aurora', dim: 10, labels: true });
    },
    // Static CSS version of a preset, used for the swatches.
    gradient: function (key) {
      var def = BACKGROUNDS[key] || BACKGROUNDS.aurora, layers = [];
      each(def.blobs, function (b) {
        layers.push('radial-gradient(circle at ' + b[0] + ' ' + b[1] + ', ' + hexToRgba(b[2], 0.95) + ', ' + hexToRgba(b[2], 0) + ' 60%)');
      });
      return layers.join(', ') + ', ' + def.base;
    },
    wallpaperUrl: function (src, theme) {
      var v = theme && theme.versions ? theme.versions[src] : 0;
      return '/api/wallpaper?src=' + src + '&v=' + (v || 0) + tokenParam();
    },
    apply: function (theme) {
      Theme.current = theme;
      store.set('sc.theme', JSON.stringify({ bg: theme.bg, dim: theme.dim, labels: theme.labels, versions: theme.versions }));
      toggleClass($('root'), 'no-labels', theme.labels === false);
      Theme.setDim(theme.dim);
      var isImage = theme.bg === 'pc' || theme.bg === 'custom';
      var key = isImage ? theme.bg + ':' + ((theme.versions && theme.versions[theme.bg]) || 0) : theme.bg;
      if (Theme.shown === key) return;
      Theme.shown = key;
      Theme.paint($('bg-a'), theme.bg);
      Theme.blurData = null;
      Theme.glassCss();
      if (isImage && !Theme.backdrop) Theme.blurFrom(Theme.wallpaperUrl(theme.bg, theme));
    },
    paint: function (layer, bg) {
      if (bg === 'pc' || bg === 'custom') {
        layer.style.backgroundColor = '#0a0f1e';
        layer.innerHTML = '<div class="bg-img" style="background-image:url(' + esc(Theme.wallpaperUrl(bg, Theme.current)) + ')"></div>';
        return;
      }
      var def = BACKGROUNDS[bg] || BACKGROUNDS.aurora, html = '';
      layer.style.backgroundColor = def.base;
      each(def.blobs, function (b, i) {
        html += '<i class="blob b' + i + '" style="left:' + b[0] + ';top:' + b[1] + ';background:radial-gradient(circle closest-side, ' +
          hexToRgba(b[2], 0.9) + ', ' + hexToRgba(b[2], 0) + ')"></i>';
      });
      layer.innerHTML = html;
    },
    setDim: function (dim) {
      $('bg-dim').style.opacity = (dim || 0) / 100;
      if (Theme.current) Theme.current.dim = dim;
      if (Theme.blurData) Theme.glassCss();
    },
    // IE11 has no backdrop-filter: shrink the wallpaper to a few dozen pixels, blur that, and let
    // the browser stretch it back over every glass surface (fixed to the viewport).
    blurFrom: function (url) {
      var im = new Image();
      im.onload = function () {
        try {
          var w = im.naturalWidth || im.width, h = im.naturalHeight || im.height, source = im, canvas = null;
          while (w > 80 || !canvas) {
            w = Math.max(1, Math.round(w / 2));
            h = Math.max(1, Math.round(h / 2));
            canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            canvas.getContext('2d').drawImage(source, 0, 0, w, h);
            source = canvas;
          }
          Theme.boxBlur(canvas.getContext('2d'), w, h, 2, 3);
          Theme.blurData = canvas.toDataURL('image/png');
        } catch (e) {
          Theme.blurData = null;
        }
        Theme.glassCss();
      };
      im.src = url;
    },
    // Repeated horizontal + vertical box blurs approximate a gaussian; cheap on a ~80px image.
    boxBlur: function (ctx, w, h, radius, rounds) {
      var image = ctx.getImageData(0, 0, w, h), px = image.data, src = [], i, x, y, c, k, sum, n, xx, yy;
      for (var pass = 0; pass < rounds * 2; pass++) {
        var horizontal = pass % 2 === 0;
        for (i = 0; i < px.length; i++) src[i] = px[i];
        for (y = 0; y < h; y++) {
          for (x = 0; x < w; x++) {
            for (c = 0; c < 3; c++) {
              sum = 0;
              n = 0;
              for (k = -radius; k <= radius; k++) {
                xx = horizontal ? x + k : x;
                yy = horizontal ? y : y + k;
                if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
                sum += src[(yy * w + xx) * 4 + c];
                n++;
              }
              px[(y * w + x) * 4 + c] = Math.round(sum / n);
            }
          }
        }
      }
      ctx.putImageData(image, 0, 0);
    },
    glassCss: function () {
      var css = '';
      if (Theme.blurData && !Theme.backdrop) {
        var dim = 'rgba(0,0,0,' + ((Theme.current.dim || 0) / 100) + ')';
        css = '.glass{background-image:linear-gradient(rgba(255,255,255,.16),rgba(255,255,255,.16)),linear-gradient(' + dim + ',' + dim +
          '),url(' + Theme.blurData + ');background-attachment:scroll,fixed,fixed;background-size:auto,auto,cover;' +
          'background-position:0 0,0 0,center;background-repeat:no-repeat}';
      }
      $('theme-css').textContent = css;
    },
    save: function (changes, cb) {
      post('/api/theme', changes, function (err, theme) {
        if (err) { toast(err.message, 'err'); return; }
        S.config.theme = theme;
        Theme.apply(theme);
        if (cb) cb(theme);
      });
    }
  };

  // ------------------------------------------------------- toasts, modals

  function toast(message, kind, action) {
    var root = $('toasts');
    var el = document.createElement('div');
    el.className = 'toast glass-dark ' + (kind || 'ok');
    el.innerHTML = icon(kind === 'err' ? 'alert' : kind === 'info' ? 'bolt' : 'check') + '<span>' + esc(message) + '</span>' +
      (action ? '<div class="btn sm" data-act="toast-action">' + esc(action.label) + '</div>' : '');
    el._action = action;
    root.appendChild(el);
    while (root.childNodes.length > 3) root.removeChild(root.firstChild);
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, action ? 6000 : 3200);
  }

  var Modal = {
    cur: null,
    open: function (o) {
      Modal.close();
      var wrap = document.createElement('div');
      wrap.className = 'modal-wrap';
      var html = '<div class="modal glass-dark ' + (o.cls || '') + '"><div class="modal-h"><h3>' + esc(o.title) + '</h3>' +
        '<div class="btn sm icon-only" data-act="modal-close">' + icon('x') + '</div></div>' +
        '<div class="modal-b">' + (o.body || '') + '</div>';
      if (o.buttons && o.buttons.length) {
        html += '<div class="modal-f">';
        each(o.buttons, function (b, i) {
          html += '<div class="btn ' + (b.cls || '') + (b.left ? ' left' : '') + '" data-act="modal-btn" data-i="' + i + '">' +
            (b.icon ? icon(b.icon) : '') + esc(b.label) + '</div>';
        });
        html += '</div>';
      }
      wrap.innerHTML = html + '</div>';
      wrap.addEventListener('click', function (e) { if (e.target === wrap) Modal.close(); });
      $('modal-root').appendChild(wrap);
      Modal.cur = { el: wrap, o: o };
      if (o.onOpen) o.onOpen(wrap.firstChild);
    },
    close: function () {
      var c = Modal.cur;
      if (!c) return;
      Modal.cur = null;
      if (c.el.parentNode) c.el.parentNode.removeChild(c.el);
      if (c.o.onClose) c.o.onClose();
    },
    button: function (el) {
      if (!Modal.cur) return;
      var b = Modal.cur.o.buttons[+el.getAttribute('data-i')];
      if (b.act && b.act(Modal.cur.el.firstChild, el) === true) return; // handler keeps it open
      Modal.close();
    },
    val: function (name) {
      var input = Modal.cur && Modal.cur.el.querySelector('[name="' + name + '"]');
      return input ? input.value.replace(/^\s+|\s+$/g, '') : '';
    }
  };

  function confirmBox(title, text, okLabel, danger, onOk) {
    Modal.open({
      title: title, cls: 'narrow', body: '<p>' + esc(text) + '</p>',
      buttons: [{ label: 'Annuler' }, { label: okLabel, cls: danger ? 'danger' : 'primary', act: onOk }]
    });
  }

  function field(label, name, value, placeholder, hint) {
    return '<div class="field"><span class="label">' + esc(label) + '</span><input class="input" name="' + name +
      '" value="' + esc(value) + '" placeholder="' + esc(placeholder || '') + '" autocomplete="off" spellcheck="false">' +
      (hint ? '<div class="hint">' + esc(hint) + '</div>' : '') + '</div>';
  }

  // ------------------------------------------------------------ ui pieces

  function keyHtml(o) {
    return '<div class="key glass' + (o.label ? ' has-label' : '') + (o.cls ? ' ' + o.cls : '') + '" data-act="' + o.act + '"' +
      (o.attrs || '') + (o.title ? ' title="' + esc(o.title) + '"' : '') + '><span class="k-ico">' + o.ico + '</span>' +
      (o.label ? '<span class="k-label">' + esc(o.label) + '</span>' : '') + (o.extra || '') + '</div>';
  }
  function tool(act, ico, title, on) {
    return '<div class="tool glass' + (on ? ' on' : '') + '" data-act="' + act + '" title="' + esc(title) + '">' + icon(ico) + '</div>';
  }
  function seg(act, options, current) {
    var html = '<div class="seg glass">';
    each(options, function (o) {
      html += '<span' + (String(current) === String(o[0]) ? ' class="on"' : '') + ' data-act="' + act + '" data-v="' + o[0] + '">' + o[1] + '</span>';
    });
    return html + '</div>';
  }
  function switchHtml(act, on, key) {
    return '<div class="switch' + (on ? ' on' : '') + '" data-act="' + act + '"' + (key ? ' data-k="' + key + '"' : '') + '><i></i></div>';
  }
  function itemInner(k, sub, v) {
    return '<div class="k"><b>' + k + '</b>' + (sub ? '<span>' + sub + '</span>' : '') + '</div><div class="v">' + v + '</div>';
  }
  function item(k, sub, v) { return '<div class="item">' + itemInner(k, sub, v) + '</div>'; }
  // Running apps get a green outline, and a count badge when they have several windows.
  function paintRunning(root) {
    if (!root) return;
    var running = (S.state && S.state.apps) || {};
    each(root.querySelectorAll('[data-app]'), function (k) {
      var r = running[k.getAttribute('data-app')];
      toggleClass(k, 'is-running', !!r);
      var n = r ? r.windows : 0, badge = null;
      each(k.childNodes, function (c) { if (c.className === 'badge') badge = c; });
      if (n > 1) {
        if (!badge) { badge = document.createElement('span'); badge.className = 'badge'; k.appendChild(badge); }
        setText(badge, String(n));
      } else if (badge) {
        k.removeChild(badge);
      }
    });
  }

  // ---------------------------------------------------------------- commands

  function flash(el, ok) {
    if (!el) return;
    var c = ok ? 'flash-ok' : 'flash-err';
    addClass(el, c);
    setTimeout(function () { removeClass(el, c); }, 750);
  }

  // POST a command, give the pressed control feedback, refresh state right after.
  function exec(path, body, el, opts) {
    opts = opts || {};
    if (el) {
      if (hasClass(el, 'is-busy')) return;
      addClass(el, 'is-busy');
    }
    post(path, body, function (err, data) {
      if (el) { removeClass(el, 'is-busy'); flash(el, !err); }
      if (err) toast(err.message, 'err');
      else if (opts.toast) toast(typeof opts.toast === 'string' ? opts.toast : (data && data.message) || 'Fait', 'ok', opts.action);
      poll.soon();
      if (opts.done) opts.done(err, data);
    });
  }

  function resolveCommand(id) {
    if (!S.config) return null;
    if (id.indexOf('app:') === 0) {
      var app = findBy(S.config.apps, 'id', id.slice(4));
      return app ? { id: id, label: app.name, ico: appIcon(app, 128), appId: app.id, group: 'Applis' } : null;
    }
    if (id.indexOf('link:') === 0) {
      var link = findBy(S.config.links, 'id', id.slice(5));
      return link ? { id: id, label: link.name, ico: linkIcon(link), group: 'Liens', showLabel: true } : null;
    }
    var a = findBy(S.config.catalog, 'id', id);
    return a ? { id: id, label: SHORT[id] || a.label, full: a.label, ico: icon(a.icon), group: a.group, confirm: a.confirm, showLabel: true } : null;
  }

  function commandKey(cmd) {
    return keyHtml({
      act: 'cmd', attrs: ' data-id="' + esc(cmd.id) + '"' + (cmd.appId ? ' data-app="' + esc(cmd.appId) + '"' : ''),
      ico: cmd.ico, label: cmd.showLabel ? cmd.label : '', title: cmd.full || cmd.label
    });
  }

  function runCommand(id, el) {
    var cmd = resolveCommand(id);
    if (!cmd) return;
    var go = function () {
      var opts = {};
      if (id === 'system.restart' || id === 'system.shutdown') {
        opts = { toast: (cmd.full || cmd.label) + ' dans 5 secondes', action: { label: 'Annuler', id: 'system.abort' } };
      }
      exec('/api/action', { id: id }, el, opts);
    };
    if (cmd.confirm && S.prefs.confirm) confirmBox((cmd.full || cmd.label) + ' ?', POWER_TEXT[id] || 'Confirmer ?', cmd.full || cmd.label, true, go);
    else go();
  }

  // ----------------------------------------------------------- connection

  var poll = {
    timer: null,
    busy: false,
    fails: 0,
    schedule: function (ms) { clearTimeout(poll.timer); poll.timer = setTimeout(poll.tick, ms); },
    soon: function () { poll.schedule(150); },
    stop: function () { clearTimeout(poll.timer); },
    tick: function () {
      if (poll.busy) return;
      if (document.hidden) { poll.schedule(1500); return; }
      poll.busy = true;
      get('/api/state', function (err, data, ms) {
        poll.busy = false;
        if (err) {
          if (err.status === 401) return;
          poll.fails++;
          if (poll.fails >= 2) setConnected(false);
          poll.schedule(Math.min(5000, 1000 * poll.fails));
          return;
        }
        poll.fails = 0;
        setConnected(true, ms);
        applyState(data);
        poll.schedule(S.prefs.refresh);
      });
      var page = PAGES[S.page];
      if (page && page.mounted && page.poll && S.connected) page.poll();
    }
  };

  function renderStatus() {
    var el = $('status'), name = (S.info && S.info.name) || 'votre PC';
    if (S.connected) {
      el.className = 'status glass is-ok';
      setText($('status-text'), 'Connect\u00e9 \u00e0 ' + name);
    } else if (S.everConnected) {
      el.className = 'status glass is-off';
      setText($('status-text'), 'Reconnexion \u00e0 ' + name + '\u2026');
    } else {
      el.className = 'status glass is-wait';
      setText($('status-text'), 'Connexion \u00e0 ' + name + '\u2026');
    }
  }

  function setConnected(ok, ms) {
    var was = S.connected;
    S.connected = ok;
    if (ok) {
      S.latency = ms;
      if (!was && S.everConnected) toast('Reconnect\u00e9 \u00e0 ' + (S.info ? S.info.name : 'votre PC'), 'ok');
      S.everConnected = true;
    }
    renderStatus();
    if (Settings.mounted) Settings.renderConn();
  }

  function applyState(data) {
    S.state = data;
    S.offset = data.time * 1000 - now();
    S.tz = data.utc_offset;
    var running = 0;
    for (var k in data.apps) if (data.apps.hasOwnProperty(k)) running++;
    var count = $('nav-apps');
    setText(count, String(running));
    toggleClass(count, 'on', running > 0);
    toggleClass($('nav-unity'), 'on', !!(data.unity && data.unity.running));
    // Every page is laid out side by side, so neighbours stay fresh while swiping.
    for (var name in PAGES) {
      if (PAGES.hasOwnProperty(name) && PAGES[name].mounted && PAGES[name].update) PAGES[name].update(data);
    }
  }

  function loadConfig(cb) {
    get('/api/config', function (err, data) {
      if (err) {
        if (err.status !== 401) setTimeout(function () { loadConfig(cb); }, 2500);
        return;
      }
      S.config = data;
      Theme.apply(data.theme);
      each(ORDER, function (name) {
        var page = PAGES[name];
        if (!page.mounted) { page.mount($('page-' + name)); page.mounted = true; }
        else if (page.config) page.config();
      });
      if (cb) cb();
    });
  }

  function connect() {
    get('/api/ping', function (err, data) {
      if (err) {
        setConnected(false);
        setTimeout(connect, 2500);
        return;
      }
      S.info = data;
      renderStatus();
      setText($('pair-pc'), data.name);
      if (!data.paired) { Pair.show(data.pin_length); return; }
      Pair.hide();
      loadConfig(function () {
        route();
        poll.schedule(0);
      });
    });
  }

  function needPairing() {
    if (Pair.visible) return;
    poll.stop();
    S.token = null;
    store.remove('sc.token');
    Modal.close();
    Pair.show(S.info && S.info.pin_length);
  }

  // ------------------------------------------------------------------ pairing

  var Pair = {
    visible: false,
    pin: '',
    length: 6,
    busy: false,
    show: function (length) {
      Pair.length = length || 6;
      Pair.visible = true;
      Pair.pin = '';
      if (!$('keypad').firstChild) {
        var html = '';
        each(['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'del'], function (k) {
          if (!k) html += '<div class="pkey blank"></div>';
          else html += '<div class="pkey glass" data-act="key" data-k="' + k + '">' + (k === 'del' ? icon('backspace') : k) + '</div>';
        });
        $('keypad').innerHTML = html;
      }
      setText($('pin-error'), '');
      Pair.dots();
      addClass($('pair'), 'on');
    },
    hide: function () { Pair.visible = false; removeClass($('pair'), 'on'); },
    dots: function () {
      var html = '';
      for (var i = 0; i < Pair.length; i++) html += '<i' + (i < Pair.pin.length ? ' class="on"' : '') + '></i>';
      $('pin-dots').innerHTML = html;
    },
    press: function (k) {
      if (Pair.busy) return;
      if (k === 'del') Pair.pin = Pair.pin.slice(0, -1);
      else if (Pair.pin.length < Pair.length) Pair.pin += k;
      setText($('pin-error'), '');
      Pair.dots();
      if (Pair.pin.length === Pair.length) Pair.submit();
    },
    submit: function () {
      Pair.busy = true;
      post('/api/pair', { pin: Pair.pin, device: deviceName() }, function (err, data) {
        Pair.busy = false;
        if (err) {
          Pair.pin = '';
          Pair.dots();
          setText($('pin-error'), err.message);
          var dots = $('pin-dots');
          removeClass(dots, 'shake');
          setTimeout(function () { addClass(dots, 'shake'); }, 10);
          return;
        }
        S.token = data.token;
        store.set('sc.token', data.token);
        Pair.hide();
        connect();
      });
    }
  };

  // ------------------------------------------------------------ pager/router

  // Pages sit side by side in a horizontally snapping scroller: swipe, or tap the nav.
  var Pager = {
    index: -1,
    timer: null,
    init: function () {
      $('pager').addEventListener('scroll', function () {
        clearTimeout(Pager.timer);
        Pager.timer = setTimeout(Pager.settle, 130);
      });
    },
    // Real offsets rather than index x width, so a page that isn't exactly one screen wide can't drift.
    left: function (i) { return $('page-' + ORDER[i]).offsetLeft; },
    settle: function () {
      var x = $('pager').scrollLeft, best = 0;
      for (var i = 1; i < ORDER.length; i++) if (Math.abs(Pager.left(i) - x) < Math.abs(Pager.left(best) - x)) best = i;
      Pager.activate(best, true);
    },
    // A nav tap jumps straight to the page: animating six pages of glass is too heavy for the Surface.
    go: function (name) {
      var i = indexOf(ORDER, name);
      if (i < 0) i = 0;
      $('pager').scrollLeft = Pager.left(i);
      Pager.activate(i, false);
    },
    realign: function () {
      if (Pager.index >= 0) $('pager').scrollLeft = Pager.left(Pager.index);
    },
    activate: function (i, fromSwipe) {
      if (i === Pager.index) return;
      var prev = PAGES[S.page];
      if (prev && prev.leave) prev.leave();
      Pager.index = i;
      S.page = ORDER[i];
      each($('nav').getElementsByTagName('a'), function (a) { toggleClass(a, 'is-active', a.getAttribute('data-page') === S.page); });
      renderTools();
      var page = PAGES[S.page];
      if (page.enter) page.enter();
      if (S.state && page.update) page.update(S.state);
      if (fromSwipe && window.history && history.replaceState) history.replaceState(null, '', '#' + S.page);
    }
  };

  function route() {
    if (!S.config || Pair.visible) return;
    Pager.go((location.hash || '#home').slice(1));
  }

  function renderTools() {
    var page = PAGES[S.page];
    $('tools').innerHTML = (page && page.tools ? page.tools() : '') + tool('fullscreen', 'fullscreen', 'Plein \u00e9cran');
    if (page && page.afterTools) page.afterTools();
  }

  function toggleFullscreen() {
    var d = document, el = $('root');
    if (d.fullscreenElement || d.msFullscreenElement || d.webkitFullscreenElement) {
      (d.exitFullscreen || d.msExitFullscreen || d.webkitExitFullscreen).call(d);
      return;
    }
    var req = el.requestFullscreen || el.msRequestFullscreen || el.webkitRequestFullscreen;
    if (req) req.call(el);
    else toast('Ce navigateur ne peut pas passer en plein \u00e9cran.', 'info');
  }

  // ------------------------------------------------------------------ slider

  function Slider(el, onInput, onCommit) {
    var self = this;
    this.el = el;
    this.value = 0;
    this.dragging = false;
    this.fill = el.querySelector('.slider-fill');
    this.thumb = el.querySelector('.slider-thumb');
    function at(e) {
      var r = el.getBoundingClientRect();
      var x = e.touches ? e.touches[0].clientX : e.clientX;
      return clamp(Math.round((x - r.left) / r.width * 100), 0, 100);
    }
    function start(e) {
      self.dragging = true;
      addClass(el, 'is-dragging');
      if (e.pointerId !== undefined && el.setPointerCapture) { try { el.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ } }
      self.set(at(e));
      onInput(self.value);
      if (e.preventDefault) e.preventDefault();
    }
    function move(e) {
      if (!self.dragging) return;
      self.set(at(e));
      onInput(self.value);
      if (e.preventDefault) e.preventDefault();
    }
    function end() {
      if (!self.dragging) return;
      self.dragging = false;
      removeClass(el, 'is-dragging');
      onCommit(self.value);
    }
    if (window.PointerEvent) {
      el.addEventListener('pointerdown', start);
      el.addEventListener('pointermove', move);
      el.addEventListener('pointerup', end);
      el.addEventListener('pointercancel', end);
    } else if (window.navigator.msPointerEnabled) {
      el.addEventListener('MSPointerDown', start);
      el.addEventListener('MSPointerMove', move);
      el.addEventListener('MSPointerUp', end);
      el.addEventListener('MSPointerCancel', end);
    } else {
      el.addEventListener('mousedown', start);
      document.addEventListener('mousemove', move);
      document.addEventListener('mouseup', end);
      el.addEventListener('touchstart', start);
      el.addEventListener('touchmove', move);
      el.addEventListener('touchend', end);
    }
  }
  Slider.prototype.set = function (v) {
    this.value = v;
    this.fill.style.width = v + '%';
    this.thumb.style.left = v + '%';
  };

  function throttle(fn, ms) {
    var last = 0, timer = null, pending = null;
    return function (v) {
      pending = v;
      var wait = ms - (now() - last);
      if (wait <= 0) { last = now(); fn(v); }
      else if (!timer) timer = setTimeout(function () { timer = null; last = now(); fn(pending); }, wait);
    };
  }

  // ================================================================== HOME

  function fmtClock(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    var h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
    return (h ? h + ':' + (m < 10 ? '0' : '') : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  var Home = {
    media: null,
    seekHoldUntil: 0,
    tools: function () { return tool('edit-quick', 'edit', 'Modifier les boutons'); },
    mount: function (el) {
      addClass(el, 'fixed');
      function slider(id) {
        return '<div class="slider" id="' + id + '"><div class="slider-track"><div class="slider-fill"></div></div><div class="slider-thumb"></div></div>';
      }
      el.innerHTML = '<div id="h-wrap"><div class="keys deck" id="h-deck"></div></div>' +
        '<div class="media-dock glass" id="h-dock">' +
          '<div class="mbtn" data-act="cmd" data-id="media.prev" title="Précédent">' + icon('prev') + '</div>' +
          '<div class="mbtn mbtn-main" data-act="cmd" data-id="media.playpause" id="h-play" title="Lecture / Pause">' + icon('playpause') + '</div>' +
          '<div class="mbtn" data-act="cmd" data-id="media.next" title="Suivant">' + icon('next') + '</div>' +
          '<div class="media-sep"></div>' +
          '<div class="mid">' +
            // Something playing: its title and a progress bar you can drag to seek.
            '<div id="h-np" class="hidden"><div class="np-title" id="h-np-title"></div><div class="np-row">' +
              '<span class="np-t" id="h-np-pos">0:00</span>' + slider('h-seek') + '<span class="np-t end" id="h-np-dur">0:00</span></div></div>' +
            // Nothing playing: the volume slider.
            '<div id="h-volrow" class="np-row">' + slider('h-vol') + '</div>' +
          '</div>' +
          '<div class="vstep">' +
            '<div class="mbtn" data-act="vol-step" data-d="-5" title="Baisser le volume">' + icon('voldown') + '</div>' +
            '<div class="vol-val" id="h-vol-val">' + DASH + '</div>' +
            '<div class="mbtn" data-act="vol-step" data-d="5" title="Monter le volume">' + icon('volup') + '</div>' +
            '<div class="mbtn" data-act="mute" id="h-mute" title="Couper le son">' + icon('volume') + '</div>' +
          '</div>' +
        '</div>';
      var sendVolume = throttle(function (v) { post('/api/volume', { level: v }); }, 150);
      Home.slider = new Slider($('h-vol'), function (v) {
        S.volHoldUntil = now() + 1500;
        setText($('h-vol-val'), pct(v));
        sendVolume(v);
      }, function (v) {
        S.volHoldUntil = now() + 1500;
        post('/api/volume', { level: v, final: true }, function () { poll.soon(); });
      });
      Home.seek = new Slider($('h-seek'), function (v) {
        Home.seekHoldUntil = now() + 2500;
        if (Home.media) setText($('h-np-pos'), fmtClock(v / 100 * Home.media.duration));
      }, function (v) {
        var m = Home.media;
        if (!m) return;
        var target = v / 100 * m.duration;
        Home.seekHoldUntil = now() + 2500;
        post('/api/media/seek', { position: target }, function (err, data) {
          if (err) { toast(err.message, 'err'); return; }
          if (data && data.media) Home.setMedia(data.media);
        });
      });
      setInterval(Home.tick, 1000);
      Home.config();
    },
    config: function () {
      var html = '', items = S.config.quick_actions || [];
      each(items, function (id) {
        var cmd = resolveCommand(id);
        if (cmd) html += commandKey(cmd);
      });
      if (items.length < MAX_KEYS) html += '<div class="key add" data-act="edit-quick" title="Ajouter un bouton"><span class="k-ico">' + icon('plus') + '</span></div>';
      var deck = $('h-deck');
      deck.innerHTML = html;
      paintRunning(deck);
      Home.layout();
    },
    // Size the keys so the whole deck fits above the media dock: everything in a key is in em.
    layout: function () {
      var page = $('page-home'), deck = $('h-deck'), dock = $('h-dock');
      if (!deck || !page.clientWidth) return;
      var rem = S.rem;
      var n = deck.childNodes.length, cols = Math.max(1, Math.min(6, n)), rows = Math.ceil(n / cols);
      var W = page.clientWidth - 2 * rem, H = page.clientHeight - 0.5 * rem - dock.offsetHeight - 2.5 * rem;
      var unit = Math.floor(Math.min(W / (cols * 11), H / (rows * 11), 1.2 * rem) * 10) / 10;
      unit = Math.max(7, unit);
      deck.style.fontSize = unit + 'px';
      deck.style.width = cols * 11 * unit + 'px';
      $('h-wrap').style.paddingTop = Math.max(0, Math.floor((H - rows * 11 * unit) / 2)) + 'px';
      var width = Math.min(W, Math.max(50 * rem, Math.round(cols * 11 * unit - unit)));
      dock.style.width = width + 'px';
      dock.style.marginLeft = -Math.round(width / 2) + 'px';
    },
    update: function (s) {
      paintRunning($('h-deck'));
      if (s.volume && now() > S.volHoldUntil && !Home.slider.dragging) Home.showVolume(s.volume);
      Home.setMedia(s.media);
    },
    showVolume: function (v) {
      Home.slider.set(v.level);
      setText($('h-vol-val'), v.muted ? 'Muet' : pct(v.level));
      var mute = $('h-mute');
      toggleClass(mute, 'muted-on', v.muted);
      setHTML(mute, icon(v.muted ? 'mute' : 'volume'));
    },
    setMedia: function (m) {
      Home.media = m && m.duration > 0 ? m : null;
      toggleClass($('h-np'), 'hidden', !Home.media);
      toggleClass($('h-volrow'), 'hidden', !!Home.media);
      setHTML($('h-play'), icon(m ? (m.playing ? 'pause' : 'play') : 'playpause'));
      if (!Home.media) return;
      setHTML($('h-np-title'), esc(m.title || m.app) + (m.artist ? '<span>' + DOT + esc(m.artist) + '</span>' : ''));
      setText($('h-np-dur'), fmtClock(m.duration));
      toggleClass($('h-seek'), 'no-seek', !m.seekable);
      Home.tick();
    },
    // Moves the progress bar every second between two polls (the PC sends where it was and when).
    tick: function () {
      var m = Home.media;
      if (!m || S.page !== 'home' || Home.seek.dragging || now() < Home.seekHoldUntil) return;
      var pos = m.position + (m.playing ? Math.max(0, (now() + S.offset) / 1000 - m.at) : 0);
      pos = Math.min(pos, m.duration);
      Home.seek.set(pos / m.duration * 100);
      setText($('h-np-pos'), fmtClock(pos));
    }
  };

  var QuickEditor = {
    items: [],
    open: function () {
      QuickEditor.items = (S.config.quick_actions || []).slice(0, MAX_KEYS);
      Modal.open({
        title: 'Boutons de l\u2019accueil', cls: 'wide',
        body: '<div class="keys force-labels" id="qe-slots"></div><div class="pick-list" id="qe-list"></div>',
        buttons: [
          { label: 'Tout retirer', left: true, act: function () { QuickEditor.items = []; QuickEditor.render(); return true; } },
          { label: 'Annuler' },
          { label: 'Enregistrer', cls: 'primary', act: QuickEditor.save }
        ],
        onOpen: QuickEditor.render
      });
    },
    choices: function () {
      var groups = [], byGroup = {};
      function add(group, id) {
        if (!byGroup[group]) { byGroup[group] = []; groups.push(group); }
        byGroup[group].push(id);
      }
      each(S.config.apps, function (a) { add('Applis', 'app:' + a.id); });
      each(S.config.catalog, function (a) { add(a.group, a.id); });
      each(S.config.links, function (l) { add('Liens', 'link:' + l.id); });
      return { groups: groups, byGroup: byGroup };
    },
    render: function () {
      var slots = '';
      each(QuickEditor.items, function (id, i) {
        var cmd = resolveCommand(id);
        if (cmd) slots += keyHtml({ act: 'qe-remove', attrs: ' data-i="' + i + '"', ico: cmd.ico, label: cmd.label, title: 'Retirer' });
      });
      if (!slots) slots = '<div class="empty" style="width:100%;padding:1.125rem">Touchez des \u00e9l\u00e9ments ci-dessous pour les ajouter.</div>';
      $('qe-slots').innerHTML = slots;
      var c = QuickEditor.choices(), html = '';
      each(c.groups, function (g) {
        html += '<div class="pick-group">' + esc(g) + '</div>';
        each(c.byGroup[g], function (id) {
          var cmd = resolveCommand(id), on = indexOf(QuickEditor.items, id) > -1;
          html += '<div class="pick' + (on ? ' on' : '') + '" data-act="qe-toggle" data-id="' + esc(id) + '">' + cmd.ico +
            '<span>' + esc(cmd.full || cmd.label) + '</span>' + (on ? icon('check', 'check') : '') + '</div>';
        });
      });
      var list = $('qe-list'), top = list.scrollTop;
      list.innerHTML = html;
      list.scrollTop = top;
    },
    toggle: function (id) {
      var i = indexOf(QuickEditor.items, id);
      if (i > -1) QuickEditor.items.splice(i, 1);
      else if (QuickEditor.items.length >= MAX_KEYS) { toast('Les ' + MAX_KEYS + ' emplacements sont pris. Retirez-en un d\u2019abord.', 'info'); return; }
      else QuickEditor.items.push(id);
      QuickEditor.render();
    },
    save: function () {
      post('/api/quick_actions', { items: QuickEditor.items }, function (err, data) {
        if (err) { toast(err.message, 'err'); return; }
        S.config.quick_actions = data.quick_actions;
        Home.config();
      });
    }
  };

  // ================================================================= UNITY

  var UNITY_GROUPS = [
    ['Mode jeu', [['play', 'play', 'Play', 'solid'], ['pause', 'pause', 'Pause'], ['step', 'step', 'Image suivante']]],
    ['\u00c9dition', [['save', 'save', 'Enregistrer'], ['refresh', 'refresh', 'Actualiser'], ['undo', 'undo', 'Annuler'], ['redo', 'redo', 'R\u00e9tablir']]],
    ['Build', [['build_settings', 'hammer', 'Profils de build'], ['build_run', 'buildrun', 'Build & Run']]],
    ['Fen\u00eatres', [['focus', 'focus', 'Afficher l\u2019\u00e9diteur'], ['hub', 'apps', 'Unity Hub']]]
  ];

  var Unity = {
    tab: 'open',
    filter: 'all',
    data: null,
    log: null,
    logSince: '',
    clearedAt: 0,
    lastProjects: 0,
    lastLog: 0,
    openPath: null,
    tools: function () {
      return '<div class="chip-status glass" id="u-chip"><i class="dot"></i><span id="u-chip-text"></span></div>' +
        seg('u-tab', [['open', 'Ouvrir'], ['actions', 'Actions'], ['console', 'Console']], Unity.tab);
    },
    afterTools: function () { if (S.state) Unity.update(S.state); },
    mount: function (el) {
      var groups = '';
      each(UNITY_GROUPS, function (g) {
        var keys = '';
        each(g[1], function (a) {
          keys += a[0] === 'hub' ? keyHtml({ act: 'u-hub', ico: icon(a[1]), label: a[2] })
            : keyHtml({ act: 'u-cmd', attrs: ' data-cmd="' + a[0] + '"', ico: icon(a[1]), label: a[2], cls: 'needs-editor' + (a[3] ? ' ' + a[3] : '') });
        });
        groups += '<div class="group"><div class="group-h">' + g[0] + '</div><div class="keys force-labels">' + keys + '</div></div>';
      });
      el.innerHTML = '<div id="u-open"><div class="cards" id="u-cards"><div class="empty" style="width:100%">Chargement des projets\u2026</div></div></div>' +
        '<div id="u-actions" class="hidden"><div class="groups" id="u-groups">' + groups + '</div></div>' +
        '<div id="u-console" class="fill hidden"><div class="console glass"><div class="console-h" id="u-log-tools"></div>' +
        '<div class="console-body" id="u-log"></div></div></div>';
      Unity.showTab(Unity.tab);
      Unity.fetchProjects();
    },
    enter: function () { Unity.fetchProjects(); if (Unity.tab === 'console') Unity.fetchLog(true); },
    poll: function () {
      if (Unity.tab === 'console' && now() - Unity.lastLog > 2800) Unity.fetchLog();
      if (Unity.tab === 'open' && now() - Unity.lastProjects > 30000) Unity.fetchProjects();
    },
    update: function (s) {
      var u = s.unity;
      if (!u) return;
      var chip = $('u-chip');
      if (chip && S.page === 'unity') {
        toggleClass(chip, 'on', u.running);
        setText($('u-chip-text'), u.running ? u.project + (u.scene ? DOT + u.scene + (u.dirty ? '*' : '') : '')
          : u.starting ? 'Unity d\u00e9marre\u2026' : '\u00c9diteur ferm\u00e9');
      }
      each($('u-groups').querySelectorAll('.needs-editor'), function (k) { toggleClass(k, 'is-off', !u.running); });
      var openPath = u.running ? (u.path || '').toLowerCase() : '';
      if (Unity.openPath !== openPath) { Unity.openPath = openPath; Unity.renderProjects(); }
    },
    showTab: function (tab) {
      Unity.tab = tab;
      toggleClass($('u-open'), 'hidden', tab !== 'open');
      toggleClass($('u-actions'), 'hidden', tab !== 'actions');
      toggleClass($('u-console'), 'hidden', tab !== 'console');
      toggleClass($('page-unity'), 'fixed', tab === 'console');
      if (S.page === 'unity') renderTools();
      if (tab === 'console') { Unity.renderLogTools(); Unity.fetchLog(true); }
      if (tab === 'open') Unity.fetchProjects();
    },
    fetchProjects: function () {
      Unity.lastProjects = now();
      get('/api/unity', function (err, data) {
        if (err) return;
        Unity.data = data;
        Unity.renderProjects();
      });
    },
    renderProjects: function () {
      var d = Unity.data;
      if (!d || !$('u-cards')) return;
      if (!d.projects.length) {
        setHTML($('u-cards'), '<div class="empty" style="width:100%">' + icon('unity') + 'Aucun projet dans Unity Hub.</div>');
        return;
      }
      var html = '';
      each(d.projects, function (p, i) {
        var open = !!Unity.openPath && Unity.openPath === p.path.toLowerCase();
        html += '<div class="pcard glass' + (open ? ' is-running' : '') + '" data-act="u-open" data-i="' + i + '" title="' + esc(p.path) + '">' +
          '<span class="k-ico">' + exeIcon(p.exe, 'unity', 128) + '</span>' +
          '<div class="pcard-name">' + esc(p.name) + '</div>' +
          '<div class="pcard-ver' + (p.installed ? '' : ' warn') + '">' + esc(p.version || 'Version inconnue') + (p.installed ? '' : ' (non install\u00e9e)') + '</div>' +
          '<span class="pill">' + (open ? 'Afficher' : 'Ouvrir') + '</span></div>';
      });
      setHTML($('u-cards'), html);
    },
    renderLogTools: function () {
      var counts = { all: 0, error: 0, warning: 0 };
      each(Unity.visibleLines(), function (l) { counts.all++; if (counts[l.l] !== undefined) counts[l.l]++; });
      setHTML($('u-log-tools'), seg('u-filter', [['all', 'Tout<em>' + counts.all + '</em>'], ['error', 'Erreurs<em>' + counts.error + '</em>'],
        ['warning', 'Avertissements<em>' + counts.warning + '</em>']], Unity.filter) + '<div class="spacer"></div>' +
        '<div class="btn" data-act="u-clear">' + icon('trash') + 'Vider</div>');
    },
    visibleLines: function () {
      var lines = (Unity.log && Unity.log.lines) || [];
      return Unity.clearedAt ? lines.slice(Unity.clearedAt) : lines;
    },
    fetchLog: function (force) {
      Unity.lastLog = now();
      get('/api/unity/log?lines=400' + (force ? '' : '&since=' + encodeURIComponent(Unity.logSince)), function (err, data) {
        if (err || !data || data.unchanged) return;
        if (Unity.log && Unity.log.path !== data.path) Unity.clearedAt = 0;
        Unity.log = data;
        Unity.logSince = data.modified || '';
        Unity.renderLog();
      });
    },
    renderLog: function () {
      var box = $('u-log');
      if (!Unity.log || !box) return;
      var atBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 30;
      var html = '';
      each(Unity.visibleLines(), function (l) {
        if (Unity.filter === 'all' || l.l === Unity.filter) html += '<div class="log-line ' + l.l + '">' + esc(l.t) + '</div>';
      });
      if (!html) {
        html = '<div class="empty">' + icon('check') + (Unity.filter === 'all' ? 'Rien dans le journal.'
          : Unity.filter === 'error' ? 'Aucune erreur.' : 'Aucun avertissement.') + '</div>';
      }
      box.innerHTML = '<div class="log">' + html + '</div><div class="log-path">' + esc(Unity.log.path || 'Aucun Editor.log trouv\u00e9') + '</div>';
      if (atBottom || !box._seen) { box.scrollTop = box.scrollHeight; box._seen = true; }
      Unity.renderLogTools();
    },
    project: function (el) { return Unity.data && Unity.data.projects[+el.getAttribute('data-i')]; }
  };

  // ==================================================================== APPS

  var Apps = {
    editing: false,
    discovered: null,
    tools: function () { return tool('apps-edit', 'edit', 'Modifier les applis', Apps.editing); },
    mount: function (el) { el.innerHTML = '<div class="keys" id="a-keys"></div>'; Apps.config(); },
    config: function () {
      var html = '';
      each(S.config.apps, function (a) {
        html += keyHtml({
          act: 'app', attrs: ' data-id="' + esc(a.id) + '" data-app="' + esc(a.id) + '" data-hold="app-hold"',
          ico: appIcon(a, 128), label: Apps.editing ? a.name : '', title: a.name,
          cls: Apps.editing ? 'force-labels' : '', extra: Apps.editing ? '<span class="edit-mark">' + icon('edit') + '</span>' : ''
        });
      });
      html += '<div class="key add" data-act="app-add" title="Ajouter une appli"><span class="k-ico">' + icon('plus') + '</span></div>';
      var keys = $('a-keys');
      keys.innerHTML = html;
      paintRunning(keys);
    },
    update: function () { paintRunning($('a-keys')); },
    tap: function (el) {
      var app = findBy(S.config.apps, 'id', el.getAttribute('data-id'));
      if (!app) return;
      if (Apps.editing) Apps.edit(app);
      else exec('/api/apps/launch', { id: app.id }, el);
    },
    sheet: function (el) {
      var app = findBy(S.config.apps, 'id', el.getAttribute('data-id'));
      if (!app) return;
      var r = S.state && S.state.apps[app.id], items = [];
      if (r && r.windows) items.push(['focus', 'focus', 'Basculer']);
      items.push(['new', 'plus', r ? 'Nouvelle fen\u00eatre' : 'Lancer']);
      if (r && r.windows) items.push(['close', 'x', 'Fermer']);
      if (r) items.push(['kill', 'ban', 'Forcer l\u2019arr\u00eat']);
      items.push(['edit', 'edit', 'Modifier']);
      items.push(['remove', 'trash', 'Retirer']);
      var html = '<div class="keys force-labels">';
      each(items, function (it) {
        html += keyHtml({ act: 'app-sheet', attrs: ' data-op="' + it[0] + '" data-id="' + esc(app.id) + '"', ico: icon(it[1]), label: it[2] });
      });
      Modal.open({ title: app.name, body: html + '</div>' });
    },
    op: function (op, app) {
      Modal.close();
      if (op === 'focus') exec('/api/apps/launch', { id: app.id, mode: 'auto' });
      else if (op === 'new') exec('/api/apps/launch', { id: app.id, mode: 'new' }, null, { toast: true });
      else if (op === 'close') exec('/api/apps/close', { id: app.id }, null, { toast: true });
      else if (op === 'kill') {
        confirmBox('Forcer l\u2019arr\u00eat de ' + app.name + ' ?', 'Tous les processus ' + app.name + ' seront arr\u00eat\u00e9s imm\u00e9diatement. Le travail non enregistr\u00e9 sera perdu.',
          'Forcer l\u2019arr\u00eat', true, function () { exec('/api/apps/kill', { id: app.id }, null, { toast: true }); });
      } else if (op === 'edit') Apps.edit(app);
      else if (op === 'remove') Apps.remove(app);
    },
    remove: function (app) {
      confirmBox('Retirer ' + app.name + ' ?', 'Elle est seulement retir\u00e9e du tableau de bord, pas d\u00e9sinstall\u00e9e du PC.', 'Retirer', true, function () {
        post('/api/apps/delete', { id: app.id }, function (err) {
          if (err) { toast(err.message, 'err'); return; }
          loadConfig();
        });
      });
    },
    edit: function (app) {
      app = app || {};
      Modal.open({
        title: app.id ? app.name : 'Ajouter une appli par son chemin',
        body: field('Nom', 'name', app.name, 'ex. Blender') +
          field('Chemin sur le PC', 'path', app.path, 'C:\\Program Files\\App\\app.exe', 'Un .exe, un raccourci (.lnk) ou une URI comme steam://') +
          field('Arguments', 'args', app.args, 'Facultatif') +
          field('Nom du processus', 'process', app.process, 'ex. blender.exe', 'Sert \u00e0 savoir si l\u2019appli est ouverte. Rempli automatiquement depuis le chemin.'),
        buttons: (app.id ? [{ label: 'Retirer', cls: 'danger', icon: 'trash', left: true, act: function () { Apps.remove(app); return true; } }] : [])
          .concat([{ label: 'Annuler' }, { label: 'Enregistrer', cls: 'primary', act: function () {
            var body = { id: app.id, name: Modal.val('name'), path: Modal.val('path'), args: Modal.val('args'), process: Modal.val('process') };
            post('/api/apps/save', body, function (err) {
              if (err) { toast(err.message, 'err'); return; }
              Modal.close();
              loadConfig();
            });
            return true;
          } }])
      });
    },
    add: function () {
      Modal.open({
        title: 'Ajouter une appli', cls: 'wide',
        body: '<div style="display:flex;align-items:center"><div class="search" style="flex:1 1 0%;margin-left:0"><svg class="ico" focusable="false"><use xlink:href="#i-search"></use></svg>' +
          '<input class="input" id="ad-q" placeholder="Rechercher dans le menu D\u00e9marrer" autocomplete="off"></div>' +
          '<div class="btn" data-act="app-custom" style="margin-left:.625rem">' + icon('file') + 'Par chemin</div></div>' +
          '<div class="pick-list" id="ad-list"><div class="empty">Lecture du menu D\u00e9marrer\u2026</div></div>',
        onOpen: function () {
          var q = $('ad-q');
          var redraw = function () { Apps.renderDiscovered(q.value); };
          q.addEventListener('input', redraw);
          q.addEventListener('keyup', redraw);
          if (Apps.discovered) redraw();
          else get('/api/apps/discover', function (err, data) {
            if (err) { setHTML($('ad-list'), '<div class="empty">' + esc(err.message) + '</div>'); return; }
            Apps.discovered = data.items;
            redraw();
          });
        }
      });
    },
    renderDiscovered: function (query) {
      var list = $('ad-list');
      if (!list || !Apps.discovered) return;
      query = (query || '').toLowerCase();
      var html = '', shown = 0;
      each(Apps.discovered, function (item, i) {
        if (shown >= 150 || (query && item.name.toLowerCase().indexOf(query) < 0)) return;
        shown++;
        html += '<div class="pick" data-act="app-pick" data-i="' + i + '">' + icon('window') + '<span>' + esc(item.name) + '</span>' + icon('plus', 'check') + '</div>';
      });
      list.innerHTML = html || '<div class="empty">Aucun r\u00e9sultat. Utilisez \u00ab\u00a0Par chemin\u00a0\u00bb.</div>';
    },
    pick: function (el) {
      var item = Apps.discovered[+el.getAttribute('data-i')];
      if (!item || hasClass(el, 'is-busy')) return;
      addClass(el, 'is-busy');
      post('/api/apps/save', { name: item.name, path: item.path }, function (err) {
        removeClass(el, 'is-busy');
        if (err) { toast(err.message, 'err'); return; }
        Modal.close();
        loadConfig();
        toast(item.name + ' ajout\u00e9e', 'ok');
      });
    }
  };

  // =================================================================== LINKS

  var Links = {
    editing: false,
    tools: function () { return tool('links-edit', 'edit', 'Modifier les liens', Links.editing); },
    mount: function (el) { el.innerHTML = '<div class="keys" id="l-keys"></div>'; Links.config(); },
    config: function () {
      var html = '';
      each(S.config.links, function (l) {
        html += keyHtml({
          act: 'link', attrs: ' data-id="' + esc(l.id) + '" data-hold="link-hold"', ico: linkIcon(l), label: l.name, title: l.target,
          cls: 'force-labels', extra: Links.editing ? '<span class="edit-mark">' + icon('edit') + '</span>' : ''
        });
      });
      html += '<div class="key add" data-act="link-add" title="Ajouter un lien"><span class="k-ico">' + icon('plus') + '</span></div>';
      var keys = $('l-keys');
      keys.innerHTML = html;
    },
    tap: function (el) {
      var link = findBy(S.config.links, 'id', el.getAttribute('data-id'));
      if (!link) return;
      if (Links.editing) Links.edit(link);
      else exec('/api/links/open', { id: link.id }, el);
    },
    edit: function (link) {
      link = link || {};
      Modal.open({
        title: link.id ? link.name : 'Ajouter un lien',
        body: field('Nom', 'name', link.name, 'ex. Forum Unity') +
          field('Ouvre', 'target', link.target, 'https://\u2026 ou D:\\Projets', 'Une adresse web, un dossier ou un fichier du PC.'),
        buttons: (link.id ? [{ label: 'Retirer', cls: 'danger', icon: 'trash', left: true, act: function () {
          confirmBox('Retirer ' + link.name + ' ?', 'Le lien est retir\u00e9 du tableau de bord.', 'Retirer', true, function () {
            post('/api/links/delete', { id: link.id }, function (err) {
              if (err) { toast(err.message, 'err'); return; }
              loadConfig();
            });
          });
          return true;
        } }] : []).concat([{ label: 'Annuler' }, { label: 'Enregistrer', cls: 'primary', act: function () {
          var body = { id: link.id, name: Modal.val('name'), target: Modal.val('target'), group: link.group };
          post('/api/links/save', body, function (err) {
            if (err) { toast(err.message, 'err'); return; }
            Modal.close();
            loadConfig();
          });
          return true;
        } }])
      });
    }
  };

  // ============================================================ TASK MANAGER

  var Tasks = {
    filter: 'apps',
    sort: 'cpu',
    query: '',
    data: null,
    busy: false,
    last: 0,
    order: null,
    orderKey: null,
    touchedAt: 0,
    pending: false,
    tools: function () {
      return '<div class="search"><svg class="ico" focusable="false"><use xlink:href="#i-search"></use></svg>' +
        '<input class="input glass" id="t-search" placeholder="Rechercher" autocomplete="off" value="' + esc(Tasks.query) + '"></div>' +
        seg('t-filter', [['apps', 'Applis'], ['bg', 'Arri\u00e8re-plan'], ['all', 'Tout']], Tasks.filter);
    },
    afterTools: function () {
      var search = $('t-search');
      var onSearch = function () { if (Tasks.query !== search.value) { Tasks.query = search.value; Tasks.render(); } };
      search.addEventListener('input', onSearch);
      search.addEventListener('keyup', onSearch);
    },
    mount: function (el) {
      addClass(el, 'fixed');
      function pill(id, label, meter) {
        return '<div class="tm-pill glass"><b>' + label + '</b><span id="' + id + '">' + DASH + '</span>' +
          (meter ? '<span class="mini" id="' + id + '-m"><i></i></span>' : '') + '</div>';
      }
      function col(key, text, cls) { return '<th class="' + (cls || '') + '"' + (key ? ' data-act="t-sort" data-s="' + key + '"' : '') + '>' + text + '</th>'; }
      var cols = '<colgroup><col><col style="width:6.5rem"><col style="width:7.5rem"><col style="width:10.5rem"></colgroup>';
      el.innerHTML = '<div class="fill">' +
        '<div class="tm-strip">' + pill('t-cpu', 'CPU', true) + pill('t-ram', 'M\u00e9moire', true) + pill('t-disk', 'Disque', true) +
          pill('t-net', 'R\u00e9seau') + pill('t-procs', 'Processus') + '</div>' +
        '<div class="tm-table glass" id="t-table"><div class="tm-head"><table class="ptable">' + cols + '<thead><tr id="t-head">' +
          col('name', 'Nom') + col('cpu', 'Processeur', 'r') + col('mem', 'M\u00e9moire', 'r') + col('', 'Actions', 'r') +
          '</tr></thead></table></div><div class="tm-body" id="t-body"><div class="empty">Lecture des processus\u2026</div></div></div>' +
      '</div>';
      Tasks.cols = cols;
    },
    enter: function () { Tasks.fetch(); },
    poll: function () { if (now() - Tasks.last > 1900) Tasks.fetch(); },
    fetch: function () {
      if (Tasks.busy) return;
      Tasks.busy = true;
      Tasks.last = now();
      get('/api/processes', function (err, data) {
        Tasks.busy = false;
        if (err) return;
        if (!data.ready) { setTimeout(Tasks.fetch, 1200); return; }
        Tasks.data = data;
        Tasks.render();
      });
    },
    update: function (s) {
      setText($('t-cpu'), pct(s.cpu.percent));
      setMeter($('t-cpu-m'), s.cpu.percent);
      setText($('t-ram'), fmtBytes(s.ram.used) + ' / ' + fmtBytes(s.ram.total));
      setMeter($('t-ram-m'), s.ram.percent);
      var d = s.drives && s.drives[0];
      setText($('t-disk'), d ? d.mount + ' ' + pct(d.percent) : DASH);
      setMeter($('t-disk-m'), d ? d.percent : 0);
      setText($('t-net'), '\u2193 ' + fmtRate(s.net.down) + '  \u2191 ' + fmtRate(s.net.up));
      setText($('t-procs'), String(s.processes));
    },
    sorted: function () {
      var q = Tasks.query.toLowerCase(), out = [];
      each(Tasks.data.groups, function (g) {
        if (q && (g.display + ' ' + g.name + ' ' + g.title).toLowerCase().indexOf(q) < 0) return;
        out.push(g);
      });
      var key = Tasks.sort;
      // Rows must not jump under a finger: keep the previous order right after the list was
      // touched; values still update in place.
      var frozen = Tasks.order && Tasks.orderKey === key && now() - Tasks.touchedAt < 4000;
      out.sort(function (a, b) {
        if (frozen) {
          var ia = Tasks.order.hasOwnProperty(a.name) ? Tasks.order[a.name] : 1e6;
          var ib = Tasks.order.hasOwnProperty(b.name) ? Tasks.order[b.name] : 1e6;
          if (ia !== ib) return ia - ib;
        }
        if (key === 'name') return a.display.toLowerCase() < b.display.toLowerCase() ? -1 : 1;
        return (b[key] - a[key]) || (b.mem - a.mem);
      });
      if (!frozen) {
        Tasks.order = {};
        Tasks.orderKey = key;
        each(out, function (g, i) { Tasks.order[g.name] = i; });
      }
      return out;
    },
    render: function () {
      if (!Tasks.data) return;
      // Re-rendering under a finger would swallow the tap: wait for the release.
      if (S.pointerDown && S.page === 'tasks') { Tasks.pending = true; return; }
      Tasks.pending = false;
      each($('t-head').childNodes, function (th) { toggleClass(th, 'on', th.getAttribute('data-s') === Tasks.sort); });
      var total = S.state ? S.state.ram.total : 0;
      var groups = Tasks.sorted(), apps = [], bg = [];
      each(groups, function (g) { (g.app ? apps : bg).push(g); });
      var html = '';
      function ibtn(act, ico, title, g, cls) {
        return '<span class="ibtn' + (cls ? ' ' + cls : '') + '" data-act="' + act + '" data-name="' + esc(g.name) + '" data-label="' +
          esc(g.display) + '" data-count="' + g.count + '" title="' + esc(title) + '">' + icon(ico) + '</span>';
      }
      function rows(list) {
        each(list, function (g) {
          var cpuA = Math.min(0.32, g.cpu / 100 * 1.5), memA = total ? Math.min(0.32, g.mem / total * 1.2) : 0;
          var acts = g.app ? ibtn('t-focus', 'focus', 'Basculer', g) + ibtn('t-close', 'x', 'Fermer', g) : '';
          acts += g.protected ? '<span class="ibtn off" title="Processus prot\u00e9g\u00e9">' + icon('lock') + '</span>'
            : ibtn('t-end', 'ban', 'Terminer la t\u00e2che', g, 'danger');
          html += '<tr><td><div class="p-name"><div class="p-ico">' + exeIcon(g.exe, g.app ? 'window' : 'cpu') + '</div><div class="p-text">' +
            '<div class="p-title">' + esc(g.display) + (g.count > 1 ? '<em>(' + g.count + ')</em>' : '') + '</div>' +
            '<div class="p-sub">' + esc(g.app && g.title ? g.title : g.name) + '</div></div></div></td>' +
            '<td class="r heat" style="background:rgba(255,255,255,' + cpuA.toFixed(2) + ')">' + dec(g.cpu, 1) + NB + '%</td>' +
            '<td class="r heat" style="background:rgba(255,255,255,' + memA.toFixed(2) + ')">' + fmtBytes(g.mem) + '</td>' +
            '<td class="r acts">' + acts + '</td></tr>';
        });
      }
      function section(text, n) { html += '<tr class="sec"><td colspan="4">' + text + ' (' + n + ')</td></tr>'; }
      if (Tasks.filter !== 'bg' && apps.length) { if (Tasks.filter === 'all') section('Applis', apps.length); rows(apps); }
      if (Tasks.filter !== 'apps' && bg.length) { if (Tasks.filter === 'all') section('Processus en arri\u00e8re-plan', bg.length); rows(bg); }
      setHTML($('t-body'), html ? '<table class="ptable">' + Tasks.cols + '<tbody>' + html + '</tbody></table>'
        : '<div class="empty">' + icon('search') + (Tasks.query ? 'Aucun processus ne correspond \u00e0 \u00ab\u00a0' + esc(Tasks.query) + '\u00a0\u00bb.' : 'Rien \u00e0 afficher.') + '</div>');
    }
  };

  // ================================================================ SETTINGS

  var Settings = {
    security: null,
    mount: function (el) {
      function sec(ico, title, cls) { return '<div class="sec-h' + (cls ? ' ' + cls : '') + '">' + icon(ico) + title + '</div>'; }
      el.innerHTML = '<div class="settings">' +
        sec('image', 'Apparence') + '<div class="list glass">' +
          '<div class="item block"><div class="k"><b>Fond d\u2019\u00e9cran</b></div><div class="swatches" id="s-swatches"></div></div>' +
          '<div class="item"><div class="k"><b>Assombrir</b></div><div class="v wide"><div class="slider" id="s-dim"><div class="slider-track">' +
            '<div class="slider-fill"></div></div><div class="slider-thumb"></div></div></div></div>' +
          '<div class="item" id="s-scale"></div>' +
          '<div class="item" id="s-labels"></div>' +
        '</div>' +
        sec('tablet', 'Comportement') + '<div class="list glass" id="s-behaviour"></div>' +
        sec('monitor', 'Connexion') + '<div class="list glass" id="s-conn"></div>' +
        sec('shield', 'Zone sensible \u00b7 appairage', 'danger') + '<div class="list glass danger" id="s-sec"><div class="empty">Chargement\u2026</div></div>' +
        '</div><input type="file" accept="image/*" class="file-input" id="s-file">';
      Settings.dim = new Slider($('s-dim'), function (v) { Theme.setDim(Math.round(v * 0.7)); },
        function (v) { Theme.save({ dim: Math.round(v * 0.7) }); });
      $('s-file').addEventListener('change', function () {
        var file = this.files && this.files[0];
        this.value = '';
        Settings.upload(file);
      });
      Settings.mounted = true;
      Settings.config();
      Settings.renderBehaviour();
      Settings.renderConn();
    },
    enter: function () { Settings.loadSecurity(); },
    config: function () { Settings.renderLook(); },
    renderLook: function () {
      var t = S.config.theme, html = '';
      each(BG_ORDER, function (k) {
        html += '<div class="swatch' + (t.bg === k ? ' on' : '') + '" data-act="set-bg" data-v="' + k + '" style="background:' +
          Theme.gradient(k) + '"><span>' + BACKGROUNDS[k].name + '</span></div>';
      });
      if (t.versions && t.versions.pc) {
        html += '<div class="swatch' + (t.bg === 'pc' ? ' on' : '') + '" data-act="set-bg" data-v="pc" style="background-image:url(' +
          esc(Theme.wallpaperUrl('pc', t)) + ')"><span>Fond du PC</span></div>';
      }
      if (t.versions && t.versions.custom) {
        html += '<div class="swatch' + (t.bg === 'custom' ? ' on' : '') + '" data-act="set-bg" data-v="custom" style="background-image:url(' +
          esc(Theme.wallpaperUrl('custom', t)) + ')"><span>Mon image</span></div>';
      }
      html += '<div class="swatch upload" data-act="upload-bg">' + icon('upload') + '<span>Importer</span></div>';
      setHTML($('s-swatches'), html);
      if (!Settings.dim.dragging) Settings.dim.set(Math.round((t.dim || 0) / 0.7));
      setHTML($('s-scale'), itemInner('Taille de l\u2019interface', 'S\u2019ajoute \u00e0 l\u2019adaptation automatique \u00e0 l\u2019\u00e9cran',
        seg('set-scale', [[0.8, '80\u00a0%'], [0.9, '90\u00a0%'], [1, '100\u00a0%'], [1.1, '110\u00a0%'], [1.25, '125\u00a0%']], S.prefs.scale)));
      setHTML($('s-labels'), itemInner('Libell\u00e9s sous les boutons', 'Les applis n\u2019affichent que leur logo', switchHtml('set-labels', t.labels !== false)));
    },
    upload: function (file) {
      if (!file) return;
      if (!/^image\//.test(file.type || '')) { toast('Choisissez une image', 'err'); return; }
      toast('Import de ' + (file.name || 'l\u2019image') + '\u2026', 'info');
      var reader = new FileReader();
      reader.onload = function () {
        Settings.shrink(reader.result, function (dataUrl) {
          post('/api/wallpaper', { data: dataUrl }, function (err, theme) {
            if (err) { toast(err.message, 'err'); return; }
            S.config.theme = theme;
            Theme.apply(theme);
            Settings.renderLook();
            toast('Fond d\u2019\u00e9cran mis \u00e0 jour', 'ok');
          });
        });
      };
      reader.readAsDataURL(file);
    },
    // Big photos are scaled down on the tablet first: faster upload, lighter for the Surface to draw.
    shrink: function (dataUrl, cb) {
      var im = new Image();
      im.onload = function () {
        try {
          var scale = Math.min(1, 2560 / Math.max(im.width, im.height));
          if (scale >= 1 && dataUrl.length < 4000000) { cb(dataUrl); return; }
          var c = document.createElement('canvas');
          c.width = Math.round(im.width * scale);
          c.height = Math.round(im.height * scale);
          c.getContext('2d').drawImage(im, 0, 0, c.width, c.height);
          cb(c.toDataURL('image/jpeg', 0.88));
        } catch (e) {
          cb(dataUrl);
        }
      };
      im.onerror = function () { cb(dataUrl); };
      im.src = dataUrl;
    },
    renderBehaviour: function () {
      setHTML($('s-behaviour'),
        item('Actualisation', 'Plus lent \u00e9conomise la batterie de la tablette',
          seg('set-refresh', [[1000, 'Rapide'], [2000, 'Normale'], [5000, '\u00c9conomie']], S.prefs.refresh)) +
        item('Confirmer les actions d\u2019alimentation', 'Demander avant veille, red\u00e9marrage et arr\u00eat', switchHtml('set-pref', S.prefs.confirm, 'confirm')) +
        item('Plein \u00e9cran', null, '<div class="btn sm" data-act="fullscreen">' + icon('fullscreen') + 'Basculer</div>'));
    },
    renderConn: function () {
      if (!S.config) return;
      var pc = (S.state && S.state.pc) || S.config.pc;
      var addresses = [];
      each(S.config.addresses, function (a) { addresses.push('<span class="addr">' + esc(a.ip) + ':' + S.config.port + '</span>'); });
      setHTML($('s-conn'),
        item('\u00c9tat', null, S.connected ? 'Connect\u00e9' + DOT + S.latency + NB + 'ms' : 'Hors ligne') +
        item('PC', esc(pc.os), esc(pc.name)) +
        item('Processeur', null, esc(shortCpu(pc.cpu)) + DOT + esc(fmtBytes(pc.ram))) +
        item('Adresse', 'Ouvrez-la sur un autre appareil, puis saisissez le code', addresses.join('<br>')));
    },
    loadSecurity: function () {
      get('/api/security', function (err, data) {
        if (err) return;
        Settings.security = data;
        Settings.renderSecurity();
      });
    },
    renderSecurity: function () {
      var d = Settings.security, me = S.config.device || {};
      var html = item('Code PIN', d.pin ? 'Les nouveaux appareils saisissent ce code' : 'Affich\u00e9 dans la fen\u00eatre du serveur sur le PC',
        (d.pin ? '<span class="pin-big">' + esc(d.pin) + '</span> ' : '') + '<div class="btn sm" data-act="change-pin" style="margin-left:.625rem">Modifier</div>');
      each(d.devices, function (dev) {
        html += item(esc(dev.name) + (dev.current ? ' (cet appareil)' : ''),
          'Appair\u00e9 le ' + esc(fmtDay(dev.paired)) + DOT + 'vu ' + esc(fmtAgo(dev.seen)),
          dev.current ? '' : '<div class="btn sm danger" data-act="revoke" data-id="' + esc(dev.id) + '">R\u00e9voquer</div>');
      });
      html += item('<span class="danger-text">Dissocier cet appareil</span>',
        me.id ? 'Il faudra ressaisir le code PIN pour se reconnecter' : 'Ce PC est toujours autoris\u00e9 (acc\u00e8s local)',
        me.id ? '<div class="btn sm danger" data-act="unpair">Dissocier</div>' : '');
      setHTML($('s-sec'), html);
    },
    changePin: function () {
      Modal.open({
        title: 'Modifier le code PIN', cls: 'narrow',
        body: '<p>Les appareils d\u00e9j\u00e0 appair\u00e9s restent connect\u00e9s.</p><div style="height:.75rem"></div>' +
          '<input class="input" name="pin" type="tel" maxlength="8" placeholder="4 \u00e0 8 chiffres" autocomplete="off" style="font-size:1.375rem;letter-spacing:.2em">',
        buttons: [{ label: 'Annuler' }, { label: 'Enregistrer', cls: 'primary', act: function () {
          post('/api/security/pin', { pin: Modal.val('pin') }, function (err) {
            if (err) { toast(err.message, 'err'); return; }
            Modal.close();
            toast('Code PIN modifi\u00e9', 'ok');
            Settings.loadSecurity();
          });
          return true;
        } }]
      });
    }
  };

  var PAGES = { home: Home, unity: Unity, links: Links, apps: Apps, tasks: Tasks, settings: Settings };

  // ============================================================ interaction

  var ACTS = {
    'fullscreen': toggleFullscreen,
    'cmd': function (el) { runCommand(el.getAttribute('data-id'), el); },
    'toast-action': function (el) {
      var t = el.parentNode;
      if (t._action) exec('/api/action', { id: t._action.id }, null, { toast: 'Annul\u00e9' });
      if (t.parentNode) t.parentNode.removeChild(t);
    },
    'edit-quick': function () { QuickEditor.open(); },
    'qe-toggle': function (el) { QuickEditor.toggle(el.getAttribute('data-id')); },
    'qe-remove': function (el) { QuickEditor.items.splice(+el.getAttribute('data-i'), 1); QuickEditor.render(); },
    'vol-step': function (el) {
      post('/api/volume', { delta: +el.getAttribute('data-d') }, function (err, v) {
        flash(el, !err);
        if (err) { toast(err.message, 'err'); return; }
        S.volHoldUntil = now() + 1200;
        Home.showVolume(v);
      });
    },
    'mute': function (el) {
      var muted = S.state && S.state.volume && S.state.volume.muted;
      exec('/api/volume', { muted: !muted }, el);
    },
    'modal-close': function () { Modal.close(); },
    'modal-btn': function (el) { Modal.button(el); },
    'key': function (el) { Pair.press(el.getAttribute('data-k')); },

    'u-tab': function (el) { Unity.showTab(el.getAttribute('data-v')); },
    'u-cmd': function (el) { exec('/api/unity/command', { cmd: el.getAttribute('data-cmd') }, el); },
    'u-hub': function (el) { exec('/api/unity/hub', {}, el); },
    'u-filter': function (el) { Unity.filter = el.getAttribute('data-v'); Unity.renderLog(); },
    'u-clear': function () { Unity.clearedAt = Unity.log ? Unity.log.lines.length : 0; Unity.renderLog(); },
    'u-open': function (el) {
      var p = Unity.project(el);
      if (!p) return;
      if (Unity.openPath && Unity.openPath === p.path.toLowerCase()) exec('/api/unity/command', { cmd: 'focus' }, el);
      else exec('/api/unity/open', { path: p.path }, el, { toast: true });
    },

    'app': function (el) { Apps.tap(el); },
    'app-hold': function (el) { Apps.sheet(el); },
    'app-sheet': function (el) {
      var app = findBy(S.config.apps, 'id', el.getAttribute('data-id'));
      if (app) Apps.op(el.getAttribute('data-op'), app);
    },
    'app-add': function () { Apps.add(); },
    'app-custom': function () { Apps.edit(null); },
    'app-pick': function (el) { Apps.pick(el); },
    'apps-edit': function () { Apps.editing = !Apps.editing; Apps.config(); renderTools(); },

    'link': function (el) { Links.tap(el); },
    'link-hold': function (el) { var l = findBy(S.config.links, 'id', el.getAttribute('data-id')); if (l) Links.edit(l); },
    'link-add': function () { Links.edit(null); },
    'links-edit': function () { Links.editing = !Links.editing; Links.config(); renderTools(); },

    't-filter': function (el) { Tasks.filter = el.getAttribute('data-v'); renderTools(); Tasks.order = null; Tasks.render(); },
    't-sort': function (el) { Tasks.sort = el.getAttribute('data-s'); Tasks.order = null; Tasks.render(); },
    't-focus': function (el) { exec('/api/processes/focus', { name: el.getAttribute('data-name'), label: el.getAttribute('data-label') }, el); },
    't-close': function (el) { exec('/api/processes/close', { name: el.getAttribute('data-name'), label: el.getAttribute('data-label') }, el, { toast: true }); },
    't-end': function (el) {
      var name = el.getAttribute('data-name'), label = el.getAttribute('data-label'), count = +el.getAttribute('data-count');
      confirmBox('Terminer ' + label + ' ?', count > 1 ? 'Les ' + count + ' processus ' + name + ' seront arr\u00eat\u00e9s. Le travail non enregistr\u00e9 sera perdu.'
        : name + ' sera arr\u00eat\u00e9. Le travail non enregistr\u00e9 sera perdu.', 'Terminer', true, function () {
        exec('/api/processes/end', { name: name, label: label }, null, { toast: true, done: function (err) { if (!err) Tasks.fetch(); } });
      });
    },

    'set-bg': function (el) { Theme.save({ bg: el.getAttribute('data-v') }, Settings.renderLook); },
    'upload-bg': function () { $('s-file').click(); },
    'set-labels': function () { Theme.save({ labels: S.config.theme.labels === false }, Settings.renderLook); },
    'set-scale': function (el) {
      S.prefs.scale = +el.getAttribute('data-v');
      savePrefs();
      onResize();
      Settings.renderLook();
    },
    'set-refresh': function (el) {
      S.prefs.refresh = +el.getAttribute('data-v');
      savePrefs();
      Settings.renderBehaviour();
      poll.soon();
    },
    'set-pref': function (el) {
      var k = el.getAttribute('data-k');
      S.prefs[k] = !S.prefs[k];
      savePrefs();
      Settings.renderBehaviour();
    },
    'unpair': function () {
      confirmBox('Dissocier cet appareil ?', 'Il faudra le code PIN pour se reconnecter.', 'Dissocier', true, function () {
        post('/api/unpair', {}, function () { needPairing(); });
      });
    },
    'change-pin': function () { Settings.changePin(); },
    'revoke': function (el) {
      confirmBox('R\u00e9voquer cet appareil ?', 'Il devra ressaisir le code PIN pour se reconnecter.', 'R\u00e9voquer', true, function () {
        post('/api/security/revoke', { id: el.getAttribute('data-id') }, function (err) {
          if (err) toast(err.message, 'err');
          else Settings.loadSecurity();
        });
      });
    }
  };

  function onResize() {
    applyScale();
    Home.layout();
    Pager.realign();
  }

  function bindInput() {
    var pressed = null;
    // Long press (data-hold) opens an item's menu; the click that follows it is swallowed.
    var hold = { timer: null, fired: false, x: 0, y: 0 };
    function fireHold(el) {
      hold.timer = null;
      hold.fired = true;
      if (pressed) { removeClass(pressed, 'is-pressed'); pressed = null; }
      var fn = ACTS[el.getAttribute('data-hold')];
      if (fn) fn(el);
    }
    function cancelHold() { clearTimeout(hold.timer); hold.timer = null; }
    function down(e) {
      hold.fired = false;
      S.pointerDown = true;
      if (S.page === 'tasks') Tasks.touchedAt = now();
      var el = withAttr(e.target, 'data-act') || withAttr(e.target, 'data-page');
      if (!el) return;
      pressed = el;
      addClass(el, 'is-pressed');
      var holdEl = withAttr(e.target, 'data-hold');
      if (holdEl) {
        cancelHold();
        hold.x = e.clientX || 0;
        hold.y = e.clientY || 0;
        hold.timer = setTimeout(function () { fireHold(holdEl); }, 550);
      }
    }
    function move(e) {
      if (hold.timer && (Math.abs((e.clientX || 0) - hold.x) > 12 || Math.abs((e.clientY || 0) - hold.y) > 12)) cancelHold();
    }
    function up() {
      cancelHold();
      S.pointerDown = false;
      if (pressed) { removeClass(pressed, 'is-pressed'); pressed = null; }
      if (Tasks.pending) setTimeout(Tasks.render, 0);
    }
    if (window.PointerEvent) {
      document.addEventListener('pointerdown', down);
      document.addEventListener('pointermove', move);
      document.addEventListener('pointerup', up);
      document.addEventListener('pointercancel', up);
    } else if (window.navigator.msPointerEnabled) {
      document.addEventListener('MSPointerDown', down);
      document.addEventListener('MSPointerMove', move);
      document.addEventListener('MSPointerUp', up);
      document.addEventListener('MSPointerCancel', up);
    } else {
      document.addEventListener('touchstart', function (e) { down(e.touches[0] ? { target: e.target, clientX: e.touches[0].clientX, clientY: e.touches[0].clientY } : e); });
      document.addEventListener('touchend', up);
      document.addEventListener('mousedown', down);
      document.addEventListener('mouseup', up);
    }
    // Scrolling (including swiping between pages) shouldn't leave a button looking pressed.
    document.addEventListener('scroll', function () { cancelHold(); if (pressed) { removeClass(pressed, 'is-pressed'); pressed = null; } }, true);

    document.addEventListener('click', function (e) {
      if (hold.fired) { hold.fired = false; e.preventDefault(); return; }
      var el = withAttr(e.target, 'data-act');
      if (!el) return;
      var fn = ACTS[el.getAttribute('data-act')];
      if (fn) { e.preventDefault(); fn(el, e); }
    });
    // Touch press-and-hold and right-click both arrive here.
    document.addEventListener('contextmenu', function (e) {
      if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) return;
      e.preventDefault();
      var el = withAttr(e.target, 'data-hold');
      if (el && !hold.fired) { cancelHold(); fireHold(el); }
    });
    document.addEventListener('MSHoldVisual', function (e) { e.preventDefault(); });
    // Icons that fail to load fall back to a glyph (error events don't bubble, so capture).
    document.addEventListener('error', function (e) {
      var t = e.target;
      if (!t || t.tagName !== 'IMG' || !t.getAttribute('data-fallback')) return;
      S.badIcons[t.getAttribute('src')] = true;
      var span = document.createElement('span');
      span.innerHTML = icon(t.getAttribute('data-fallback'));
      if (t.parentNode) t.parentNode.replaceChild(span.firstChild, t);
    }, true);
    document.addEventListener('keydown', function (e) {
      if (e.keyCode === 27) Modal.close();
      if (Pair.visible && !Modal.cur) {
        if (e.keyCode >= 48 && e.keyCode <= 57) Pair.press(String(e.keyCode - 48));
        else if (e.keyCode >= 96 && e.keyCode <= 105) Pair.press(String(e.keyCode - 96));
        else if (e.keyCode === 8) { Pair.press('del'); e.preventDefault(); }
      }
    });
    window.addEventListener('hashchange', route);
    window.addEventListener('resize', onResize);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll.soon(); });
  }

  applyScale();
  Theme.init();
  Pager.init();
  bindInput();
  renderStatus();
  connect();
})();
