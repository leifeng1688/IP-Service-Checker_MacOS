import socket
import ssl
import csv
import requests
import urllib3
import webview
import threading
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── 服務判斷 ──────────────────────────────────────
SERVICE_PROBES = {
    21:  b"",
    22:  b"",
    25:  b"",
    80:  b"HEAD / HTTP/1.0\r\n\r\n",
    110: b"",
    143: b"",
    443: b"HEAD / HTTP/1.0\r\n\r\n",
    3306:b"",
    3389:b"",
    6379:b"PING\r\n",
    8080:b"HEAD / HTTP/1.0\r\n\r\n",
    8443:b"HEAD / HTTP/1.0\r\n\r\n",
}

SERVICE_SIGNATURES = {
    "SSH":   ["SSH-"],
    "FTP":   ["220", "FTP", "FileZilla", "vsftpd", "ProFTPD"],
    "SMTP":  ["220", "ESMTP", "Postfix", "Sendmail", "Exchange"],
    "HTTP":  ["HTTP/1.", "Server:", "Apache", "nginx", "IIS", "Caddy"],
    "MySQL": ["mysql", "MariaDB", "\x4a\x00\x00\x00"],
    "RDP":   ["\x03\x00"],
    "Redis": ["+PONG", "Redis"],
    "POP3":  ["+OK"],
    "IMAP":  ["* OK", "IMAP"],
}

SSL_PORTS = {443, 8443, 465, 993, 995}

def detect_service(banner, port):
    for service, sigs in SERVICE_SIGNATURES.items():
        for sig in sigs:
            if sig.lower() in banner.lower():
                return service
    fallback = {
        21:"FTP?", 22:"SSH?", 25:"SMTP?", 80:"HTTP?",
        110:"POP3?", 143:"IMAP?", 443:"HTTPS?",
        3306:"MySQL?", 3389:"RDP?", 6379:"Redis?",
        8080:"HTTP?", 8443:"HTTPS?"
    }
    return fallback.get(port, "UNKNOWN")

def grab_tls_cert(host, port):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_OPTIONAL
        with socket.create_connection((host, port), timeout=5) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as ssock:
                cert   = ssock.getpeercert()
                cipher = ssock.cipher()
        subject    = dict(x[0] for x in cert.get("subject", []))
        cn         = subject.get("commonName", "")
        san_list   = [val for typ, val in cert.get("subjectAltName", []) if typ == "DNS"]
        not_after  = cert.get("notAfter", "")
        not_before = cert.get("notBefore", "")
        expire_dt  = datetime.strptime(not_after,  "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc) if not_after  else None
        issue_dt   = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc) if not_before else None
        days_left  = (expire_dt - datetime.now(timezone.utc)).days if expire_dt else None
        expired    = days_left is not None and days_left < 0
        issuer     = dict(x[0] for x in cert.get("issuer", []))
        issuer_cn  = issuer.get("commonName", "")
        return {
            "tls_cn": cn, "tls_san": ", ".join(san_list[:5]),
            "tls_issuer": issuer_cn,
            "tls_not_before": issue_dt.strftime("%Y-%m-%d") if issue_dt else "",
            "tls_not_after":  expire_dt.strftime("%Y-%m-%d") if expire_dt else "",
            "tls_days_left": days_left, "tls_expired": expired,
            "tls_cipher": cipher[0] if cipher else "", "tls_error": "",
        }
    except Exception as e:
        return {"tls_cn":"","tls_san":"","tls_issuer":"","tls_not_before":"",
                "tls_not_after":"","tls_days_left":"","tls_expired":"",
                "tls_cipher":"","tls_error":str(e)}

def grab_banner(ip, port):
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((ip, port))
        probe = SERVICE_PROBES.get(port, b"")
        if probe:
            s.send(probe)
        banner = s.recv(1024)
        s.close()
        return banner.decode(errors="replace").strip()
    except Exception as e:
        return f"[ERR] {e}"

def check_tcp(ip, port):
    try:
        s = socket.create_connection((ip, port), timeout=3)
        s.close()
        return True
    except:
        return False

def scan_tcp(ip, port):
    is_open = check_tcp(ip, port)
    cert = {}
    if is_open:
        banner  = grab_banner(ip, port)
        service = detect_service(banner, port)
        if port in SSL_PORTS:
            cert = grab_tls_cert(ip, port)
    else:
        banner, service = "", "CLOSED"
    return {"ip": ip, "port": port,
            "status": "OPEN" if is_open else "CLOSED",
            "service": service, "banner": banner, **cert}

def check_http(url):
    try:
        r      = requests.get(url, timeout=5, verify=False)
        server = r.headers.get("Server", "")
        return {"url": url, "status_code": r.status_code, "server": server, "error": ""}
    except Exception as e:
        return {"url": url, "status_code": "", "server": "", "error": str(e)}

def scan_ssl(host, port):
    cert = grab_tls_cert(host, port)
    return {"host": host, "port": port, **cert}

def build_html_report(results, mode):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def day_cell(r):
        days    = r.get("tls_days_left", "")
        expired = r.get("tls_expired", False)
        if days == "": return ""
        color = "var(--red)" if expired else ("var(--orange)" if isinstance(days, int) and days < 30 else "var(--green)")
        return f'<span style="color:{color};font-weight:600">{days}d</span>'

    if mode == "tcp":
        headers = ["IP","Port","Status","Service","Banner","TLS CN","Issuer","Not After","Days Left","Cipher"]
        rows = "".join(f"""<tr>
            <td>{r.get('ip','')}</td><td>{r.get('port','')}</td>
            <td class="status-{'open' if r.get('status')=='OPEN' else 'closed'}">{r.get('status','')}</td>
            <td>{r.get('service','')}</td>
            <td class="mono small">{r.get('banner','')[:60]}</td>
            <td>{r.get('tls_cn','')}</td><td>{r.get('tls_issuer','')}</td>
            <td>{r.get('tls_not_after','')}</td><td>{day_cell(r)}</td>
            <td class="mono small">{r.get('tls_cipher','')}</td>
        </tr>""" for r in results)

    elif mode == "http":
        headers = ["URL","Status","Server","Error"]
        def code_color(c):
            s = str(c)
            if s.startswith("2"): return "var(--green)"
            if s.startswith("3"): return "var(--orange)"
            return "var(--red)"
        rows = "".join(f"""<tr>
            <td>{r.get('url','')}</td>
            <td style="color:{code_color(r.get('status_code',''))};font-weight:600">{r.get('status_code','')}</td>
            <td>{r.get('server','')}</td>
            <td class="small" style="color:var(--red)">{r.get('error','')}</td>
        </tr>""" for r in results)

    elif mode == "ssl":
        headers = ["Host","Port","CN","SAN","Issuer","Not Before","Not After","Days Left","Cipher","Error"]
        rows = "".join(f"""<tr>
            <td>{r.get('host','')}</td><td>{r.get('port','')}</td>
            <td>{r.get('tls_cn','')}</td><td class="small">{r.get('tls_san','')}</td>
            <td>{r.get('tls_issuer','')}</td>
            <td>{r.get('tls_not_before','')}</td><td>{r.get('tls_not_after','')}</td>
            <td>{day_cell(r)}</td>
            <td class="mono small">{r.get('tls_cipher','')}</td>
            <td style="color:var(--red)" class="small">{r.get('tls_error','')}</td>
        </tr>""" for r in results)

    th = "".join(f"<th>{h}</th>" for h in headers)

    return f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><title>Scan Report</title>
<style>
  :root {{
    --bg:#0d1117; --surface:#161b22; --border:#30363d;
    --text:#c9d1d9; --muted:#8b949e; --accent:#58a6ff;
    --green:#3fb950; --orange:#e3b341; --red:#f85149;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Courier New',monospace; background:var(--bg); color:var(--text); padding:32px; }}
  h1 {{ color:var(--accent); font-size:20px; margin-bottom:6px; letter-spacing:1px; }}
  .meta {{ color:var(--muted); font-size:12px; margin-bottom:24px; }}
  table {{ border-collapse:collapse; width:100%; font-size:12px; }}
  th {{ background:var(--surface); color:var(--accent); padding:10px 14px;
        border:1px solid var(--border); text-align:left; white-space:nowrap; }}
  td {{ padding:8px 14px; border:1px solid var(--border); vertical-align:top; }}
  tr:hover td {{ background:var(--surface); }}
  .status-open  {{ color:var(--green); font-weight:700; }}
  .status-closed {{ color:var(--red); }}
  .mono {{ font-family:'Courier New',monospace; }}
  .small {{ font-size:11px; color:var(--muted); word-break:break-all; }}
</style></head><body>
<h1>🔍 SCAN REPORT</h1>
<div class="meta">產生時間：{now} ｜ 模式：{mode.upper()} ｜ 筆數：{len(results)}</div>
<table><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table>
</body></html>"""


# ── PyWebView API ─────────────────────────────────
class API:
    def __init__(self):
        self.window  = None
        self._results = []
        self._mode    = ""

    def run_scan(self, params):
        mode    = params.get("mode")
        threads = int(params.get("threads", 20))
        self._mode = mode
        self._results = []

        def send(msg, type="log"):
            safe = msg.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace('"', '\\"')
            self.window.evaluate_js(f'appendLog("{safe}", "{type}")')

        def finish(results):
            self._results = results
            payload = json.dumps(results).replace("\\", "\\\\").replace("'", "\\'")
            self.window.evaluate_js(f"renderResults('{payload}', '{mode}')")
            self.window.evaluate_js("scanDone()")

        def do_scan():
            try:
                if mode == "tcp":
                    raw_ips   = params.get("hosts", "")
                    port_strs = params.get("ports", "")
                    ips   = [l.strip() for l in raw_ips.splitlines() if l.strip()]
                    ports = [int(p.strip()) for p in port_strs.replace(",", " ").split() if p.strip().isdigit()]
                    tasks = [(ip, port) for ip in ips for port in ports]
                    results = []
                    with ThreadPoolExecutor(max_workers=threads) as ex:
                        futs = {ex.submit(scan_tcp, ip, port): (ip, port) for ip, port in tasks}
                        for f in as_completed(futs):
                            r = f.result()
                            results.append(r)
                            status = r.get("status","")
                            svc    = r.get("service","")
                            send(f"{r['ip']}:{r['port']} → {status} | {svc}", "open" if status=="OPEN" else "closed")
                    finish(results)

                elif mode == "http":
                    raw_urls = params.get("hosts", "")
                    urls     = [l.strip() for l in raw_urls.splitlines() if l.strip()]
                    results  = []
                    with ThreadPoolExecutor(max_workers=threads) as ex:
                        futs = {ex.submit(check_http, u): u for u in urls}
                        for f in as_completed(futs):
                            r = f.result()
                            results.append(r)
                            code = r.get("status_code","ERR")
                            send(f"{r['url']} → {code} | {r.get('server','')}", "open" if str(code).startswith("2") else "closed")
                    finish(results)

                elif mode == "ssl":
                    raw_hosts = params.get("hosts", "")
                    port      = int(params.get("sslPort", 443))
                    hosts     = [l.strip() for l in raw_hosts.splitlines() if l.strip()]
                    results   = []
                    with ThreadPoolExecutor(max_workers=threads) as ex:
                        futs = {ex.submit(scan_ssl, h, port): h for h in hosts}
                        for f in as_completed(futs):
                            r = f.result()
                            results.append(r)
                            days = r.get("tls_days_left","")
                            cn   = r.get("tls_cn","—")
                            exp  = r.get("tls_not_after","")
                            t    = "closed" if r.get("tls_expired") else ("warn" if isinstance(days,int) and days<30 else "open")
                            send(f"{r['host']}:{r['port']} → CN:{cn} | 到期:{exp} ({days}天)", t)
                    finish(results)

            except Exception as e:
                send(f"[ERROR] {e}", "closed")
                self.window.evaluate_js("scanDone()")

        threading.Thread(target=do_scan, daemon=True).start()
        return {"ok": True}

    def export_html(self, path):
        if not self._results:
            return {"ok": False, "error": "沒有資料"}
        try:
            html = build_html_report(self._results, self._mode)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_csv(self, path):
        if not self._results:
            return {"ok": False, "error": "沒有資料"}
        try:
            if self._results:
                fields = list(self._results[0].keys())
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                    w.writeheader()
                    w.writerows(self._results)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_dialog(self, ext):
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=f"report_{self._mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}",
            file_types=(f"{ext.upper()} files (*.{ext})",)
        )
        return result[0] if result else None

    def open_html_in_browser(self):
        if not self._results:
            return {"ok": False}
        try:
            html  = build_html_report(self._results, self._mode)
            fname = os.path.join(tempfile.gettempdir(),
                                 f"ipcheck_{self._mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
            with open(fname, "w", encoding="utf-8") as f:
                f.write(html)
            import subprocess
            subprocess.Popen(["open", fname])
            return {"ok": True, "path": fname}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ── HTML UI ───────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>IP Service Checker</title>
<style>
  :root {
    --bg:#0d1117; --surface:#161b22; --surface2:#21262d;
    --border:#30363d; --text:#c9d1d9; --muted:#8b949e;
    --accent:#58a6ff; --green:#3fb950; --orange:#e3b341; --red:#f85149;
    --font:'Courier New',monospace;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:var(--font); background:var(--bg); color:var(--text);
         height:100vh; display:flex; flex-direction:column; overflow:hidden; }

  /* ── Header ── */
  header { padding:16px 24px; border-bottom:1px solid var(--border);
           display:flex; align-items:center; gap:12px; }
  header h1 { font-size:15px; color:var(--accent); letter-spacing:2px; }
  .badge { font-size:10px; background:var(--surface2); color:var(--muted);
           padding:2px 8px; border:1px solid var(--border); }

  /* ── Tabs ── */
  .tabs { display:flex; border-bottom:1px solid var(--border); background:var(--surface); }
  .tab  { padding:10px 24px; font-size:12px; cursor:pointer; color:var(--muted);
          border-bottom:2px solid transparent; transition:all .15s; letter-spacing:1px; }
  .tab:hover  { color:var(--text); }
  .tab.active { color:var(--accent); border-bottom-color:var(--accent); }

  /* ── Main ── */
  .main { flex:1; display:flex; overflow:hidden; }

  /* ── Left Panel ── */
  .panel-left { width:320px; border-right:1px solid var(--border);
                display:flex; flex-direction:column; overflow:hidden; }
  .panel-body { flex:1; overflow-y:auto; padding:20px; }
  .field { margin-bottom:16px; }
  label  { display:block; font-size:11px; color:var(--muted);
           letter-spacing:1px; margin-bottom:6px; }
  textarea, input[type=text], input[type=number] {
    width:100%; background:var(--surface2); border:1px solid var(--border);
    color:var(--text); font-family:var(--font); font-size:12px;
    padding:8px 10px; outline:none; resize:vertical;
    transition:border-color .15s;
  }
  textarea:focus, input:focus { border-color:var(--accent); }
  textarea { min-height:100px; }
  .row2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }

  /* ── Buttons ── */
  .btn { width:100%; padding:10px; font-family:var(--font); font-size:12px;
         cursor:pointer; border:1px solid; letter-spacing:1px; transition:all .15s; }
  .btn-primary { background:var(--accent); color:#0d1117; border-color:var(--accent); font-weight:700; }
  .btn-primary:hover { background:#79c0ff; }
  .btn-primary:disabled { opacity:.4; cursor:not-allowed; }
  .btn-ghost { background:transparent; color:var(--muted); border-color:var(--border); }
  .btn-ghost:hover { color:var(--text); border-color:var(--text); }
  .btn-ghost:disabled { opacity:.3; cursor:not-allowed; }
  .btn-row { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }

  /* ── Right Panel ── */
  .panel-right { flex:1; display:flex; flex-direction:column; overflow:hidden; }

  /* ── Log ── */
  .log-wrap { flex:1; overflow-y:auto; padding:16px 20px; }
  .log-line { font-size:12px; padding:3px 0; border-bottom:1px solid #1c2128; }
  .log-line.open   { color:var(--green); }
  .log-line.closed { color:var(--red); }
  .log-line.warn   { color:var(--orange); }
  .log-line.log    { color:var(--muted); }

  /* ── Results Table ── */
  .table-wrap { flex:1; overflow:auto; padding:16px 20px; display:none; }
  table { border-collapse:collapse; width:100%; font-size:12px; white-space:nowrap; }
  th { background:var(--surface); color:var(--accent); padding:8px 12px;
       border:1px solid var(--border); position:sticky; top:0; }
  td { padding:6px 12px; border:1px solid var(--border); }
  tr:hover td { background:var(--surface2); }
  .s-open   { color:var(--green); font-weight:700; }
  .s-closed { color:var(--red); }
  .muted    { color:var(--muted); font-size:11px; }
  .day-ok   { color:var(--green); font-weight:600; }
  .day-warn { color:var(--orange); font-weight:600; }
  .day-err  { color:var(--red); font-weight:600; }

  /* ── Bottom Bar ── */
  .bottom-bar { padding:10px 20px; border-top:1px solid var(--border);
                display:flex; align-items:center; gap:10px; }
  .view-toggle { display:flex; gap:0; }
  .vtab { padding:5px 14px; font-size:11px; cursor:pointer; color:var(--muted);
          border:1px solid var(--border); background:transparent; font-family:var(--font); }
  .vtab:first-child { border-right:0; }
  .vtab.active { color:var(--accent); border-color:var(--accent); background:var(--surface); }
  .spacer { flex:1; }
  #statusBar { font-size:11px; color:var(--muted); }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width:6px; height:6px; }
  ::-webkit-scrollbar-track { background:var(--bg); }
  ::-webkit-scrollbar-thumb { background:var(--border); }
</style>
</head>
<body>

<header>
  <h1>⬡ IP SERVICE CHECKER</h1>
  <span class="badge">TCP · HTTP · SSL</span>
</header>

<div class="tabs">
  <div class="tab active" onclick="switchMode('tcp')">TCP</div>
  <div class="tab" onclick="switchMode('http')">HTTP</div>
  <div class="tab" onclick="switchMode('ssl')">SSL</div>
</div>

<div class="main">
  <!-- Left Panel -->
  <div class="panel-left">
    <div class="panel-body">

      <!-- TCP -->
      <div id="form-tcp">
        <div class="field">
          <label>TARGET IPs（每行一筆）</label>
          <textarea id="tcp-hosts" placeholder="192.168.1.1&#10;10.0.0.1&#10;8.8.8.8"></textarea>
        </div>
        <div class="field">
          <label>PORTS（空格或逗號分隔）</label>
          <input type="text" id="tcp-ports" value="80 443 8080 8443">
        </div>
        <div class="field">
          <label>THREADS</label>
          <input type="number" id="tcp-threads" value="50" min="1" max="200">
        </div>
      </div>

      <!-- HTTP -->
      <div id="form-http" style="display:none">
        <div class="field">
          <label>TARGET URLs（每行一筆）</label>
          <textarea id="http-hosts" placeholder="https://example.com&#10;https://192.168.1.1:8443&#10;http://10.0.0.1"></textarea>
        </div>
        <div class="field">
          <label>THREADS</label>
          <input type="number" id="http-threads" value="20" min="1" max="100">
        </div>
      </div>

      <!-- SSL -->
      <div id="form-ssl" style="display:none">
        <div class="field">
          <label>TARGET HOSTS（每行一筆）</label>
          <textarea id="ssl-hosts" placeholder="www.google.com.tw&#10;8.8.8.8&#10;example.com"></textarea>
        </div>
        <div class="row2">
          <div class="field">
            <label>PORT</label>
            <input type="number" id="ssl-port" value="443" min="1" max="65535">
          </div>
          <div class="field">
            <label>THREADS</label>
            <input type="number" id="ssl-threads" value="20" min="1" max="100">
          </div>
        </div>
      </div>

      <button class="btn btn-primary" id="btnRun" onclick="runScan()">▶ RUN SCAN</button>

      <div class="btn-row" style="margin-top:16px">
        <button class="btn btn-ghost" id="btnHtml" onclick="exportHTML()" disabled>↗ HTML</button>
        <button class="btn btn-ghost" id="btnCsv"  onclick="exportCSV()"  disabled>↓ CSV</button>
      </div>
      <button class="btn btn-ghost" id="btnBrowser" onclick="openBrowser()"
              style="margin-top:8px" disabled>⧉ 在瀏覽器開啟報告</button>
    </div>
  </div>

  <!-- Right Panel -->
  <div class="panel-right">
    <div class="log-wrap"   id="logWrap"></div>
    <div class="table-wrap" id="tableWrap"></div>
  </div>
</div>

<div class="bottom-bar">
  <div class="view-toggle">
    <button class="vtab active" id="vLog"   onclick="switchView('log')">LOG</button>
    <button class="vtab"        id="vTable" onclick="switchView('table')">TABLE</button>
  </div>
  <div class="spacer"></div>
  <span id="statusBar">準備就緒</span>
</div>

<script>
let currentMode = 'tcp';

function switchMode(m) {
  currentMode = m;
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', ['tcp','http','ssl'][i]===m));
  ['tcp','http','ssl'].forEach(x => document.getElementById('form-'+x).style.display = x===m?'block':'none');
}

function switchView(v) {
  document.getElementById('vLog').classList.toggle('active', v==='log');
  document.getElementById('vTable').classList.toggle('active', v==='table');
  document.getElementById('logWrap').style.display   = v==='log'   ? 'block' : 'none';
  document.getElementById('tableWrap').style.display = v==='table' ? 'block' : 'none';
}

function appendLog(msg, type) {
  const wrap = document.getElementById('logWrap');
  const line = document.createElement('div');
  line.className = 'log-line ' + type;
  line.textContent = new Date().toLocaleTimeString('zh-TW', {hour12:false}) + '  ' + msg;
  wrap.appendChild(line);
  wrap.scrollTop = wrap.scrollHeight;
}

function dayClass(d) {
  if (d === null || d === '') return '';
  if (d < 0)  return 'day-err';
  if (d < 30) return 'day-warn';
  return 'day-ok';
}

function renderResults(payload, mode) {
  const results = JSON.parse(payload);
  const wrap    = document.getElementById('tableWrap');
  wrap.innerHTML = '';

  let headers = [], rows = '';

  if (mode === 'tcp') {
    headers = ['IP','Port','Status','Service','Banner','TLS CN','Issuer','Not After','Days Left','Cipher'];
    rows = results.map(r => `<tr>
      <td>${r.ip||''}</td><td>${r.port||''}</td>
      <td class="${r.status==='OPEN'?'s-open':'s-closed'}">${r.status||''}</td>
      <td>${r.service||''}</td>
      <td class="muted">${(r.banner||'').slice(0,60)}</td>
      <td>${r.tls_cn||''}</td><td>${r.tls_issuer||''}</td>
      <td>${r.tls_not_after||''}</td>
      <td class="${dayClass(r.tls_days_left)}">${r.tls_days_left!==''&&r.tls_days_left!=null?r.tls_days_left+'d':''}</td>
      <td class="muted">${r.tls_cipher||''}</td>
    </tr>`).join('');
  } else if (mode === 'http') {
    headers = ['URL','Status','Server','Error'];
    rows = results.map(r => {
      const c = String(r.status_code||'');
      const col = c.startsWith('2')?'var(--green)':c.startsWith('3')?'var(--orange)':'var(--red)';
      return `<tr>
        <td>${r.url||''}</td>
        <td style="color:${col};font-weight:600">${r.status_code||''}</td>
        <td>${r.server||''}</td>
        <td class="muted" style="color:var(--red)">${r.error||''}</td>
      </tr>`;
    }).join('');
  } else if (mode === 'ssl') {
    headers = ['Host','Port','CN','SAN','Issuer','Not Before','Not After','Days Left','Cipher','Error'];
    rows = results.map(r => `<tr>
      <td>${r.host||''}</td><td>${r.port||''}</td>
      <td>${r.tls_cn||''}</td>
      <td class="muted">${r.tls_san||''}</td>
      <td>${r.tls_issuer||''}</td>
      <td>${r.tls_not_before||''}</td><td>${r.tls_not_after||''}</td>
      <td class="${dayClass(r.tls_days_left)}">${r.tls_days_left!==''&&r.tls_days_left!=null?r.tls_days_left+'d':''}</td>
      <td class="muted">${r.tls_cipher||''}</td>
      <td class="muted" style="color:var(--red)">${r.tls_error||''}</td>
    </tr>`).join('');
  }

  const th = headers.map(h=>`<th>${h}</th>`).join('');
  wrap.innerHTML = `<table><thead><tr>${th}</tr></thead><tbody>${rows}</tbody></table>`;
}

function scanDone() {
  document.getElementById('btnRun').disabled     = false;
  document.getElementById('btnRun').textContent  = '▶ RUN SCAN';
  document.getElementById('btnHtml').disabled    = false;
  document.getElementById('btnCsv').disabled     = false;
  document.getElementById('btnBrowser').disabled = false;
  document.getElementById('statusBar').textContent = '完成 ' + new Date().toLocaleTimeString('zh-TW',{hour12:false});
  switchView('table');
}

function runScan() {
  const btn = document.getElementById('btnRun');
  btn.disabled    = true;
  btn.textContent = '⏳ SCANNING...';
  document.getElementById('btnHtml').disabled    = true;
  document.getElementById('btnCsv').disabled     = true;
  document.getElementById('btnBrowser').disabled = true;
  document.getElementById('logWrap').innerHTML   = '';
  document.getElementById('tableWrap').innerHTML = '';
  document.getElementById('statusBar').textContent = '掃描中...';
  switchView('log');

  let params = { mode: currentMode };
  if (currentMode === 'tcp') {
    params.hosts   = document.getElementById('tcp-hosts').value;
    params.ports   = document.getElementById('tcp-ports').value;
    params.threads = document.getElementById('tcp-threads').value;
  } else if (currentMode === 'http') {
    params.hosts   = document.getElementById('http-hosts').value;
    params.threads = document.getElementById('http-threads').value;
  } else if (currentMode === 'ssl') {
    params.hosts   = document.getElementById('ssl-hosts').value;
    params.sslPort = document.getElementById('ssl-port').value;
    params.threads = document.getElementById('ssl-threads').value;
  }
  window.pywebview.api.run_scan(params);
}

async function exportHTML() {
  const path = await window.pywebview.api.save_dialog('html');
  if (!path) return;
  const r = await window.pywebview.api.export_html(path);
  document.getElementById('statusBar').textContent = r.ok ? '✓ HTML 已儲存' : '✗ ' + r.error;
}

async function exportCSV() {
  const path = await window.pywebview.api.save_dialog('csv');
  if (!path) return;
  const r = await window.pywebview.api.export_csv(path);
  document.getElementById('statusBar').textContent = r.ok ? '✓ CSV 已儲存' : '✗ ' + r.error;
}

async function openBrowser() {
  const r = await window.pywebview.api.open_html_in_browser();
  document.getElementById('statusBar').textContent = r.ok ? '✓ 已在瀏覽器開啟' : '✗ ' + r.error;
}
</script>
</body></html>"""


# ── 啟動 App ──────────────────────────────────────
if __name__ == "__main__":
    api    = API()
    window = webview.create_window(
        title="IP Service Checker",
        html=HTML,
        js_api=api,
        width=1100,
        height=720,
        min_size=(800, 500),
    )
    api.window = window
    webview.start(debug=False)
