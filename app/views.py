from __future__ import annotations


LOGIN_PAGE = """
<!doctype html>
<html lang="en" data-theme="__DEFAULT_THEME__">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleMT Admin Login</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eef3f5;
      --panel: #ffffff;
      --ink: #17212b;
      --muted: #52616e;
      --line: #d7e0e6;
      --control: #ffffff;
      --accent: #147d78;
      --accent-dark: #0e5e5a;
      --danger: #b72d3a;
      --shadow: rgba(16, 31, 45, .12);
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #11181f;
      --panel: #18222b;
      --ink: #e8eef2;
      --muted: #a9b7c3;
      --line: #31414f;
      --control: #121b23;
      --accent: #35aaa2;
      --accent-dark: #69c9c2;
      --danger: #ff7883;
      --shadow: rgba(0, 0, 0, .34);
    }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: var(--bg); color: var(--ink); }
    .top-controls { position: fixed; top: 16px; right: 16px; display: flex; gap: 8px; align-items: center; }
    select { height: 34px; border: 1px solid var(--line); border-radius: 7px; background: var(--control); color: var(--ink); padding: 0 9px; font: inherit; }
    form { width: min(360px, calc(100vw - 32px)); background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 22px; box-shadow: 0 18px 48px var(--shadow); }
    h1 { margin: 0 0 18px; font-size: 24px; letter-spacing: 0; }
    label { display: block; margin: 0 0 6px; color: var(--muted); font-size: 13px; }
    input { width: 100%; height: 38px; border: 1px solid var(--line); border-radius: 7px; padding: 0 10px; font: inherit; box-sizing: border-box; background: var(--control); color: var(--ink); }
    .field { margin-bottom: 14px; }
    button { width: 100%; height: 40px; border: 1px solid var(--accent); border-radius: 7px; background: var(--accent); color: #fff; font: inherit; cursor: pointer; }
    button:hover { background: var(--accent-dark); }
    .error { margin-bottom: 12px; color: var(--danger); font-size: 13px; }
  </style>
</head>
<body>
  <div class="top-controls">
    <select id="loginLangSelect" title="Language">
      <option value="__DEFAULT_LANG__">__DEFAULT_LANG__</option>
    </select>
    <select id="loginThemeSelect" data-i18n-title="theme.theme" title="Theme">
      <option value="light" data-i18n="theme.light">Light</option>
      <option value="dark" data-i18n="theme.dark">Dark</option>
    </select>
  </div>
  <form method="post" action="login">
    <h1>TeleMT Admin</h1>
    {error}
    <div class="field"><label data-i18n="login.username">Username</label><input name="username" autocomplete="username" required autofocus></div>
    <div class="field"><label data-i18n="login.password">Password</label><input name="password" type="password" autocomplete="current-password" required></div>
    <button type="submit" data-i18n="login.signIn">Sign in</button>
  </form>
  <script>
    const defaultLang = "__DEFAULT_LANG__";
    const defaultTheme = "__DEFAULT_THEME__";
    const langSelect = document.getElementById("loginLangSelect");
    const themeSelect = document.getElementById("loginThemeSelect");
    let i18n = {};
    let locales = [];
    function t(key) { return i18n[key] || key; }
    function esc(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }
    async function loadLocales() {
      const res = await fetch("api/i18n", { credentials: "same-origin" });
      const data = await res.json();
      locales = data.locales || [];
      if (!locales.length) locales = [{ code: defaultLang, native_name: defaultLang }];
      langSelect.innerHTML = locales.map(item => `<option value="${esc(item.code)}">${esc(item.native_name || item.name || item.code)}</option>`).join("");
    }
    function pickLang(lang) {
      if (locales.some(item => item.code === lang)) return lang;
      if (locales.some(item => item.code === defaultLang)) return defaultLang;
      return locales[0]?.code || defaultLang;
    }
    function applyI18n() {
      document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
      document.querySelectorAll("[data-i18n-title]").forEach(el => { el.title = t(el.dataset.i18nTitle); });
      document.documentElement.lang = langSelect.value || "en";
    }
    async function loadI18n(lang) {
      const res = await fetch(`api/i18n/${encodeURIComponent(lang)}`, { credentials: "same-origin" });
      i18n = await res.json();
      localStorage.setItem("telemtAdmin.lang", lang);
      langSelect.value = lang;
      applyI18n();
    }
    function setTheme(theme) {
      const safeTheme = theme === "dark" ? "dark" : "light";
      document.documentElement.dataset.theme = safeTheme;
      themeSelect.value = safeTheme;
      localStorage.setItem("telemtAdmin.theme", safeTheme);
    }
    langSelect.onchange = () => loadI18n(langSelect.value);
    themeSelect.onchange = () => setTheme(themeSelect.value);
    setTheme(localStorage.getItem("telemtAdmin.theme") || defaultTheme);
    async function bootLogin() {
      await loadLocales();
      await loadI18n(pickLang(localStorage.getItem("telemtAdmin.lang") || defaultLang));
    }
    bootLogin().catch(() => {});
  </script>
</body>
</html>
"""

PAGE = r"""
<!doctype html>
<html lang="ru" data-theme="__DEFAULT_THEME__">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TeleMT Admin</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eef3f5;
      --panel: #ffffff;
      --ink: #17212b;
      --muted: #64717f;
      --line: #d7e0e6;
      --accent: #147d78;
      --accent-dark: #0e5e5a;
      --danger: #b72d3a;
      --warn: #a56a00;
      --ok: #1d7a46;
      --control: #ffffff;
      --soft: #f8fafb;
      --soft-2: #fbfcfd;
      --accent-soft: #f0fbf9;
      --blocked-bg: #f7f8f9;
      --hover: #edf4f6;
      --line-strong: #a8bac6;
      --tooltip-bg: #111f2a;
      --tooltip-ink: #ffffff;
      --shadow: rgba(16, 31, 45, .26);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    :root[data-theme="dark"] {
      color-scheme: dark;
      --bg: #11181f;
      --panel: #18222b;
      --ink: #e8eef2;
      --muted: #a9b7c3;
      --line: #31414f;
      --accent: #35aaa2;
      --accent-dark: #69c9c2;
      --danger: #ff7883;
      --warn: #f1b861;
      --ok: #6fd098;
      --control: #121b23;
      --soft: #141e27;
      --soft-2: #16212a;
      --accent-soft: #132a2a;
      --blocked-bg: #151d25;
      --hover: #20303b;
      --line-strong: #587080;
      --tooltip-bg: #e8eef2;
      --tooltip-ink: #11181f;
      --shadow: rgba(0, 0, 0, .42);
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--ink); }
    .shell { max-width: 1180px; margin: 0 auto; padding: 26px 18px 42px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
    .title-row { display: flex; align-items: center; gap: 8px; }
    .top-actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
    .lang-select { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    h1 { margin: 0; font-size: 26px; line-height: 1.1; letter-spacing: 0; }
    .subtitle { margin-top: 6px; color: var(--muted); font-size: 14px; }
    .subtitle button { height: auto; min-height: 0; border: 0; background: transparent; padding: 0; color: var(--accent-dark); font-weight: 700; vertical-align: baseline; }
    .subtitle button:hover { border: 0; text-decoration: underline; }
    .toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: space-between; margin-top: 14px; }
    .toolbar-side { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .toolbar-stack { display: grid; gap: 6px; justify-items: end; }
    .toolbar-updated { color: var(--muted); font-size: 12px; min-height: 16px; }
    .app-footer { margin-top: 18px; text-align: center; color: var(--muted); font-size: 12px; }
    .app-footer a { color: var(--muted); text-decoration: none; }
    .app-footer a:hover { color: var(--accent-dark); text-decoration: underline; }
    button, a.button-link { height: 38px; border: 1px solid var(--line); border-radius: 7px; background: var(--control); color: var(--ink); padding: 0 12px; font: inherit; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; }
    button:hover, a.button-link:hover { border-color: var(--line-strong); }
    button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
    button.primary:hover { background: var(--accent-dark); }
    button.danger { color: var(--danger); }
    button:disabled { opacity: .45; cursor: not-allowed; }
    button:disabled:hover { text-decoration: none; }
    button.icon, a.button-link.icon { width: 34px; height: 34px; padding: 0; display: inline-grid; place-items: center; }
    .icon-svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    button.icon.large { width: 42px; height: 38px; font-size: 18px; }
    button.header-stat { min-width: 40px; height: 20px; flex: 0 0 auto; transform: translateY(2px); }
    button.header-stat:hover { background: var(--hover); border-color: var(--line-strong); }
    button.busy { position: relative; color: transparent !important; pointer-events: none; }
    button.busy::after { content: ""; width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-bottom-color: transparent; border-radius: 50%; color: var(--ink); position: absolute; inset: 0; margin: auto; animation: spin .72s linear infinite; }
    button.primary.busy::after { color: #fff; }
    @keyframes spin { to { transform: rotate(360deg); } }
    button.mini { width: 22px; height: 22px; padding: 0; display: inline-grid; place-items: center; border: 0; border-radius: 5px; background: transparent; color: var(--muted); font-size: 13px; line-height: 1; }
    button.mini:hover { background: var(--hover); color: var(--accent-dark); border: 0; }
    button.qr-mini { width: auto; min-width: 26px; height: 18px; padding: 0 5px; border: 1px solid var(--line); border-radius: 5px; background: var(--soft-2); color: var(--ink); font-size: 10px; font-weight: 700; line-height: 16px; letter-spacing: .02em; text-transform: uppercase; transform: translateY(1px); }
    button.qr-mini:hover { background: var(--hover); border-color: var(--line-strong); color: var(--accent-dark); }
    select { height: 38px; border: 1px solid var(--line); border-radius: 7px; background: var(--control); color: var(--ink); padding: 0 10px; font: inherit; }
    .statusbar { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
    .metric { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
    .metric.filter { cursor: pointer; transition: .16s ease; }
    .metric.filter:hover { border-color: #9fb5bf; transform: translateY(-1px); }
    .metric.active { border-color: #45a39d; box-shadow: 0 0 0 2px rgba(20, 125, 120, .14); background: var(--accent-soft); }
    .metric b { display: block; font-size: 24px; line-height: 1.1; }
    .metric span { display: block; color: var(--muted); margin-top: 6px; font-size: 13px; }
    .table-wrap { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: middle; font-size: 14px; }
    th { background: var(--soft); color: var(--muted); font-weight: 600; }
    th.sortable { cursor: pointer; user-select: none; }
    th.sortable:hover { color: var(--accent-dark); }
    th.sortable::after { content: "↕"; margin-left: 6px; color: #9aa7b1; font-size: 11px; }
    th.sortable.sort-asc::after { content: "↑"; color: var(--accent); }
    th.sortable.sort-desc::after { content: "↓"; color: var(--accent); }
    th.sortable.sort-secondary::after { color: #9aa7b1; }
    tr:last-child td { border-bottom: 0; }
    tr.blocked { color: var(--muted); background: var(--blocked-bg); }
    .name-row { display: flex; align-items: baseline; gap: 6px; min-width: 0; }
    .name { color: var(--ink); font-weight: 700; overflow-wrap: anywhere; text-align: left; min-width: 0; }
    .comment { color: var(--muted); overflow-wrap: anywhere; max-width: 260px; line-height: 1.35; }
    .pill { display: inline-flex; align-items: center; height: 24px; border-radius: 999px; padding: 0 9px; font-size: 12px; border: 1px solid var(--line); background: var(--control); white-space: nowrap; }
    .pill small { display: block; font-size: 11px; line-height: 1.15; opacity: .78; }
    .pill.ok { color: var(--ok); border-color: var(--line); background: var(--accent-soft); }
    .pill.off { height: auto; min-height: 30px; align-items: flex-start; flex-direction: column; justify-content: center; gap: 1px; color: var(--muted); background: var(--soft); white-space: normal; }
    td.limits-td { padding-top: 2px; padding-bottom: 2px; }
    .limits-cell { display: inline-grid; gap: 2px; align-items: center; justify-items: start; }
    .limit-pill { display: inline-flex; align-items: center; min-height: 18px; border-radius: 999px; padding: 0 7px; border: 1px solid var(--line); background: var(--control); color: var(--ink); font-size: 12px; line-height: 1.15; white-space: nowrap; }
    .limit-empty { color: var(--muted); font-size: 13px; }
    .stat-cell { color: var(--muted); font-size: 13px; }
    td.stat-td { padding-top: 2px; padding-bottom: 2px; }
    .stat-button, .stat-text { height: auto; min-height: 24px; border: 0; border-radius: 5px; background: transparent; padding: 2px 4px; color: var(--ink); font-size: 13px; line-height: 1.25; text-align: left; display: grid; justify-items: start; gap: 1px; }
    .stat-button:hover { background: var(--hover); border: 0; color: var(--accent-dark); }
    .stat-button small, .stat-text small { display: block; color: var(--muted); font-size: 12px; white-space: nowrap; }
    .date-cell { color: var(--ink); font-size: 13px; line-height: 1.35; }
    .date-cell small { display: block; color: var(--muted); margin-top: 2px; }
    .date-help { position: relative; display: inline-flex; align-items: center; min-height: 22px; border-bottom: 1px dotted #9aa7b1; cursor: help; }
    .date-help .tip { position: absolute; left: 0; bottom: calc(100% + 8px); min-width: 220px; max-width: 280px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 7px; background: var(--tooltip-bg); color: var(--tooltip-ink); font-size: 12px; line-height: 1.35; box-shadow: 0 10px 28px rgba(15, 30, 42, .22); opacity: 0; transform: translateY(4px); pointer-events: none; transition: .14s ease; z-index: 10; }
    .date-help .tip::after { content: ""; position: absolute; left: 16px; top: 100%; border: 6px solid transparent; border-top-color: var(--tooltip-bg); }
    .date-help:hover .tip { opacity: 1; transform: translateY(0); }
    .status-cell { display: flex; align-items: center; gap: 7px; }
    .empty { padding: 38px 18px; text-align: center; color: var(--muted); }
    dialog { width: min(620px, calc(100vw - 26px)); border: 1px solid var(--line); border-radius: 8px; padding: 0; box-shadow: 0 24px 80px var(--shadow); background: var(--panel); color: var(--ink); }
    dialog.wide { width: min(920px, calc(100vw - 26px)); }
    dialog::backdrop { background: rgba(20, 31, 42, .46); }
    .modal-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--line); }
    .modal-head h2 { margin: 0; font-size: 18px; letter-spacing: 0; }
    .modal-body { padding: 18px; }
    .modal-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--line); background: var(--soft); }
    .modal-foot .danger { margin-right: auto; }
    label { display: block; color: var(--muted); font-size: 13px; margin: 0 0 6px; }
    .label-help { display: inline-flex; align-items: center; gap: 5px; color: var(--muted); font-size: 13px; margin: 0 0 6px; }
    .help-mark { display: inline-flex; align-items: center; justify-content: center; width: 15px; height: 15px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); font-size: 10px; font-weight: 800; cursor: help; }
    input, textarea { width: 100%; border: 1px solid var(--line); border-radius: 7px; padding: 10px 11px; font: inherit; color: var(--ink); background: var(--control); }
    textarea { min-height: 76px; resize: vertical; }
    .grid { display: grid; grid-template-columns: 1fr 140px; gap: 14px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .user-limits-grid { display: grid; grid-template-columns: minmax(86px, 1fr) minmax(86px, 1fr) minmax(220px, 2fr); gap: 14px; align-items: end; }
    .field { margin-bottom: 14px; }
    .unit-row { display: grid; grid-template-columns: 1fr 96px; gap: 8px; }
    .datetime-row { display: grid; grid-template-columns: minmax(0, 1fr) 92px; gap: 8px; }
    .checkline { display: flex; gap: 9px; align-items: center; }
    .checkline input { width: auto; }
    .secret-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
    .link-box { display: grid; gap: 12px; justify-items: center; }
    .stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
    .stats-controls { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
    .stats-control-side { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .stat-card { border: 1px solid var(--line); border-radius: 8px; padding: 10px; background: var(--soft-2); }
    .stat-card b { display: block; font-size: 18px; line-height: 1.2; }
    .stat-card span { display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }
    .metric-list { max-height: 320px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    .metric-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; padding: 9px 10px; border-bottom: 1px solid var(--line); font-size: 13px; }
    .metric-row:last-child { border-bottom: 0; }
    .metric-row code { color: var(--muted); overflow-wrap: anywhere; }
    .stats-updated { color: var(--muted); font-size: 12px; margin: -4px 0 12px; }
    .config-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
    .config-toolbar .checkline { margin: 0; }
    .config-filters { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(180px, 1fr); gap: 10px; margin-bottom: 12px; align-items: end; }
    .config-filters input { height: 38px; }
    .multi-select { position: relative; }
    .multi-trigger { width: 100%; min-height: 38px; height: auto; justify-content: space-between; gap: 10px; padding: 5px 9px; }
    .multi-value { min-width: 0; max-height: 58px; overflow-y: auto; display: flex; align-items: center; gap: 5px; flex-wrap: wrap; text-align: left; }
    .multi-placeholder { color: var(--muted); font-size: 13px; }
    .multi-chip { display: inline-flex; align-items: center; gap: 4px; max-width: 160px; min-height: 22px; padding: 0 6px; border: 1px solid var(--line); border-radius: 999px; background: var(--soft-2); color: var(--ink); font-size: 12px; }
    .multi-chip span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .multi-chip button { width: 16px; height: 16px; padding: 0; border: 0; background: transparent; color: var(--muted); font-size: 13px; line-height: 1; }
    .multi-chip button:hover { color: var(--danger); border: 0; background: transparent; }
    .multi-arrow { flex: 0 0 auto; color: var(--muted); }
    .multi-menu { position: fixed; z-index: 9998; max-height: 260px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); box-shadow: 0 18px 44px var(--shadow); padding: 8px; display: none; }
    .multi-select.open .multi-menu { display: grid; gap: 4px; }
    .multi-option { display: flex; align-items: center; gap: 8px; padding: 6px 7px; border-radius: 6px; color: var(--ink); font-size: 13px; cursor: pointer; }
    .multi-option:hover { background: var(--hover); }
    .multi-option input { width: auto; height: auto; }
    .multi-clear { margin-top: 6px; width: 100%; height: 30px; font-size: 12px; }
    .settings-list { max-height: 420px; overflow-y: auto; overflow-x: hidden; border: 1px solid var(--line); border-radius: 8px; }
    .settings-row { display: grid; grid-template-columns: minmax(170px, 1.2fr) minmax(150px, 1fr) minmax(120px, .8fr) minmax(156px, auto); gap: 10px; align-items: center; padding: 8px 10px; border-bottom: 1px solid var(--line); font-size: 13px; }
    .settings-row.head { position: sticky; top: 0; z-index: 3; background: var(--soft-2); color: var(--muted); font-size: 12px; font-weight: 700; box-shadow: 0 1px 0 var(--line); }
    .settings-title { grid-column: 1 / -1; padding: 9px 10px; background: var(--soft); color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
    .settings-row:last-child { border-bottom: 0; }
    .settings-row code { overflow-wrap: anywhere; color: var(--ink); }
    .settings-row .muted, .settings-value { color: var(--muted); overflow-wrap: anywhere; }
    .settings-default { color: var(--ok); overflow-wrap: anywhere; }
    .settings-value.same-default { color: var(--ok); }
    .settings-value.diff-default { color: #9d4edd; }
    .settings-row.changed { background: var(--accent-soft); }
    .settings-row.delete-pending { background: color-mix(in srgb, var(--danger) 9%, transparent); }
    .settings-changed { color: var(--danger); font-weight: 900; margin-left: 4px; }
    .settings-actions { display: flex; gap: 5px; justify-content: flex-end; flex-wrap: wrap; align-items: center; }
    .settings-badges { display: inline-flex; gap: 5px; justify-content: flex-end; flex-wrap: wrap; align-items: center; }
    .settings-badge { display: inline-flex; align-items: center; min-height: 18px; border: 1px solid var(--line); border-radius: 999px; padding: 0 6px; font-size: 11px; color: var(--muted); background: var(--control); white-space: nowrap; }
    .settings-badge.ok { color: var(--ok); background: var(--accent-soft); }
    .settings-badge.warn { color: var(--warn); }
    .settings-badge.danger { color: var(--danger); }
    .settings-badge.add, .settings-badge.change { color: var(--warn); background: color-mix(in srgb, var(--warn) 12%, transparent); }
    .settings-badge.delete { color: var(--danger); background: color-mix(in srgb, var(--danger) 10%, transparent); }
    .settings-badge.state { min-width: 18px; justify-content: center; border-color: transparent; background: transparent; padding: 0 2px; cursor: help; }
    .settings-key { cursor: help; }
    .settings-icon { display: inline-flex; align-items: center; justify-content: center; min-width: 18px; height: 18px; padding: 0 5px; border: 1px solid var(--line); border-radius: 999px; background: var(--control); color: var(--muted); font-size: 11px; font-weight: 800; cursor: pointer; }
    .settings-icon:hover { color: var(--accent-dark); border-color: var(--accent); }
    .settings-icon.danger:hover { color: var(--danger); border-color: var(--danger); }
    .settings-edit { width: 100%; min-height: 30px; padding: 5px 7px; border-radius: 7px; border: 1px solid var(--line); background: var(--control); color: var(--ink); font: inherit; }
    .settings-edit[type="checkbox"] { width: auto; min-height: auto; }
    .settings-savebar { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 10px; }
    .settings-warnings { display: grid; gap: 4px; color: var(--danger); font-size: 12px; font-weight: 700; }
    .settings-save-actions { display: flex; gap: 8px; margin-left: auto; }
    .modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
    .settings-help { display: inline-flex; align-items: center; width: fit-content; max-width: 100%; }
    .float-tip { position: fixed; z-index: 9999; max-width: min(420px, calc(100vw - 32px)); padding: 8px 10px; border: 1px solid var(--line); border-radius: 7px; background: var(--tooltip-bg); color: var(--tooltip-ink); font-size: 12px; line-height: 1.35; box-shadow: 0 10px 28px rgba(15, 30, 42, .22); pointer-events: none; opacity: 0; transform: translateY(4px); transition: opacity .12s ease, transform .12s ease; white-space: normal; }
    .float-tip.show { opacity: 1; transform: translateY(0); pointer-events: auto; }
    .float-tip a { display: inline-flex; margin-top: 7px; color: var(--tooltip-ink); font-weight: 700; text-decoration: underline; text-underline-offset: 2px; }
    .config-docs { margin-top: 10px; text-align: right; font-size: 13px; }
    .config-docs a { color: var(--accent-dark); font-weight: 700; text-decoration: none; }
    .config-docs a:hover { text-decoration: underline; }
    .qr { width: 220px; height: 220px; image-rendering: crisp-edges; border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fff; }
    .copy-row { display: grid; grid-template-columns: 1fr auto; gap: 8px; width: 100%; }
    .toast { position: fixed; right: 18px; bottom: 18px; background: #13212c; color: #fff; padding: 11px 13px; border-radius: 7px; opacity: 0; transform: translateY(8px); transition: .18s ease; pointer-events: none; }
    .toast.show { opacity: 1; transform: translateY(0); }
    @media (max-width: 780px) {
      header { align-items: stretch; flex-direction: column; }
      .statusbar { grid-template-columns: 1fr 1fr; }
      table, thead, tbody, th, td, tr { display: block; }
      thead { display: none; }
      tr { border-bottom: 1px solid var(--line); padding: 12px; }
      td { border: 0; padding: 5px 0; }
      .status-cell { justify-content: flex-start; }
      .grid { grid-template-columns: 1fr; }
      .copy-row { grid-template-columns: 1fr; }
      .stats-grid { grid-template-columns: 1fr 1fr; }
      .config-filters { grid-template-columns: 1fr; }
      .settings-row { grid-template-columns: 1fr; gap: 4px; }
      .settings-badges, .settings-actions { justify-content: flex-start; }
      .settings-savebar { align-items: stretch; flex-direction: column; }
      .settings-save-actions { margin-left: 0; justify-content: flex-end; }
      .modal-actions { justify-content: stretch; }
      .modal-actions button { width: 100%; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <div class="title-row">
          <h1 data-i18n="app.title">TeleMT Admin</h1>
          __METRICS_BUTTON__
        </div>
        <div class="subtitle" id="subtitle" data-i18n="app.loading">Загрузка пользователей...</div>
      </div>
      <div class="top-actions">
        <div class="lang-select">
          <span>🌐</span>
          <select id="langSelect" title="Language">
            <option value="__DEFAULT_LANG__">__DEFAULT_LANG__</option>
          </select>
        </div>
        <select id="themeSelect" data-i18n-title="theme.theme" title="Theme">
          <option value="light" data-i18n="theme.light">Light</option>
          <option value="dark" data-i18n="theme.dark">Dark</option>
        </select>
        <a class="button-link icon" id="logoutBtn" href="logout" data-i18n-title="common.logout" title="Logout" __WEB_AUTH_HIDDEN__ aria-label="Logout">
          <svg class="icon-svg" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4"></path>
            <path d="M14 16l4-4-4-4"></path>
            <path d="M18 12H9"></path>
          </svg>
        </a>
      </div>
    </header>

    <section class="statusbar">
      <div class="metric filter active" data-filter="all"><b id="mTotal">0</b><span data-i18n="filters.total">Всего пользователей</span></div>
      <div class="metric filter" data-filter="active"><b id="mActive">0</b><span data-i18n="filters.active">Активны</span></div>
      <div class="metric filter" data-filter="blocked"><b id="mBlocked">0</b><span data-i18n="filters.blocked">Заблокированы</span></div>
      <div class="metric filter" data-filter="limited"><b id="mLimited">0</b><span data-i18n="filters.limited">С лимитами</span></div>
    </section>

    <section class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="sortable" data-sort="name" style="width: 19%" data-i18n="table.user">Пользователь</th>
            <th class="sortable" data-sort="comment" data-i18n="table.comment">Комментарий</th>
            <th class="sortable" data-sort="stats" style="width: 120px" data-i18n="table.stats">Статистика</th>
            <th class="sortable" data-sort="added" style="width: 155px" data-i18n="table.added">Добавлен</th>
            <th class="sortable" data-sort="limit" style="width: 135px" data-i18n="table.limit">Лимиты</th>
            <th class="sortable" data-sort="status" style="width: 150px" data-i18n="table.status">Статус</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
      <div class="empty" id="empty" hidden data-i18n="table.empty">Пользователей пока нет.</div>
    </section>

    <div class="toolbar">
      <div class="toolbar-side">
        <button type="button" class="primary icon large" id="addBtn" data-i18n-title="common.add" title="Добавить">＋</button>
      </div>
      <div class="toolbar-stack">
        <div class="toolbar-side">
          <label for="refreshInterval" style="margin: 0; color: var(--muted);" data-i18n="common.auto">Авто</label>
          <select id="refreshInterval">
            <option value="0" data-i18n="time.off">off</option>
            <option value="1000" data-i18n="time.1s">1s</option>
            <option value="10000" data-i18n="time.10s">10s</option>
            <option value="60000" data-i18n="time.60s">60s</option>
          </select>
          <button type="button" class="icon large" id="refreshBtn" data-i18n-title="common.refresh" title="Обновить">↻</button>
        </div>
        <div class="toolbar-updated" id="updatedAt"></div>
      </div>
    </div>
    <div class="app-footer">Powered by: <a href="https://github.com/Vozdr/telemt-admin/" target="_blank" rel="noopener noreferrer">TeleMT Admin __APP_VERSION__</a></div>
  </div>

  <dialog id="editDialog">
    <form method="dialog" id="editForm">
      <div class="modal-head">
        <h2 id="editTitle" data-i18n="modal.addUser">Добавить пользователя</h2>
        <button type="button" class="icon" data-close="editDialog" data-i18n-title="common.close" title="Закрыть">×</button>
      </div>
      <div class="modal-body">
        <div class="field">
          <label for="name" data-i18n="form.name">Имя</label>
          <input id="name" name="name" autocomplete="off" required pattern="[A-Za-z0-9_-]{1,64}">
        </div>
        <div class="field">
          <label for="secret" data-i18n="form.secret">Secret</label>
          <div class="secret-row">
            <input id="secret" name="secret" autocomplete="off" pattern="[0-9a-fA-F]{32}">
            __USER_GEN_SECRET_BUTTON__
          </div>
        </div>
        <div class="user-limits-grid">
          <div class="field">
            <label class="label-help" for="limit"><span data-i18n="form.limit">Лимит IP</span><span class="help-mark" data-i18n-tip="help.limit" data-tip="Maximum simultaneous unique IP addresses for this user. 0 means no limit.">?</span></label>
            <input id="limit" name="limit" type="number" min="0" max="100000" value="0">
          </div>
          <div class="field">
            <label class="label-help" for="maxTcpConns"><span data-i18n="form.maxTcpConns">TCP limit</span><span class="help-mark" data-i18n-tip="help.maxTcpConns" data-tip="Maximum simultaneous TCP connections for this user. 0 means no per-user override.">?</span></label>
            <input id="maxTcpConns" name="maxTcpConns" type="number" min="0" max="1000000" value="0">
          </div>
          <div class="field">
            <label class="label-help" for="expirationDate"><span data-i18n="form.expiration">Expiration</span><span class="help-mark" data-i18n-tip="help.expiration" data-tip="User expiration date and time. Empty means no expiration. Stored in config.toml as RFC3339.">?</span></label>
            <div class="datetime-row">
              <input id="expirationDate" name="expirationDate" type="date">
              <input id="expirationTime" name="expirationTime" type="time" step="60">
            </div>
          </div>
        </div>
        <div class="field">
          <label class="label-help" for="dataQuotaValue"><span data-i18n="form.dataQuota">Traffic quota</span><span class="help-mark" data-i18n-tip="help.dataQuota" data-tip="Total traffic quota for this user. 0 means no quota. Stored in config.toml as bytes.">?</span></label>
          <div class="unit-row">
            <input id="dataQuotaValue" name="dataQuotaValue" type="number" min="0" step="1" value="0">
            <select id="dataQuotaUnit" name="dataQuotaUnit">
              <option value="1" data-i18n="unit.b">B</option>
              <option value="1024" data-i18n="unit.kb">KB</option>
              <option value="1048576" selected data-i18n="unit.mb">MB</option>
              <option value="1073741824" data-i18n="unit.gb">GB</option>
            </select>
          </div>
        </div>
        <div class="grid-2">
          <div class="field">
            <label class="label-help" for="rateLimitUpValue"><span data-i18n="form.rateLimitUp">Rate up</span><span class="help-mark" data-i18n-tip="help.rateLimitUp" data-tip="Upload speed limit for this user. 0 means no limit. Stored as bits per second.">?</span></label>
            <div class="unit-row">
              <input id="rateLimitUpValue" name="rateLimitUpValue" type="number" min="0" step="1" value="0">
              <select id="rateLimitUpUnit" name="rateLimitUpUnit">
                <option value="1" data-i18n="unit.bps">bps</option>
                <option value="1000" data-i18n="unit.kbps">Kbps</option>
                <option value="1000000" selected data-i18n="unit.mbps">Mbps</option>
                <option value="1000000000" data-i18n="unit.gbps">Gbps</option>
              </select>
            </div>
          </div>
          <div class="field">
            <label class="label-help" for="rateLimitDownValue"><span data-i18n="form.rateLimitDown">Rate down</span><span class="help-mark" data-i18n-tip="help.rateLimitDown" data-tip="Download speed limit for this user. 0 means no limit. Stored as bits per second.">?</span></label>
            <div class="unit-row">
              <input id="rateLimitDownValue" name="rateLimitDownValue" type="number" min="0" step="1" value="0">
              <select id="rateLimitDownUnit" name="rateLimitDownUnit">
                <option value="1" data-i18n="unit.bps">bps</option>
                <option value="1000" data-i18n="unit.kbps">Kbps</option>
                <option value="1000000" selected data-i18n="unit.mbps">Mbps</option>
                <option value="1000000000" data-i18n="unit.gbps">Gbps</option>
              </select>
            </div>
          </div>
        </div>
        <div class="field">
          <label for="comment" data-i18n="form.comment">Комментарий</label>
          <textarea id="comment" name="comment"></textarea>
        </div>
        <label class="checkline"><input id="blocked" name="blocked" type="checkbox"> <span data-i18n="form.blocked">Заблокирован</span></label>
      </div>
      <div class="modal-foot">
        __USER_DELETE_BUTTON__
        <button type="button" id="clearLimitsBtn" data-i18n="form.clearLimits">Очистить лимиты</button>
        <button type="button" id="editCloseBtn" data-close="editDialog" data-i18n="common.cancel">Отмена</button>
        __USER_SAVE_BUTTON__
      </div>
    </form>
  </dialog>

  <dialog id="linkDialog">
    <div class="modal-head">
      <h2 id="linkTitle" data-i18n="modal.link">Ссылка</h2>
      <button type="button" class="icon" data-close="linkDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="link-box">
        <img class="qr" id="qr" alt="QR код">
        <div class="copy-row">
          <input id="linkText" readonly>
          <button type="button" id="copyBtn" data-i18n="common.copy">Скопировать</button>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" data-close="linkDialog" data-i18n="common.close">Close</button>
      </div>
    </div>
  </dialog>

  <dialog id="statsDialog">
    <div class="modal-head">
      <h2 id="statsTitle" data-i18n="modal.userStats">Статистика</h2>
      <button type="button" class="icon" data-close="statsDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="stats-controls">
        <div class="stats-updated" id="statsUpdated">Обновление...</div>
        <div class="stats-control-side">
          <label for="statsRefreshInterval" style="margin: 0; color: var(--muted);" data-i18n="common.auto">Авто</label>
          <select id="statsRefreshInterval">
            <option value="0" data-i18n="time.off">off</option>
            <option value="1000" data-i18n="time.1s">1s</option>
            <option value="5000" selected data-i18n="time.5s">5s</option>
            <option value="10000" data-i18n="time.10s">10s</option>
            <option value="30000" data-i18n="time.30s">30s</option>
            <option value="60000" data-i18n="time.60s">60s</option>
          </select>
          <button type="button" class="icon" id="statsRefreshBtn" data-i18n-title="common.refresh" title="Обновить">↻</button>
        </div>
      </div>
      <div class="stats-grid" id="statsCards"></div>
      <div class="metric-list" id="statsMetrics"></div>
      <div class="modal-actions">
        <button type="button" data-close="statsDialog" data-i18n="common.close">Close</button>
      </div>
    </div>
  </dialog>

  <dialog id="telemtStatsDialog">
    <div class="modal-head">
      <h2 data-i18n="modal.globalStats">Общая статистика TeleMT</h2>
      <button type="button" class="icon" data-close="telemtStatsDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="stats-controls">
        <div class="stats-updated" id="telemtStatsUpdated">Обновление...</div>
        <div class="stats-control-side">
          <label for="telemtStatsRefreshInterval" style="margin: 0; color: var(--muted);" data-i18n="common.auto">Авто</label>
          <select id="telemtStatsRefreshInterval">
            <option value="0" data-i18n="time.off">off</option>
            <option value="1000" data-i18n="time.1s">1s</option>
            <option value="5000" selected data-i18n="time.5s">5s</option>
            <option value="10000" data-i18n="time.10s">10s</option>
            <option value="30000" data-i18n="time.30s">30s</option>
            <option value="60000" data-i18n="time.60s">60s</option>
          </select>
          <button type="button" class="icon" id="telemtStatsRefreshBtn" data-i18n-title="common.refresh" title="Обновить">↻</button>
        </div>
      </div>
      <div class="stats-grid" id="telemtStatsCards"></div>
      <div class="metric-list" id="telemtStatsMetrics"></div>
      <div class="modal-actions">
        <button type="button" data-close="telemtStatsDialog" data-i18n="common.close">Close</button>
      </div>
    </div>
  </dialog>

  <dialog id="configDialog" class="wide">
    <div class="modal-head">
      <h2 data-i18n="modal.telemtConfig">Настройки TeleMT</h2>
      <button type="button" class="icon" data-close="configDialog" data-i18n-title="common.close" title="Закрыть">×</button>
    </div>
    <div class="modal-body">
      <div class="config-toolbar">
        <label class="checkline"><input id="configShowAll" type="checkbox"> <span data-i18n="config.showAll">Show all settings</span></label>
        <span class="muted" id="configSettingsCount"></span>
      </div>
      <div class="config-filters">
        <div>
          <label data-i18n="config.sectionsFilter">Sections</label>
          <div class="multi-select" id="configSectionPicker">
            <button type="button" class="multi-trigger" id="configSectionTrigger"><span class="multi-value" id="configSectionValue"></span><span class="multi-arrow">▾</span></button>
            <div class="multi-menu" id="configSectionMenu"></div>
          </div>
        </div>
        <div>
          <label for="configSearch" data-i18n="config.search">Search</label>
          <input id="configSearch" type="search" autocomplete="off" data-i18n-placeholder="config.searchPlaceholder" placeholder="Key or section">
        </div>
      </div>
      <div class="settings-list" id="configSettings"></div>
      <div class="config-docs"><a id="configDocsLink" href="#" target="_blank" rel="noopener noreferrer" data-i18n="config.fullDocs">Detailed key reference</a></div>
      <div class="settings-savebar">
        <div class="settings-warnings" id="configWarnings"></div>
        <div class="settings-save-actions">
          __CONFIG_RESET_BUTTON__
          <button type="button" class="primary" id="configSaveBtn" data-i18n="common.save">Save</button>
        </div>
      </div>
    </div>
    <div class="float-tip" id="floatTip"></div>
  </dialog>

  <div class="toast" id="toast"></div>

  <script>
    const state = { users: [], domain: "", config: null, configWritable: true, configShowAll: false, configSearch: "", configSections: [], configDraft: {}, configEditing: "", configPending: false, metrics: { enabled: "__METRICS_ENABLED__" === "true", available: false, url: "" }, updatedAt: "", editing: null, editPending: false, loadingUsers: false, statsLoading: false, telemtStatsLoading: false, filter: "all", sorts: [], refreshTimer: null, statsUser: null, statsTimer: null, telemtStatsTimer: null, lang: localStorage.getItem("telemtAdmin.lang") || "", locales: [], theme: localStorage.getItem("telemtAdmin.theme") || "__DEFAULT_THEME__", i18n: {}, webAuthEnabled: "__WEB_AUTH_ENABLED__" === "true" };
    const $ = (id) => document.getElementById(id);
    let tipHideTimer = null;
    let tipActiveTarget = null;

    function t(key, params = {}) {
      let text = state.i18n[key] || key;
      for (const [name, value] of Object.entries(params)) {
        text = text.replace(`{${name}}`, value);
      }
      return text;
    }

    async function loadLocales() {
      const res = await fetch("api/i18n", { credentials: "same-origin" });
      const data = await res.json();
      state.locales = data.locales || [];
      if (!state.locales.length) state.locales = [{ code: "__DEFAULT_LANG__", native_name: "__DEFAULT_LANG__" }];
      $("langSelect").innerHTML = state.locales.map(item => `<option value="${esc(item.code)}">${esc(item.native_name || item.name || item.code)}</option>`).join("");
    }

    function pickLang(lang) {
      if (state.locales.some(item => item.code === lang)) return lang;
      if (state.locales.some(item => item.code === "__DEFAULT_LANG__")) return "__DEFAULT_LANG__";
      return state.locales[0]?.code || "__DEFAULT_LANG__";
    }

    async function loadI18n(lang) {
      const res = await fetch(`api/i18n/${encodeURIComponent(lang)}`, { credentials: "same-origin" });
      state.i18n = await res.json();
      state.lang = lang;
      localStorage.setItem("telemtAdmin.lang", lang);
      $("langSelect").value = lang;
      applyI18n();
    }

    function applyI18n() {
      document.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = t(el.dataset.i18n);
      });
      document.querySelectorAll("[data-i18n-title]").forEach(el => {
        el.title = t(el.dataset.i18nTitle);
      });
      document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        el.placeholder = t(el.dataset.i18nPlaceholder);
      });
      document.querySelectorAll("[data-i18n-tip]").forEach(el => {
        el.dataset.tip = t(el.dataset.i18nTip);
      });
      document.documentElement.lang = state.lang || "en";
      render();
      if ($("configDialog") && $("configDialog").open && state.config) {
        renderConfigSettings();
        updateConfigDocsLink();
      }
    }

    function setTheme(theme) {
      const safeTheme = theme === "dark" ? "dark" : "light";
      state.theme = safeTheme;
      document.documentElement.dataset.theme = safeTheme;
      $("themeSelect").value = safeTheme;
      localStorage.setItem("telemtAdmin.theme", safeTheme);
    }

    function toast(text) {
      const el = $("toast");
      el.textContent = text;
      el.classList.add("show");
      setTimeout(() => el.classList.remove("show"), 1800);
    }

    function positionFloatTip(target) {
      const tipEl = $("floatTip");
      if (!tipEl || !tipEl.classList.contains("show")) return;
      const rect = target.getBoundingClientRect();
      const margin = 10;
      const width = tipEl.offsetWidth || 260;
      const height = tipEl.offsetHeight || 48;
      let left = rect.left;
      let top = rect.top - height - 8;
      if (left + width > window.innerWidth - margin) left = window.innerWidth - width - margin;
      if (left < margin) left = margin;
      if (top < margin) top = rect.bottom + 8;
      if (top + height > window.innerHeight - margin) top = window.innerHeight - height - margin;
      tipEl.style.left = `${Math.max(margin, left)}px`;
      tipEl.style.top = `${Math.max(margin, top)}px`;
    }

    function positionSectionMenu() {
      const picker = $("configSectionPicker");
      const menu = $("configSectionMenu");
      const trigger = $("configSectionTrigger");
      if (!picker || !menu || !trigger || !picker.classList.contains("open")) return;
      const rect = trigger.getBoundingClientRect();
      const margin = 10;
      const width = Math.max(rect.width, 240);
      let left = rect.left;
      let top = rect.bottom + 5;
      if (left + width > window.innerWidth - margin) left = window.innerWidth - width - margin;
      if (left < margin) left = margin;
      const maxHeight = Math.max(160, window.innerHeight - top - margin);
      menu.style.left = `${left}px`;
      menu.style.top = `${top}px`;
      menu.style.width = `${width}px`;
      menu.style.maxHeight = `${maxHeight}px`;
    }

    function docsLang() {
      return state.lang === "ru" ? "ru" : "en";
    }

    function docsBaseUrl() {
      const docs = state.config?.docs || {};
      return docs[docsLang()] || docs.en || docs.ru || "";
    }

    function docsAnchor(value) {
      return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
    }

    function docsUrl(anchor = "") {
      const base = docsBaseUrl();
      if (!base) return "";
      const cleanAnchor = docsAnchor(anchor);
      return cleanAnchor ? `${base}#${encodeURIComponent(cleanAnchor)}` : base;
    }

    function updateConfigDocsLink() {
      const link = $("configDocsLink");
      if (!link) return;
      const url = docsUrl();
      link.href = url || "#";
      link.hidden = !url;
    }

    async function request(url, options = {}) {
      const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        ...options
      });
      if (!res.ok) {
        let msg = t("common.error");
        try { msg = (await res.json()).detail || msg; } catch (_) {}
        throw new Error(msg);
      }
      return res.json();
    }

    function setButtonBusy(button, busy) {
      if (!button) return;
      if (busy) {
        button.dataset.wasDisabled = button.disabled ? "1" : "0";
        button.disabled = true;
        button.classList.add("busy");
      } else {
        button.classList.remove("busy");
        button.disabled = button.dataset.wasDisabled === "1";
        delete button.dataset.wasDisabled;
      }
    }

    function setControlDisabled(control, disabled) {
      if (!control) return;
      if (disabled) {
        control.dataset.wasDisabled = control.disabled ? "1" : "0";
        control.disabled = true;
      } else {
        control.disabled = control.dataset.wasDisabled === "1";
        delete control.dataset.wasDisabled;
      }
    }

    function setEditPending(pending, activeButton) {
      state.editPending = pending;
      ["saveBtn", "deleteBtn", "editCloseBtn", "genSecret", "clearLimitsBtn"].forEach(id => {
        const el = $(id);
        if (el === activeButton) setButtonBusy(el, pending);
        else setControlDisabled(el, pending);
      });
      document.querySelectorAll('[data-close="editDialog"]:not(#editCloseBtn)').forEach(el => setControlDisabled(el, pending));
    }

    function setConfigPending(pending) {
      state.configPending = pending;
      setButtonBusy($("configSaveBtn"), pending);
      ["configResetBtn", "configShowAll", "configSearch", "configSectionTrigger"].forEach(id => setControlDisabled($(id), pending));
      document.querySelectorAll('[data-close="configDialog"], .settings-icon, .settings-edit').forEach(el => setControlDisabled(el, pending));
    }

    function randomSecret() {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
    }

    function splitUnitValue(raw, units, fallback) {
      const value = Number(raw || 0);
      const preferred = units.find(item => item.mult === fallback) || units[0];
      if (!value) return { value: 0, unit: preferred.mult };
      for (const item of [...units].sort((a, b) => b.mult - a.mult)) {
        if (value >= item.mult && value % item.mult === 0) {
          return { value: value / item.mult, unit: item.mult };
        }
      }
      return { value, unit: 1 };
    }

    function setUnitValue(valueId, unitId, raw, units, fallback) {
      const item = splitUnitValue(raw, units, fallback);
      $(valueId).value = item.value;
      $(unitId).value = String(item.unit);
    }

    function readUnitValue(valueId, unitId) {
      const value = Number($(valueId).value || 0);
      const unit = Number($(unitId).value || 1);
      return Math.max(0, Math.round(value * unit));
    }

    function toDateTimeParts(value) {
      if (!value) return { date: "", time: "" };
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        const raw = String(value);
        return { date: raw.slice(0, 10), time: raw.slice(11, 16) || "" };
      }
      const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      const iso = local.toISOString();
      return { date: iso.slice(0, 10), time: iso.slice(11, 16) };
    }

    function setDateTimeFields(value) {
      const parts = toDateTimeParts(value);
      $("expirationDate").value = parts.date || "";
      $("expirationTime").value = parts.time || "";
    }

    function readDateTimeFields() {
      const dateValue = $("expirationDate").value.trim();
      const timeValue = $("expirationTime").value.trim();
      if (!dateValue) return "";
      const timePart = timeValue || "00:00:00";
      const normalizedTime = timePart.length === 5 ? `${timePart}:00` : timePart;
      const date = new Date(`${dateValue}T${normalizedTime}`);
      if (Number.isNaN(date.getTime())) return "";
      return date.toISOString().replace(".000Z", "Z");
    }

    const DATA_UNITS = [{ mult: 1 }, { mult: 1024 }, { mult: 1048576 }, { mult: 1073741824 }];
    const RATE_UNITS = [{ mult: 1 }, { mult: 1000 }, { mult: 1000000 }, { mult: 1000000000 }];

    async function load() {
      if (state.loadingUsers) return;
      state.loadingUsers = true;
      setButtonBusy($("refreshBtn"), true);
      try {
        const data = await request("api/users");
        state.users = data.users;
        state.domain = data.domain;
        state.config = data.config || null;
        state.configWritable = data.config_writable !== false;
        state.metrics = data.metrics || { enabled: true, available: false, url: "" };
        state.updatedAt = data.updated_at;
        const metricsText = !state.metrics.enabled ? t("metrics.off") : (state.metrics.available ? t("metrics.on") : t("metrics.down"));
        const modeText = (!data.config_read_error && !state.configWritable) ? ` ${esc(t("app.readOnly"))}.` : "";
        const domainHtml = data.domain
          ? `<button type="button" id="configLink">${esc(data.domain)}</button>`
          : `<span>${esc(t("common.na"))}</span>`;
        const errorText = data.config_read_error ? ` ${esc(t("app.configReadError"))}.` : "";
        $("subtitle").innerHTML = `${esc(t("app.domain"))}: ${domainHtml}. ${esc(t("app.metrics"))}: ${esc(metricsText)}.${modeText}${errorText}`;
        if (data.domain) $("configLink").onclick = showConfig;
        $("updatedAt").textContent = `${t("app.updated")}: ${formatFullDate(data.updated_at)}`;
        if ($("telemtStatsBtn")) $("telemtStatsBtn").hidden = !(state.metrics.enabled && state.metrics.available);
        $("addBtn").disabled = !state.configWritable;
        render();
      } finally {
        setButtonBusy($("refreshBtn"), false);
        state.loadingUsers = false;
      }
    }

    function filteredUsers() {
      if (state.filter === "active") return state.users.filter(u => !u.blocked);
      if (state.filter === "blocked") return state.users.filter(u => u.blocked);
      if (state.filter === "limited") return state.users.filter(hasUserLimits);
      return state.users;
    }

    const SORT_KEYS = ["name", "comment", "stats", "added", "limit", "status"];

    function defaultSorts() {
      return [{ key: "added", dir: "desc" }];
    }

    function normalizeSorts(value) {
      const seen = new Set();
      const result = [];
      const items = Array.isArray(value) ? value : [];
      for (const item of items) {
        const key = String(item && item.key || "");
        const dir = item && item.dir === "desc" ? "desc" : "asc";
        if (!SORT_KEYS.includes(key) || seen.has(key)) continue;
        seen.add(key);
        result.push({ key, dir });
      }
      return result;
    }

    function loadSorts() {
      try {
        const saved = normalizeSorts(JSON.parse(localStorage.getItem("telemtAdmin.sorts") || "null"));
        state.sorts = saved.length ? saved : defaultSorts();
      } catch {
        state.sorts = defaultSorts();
      }
    }

    function saveSorts() {
      localStorage.setItem("telemtAdmin.sorts", JSON.stringify(state.sorts));
    }

    function cycleSort(key) {
      const index = state.sorts.findIndex(item => item.key === key);
      if (index === -1) {
        state.sorts = [{ key, dir: "asc" }, ...state.sorts];
      } else {
        const current = state.sorts[index];
        const rest = state.sorts.filter(item => item.key !== key);
        if (current.dir === "asc") state.sorts = [{ key, dir: "desc" }, ...rest];
        else state.sorts = rest;
      }
      saveSorts();
    }

    function sortValue(u, key) {
      if (key === "name") return u.name.toLowerCase();
      if (key === "comment") return (u.comment || "").toLowerCase();
      if (key === "added") return u.added_at || "";
      if (key === "limit") return userLimitSortValue(u);
      return "";
    }

    function numberValue(value) {
      const number = Number(value);
      return Number.isFinite(number) ? number : 0;
    }

    function compareByStats(a, b, dir) {
      const aAvailable = Boolean(a.stats && a.stats.available);
      const bAvailable = Boolean(b.stats && b.stats.available);
      if (aAvailable !== bAvailable) {
        if (dir === 1) return aAvailable ? 1 : -1;
        return aAvailable ? -1 : 1;
      }
      if (!aAvailable && !bAvailable) return a.name.localeCompare(b.name, "ru", { numeric: true, sensitivity: "base" });
      const keys = ["connections_current", "bytes_from_client", "bytes_to_client"];
      for (const key of keys) {
        const diff = numberValue(a.stats[key]) - numberValue(b.stats[key]);
        if (diff !== 0) return diff * dir;
      }
      return 0;
    }

    function compareByStatus(a, b, dir) {
      if (a.blocked !== b.blocked) return a.blocked ? -1 : 1;
      if (a.blocked && b.blocked) {
        const av = Date.parse(a.blocked_at || "") || 0;
        const bv = Date.parse(b.blocked_at || "") || 0;
        if (av !== bv) return (av - bv) * dir;
      }
      return 0;
    }

    function compareByKey(a, b, key, dir) {
      if (key === "stats") return compareByStats(a, b, dir);
      if (key === "status") return compareByStatus(a, b, dir);
      const av = sortValue(a, key);
      const bv = sortValue(b, key);
      if (typeof av === "number" || typeof bv === "number") return (Number(av) - Number(bv)) * dir;
      return String(av).localeCompare(String(bv), "ru", { numeric: true, sensitivity: "base" }) * dir;
    }

    function sortedUsers(users) {
      const sorts = Array.isArray(state.sorts) ? state.sorts : [];
      return [...users].sort((a, b) => {
        for (const sort of sorts) {
          const dir = sort.dir === "desc" ? -1 : 1;
          const result = compareByKey(a, b, sort.key, dir);
          if (result !== 0) return result;
        }
        return a.name.localeCompare(b.name, "ru", { numeric: true, sensitivity: "base" });
      });
    }

    function formatDate(value) {
      if (!value) return "N/A";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "N/A";
      return date.toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" });
    }

    function formatExpirationLimit(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "";
      const locale = state.lang === "ru" ? "ru-RU" : "en-US";
      const day = date.toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "2-digit" });
      const hours = date.getHours();
      const minutes = date.getMinutes();
      if (hours === 0 && minutes === 0) return `${t("limits.until")} ${day}`;
      const time = date.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
      return `${t("limits.until")} ${day} ${time}`;
    }

    function formatFullDate(value) {
      if (!value) return "N/A";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "N/A";
      return date.toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US");
    }

    function formatBytes(bytes) {
      if (!Number.isFinite(Number(bytes))) return "N/A";
      const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
      let value = Number(bytes);
      let unit = 0;
      while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit += 1;
      }
      return `${Math.round(value)} ${units[unit]}`;
    }

    function formatRateBps(value) {
      const units = [
        [1000000000, t("unit.gbpsShort")],
        [1000000, t("unit.mbpsShort")],
        [1000, t("unit.kbpsShort")],
        [1, t("unit.bpsShort")]
      ];
      const raw = Number(value || 0);
      for (const [mult, label] of units) {
        if (raw >= mult || mult === 1) {
          const number = raw / mult;
          return `${Math.round(number)}${label}`;
        }
      }
      return `0${t("unit.bpsShort")}`;
    }

    function formatNumber(value) {
      return Number(value || 0).toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US");
    }

    function hasUserLimits(u) {
      return Number(u.limit || 0) > 0
        || Number(u.max_tcp_conns || 0) > 0
        || Number(u.data_quota || 0) > 0
        || Boolean(u.expiration)
        || Number(u.rate_limit_up || 0) > 0
        || Number(u.rate_limit_down || 0) > 0;
    }

    function userLimitSortValue(u) {
      return [
        hasUserLimits(u) ? 1 : 0,
        Number(u.limit || 0),
        Number(u.max_tcp_conns || 0),
        Date.parse(u.expiration || "") || 0,
        Number(u.data_quota || 0),
        Number(u.rate_limit_up || 0),
        Number(u.rate_limit_down || 0)
      ].join("|");
    }

    function renderLimitsCell(cell, u) {
      cell.innerHTML = "";
      const box = document.createElement("div");
      box.className = "limits-cell";
      const items = [];
      if (Number(u.limit || 0) > 0) items.push(`${formatNumber(u.limit)} IP`);
      if (Number(u.max_tcp_conns || 0) > 0) items.push(`${formatNumber(u.max_tcp_conns)} TCP`);
      if (u.expiration) items.push(formatExpirationLimit(u.expiration));
      if (Number(u.data_quota || 0) > 0) items.push(`Σ ${formatBytes(u.data_quota)}`);
      const up = Number(u.rate_limit_up || 0);
      const down = Number(u.rate_limit_down || 0);
      if (up > 0 && down > 0) items.push(`↑ ${formatRateBps(up)}/↓ ${formatRateBps(down)}`);
      else if (up > 0) items.push(`↑ ${formatRateBps(up)}`);
      else if (down > 0) items.push(`↓ ${formatRateBps(down)}`);
      if (!items.length) {
        const empty = document.createElement("span");
        empty.className = "limit-empty";
        empty.textContent = "—";
        box.appendChild(empty);
      } else {
        for (const item of items) {
          const pill = document.createElement("span");
          pill.className = "limit-pill";
          pill.textContent = item;
          box.appendChild(pill);
        }
      }
      cell.appendChild(box);
    }

    function formatDuration(seconds) {
      seconds = Math.max(0, Math.floor(Number(seconds || 0)));
      const d = Math.floor(seconds / 86400);
      const h = Math.floor((seconds % 86400) / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      if (d > 0) return `${d} д ${h} ч`;
      if (h > 0) return `${h} ч ${m} мин`;
      return `${m} мин`;
    }

    function latestMetric(metrics, name, labels = {}) {
      let value = 0;
      for (const item of metrics || []) {
        if (item.name !== name) continue;
        const itemLabels = item.labels || {};
        const matched = Object.entries(labels).every(([key, expected]) => itemLabels[key] === expected);
        if (matched) value = Number(item.value || 0);
      }
      return value;
    }

    function userStatsFromMetrics(metrics) {
      const rx = latestMetric(metrics, "telemt_user_octets_from_client");
      const tx = latestMetric(metrics, "telemt_user_octets_to_client");
      return {
        connections_total: latestMetric(metrics, "telemt_user_connections_total"),
        connections_current: latestMetric(metrics, "telemt_user_connections_current"),
        bytes_from_client: rx,
        bytes_to_client: tx,
        unique_ips_current: latestMetric(metrics, "telemt_user_unique_ips_current"),
        unique_ips_recent_window: latestMetric(metrics, "telemt_user_unique_ips_recent_window"),
        unique_ips_limit: latestMetric(metrics, "telemt_user_unique_ips_limit")
      };
    }

    function telemtStatsFromMetrics(metrics) {
      return {
        uptime_seconds: latestMetric(metrics, "telemt_uptime_seconds"),
        connections_total: latestMetric(metrics, "telemt_connections_total"),
        connections_bad_total: latestMetric(metrics, "telemt_connections_bad_total"),
        handshake_timeouts_total: latestMetric(metrics, "telemt_handshake_timeouts_total"),
        user_entries: latestMetric(metrics, "telemt_stats_user_entries"),
        user_telemetry_enabled: latestMetric(metrics, "telemt_telemetry_user_enabled"),
        buffer_in_use: latestMetric(metrics, "telemt_buffer_pool_buffers_total", { kind: "in_use" }),
        buffer_allocated: latestMetric(metrics, "telemt_buffer_pool_buffers_total", { kind: "allocated" }),
        upstream_connect_success: latestMetric(metrics, "telemt_upstream_connect_success_total"),
        upstream_connect_fail: latestMetric(metrics, "telemt_upstream_connect_fail_total")
      };
    }

    function statLine(stats) {
      if (!state.metrics.enabled || !state.metrics.available) return "—";
      if (!stats || !stats.available) return "N/A";
      return `${formatNumber(stats.connections_current)} ${t("stats.activeShort")}`;
    }

    function renderStatButton(button, stats) {
      button.textContent = statLine(stats);
      if (state.metrics.enabled && stats && stats.available) {
        const small = document.createElement("small");
        small.textContent = `↑ ${formatBytes(stats.bytes_from_client)}/↓ ${formatBytes(stats.bytes_to_client)}`;
        button.appendChild(small);
      }
    }

    function renderStatCell(cell, stats) {
      cell.innerHTML = "";
      const active = state.metrics.enabled && state.metrics.available;
      const tag = active ? "button" : "div";
      const el = document.createElement(tag);
      el.className = active ? "stat-button" : "stat-text";
      if (active) {
        el.type = "button";
        el.dataset.act = "stats";
      }
      renderStatButton(el, stats);
      cell.appendChild(el);
      return el;
    }

    function esc(value) {
      return String(value).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
    }

    function render() {
      const rows = $("rows");
      rows.innerHTML = "";
      const visible = sortedUsers(filteredUsers());
      $("empty").hidden = visible.length > 0;
      const active = state.users.filter(u => !u.blocked).length;
      const blocked = state.users.length - active;
      const limited = state.users.filter(hasUserLimits).length;
      $("mTotal").textContent = state.users.length;
      $("mActive").textContent = active;
      $("mBlocked").textContent = blocked;
      $("mLimited").textContent = limited;
      document.querySelectorAll(".metric.filter").forEach(el => {
        el.classList.toggle("active", el.dataset.filter === state.filter);
      });
      document.querySelectorAll("th.sortable").forEach(th => {
        const index = state.sorts.findIndex(item => item.key === th.dataset.sort);
        const sort = index >= 0 ? state.sorts[index] : null;
        th.classList.toggle("sort-asc", Boolean(sort && sort.dir === "asc"));
        th.classList.toggle("sort-desc", Boolean(sort && sort.dir === "desc"));
        th.classList.toggle("sort-secondary", index > 0);
      });

      for (const u of visible) {
        const tr = document.createElement("tr");
        if (u.blocked) tr.className = "blocked";
        tr.innerHTML = `
          <td><div class="name-row"><span class="name"></span><button class="qr-mini" data-act="edit"></button><button class="qr-mini" data-i18n-title="button.qr" title="Показать QR и ссылку" data-act="link">qr</button></div></td>
          <td><div class="comment"></div></td>
          <td class="stat-td"></td>
          <td><div class="date-cell"></div></td>
          <td class="limits-td"></td>
          <td><div class="status-cell">__USER_TOGGLE_BUTTON__<span class="pill ${u.blocked ? "off" : "ok"}">${u.blocked ? t("status.blocked") : t("status.active")}</span></div></td>`;
        tr.querySelector(".name").textContent = u.name;
        const editBtn = tr.querySelector('[data-act="edit"]');
        editBtn.textContent = state.configWritable ? t("button.editShort") : t("button.viewShort");
        editBtn.title = state.configWritable ? t("button.edit") : t("modal.viewUser");
        tr.querySelector(".comment").textContent = u.comment || "—";
        const statsEl = renderStatCell(tr.querySelector(".stat-td"), u.stats);
        tr.querySelector(".date-cell").innerHTML = `<span class="date-help">${esc(formatDate(u.added_at))}<span class="tip">${esc(t("date.lastChanged"))}: ${esc(formatDate(u.updated_at))}</span></span>`;
        renderLimitsCell(tr.querySelector(".limits-td"), u);
        if (u.blocked && u.blocked_at) {
          tr.querySelector(".status-cell .pill").innerHTML = `${esc(t("status.blocked"))}<small>${esc(formatDate(u.blocked_at))}</small>`;
        }
        const linkBtn = tr.querySelector('[data-act="link"]');
        linkBtn.onclick = () => showLink(u, linkBtn);
        if (state.metrics.enabled && state.metrics.available) statsEl.onclick = () => showStats(u);
        editBtn.onclick = () => editUser(u, editBtn);
        __USER_TOGGLE_BINDING__
        rows.appendChild(tr);
      }
    }

    function openDialog(id) { $(id).showModal(); }
    function closeDialog(id, force = false) {
      if (!force && id === "editDialog" && state.editPending) return;
      if (!force && id === "configDialog" && state.configPending) return;
      $(id).close();
    }

    function addUser() {
      if (!state.configWritable) return;
      state.editing = null;
      $("editTitle").textContent = t("modal.addUser");
      if ($("deleteBtn")) $("deleteBtn").hidden = true;
      $("name").value = "";
      $("limit").value = "0";
      $("maxTcpConns").value = "0";
      setDateTimeFields("");
      setUnitValue("dataQuotaValue", "dataQuotaUnit", 0, DATA_UNITS, 1048576);
      setUnitValue("rateLimitUpValue", "rateLimitUpUnit", 0, RATE_UNITS, 1000000);
      setUnitValue("rateLimitDownValue", "rateLimitDownUnit", 0, RATE_UNITS, 1000000);
      $("secret").value = randomSecret();
      $("comment").value = "";
      $("blocked").checked = false;
      setEditReadonly(false);
      openDialog("editDialog");
    }

    function setEditReadonly(readonly) {
      ["name", "limit", "maxTcpConns", "expirationDate", "expirationTime", "dataQuotaValue", "rateLimitUpValue", "rateLimitDownValue", "secret", "comment"].forEach(id => {
        $(id).readOnly = readonly;
      });
      ["dataQuotaUnit", "rateLimitUpUnit", "rateLimitDownUnit"].forEach(id => {
        $(id).disabled = readonly;
      });
      $("blocked").disabled = readonly;
      if ($("genSecret")) {
        $("genSecret").hidden = readonly;
        $("genSecret").style.display = readonly ? "none" : "";
        $("genSecret").disabled = readonly;
      }
      if ($("clearLimitsBtn")) {
        $("clearLimitsBtn").hidden = readonly;
        $("clearLimitsBtn").style.display = readonly ? "none" : "";
        $("clearLimitsBtn").disabled = readonly;
      }
      if ($("deleteBtn")) {
        $("deleteBtn").hidden = readonly || !state.editing;
        $("deleteBtn").style.display = readonly || !state.editing ? "none" : "";
        $("deleteBtn").disabled = readonly;
      }
      if ($("saveBtn")) {
        $("saveBtn").hidden = readonly;
        $("saveBtn").style.display = readonly ? "none" : "";
        $("saveBtn").disabled = readonly;
      }
      $("editCloseBtn").dataset.i18n = readonly ? "common.close" : "common.cancel";
      $("editCloseBtn").textContent = readonly ? t("common.close") : t("common.cancel");
    }

    async function editUser(u, button = null) {
      setButtonBusy(button, true);
      try {
        const data = await request(`api/users/${encodeURIComponent(u.name)}`);
        const user = data.user || {};
        state.editing = user.name || u.name;
        $("editTitle").textContent = `${state.configWritable ? t("modal.editUser") : t("modal.viewUser")}: ${state.editing}`;
        $("name").value = user.name || u.name;
        $("limit").value = user.limit ?? u.limit ?? 0;
        $("maxTcpConns").value = user.max_tcp_conns ?? 0;
        setDateTimeFields(user.expiration || "");
        setUnitValue("dataQuotaValue", "dataQuotaUnit", user.data_quota || 0, DATA_UNITS, 1048576);
        setUnitValue("rateLimitUpValue", "rateLimitUpUnit", user.rate_limit_up || 0, RATE_UNITS, 1000000);
        setUnitValue("rateLimitDownValue", "rateLimitDownUnit", user.rate_limit_down || 0, RATE_UNITS, 1000000);
        $("secret").value = user.secret || "";
        $("comment").value = user.comment || "";
        $("blocked").checked = Boolean(user.blocked);
        setEditReadonly(!state.configWritable);
        openDialog("editDialog");
      } catch (err) {
        toast(err.message);
      } finally {
        setButtonBusy(button, false);
      }
    }

    function formPayload() {
      return {
        name: $("name").value.trim(),
        secret: $("secret").value.trim().toLowerCase(),
        limit: Number($("limit").value || 0),
        max_tcp_conns: Number($("maxTcpConns").value || 0),
        data_quota: readUnitValue("dataQuotaValue", "dataQuotaUnit"),
        expiration: readDateTimeFields(),
        rate_limit_up: readUnitValue("rateLimitUpValue", "rateLimitUpUnit"),
        rate_limit_down: readUnitValue("rateLimitDownValue", "rateLimitDownUnit"),
        comment: $("comment").value.trim(),
        blocked: $("blocked").checked
      };
    }

    function clearUserLimits() {
      if (!state.configWritable) return;
      $("limit").value = "0";
      $("maxTcpConns").value = "0";
      setDateTimeFields("");
      setUnitValue("dataQuotaValue", "dataQuotaUnit", 0, DATA_UNITS, 1048576);
      setUnitValue("rateLimitUpValue", "rateLimitUpUnit", 0, RATE_UNITS, 1000000);
      setUnitValue("rateLimitDownValue", "rateLimitDownUnit", 0, RATE_UNITS, 1000000);
    }

    async function saveUser(ev) {
      ev.preventDefault();
      if (!state.configWritable) return;
      const payload = formPayload();
      const url = state.editing ? `api/users/${encodeURIComponent(state.editing)}` : "api/users/add";
      const method = state.editing ? "PUT" : "POST";
      setEditPending(true, $("saveBtn"));
      try {
        await request(url, { method, body: JSON.stringify(payload) });
        closeDialog("editDialog", true);
        toast(t("common.saved"));
        await load();
      } catch (err) {
        toast(err.message);
      } finally {
        setEditPending(false, $("saveBtn"));
      }
    }

    async function showLink(u, button = null) {
      setButtonBusy(button, true);
      $("linkTitle").textContent = `${t("modal.link")}: ${u.name}`;
      $("qr").removeAttribute("src");
      $("linkText").value = "";
      openDialog("linkDialog");
      try {
        const data = await request(`api/users/${encodeURIComponent(u.name)}/link`);
        $("qr").src = data.qr || "";
        $("linkText").value = data.link || "";
      } catch (err) {
        toast(err.message);
      } finally {
        setButtonBusy(button, false);
      }
    }

    function stopStatsRefresh() {
      if (state.statsTimer) clearInterval(state.statsTimer);
      state.statsTimer = null;
      state.statsUser = null;
    }

    function restartStatsRefresh() {
      if (state.statsTimer) clearInterval(state.statsTimer);
      state.statsTimer = null;
      if (state.statsUser && $("statsDialog") && $("statsDialog").open) {
        const interval = Number($("statsRefreshInterval").value || 5000);
        localStorage.setItem("telemtAdmin.userStatsInterval", String(interval));
        if (interval <= 0) return;
        state.statsTimer = setInterval(() => refreshStatsModalBusy(state.statsUser).catch(err => toast(err.message)), interval);
      }
    }

    async function refreshStatsModal(name) {
      const data = await request(`api/users/${encodeURIComponent(name)}/stats`);
      if (state.statsUser !== name || !$("statsDialog") || !$("statsDialog").open) return;
      const s = userStatsFromMetrics(data.metrics || []);
      $("statsUpdated").textContent = `${t("stats.updated")}: ${new Date().toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US")}`;
      const cards = [
        [formatNumber(s.connections_current), t("stats.activeConnections")],
        [formatNumber(s.connections_total), t("stats.totalConnections")],
        [formatBytes(s.bytes_from_client), t("stats.fromClient")],
        [formatBytes(s.bytes_to_client), t("stats.toClient")],
        [formatNumber(s.unique_ips_current), t("stats.ipNow")],
        [formatNumber(s.unique_ips_recent_window), t("stats.ipWindow")],
        [s.unique_ips_limit ? formatNumber(s.unique_ips_limit) : "∞", t("stats.limit")]
      ];
      $("statsCards").innerHTML = cards.map(([value, label]) => `<div class="stat-card"><b>${esc(value)}</b><span>${esc(label)}</span></div>`).join("");
      if (!data.metrics.length) {
        $("statsMetrics").innerHTML = `<div class="empty">${esc(t("stats.noMetrics"))}</div>`;
        return;
      }
      $("statsMetrics").innerHTML = data.metrics
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(item => `<div class="metric-row"><code>${esc(item.name)}</code><b>${esc(Number(item.value).toLocaleString("ru-RU"))}</b></div>`)
        .join("");
    }

    async function refreshStatsModalBusy(name) {
      if (state.statsLoading) return;
      state.statsLoading = true;
      setButtonBusy($("statsRefreshBtn"), true);
      try {
        await refreshStatsModal(name);
      } finally {
        setButtonBusy($("statsRefreshBtn"), false);
        state.statsLoading = false;
      }
    }

    async function showStats(u) {
      if (!state.metrics.enabled || !state.metrics.available) return;
      stopStatsRefresh();
      state.statsUser = u.name;
      $("statsTitle").textContent = `${t("modal.userStats")}: ${u.name}`;
      $("statsUpdated").textContent = `${t("stats.updated")}...`;
      $("statsCards").innerHTML = `<div class="stat-card"><b>...</b><span>${esc(t("stats.loading"))}</span></div>`;
      $("statsMetrics").innerHTML = "";
      openDialog("statsDialog");
      await refreshStatsModalBusy(u.name);
      restartStatsRefresh();
    }

    function stopTelemtStatsRefresh() {
      if (state.telemtStatsTimer) clearInterval(state.telemtStatsTimer);
      state.telemtStatsTimer = null;
    }

    function restartTelemtStatsRefresh() {
      if (state.telemtStatsTimer) clearInterval(state.telemtStatsTimer);
      state.telemtStatsTimer = null;
      if ($("telemtStatsDialog") && $("telemtStatsDialog").open) {
        const interval = Number($("telemtStatsRefreshInterval").value || 5000);
        localStorage.setItem("telemtAdmin.globalStatsInterval", String(interval));
        if (interval <= 0) return;
        state.telemtStatsTimer = setInterval(() => refreshTelemtStatsModalBusy().catch(err => toast(err.message)), interval);
      }
    }

    async function refreshTelemtStatsModal() {
      const data = await request("api/telemt/stats");
      if (!$("telemtStatsDialog") || !$("telemtStatsDialog").open) return;
      const s = telemtStatsFromMetrics(data.metrics || []);
      $("telemtStatsUpdated").textContent = `${t("stats.updated")}: ${new Date().toLocaleString(state.lang === "ru" ? "ru-RU" : "en-US")}`;
      const cards = [
        [formatDuration(s.uptime_seconds), t("stats.uptime")],
        [formatNumber(s.connections_total), t("stats.totalConnections")],
        [formatNumber(s.connections_bad_total), t("stats.badConnections")],
        [formatNumber(s.handshake_timeouts_total), t("stats.handshakeTimeout")],
        [formatNumber(s.user_entries), t("stats.userEntries")],
        [s.user_telemetry_enabled ? "on" : "off", t("stats.userTelemetry")],
        [`${formatNumber(s.buffer_in_use)} / ${formatNumber(s.buffer_allocated)}`, t("stats.buffers")],
        [`${formatNumber(s.upstream_connect_success)} / ${formatNumber(s.upstream_connect_fail)}`, t("stats.upstream")]
      ];
      $("telemtStatsCards").innerHTML = cards.map(([value, label]) => `<div class="stat-card"><b>${esc(value)}</b><span>${esc(label)}</span></div>`).join("");
      if (!data.metrics.length) {
        $("telemtStatsMetrics").innerHTML = `<div class="empty">${esc(t("stats.globalNoMetrics"))}</div>`;
        return;
      }
      $("telemtStatsMetrics").innerHTML = data.metrics
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(item => {
          const labels = Object.entries(item.labels || {}).map(([k, v]) => `${k}="${v}"`).join(", ");
          const name = labels ? `${item.name}{${labels}}` : item.name;
          return `<div class="metric-row"><code>${esc(name)}</code><b>${esc(Number(item.value).toLocaleString("ru-RU"))}</b></div>`;
        })
        .join("");
    }

    async function refreshTelemtStatsModalBusy() {
      if (state.telemtStatsLoading) return;
      state.telemtStatsLoading = true;
      setButtonBusy($("telemtStatsRefreshBtn"), true);
      try {
        await refreshTelemtStatsModal();
      } finally {
        setButtonBusy($("telemtStatsRefreshBtn"), false);
        state.telemtStatsLoading = false;
      }
    }

    async function showTelemtStats() {
      if (!state.metrics.enabled || !state.metrics.available) return;
      stopTelemtStatsRefresh();
      $("telemtStatsUpdated").textContent = `${t("stats.updated")}...`;
      $("telemtStatsCards").innerHTML = `<div class="stat-card"><b>...</b><span>${esc(t("stats.loading"))}</span></div>`;
      $("telemtStatsMetrics").innerHTML = "";
      openDialog("telemtStatsDialog");
      await refreshTelemtStatsModalBusy();
      restartTelemtStatsRefresh();
    }

    function configItemById(id) {
      return (state.config?.settings || []).find(item => item.id === id);
    }

    function configOriginalValue(item) {
      return item.configured ? String(item.value ?? "") : "";
    }

    function configDraftEntry(item) {
      return state.configDraft[item.id] || null;
    }

    function configCurrentValue(item) {
      const draft = configDraftEntry(item);
      if (draft?.action === "set") return String(draft.value ?? "");
      if (draft?.action === "delete") return "";
      return configOriginalValue(item);
    }

    function configInputKind(item) {
      const type = String(item.type || "").toLowerCase();
      if (type.includes("bool")) return "boolean";
      if (type.includes("array") || type.includes("list") || type.includes("vec") || type.includes("[]")) return "array";
      if (type.includes("float") || type.includes("double") || type.includes("f32") || type.includes("f64")) return "float";
      if (type.includes("int") || type.includes("usize") || /\bu\d+\b/.test(type) || /\bi\d+\b/.test(type)) return "integer";
      return "string";
    }

    function configIsChanged(item) {
      return Boolean(configDraftEntry(item));
    }

    function normalizeDraftValue(item, value) {
      const kind = configInputKind(item);
      if (kind === "boolean") return value ? "true" : "false";
      return String(value ?? "").trim();
    }

    function setConfigDraft(item, action, value = "") {
      const normalized = normalizeDraftValue(item, value);
      if (action === "delete") {
        if (item.configured) state.configDraft[item.id] = { action: "delete", value: "", section: item.section, key: item.key, type: item.type };
        else delete state.configDraft[item.id];
      } else if (!item.configured && !normalized) {
        delete state.configDraft[item.id];
      } else if (item.configured && normalized === configOriginalValue(item)) {
        delete state.configDraft[item.id];
      } else {
        state.configDraft[item.id] = { action: "set", value: normalized, section: item.section, key: item.key, type: item.type };
      }
      updateConfigSaveState();
    }

    function configChangedItems() {
      return Object.keys(state.configDraft)
        .map(id => configItemById(id))
        .filter(Boolean);
    }

    function configChangesNeedRestart() {
      return configChangedItems().some(item => !item.hot_reload);
    }

    function configChangesAffectLinks() {
      const sensitive = new Set(["public_host", "public_port", "tls_domain", "tls_domains", "show_link"]);
      return configChangedItems().some(item => sensitive.has(item.key) || item.id === "general.links.public_host" || item.id === "general.links.public_port");
    }

    function updateConfigSaveState() {
      const changed = Object.keys(state.configDraft).length > 0;
      const save = $("configSaveBtn");
      const reset = $("configResetBtn");
      if (save) {
        save.disabled = state.configPending || (changed && !state.configWritable);
        save.textContent = changed && state.configWritable ? t("common.save") : t("common.close");
        save.classList.toggle("primary", changed && state.configWritable);
      }
      if (reset) {
        reset.hidden = !state.configWritable;
        reset.style.display = state.configWritable ? "" : "none";
        reset.disabled = (!changed && !state.configPending) || !state.configWritable;
        reset.textContent = t("config.cancelChanges");
      }
      const warnings = [];
      if (changed && configChangesNeedRestart()) warnings.push(t("config.restartAfterSave"));
      if (changed && configChangesAffectLinks()) warnings.push(t("config.linksAfterSave"));
      const el = $("configWarnings");
      if (el) el.innerHTML = warnings.map(item => `<div>${esc(item)}</div>`).join("");
      const savebar = document.querySelector(".settings-savebar");
      if (savebar) savebar.hidden = false;
    }

    function settingValueDisplay(item) {
      const draft = configDraftEntry(item);
      if (draft?.action === "delete") return "—";
      if (draft?.action === "set") return draft.value === "" ? "—" : draft.value;
      if (!item.configured && item.default_defined) return item.default;
      if (!item.configured) return "—";
      return item.value === "" ? "—" : item.value;
    }

    function settingDefaultDisplay(item) {
      return item.default_defined ? item.default : "—";
    }

    function settingValueClass(item) {
      if (configIsChanged(item)) return "settings-value diff-default";
      return settingValueDisplay(item) === settingDefaultDisplay(item) ? "settings-value same-default" : "settings-value diff-default";
    }

    function renderConfigValueCell(item) {
      const draft = configDraftEntry(item);
      const changedMark = configIsChanged(item) ? `<span class="settings-changed" title="${esc(t("config.changed"))}">*</span>` : "";
      if (state.configEditing === item.id && state.configWritable) {
        const value = draft?.action === "set" ? draft.value : item.configured ? (item.value === "<hidden>" ? "" : configOriginalValue(item)) : (item.default_defined ? item.default : "");
        const kind = configInputKind(item);
        if (kind === "boolean") {
          const checked = String(value).toLowerCase() === "true" ? "checked" : "";
          return `<label class="checkline"><input class="settings-edit" type="checkbox" data-config-input="${esc(item.id)}" ${checked}> <span>${esc(String(value).toLowerCase() === "true" ? t("common.yes") : t("common.no"))}</span></label>${changedMark}`;
        }
        const inputType = kind === "integer" || kind === "float" ? "number" : "text";
        const step = kind === "float" ? "any" : "1";
        const placeholder = kind === "array" ? t("config.arrayPlaceholder") : "";
        return `<input class="settings-edit" type="${inputType}" step="${step}" value="${esc(value)}" placeholder="${esc(placeholder)}" data-config-input="${esc(item.id)}">${changedMark}`;
      }
      return `${esc(settingValueDisplay(item))}${changedMark}`;
    }

    function renderConfigActions(item) {
      const draft = configDraftEntry(item);
      const status = draft?.action === "delete"
        ? t("config.deletePending")
        : draft?.action === "set" && item.configured
          ? t("config.changePending")
          : draft?.action === "set"
            ? t("config.addPending")
            : item.configured
              ? t("config.configured")
              : t("config.notConfigured");
      const statusClass = draft?.action === "delete"
        ? "delete"
        : draft?.action === "set" && item.configured
          ? "change"
          : draft?.action === "set"
            ? "add"
            : item.configured
              ? "ok"
              : "";
      const badges = `
        <span class="settings-badge ${statusClass}">${esc(status)}</span>
        ${settingReloadBadge(item)}
      `;
      if (!state.configWritable) return `<span class="settings-badges">${badges}</span>`;
      const editTitle = state.configEditing === item.id ? t("config.doneEdit") : t("config.editKey");
      const editText = state.configEditing === item.id ? "✓" : "✎";
      const resetButton = configIsChanged(item) ? `<button type="button" class="settings-icon" data-config-reset="${esc(item.id)}" title="${esc(t("config.resetChange"))}">↺</button>` : "";
      const deleteButton = item.configured ? `<button type="button" class="settings-icon danger" data-config-delete="${esc(item.id)}" title="${esc(t("config.deleteKey"))}">🗑</button>` : "";
      return `
        <span class="settings-actions">
          <span class="settings-badges">${badges}</span>
          <button type="button" class="settings-icon" data-config-edit="${esc(item.id)}" title="${esc(editTitle)}">${editText}</button>
          ${resetButton}
          ${deleteButton}
        </span>
      `;
    }

    function attachConfigSettingHandlers() {
      document.querySelectorAll("[data-config-edit]").forEach(button => {
        button.onclick = () => {
          if (state.configPending) return;
          const id = button.dataset.configEdit;
          state.configEditing = state.configEditing === id ? "" : id;
          renderConfigSettings();
        };
      });
      document.querySelectorAll("[data-config-delete]").forEach(button => {
        button.onclick = () => {
          if (state.configPending) return;
          const item = configItemById(button.dataset.configDelete);
          if (!item) return;
          state.configEditing = "";
          setConfigDraft(item, "delete");
          renderConfigSettings();
        };
      });
      document.querySelectorAll("[data-config-reset]").forEach(button => {
        button.onclick = () => {
          if (state.configPending) return;
          delete state.configDraft[button.dataset.configReset];
          if (state.configEditing === button.dataset.configReset) state.configEditing = "";
          renderConfigSettings();
        };
      });
      document.querySelectorAll("[data-config-input]").forEach(input => {
        const item = configItemById(input.dataset.configInput);
        if (!item) return;
        const apply = () => {
          const value = input.type === "checkbox" ? input.checked : input.value;
          setConfigDraft(item, "set", value);
          if (input.type === "checkbox") renderConfigSettings();
        };
        input.oninput = apply;
        input.onchange = apply;
      });
    }

    async function saveConfigSettings() {
      const changes = Object.entries(state.configDraft).map(([id, draft]) => {
        const item = configItemById(id);
        return {
          section: item?.section || draft.section || "",
          key: item?.key || draft.key || "",
          type: item?.type || draft.type || "unknown",
          action: draft.action,
          value: draft.value
        };
      }).filter(item => item.key);
      if (!changes.length || state.configPending) return;
      setConfigPending(true);
      try {
        const data = await request("api/telemt/config/settings", { method: "POST", body: JSON.stringify({ changes }) });
        state.config = data.config;
        state.configDraft = {};
        state.configEditing = "";
        updateConfigDocsLink();
        renderConfigSettings();
        toast(t("common.saved"));
        await load();
      } catch (err) {
        toast(err.message);
      } finally {
        setConfigPending(false);
        updateConfigSaveState();
      }
    }

    function resetConfigDraft() {
      if (state.configPending) return;
      state.configDraft = {};
      state.configEditing = "";
      renderConfigSettings();
    }

    function tip(text) {
      return text ? ` data-tip="${esc(text)}"` : "";
    }

    function settingReloadBadge(item) {
      const label = item.hot_reload ? "✓" : "↻";
      const title = item.hot_reload ? t("config.noRestartHint") : t("config.restartHint");
      const cls = item.hot_reload ? "ok" : "warn";
      return `<span class="settings-badge state settings-help ${cls}"${tip(title)}>${esc(label)}</span>`;
    }

    function settingDescription(item) {
      const docs = item.description || {};
      return state.lang === "ru" ? (docs.ru || docs.en || "") : (docs.en || docs.ru || "");
    }

    function settingKeyTitle(item) {
      return settingDescription(item) || item.id || item.key;
    }

    function settingKeyDocsUrl(item) {
      return settingDescription(item) ? docsUrl(item.docs_anchor || item.key) : "";
    }

    function settingSectionTitle(section) {
      return section === "top-level" ? t("config.topLevel") : section;
    }

    function configAvailableSections() {
      const all = state.config?.settings || [];
      return Array.from(new Set(all.map(item => item.section))).sort((a, b) => settingSectionTitle(a).localeCompare(settingSectionTitle(b), "ru"));
    }

    function renderConfigSectionOptions() {
      const selected = new Set(state.configSections);
      const sections = configAvailableSections();
      $("configSectionValue").innerHTML = state.configSections.length
        ? state.configSections.map(section => `
            <span class="multi-chip" data-section="${esc(section)}">
              <span>${esc(settingSectionTitle(section))}</span>
              <button type="button" data-remove-section="${esc(section)}">×</button>
            </span>
          `).join("")
        : `<span class="multi-placeholder">${esc(t("config.allSections"))}</span>`;
      $("configSectionValue").querySelectorAll("[data-remove-section]").forEach(button => {
        button.onclick = ev => {
          ev.stopPropagation();
          const section = button.dataset.removeSection;
          state.configSections = state.configSections.filter(item => item !== section);
          renderConfigSettings();
          $("configSettings").scrollTop = 0;
          positionSectionMenu();
        };
      });
      $("configSectionMenu").innerHTML = sections
        .map(section => `
          <label class="multi-option">
            <input type="checkbox" value="${esc(section)}" ${selected.has(section) ? "checked" : ""}>
            <span>${esc(settingSectionTitle(section))}</span>
          </label>
        `).join("") + `<button type="button" class="multi-clear" id="configSectionsClear">${esc(t("config.clearSections"))}</button>`;
      $("configSectionMenu").querySelectorAll('input[type="checkbox"]').forEach(input => {
        input.onchange = () => {
          state.configSections = Array.from($("configSectionMenu").querySelectorAll('input[type="checkbox"]:checked')).map(item => item.value);
          renderConfigSettings();
          $("configSettings").scrollTop = 0;
          positionSectionMenu();
        };
      });
      $("configSectionsClear").onclick = () => {
        state.configSections = [];
        renderConfigSettings();
        $("configSettings").scrollTop = 0;
        positionSectionMenu();
      };
      positionSectionMenu();
    }

    function filteredConfigSettings() {
      const all = state.config?.settings || [];
      const sections = new Set(state.configSections);
      const query = state.configSearch.trim().toLowerCase();
      return all.filter(item => {
        if (!state.configShowAll && !item.configured) return false;
        if (sections.size && !sections.has(item.section)) return false;
        if (query) {
          const haystack = `${item.key} ${item.section} ${settingSectionTitle(item.section)}`.toLowerCase();
          if (!haystack.includes(query)) return false;
        }
        return true;
      });
    }

    function renderConfigSettings() {
      const all = state.config?.settings || [];
      const rows = filteredConfigSettings();
      $("configShowAll").checked = state.configShowAll;
      $("configSearch").value = state.configSearch;
      renderConfigSectionOptions();
      $("configSettingsCount").textContent = t("config.settingsCount", { shown: rows.length, total: all.length });
      if (!rows.length) {
        $("configSettings").innerHTML = `<div class="empty">${esc(t("config.noSettings"))}</div>`;
        updateConfigSaveState();
        return;
      }
      const groups = new Map();
      for (const item of rows) {
        if (!groups.has(item.section)) groups.set(item.section, []);
        groups.get(item.section).push(item);
      }
      $("configSettings").innerHTML = `
          <div class="settings-row head">
            <span>${esc(t("config.key"))}</span>
            <span>${esc(t("config.value"))}</span>
            <span>${esc(t("config.default"))}</span>
            <span></span>
          </div>
        ${Array.from(groups.entries()).map(([section, items]) => `
          <div class="settings-row">
            <div class="settings-title">${esc(settingSectionTitle(section))}</div>
          </div>
          ${items.map(item => `
            <div class="settings-row ${item.configured ? "configured" : "not-configured"} ${configIsChanged(item) ? "changed" : ""} ${configDraftEntry(item)?.action === "delete" ? "delete-pending" : ""}">
              <span class="settings-help settings-key"${tip(settingKeyTitle(item))} data-tip-url="${esc(settingKeyDocsUrl(item))}"><code>${esc(item.key)}</code></span>
              <span class="settings-help ${settingValueClass(item)}"${tip(t("config.typeHint", { type: item.type }))}>${renderConfigValueCell(item)}</span>
              <span class="settings-default ${item.default_defined ? "defined" : ""}">${esc(settingDefaultDisplay(item))}</span>
              ${renderConfigActions(item)}
            </div>
          `).join("")}
        `).join("")}`;
      attachConfigSettingHandlers();
      updateConfigSaveState();
    }

    async function showConfig() {
      state.configShowAll = false;
      state.configSearch = "";
      state.configSections = [];
      state.configDraft = {};
      state.configEditing = "";
      state.configPending = false;
      state.configWritable = false;
      state.config = { settings: [] };
      $("configSettingsCount").textContent = "";
      $("configSearch").value = "";
      $("configSectionValue").innerHTML = `<span class="multi-placeholder">${esc(t("config.allSections"))}</span>`;
      $("configSectionMenu").innerHTML = "";
      $("configSettings").innerHTML = `<div class="empty">${esc(t("stats.loading"))}...</div>`;
      updateConfigSaveState();
      updateConfigDocsLink();
      openDialog("configDialog");
      $("configSettings").scrollTop = 0;
      try {
        const data = await request("api/telemt/config");
        state.config = data;
        state.configWritable = data.config_writable !== false;
        updateConfigDocsLink();
        renderConfigSettings();
        $("configSettings").scrollTop = 0;
      } catch (err) {
        $("configSettings").innerHTML = `<div class="empty">${esc(err.message)}</div>`;
      }
    }

    async function toggleUser(u, button) {
      setButtonBusy(button, true);
      try {
        await request(`api/users/${encodeURIComponent(u.name)}/blocked`, {
          method: "POST",
          body: JSON.stringify({ blocked: !u.blocked })
        });
        toast(u.blocked ? t("toast.enabled") : t("toast.blocked"));
        await load();
      } catch (err) {
        toast(err.message);
      } finally {
        setButtonBusy(button, false);
      }
    }

    async function deleteUser(u) {
      if (!confirm(t("confirm.delete", { name: u.name }))) return;
      setEditPending(true, $("deleteBtn"));
      try {
        await request(`api/users/${encodeURIComponent(u.name)}`, { method: "DELETE" });
        closeDialog("editDialog", true);
        toast(t("common.deleted"));
        await load();
      } catch (err) {
        toast(err.message);
      } finally {
        setEditPending(false, $("deleteBtn"));
      }
    }

    $("addBtn").onclick = addUser;
    $("refreshBtn").onclick = () => load().catch(err => toast(err.message));
    if ($("telemtStatsBtn")) $("telemtStatsBtn").onclick = showTelemtStats;
    if ($("statsRefreshBtn")) $("statsRefreshBtn").onclick = () => state.statsUser && refreshStatsModalBusy(state.statsUser).catch(err => toast(err.message));
    if ($("telemtStatsRefreshBtn")) $("telemtStatsRefreshBtn").onclick = () => refreshTelemtStatsModalBusy().catch(err => toast(err.message));
    if ($("statsRefreshInterval")) $("statsRefreshInterval").onchange = restartStatsRefresh;
    if ($("telemtStatsRefreshInterval")) $("telemtStatsRefreshInterval").onchange = restartTelemtStatsRefresh;
    if ($("configSaveBtn")) $("configSaveBtn").onclick = () => {
      if (Object.keys(state.configDraft).length === 0) closeDialog("configDialog");
      else saveConfigSettings().catch(err => toast(err.message));
    };
    if ($("configResetBtn")) $("configResetBtn").onclick = resetConfigDraft;
    $("configShowAll").onchange = () => {
      state.configShowAll = $("configShowAll").checked;
      renderConfigSettings();
      $("configSettings").scrollTop = 0;
    };
    $("configSectionTrigger").onclick = () => {
      $("configSectionPicker").classList.toggle("open");
      positionSectionMenu();
    };
    $("configSearch").oninput = () => {
      state.configSearch = $("configSearch").value;
      renderConfigSettings();
      $("configSettings").scrollTop = 0;
    };
    document.addEventListener("click", ev => {
      if ($("configSectionPicker") && !$("configSectionPicker").contains(ev.target) && !$("configSectionMenu").contains(ev.target)) {
        $("configSectionPicker").classList.remove("open");
      }
    });
    window.addEventListener("resize", positionSectionMenu);
    $("configDialog").addEventListener("scroll", positionSectionMenu);
    $("configSettings").addEventListener("scroll", positionSectionMenu);
    function showFloatTip(target) {
      const text = target.dataset.tip || "";
      if (!text) return;
      clearTimeout(tipHideTimer);
      tipActiveTarget = target;
      const tipEl = $("floatTip");
      const host = target.closest("dialog") || document.body;
      if (tipEl.parentElement !== host) host.appendChild(tipEl);
      const url = target.dataset.tipUrl || "";
      tipEl.innerHTML = `<div>${esc(text)}</div>${url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(t("config.detailsLink"))}</a>` : ""}`;
      tipEl.classList.add("show");
      positionFloatTip(target);
    }

    function hideFloatTipSoon() {
      const targetAtSchedule = tipActiveTarget;
      clearTimeout(tipHideTimer);
      tipHideTimer = setTimeout(() => {
        if (tipActiveTarget !== targetAtSchedule) return;
        const tipEl = $("floatTip");
        tipEl.classList.remove("show");
        tipEl.innerHTML = "";
        tipEl.style.left = "-9999px";
        tipEl.style.top = "-9999px";
        tipActiveTarget = null;
      }, 120);
    }

    document.addEventListener("mouseover", ev => {
      const target = ev.target.closest("[data-tip]");
      if (target) showFloatTip(target);
    });
    document.addEventListener("mousemove", ev => {
      const target = ev.target.closest("[data-tip]");
      if (target) positionFloatTip(target);
    });
    document.addEventListener("mouseout", ev => {
      const target = ev.target.closest("[data-tip]");
      if (target && !target.contains(ev.relatedTarget) && !$("floatTip").contains(ev.relatedTarget)) hideFloatTipSoon();
    });
    $("floatTip").onmouseenter = () => clearTimeout(tipHideTimer);
    $("floatTip").onmouseleave = hideFloatTipSoon;
    $("langSelect").onchange = () => loadI18n($("langSelect").value).then(load).catch(err => toast(err.message));
    $("themeSelect").onchange = () => setTheme($("themeSelect").value);
    $("refreshInterval").onchange = () => {
      if (state.refreshTimer) clearInterval(state.refreshTimer);
      const interval = Number($("refreshInterval").value);
      localStorage.setItem("telemtAdmin.tableInterval", String(interval));
      state.refreshTimer = interval ? setInterval(() => load().catch(err => toast(err.message)), interval) : null;
    };
    document.querySelectorAll(".metric.filter").forEach(el => {
      el.addEventListener("click", () => {
        state.filter = el.dataset.filter;
        render();
      });
    });
    document.querySelectorAll("th.sortable").forEach(th => {
      th.addEventListener("click", () => {
        cycleSort(th.dataset.sort);
        render();
      });
    });
    $("editForm").addEventListener("submit", saveUser);
    if ($("genSecret")) $("genSecret").onclick = () => {
      if (!state.configWritable || $("genSecret").disabled) return;
      $("secret").value = randomSecret();
    };
    if ($("clearLimitsBtn")) $("clearLimitsBtn").onclick = clearUserLimits;
    if ($("deleteBtn")) $("deleteBtn").onclick = () => state.editing && deleteUser({ name: state.editing });
    $("copyBtn").onclick = async () => {
      await navigator.clipboard.writeText($("linkText").value);
      toast(t("common.copied"));
    };
    document.querySelectorAll("[data-close]").forEach(btn => {
      btn.addEventListener("click", () => closeDialog(btn.dataset.close));
    });
    document.querySelectorAll("dialog").forEach(dialog => {
      dialog.addEventListener("click", (ev) => {
        if (ev.target === dialog) {
          closeDialog(dialog.id);
        }
      });
      dialog.addEventListener("cancel", (ev) => {
        if (dialog.id === "editDialog" && state.editPending) ev.preventDefault();
        if (dialog.id === "configDialog" && state.configPending) ev.preventDefault();
      });
      dialog.addEventListener("close", () => {
        if (dialog.id === "statsDialog") stopStatsRefresh();
        if (dialog.id === "telemtStatsDialog") stopTelemtStatsRefresh();
      });
    });
    function restoreUiPrefs() {
      loadSorts();
      $("refreshInterval").value = localStorage.getItem("telemtAdmin.tableInterval") || "0";
      if ($("statsRefreshInterval")) $("statsRefreshInterval").value = localStorage.getItem("telemtAdmin.userStatsInterval") || "5000";
      if ($("telemtStatsRefreshInterval")) $("telemtStatsRefreshInterval").value = localStorage.getItem("telemtAdmin.globalStatsInterval") || "5000";
      $("logoutBtn").hidden = !state.webAuthEnabled;
      $("refreshInterval").dispatchEvent(new Event("change"));
    }

    async function boot() {
      setTheme(state.theme);
      await loadLocales();
      const preferred = pickLang(state.lang || "__DEFAULT_LANG__");
      await loadI18n(preferred);
      restoreUiPrefs();
      await load();
    }

    boot().catch(err => toast(err.message));
  </script>
</body>
</html>
"""

