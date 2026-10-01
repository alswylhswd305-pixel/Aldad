#!/usr/bin/env python3
"""
ضاد IDE — بيئة برمجة مستقلة للغة الضاد.
شغّلها:  python aldad_ide.py      (or double-click START_ALDAD.cmd)
تنفتح في المتصفح على جهازك فقط (127.0.0.1) — ما تطلع على النت.
الملفات تنحفظ في:  المستندات/الضاد
"""
import base64
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
SOURCE_HERE = Path(__file__).resolve().parent
DAD = HERE / "dad.py"
DAD_RUNNER = HERE / "DadRunner.exe"

def _work_dir():
    """اختر مجلد كتابة مضمون قدر الإمكان على ويندوز مع بدائل تلقائية."""
    candidates = []
    if os.environ.get('DAD_WORK_DIR'):
        candidates.append(Path(os.environ['DAD_WORK_DIR']))
    home = Path.home()
    candidates.append(home / "Documents" / "Aldad")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Aldad" / "Projects")
    candidates.append(HERE / "files")
    last = None
    for c in candidates:
        try:
            c.mkdir(parents=True, exist_ok=True)
            probe = c / ".dad_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return c
        except Exception as e:
            last = e
    raise RuntimeError(f"ما قدرت أفتح مجلد للحفظ: {last}")

WORK = _work_dir()
TOKEN = secrets.token_hex(16)
DAD_VERSION = "1.9.17"
RUN_TIMEOUT = 120


def safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\n\r\t]', "", (name or "").strip()) or "program"
    if not name.endswith((".ضاد", ".dad")):
        name += ".dad"
    return name[:120]


def _dad_command(args, tmp):
    """أمر تشغيل محرك الضاد من السورس أو من نسخة EXE المجمعة."""
    if getattr(sys, "frozen", False) and DAD_RUNNER.exists():
        return [str(DAD_RUNNER), *args, str(tmp)]
    return [sys.executable, str(DAD), *args, str(tmp)]

def dad(args, code=None, answers="", timeout=RUN_TIMEOUT):
    """يشغّل محرك الضاد على ملف مؤقت داخل مجلد الضاد."""
    tmp = WORK / ".run.dad"
    if code is not None:
        tmp.write_text(code, encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", DAD_OUT_DIR=str(WORK), DAD_MEDIA="1")
    try:
        r = subprocess.run(_dad_command(args, tmp), input=answers.encode("utf-8"),
                           capture_output=True, timeout=timeout, cwd=str(WORK), env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return 1, "", f"⚠ البرنامج أخذ أكثر من {RUN_TIMEOUT} ثانية، فوقفته."


MEDIA_MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".aac": "audio/aac",
              ".flac": "audio/flac", ".mp4": "video/mp4", ".webm": "video/webm", ".ogv": "video/ogg", ".mov": "video/quicktime",
              ".m4v": "video/mp4", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
              ".webp": "image/webp", ".bmp": "image/bmp", ".svg": "image/svg+xml"}
MEDIA_MAX = 40 * 1024 * 1024


def media_item(line):
    """«@@DAD_MEDIA@@kind|path» ← عنصر يعرضه المتصفح، أو رسالة عربية لو ما ينفع."""
    kind, _, path = line[len("@@DAD_MEDIA@@"):].partition("|")
    p = Path(path.strip())
    try:
        size = p.stat().st_size
    except OSError:
        return None, "تعذر فتح الملف: " + p.name
    if size > MEDIA_MAX:
        return None, f"الملف «{p.name}» كبير ({size // (1024 * 1024)} ميجا) — الحد 40 ميجا."
    mime = MEDIA_MIME.get(p.suffix.lower(), "application/octet-stream")
    return {"name": p.name, "kind": kind, "src": f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()}, None


def run_program(code, answers):
    rc, out, err = dad(["run"], code, answers)
    images, lines, apps = [], [], []
    for line in out.splitlines():
        ma = re.match(r"^@@DAD_APP@@(.+)$", line)
        if ma:
            p = Path(ma.group(1).strip())
            try:
                apps.append({"name": p.stem, "html": p.read_text(encoding="utf-8")})
            except OSError:
                lines.append("تعذر فتح البرنامج: " + p.name)
            continue
        if line.startswith("@@DAD_MEDIA@@"):
            item, msg = media_item(line)
            if item: images.append(item)
            else: lines.append(msg)
            continue
        m = re.match(r"^@@DAD_IMAGE@@(.+)$", line)
        if m:
            p = Path(m.group(1).strip())
            p = p if p.is_absolute() else WORK / p
            try:
                images.append({"name": p.name, "src": "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()})
            except OSError:
                lines.append("تعذر فتح الرسمة: " + p.name)
        else:
            lines.append(line)
    return {"ok": rc == 0, "out": "\n".join(lines), "err": err, "images": images, "apps": apps}


class LiveRun:
    """تشغيل تفاعلي: البرنامج يوقف عند كل «اسأل» والـIDE يرد وقتها — يشتغل مع كرر/لكل/إذا/الدوال بدون عدّ مقدم."""
    RUNS = {}
    LOCK = threading.Lock()

    def __init__(self, code):
        import queue, uuid, time
        self.id = uuid.uuid4().hex[:12]; self.q = queue.Queue(); self.err = []; self.images = []; self.apps = []
        self.t = time.time()
        tmp = WORK / f".live_{self.id}.dad"; tmp.write_text(code, encoding="utf-8"); self.tmp = tmp
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", DAD_OUT_DIR=str(WORK), DAD_INTERACTIVE="1", DAD_MEDIA="1")
        self.p = subprocess.Popen(_dad_command(["run"], tmp), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, encoding="utf-8", errors="replace", cwd=str(WORK), env=env,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        threading.Thread(target=self._pump_out, daemon=True).start()
        threading.Thread(target=lambda: self.err.append(self.p.stderr.read()), daemon=True).start()
        with LiveRun.LOCK:
            LiveRun.RUNS[self.id] = self
        LiveRun.reap()

    def _pump_out(self):
        for line in self.p.stdout:
            self.q.put(line)
        self.q.put(None)

    @classmethod
    def reap(cls):
        import time
        with cls.LOCK:
            for k, r in list(cls.RUNS.items()):
                if time.time() - r.t > 900:                   # تشغيل متروك أكثر من ربع ساعة
                    r.stop()

    def stop(self):
        try: self.p.kill()
        except Exception: pass
        LiveRun.RUNS.pop(self.id, None)
        try: self.tmp.unlink()
        except OSError: pass

    def step(self, timeout=RUN_TIMEOUT):
        """يقرأ الناتج لين سؤال جديد أو نهاية البرنامج."""
        import queue, time
        self.t = time.time(); lines = []; deadline = time.time() + timeout
        while True:
            try:
                line = self.q.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                self.stop()
                return {"id": self.id, "status": "done", "ok": False, "out": "\n".join(lines),
                        "err": f"⚠ البرنامج أخذ أكثر من {timeout} ثانية بدون ما يسأل أو يخلص، فوقفته.", "images": self.images, "apps": self.apps}
            if line is None:
                self.p.wait(timeout=10)
                time.sleep(0.05)
                err = "".join(self.err)
                rc = self.p.returncode
                LiveRun.RUNS.pop(self.id, None)
                try: self.tmp.unlink()
                except OSError: pass
                return {"id": self.id, "status": "done", "ok": rc == 0, "out": "\n".join(lines), "err": err,
                        "images": self.images, "apps": self.apps}
            line = line.rstrip("\r\n")
            if line.startswith("@@DAD_ASK@@"):
                if lines and lines[-1] == "":
                    lines.pop()                                  # السطر الفاضي اللي قبل علامة السؤال مو من البرنامج
                try: prompt = json.loads(line[len("@@DAD_ASK@@"):])
                except ValueError: prompt = "سؤال"
                return {"id": self.id, "status": "ask", "prompt": prompt, "out": "\n".join(lines)}
            ma = re.match(r"^@@DAD_APP@@(.+)$", line)
            if ma:
                p = Path(ma.group(1).strip())
                try: self.apps.append({"name": p.stem, "html": p.read_text(encoding="utf-8")})
                except OSError: lines.append("تعذر فتح البرنامج: " + p.name)
                continue
            if line.startswith("@@DAD_MEDIA@@"):
                item, msg = media_item(line)
                if item: self.images.append(item)
                else: lines.append(msg)
                continue
            mi = re.match(r"^@@DAD_IMAGE@@(.+)$", line)
            if mi:
                p = Path(mi.group(1).strip()); p = p if p.is_absolute() else WORK / p
                try: self.images.append({"name": p.name, "src": "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()})
                except OSError: lines.append("تعذر فتح الرسمة: " + p.name)
                continue
            lines.append(line)

    def answer(self, text):
        try:
            self.p.stdin.write(str(text).replace("\n", " ") + "\n"); self.p.stdin.flush()
        except OSError:
            pass
        return self.step()


class Terminal:
    """جلسة طرفية وحدة شغالة طول الوقت — الذاكرة تظل بين الأسطر."""
    def __init__(self):
        self.p = None; self.lock = threading.Lock(); self.q = None; self.waiting = False

    def _start(self):
        import queue
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", DAD_OUT_DIR=str(WORK), DAD_MEDIA="1")
        cmd = [str(DAD_RUNNER), "repl"] if getattr(sys, "frozen", False) and DAD_RUNNER.exists() else [sys.executable, str(DAD), "repl"]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8", cwd=str(WORK), env=env,
                                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.q = queue.Queue()
        def pump(p=self.p, q=self.q):
            for line in p.stdout:
                q.put(line)
        threading.Thread(target=pump, daemon=True).start()

    def send(self, obj, timeout=RUN_TIMEOUT):
        import queue
        with self.lock:
            if self.waiting and 'code' in obj:
                return {'ok':False, 'out':'', 'err':'⚠ جاوب السؤال الحالي قبل كتابة أمر جديد.'}
            if self.p is None or self.p.poll() is not None:
                self._start()
            self.p.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n"); self.p.stdin.flush()
            try:
                response = json.loads(self.q.get(timeout=timeout))
                self.waiting = response.get('event') == 'question'
                return response
            except queue.Empty:
                self.p.kill(); self.p = None; self.waiting = False
                return {"ok": False, "out": "", "err": f"⚠ السطر أخذ أكثر من {timeout} ثانية فوقفته — وانمسحت ذاكرة الطرفية."}


TERM = Terminal()


def with_images(r):
    images, lines = [], []
    for line in (r.get("out") or "").splitlines():
        if line.startswith("@@DAD_MEDIA@@"):
            item, msg = media_item(line)
            if item: images.append(item)
            else: lines.append(msg)
            continue
        m = re.match(r"^@@DAD_IMAGE@@(.+)$", line)
        if m:
            p = Path(m.group(1).strip()); p = p if p.is_absolute() else WORK / p
            try: images.append({"name": p.name, "src": "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()})
            except OSError: lines.append("تعذر فتح الرسمة")
        else:
            lines.append(line)
    r["out"] = "\n".join(lines); r["images"] = images
    return r


def questions(code):
    rc, out, _ = dad(["questions"], code, timeout=30)
    try:
        return json.loads(out.strip() or "[]")
    except ValueError:
        return []

def _exe_name(name):
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(str(name or "program")).stem).strip("_") or "AldadApp"
    return name[:60]


def _launcher_source(code):
    return (
        "from pathlib import Path\nimport tempfile, webbrowser\nimport dad, ui\n"
        + "SOURCE = " + repr(code) + "\n"
        + "d=Path(tempfile.mkdtemp(prefix='aldad_')); p=d/'program.dad'; p.write_text(SOURCE,encoding='utf-8')\n"
        + "if ui.is_ui(SOURCE):\n    pr=ui.compile_ui(SOURCE); h=d/'app.html'; h.write_text(ui.to_html(pr),encoding='utf-8'); webbrowser.open(h.as_uri()); input('اضغط Enter للإغلاق...')\n"
        + "else:\n    dad.run(p)\n    try: input('\\nاضغط Enter للإغلاق...')\n    except EOFError: pass\n"
    )

def build_exe_program(code, name):
    """يبني EXE على ويندوز باستخدام PyInstaller. يبقى محرك الضاد نفسه داخل EXE."""
    if os.name != "nt":
        return {"ok": False, "error": "بناء EXE متاح على Windows فقط."}
    if getattr(sys, "frozen", False):
        return {"ok": False, "error": "لبناء برنامج EXE جديد استخدم نسخة السورس وشغّل BUILD_ALDAD_IDE_EXE.cmd. نسخة EXE الجاهزة تشغّل الضاد لكنها ما تحمل PyInstaller داخلها."}
    # برامج IDE اللي تستخدم جسر الملفات تحتاج المضيف، فلا نبني ملف مكسور بصمت.
    if re.search(r"اعرض\s+(?:ملفات|الملفات)|افتح\s+(?:المختار|الملف المختار)|شغ[للّ]\s+الكود|ابن\s+.*EXE", code):
        return {"ok": False, "error": "هذا برنامج IDE يعتمد على جسر ضاد IDE. استخدم BUILD_ALDAD_IDE_EXE.cmd لبناء نسخة IDE كاملة."}
    try:
        chk = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, timeout=30)
        if chk.returncode != 0:
            ins = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], capture_output=True, timeout=300)
            if ins.returncode != 0:
                return {"ok": False, "error": "ما قدرت أثبت PyInstaller. شغّل: python -m pip install pyinstaller"}
    except Exception as e:
        return {"ok": False, "error": "تعذر تجهيز PyInstaller: " + str(e)}
    build_dir = WORK / ".exe_build"
    dist = WORK / "EXE"
    build_dir.mkdir(parents=True, exist_ok=True); dist.mkdir(parents=True, exist_ok=True)
    exe = _exe_name(name)
    launcher = build_dir / (exe + "_launcher.py")
    launcher.write_text(_launcher_source(code), encoding="utf-8")
    compile(launcher.read_text(encoding='utf-8'), str(launcher), 'exec')
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
           "--name", exe, "--distpath", str(dist), "--workpath", str(build_dir / "work"),
           "--specpath", str(build_dir / "spec"), "--paths", str(SOURCE_HERE),
           "--hidden-import", "ui", "--hidden-import", "vnext", str(launcher)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, cwd=str(SOURCE_HERE))
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "بناء EXE أخذ أكثر من 15 دقيقة وتوقف."}
    path = dist / (exe + ".exe")
    if r.returncode != 0 or not path.exists():
        tail = (r.stderr or r.stdout or "").strip()[-1800:]
        return {"ok": False, "error": "PyInstaller فشل:\n" + tail}
    return {"ok": True, "path": str(path)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _allowed(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost") and self.headers.get("X-Dad-Token") == TOKEN

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            page = PAGE.replace("__VER__", DAD_VERSION).replace("__TOKEN__", TOKEN).replace("__WORK__", json.dumps(str(WORK), ensure_ascii=False))
            return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")
        return self._send(404, {"error": "مو موجود"})

    def do_POST(self):
        if not self._allowed():
            return self._send(403, {"error": "ممنوع"})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(min(n, 5_000_000)).decode("utf-8") or "{}")
        except ValueError:
            return self._send(400, {"error": "طلب غلط"})
        path = urlparse(self.path).path
        if path == "/questions":
            return self._send(200, {"list": questions(data.get("code", ""))})
        if path == "/run_start":
            return self._send(200, LiveRun(data.get("code", "")).step())
        if path == "/run_answer":
            r = LiveRun.RUNS.get(str(data.get("id", "")))
            if not r:
                return self._send(200, {"status": "done", "ok": False, "out": "", "err": "⚠ هذا التشغيل انتهى أو انوقف — اضغط ▶ من جديد."})
            return self._send(200, r.answer(data.get("answer", "")))
        if path == "/run_stop":
            r = LiveRun.RUNS.get(str(data.get("id", "")))
            if r: r.stop()
            return self._send(200, {"stopped": True})
        if path == "/run":
            ans = data.get("answers")
            return self._send(200, run_program(data.get("code", ""), ("\n".join(ans) + "\n") if ans else ""))
        if path == "/list":
            files = sorted((p for p in WORK.glob("*") if p.suffix in (".ضاد", ".dad") and not p.name.startswith(".")),
                           key=lambda p: p.stat().st_mtime, reverse=True)
            return self._send(200, {"files": [p.name for p in files]})
        if path == "/open":
            p = WORK / safe_name(data.get("name", ""))
            if not p.exists():
                return self._send(404, {"error": "الملف مو موجود"})
            return self._send(200, {"name": p.name, "code": p.read_text(encoding="utf-8")})
        if path == "/save":
            p = WORK / safe_name(data.get("name", ""))
            p.write_text(data.get("code", ""), encoding="utf-8")
            return self._send(200, {"name": p.name, "saved": True})
        if path == "/build_exe":
            return self._send(200, build_exe_program(data.get("code", ""), data.get("name", "program")))
        if path == "/repl":
            return self._send(200, with_images(TERM.send({"code": data.get("code", ""), "answers": data.get("answers") or [], 'live':True})))
        if path == '/repl_answer':
            reply = {'cancel':True} if data.get('cancel') else {'answer':data.get('answer','')}
            return self._send(200, with_images(TERM.send(reply)))
        if path == "/repl_reset":
            if TERM.waiting: TERM.send({'cancel':True})
            return self._send(200, TERM.send({"reset": True}))
        if path == "/rules":
            p = HERE / "rules_ar.md"
            return self._send(200, {"md": p.read_text(encoding="utf-8") if p.exists() else "القاموس مو موجود"})
        if path == "/example":
            p = HERE / "example.dad"
            return self._send(200, {"code": p.read_text(encoding="utf-8") if p.exists() else 'قل(هلا والله)\n'})
        if path == "/ide_pro_example":
            p = HERE / "aldad_ide_pro.dad"
            return self._send(200, {"code": p.read_text(encoding="utf-8") if p.exists() else ''})
        return self._send(404, {"error": "مو موجود"})


def free_port(start=8787):
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port)); return port
            except OSError:
                continue
    return 0


PAGE = r'''<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>ضاد IDE __VER__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#1b1d27;--panel:#232634;--line:#343849;--fg:#e9e9ef;--mut:#9aa0b4;--acc:#3a7bd5;--acc2:#2f9e6e;--bad:#e5534b;
 --kw:#c792ea;--str:#e0a36f;--num:#b5cea8;--com:#6a9955;--op:#6fb3ff;--var:#4fc1ff;--fs:19px;--lh:1.8}
*{box-sizing:border-box}
html,body{height:100%;margin:0;background:var(--bg);color:var(--fg);font-family:"Segoe UI","Dubai",Tahoma,sans-serif}
body{display:flex;flex-direction:column}
header{display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding:10px 14px;background:var(--panel);border-bottom:1px solid var(--line)}
header h1{font-size:17px;margin:0 0 0 10px;font-weight:700;letter-spacing:.3px}
header h1 span{color:var(--acc)}
button{font:inherit;font-size:14px;padding:7px 12px;white-space:nowrap;border-radius:7px;border:1px solid var(--line);background:#2b2f40;color:var(--fg);cursor:pointer}
button:hover{border-color:var(--acc)}
button.run{background:var(--acc);border-color:var(--acc);font-weight:600}
#fname{font:inherit;font-size:14px;padding:6px 10px;border-radius:7px;border:1px solid var(--line);background:#1b1d27;color:var(--fg);width:220px;margin-inline-start:auto}
.state{font-size:12px;color:var(--mut);min-width:70px}
main{flex:1;display:flex;flex-direction:column;min-height:0}
.edwrap{flex:1;display:flex;min-height:0;position:relative}
.gutter{width:48px;padding:14px 8px 0;text-align:left;color:#5d6380;font-size:var(--fs);line-height:var(--lh);overflow:hidden;white-space:pre;font-family:Consolas,monospace;user-select:none;border-inline-end:1px solid var(--line)}
.edbox{flex:1;position:relative;min-width:0}
.edbox textarea,.hl{position:absolute;inset:0;width:100%;height:100%;padding:14px 16px;margin:0;border:0;font-size:var(--fs);line-height:var(--lh);font-family:"Segoe UI","Dubai",Tahoma,sans-serif;tab-size:4}
.edbox textarea{resize:none;outline:0;background:transparent;color:transparent;caret-color:#fff;white-space:pre;overflow:auto;direction:rtl;unicode-bidi:plaintext;z-index:2}
.hl{overflow:hidden;pointer-events:none;z-index:1}
.ln{white-space:pre;direction:rtl;unicode-bidi:plaintext;min-height:calc(var(--fs)*var(--lh));border-radius:3px}
.ln.bad{background:rgba(229,83,75,.22);box-shadow:inset -3px 0 0 var(--bad)}
.c-kw{color:var(--kw)}.c-str{color:var(--str)}.c-num{color:var(--num)}.c-com{color:var(--com)}.c-op{color:var(--op)}.c-var{color:var(--var)}
.out{height:36%;min-height:120px;border-top:1px solid var(--line);background:#191b24;display:flex;flex-direction:column}
.outhead{display:flex;align-items:center;gap:10px;padding:7px 14px;border-bottom:1px solid var(--line);font-size:13px;color:var(--mut)}
.outhead b{color:var(--fg)}
#res{flex:1;overflow:auto;padding:10px 16px;font-size:17px;line-height:1.8}
#res pre{margin:0;white-space:pre-wrap;unicode-bidi:plaintext;font-family:inherit;text-align:right}
.ok{color:var(--acc2)} .err{color:var(--bad)} .fix{color:var(--op);font-size:15px} .meta{color:var(--mut);font-size:13px}
.qrow{display:flex;align-items:center;gap:10px;margin:8px 0}.qrow label{min-width:160px}
.qrow input{flex:1;font:inherit;font-size:17px;padding:7px 11px;border-radius:7px;border:1px solid var(--acc);background:#20232f;color:var(--fg)}
.opt{display:block;margin:6px 0;text-align:right}
.img img{max-width:100%;max-height:48vh;border-radius:8px;display:block;margin:8px 0}
.app{margin:10px 0;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.appbar{display:flex;align-items:center;gap:10px;padding:6px 10px;background:var(--panel)}.appbar button{margin-inline-start:auto;font-size:13px;padding:4px 10px}
.app iframe{width:100%;height:470px;border:0;background:#f4f5f9}
#term{flex:1;display:flex;flex-direction:column;background:#07080b;min-height:0}
#term[hidden]{display:none}
.thead{display:flex;align-items:center;gap:10px;padding:8px 14px;border-bottom:1px solid #1d2130;color:#cfd3dc}.thead .meta{margin-inline-end:auto}
#tlog{flex:1;overflow:auto;padding:12px 18px;font-size:18px;line-height:1.75;color:#e6e6e6}
#tlog .ln{white-space:pre-wrap;unicode-bidi:plaintext;text-align:right}
#tlog .cmd{color:#7ee787}#tlog .cmd b{color:#3fb950;font-weight:600;margin-inline-end:8px}
#tlog .er{color:#ff7b72}#tlog .fx{color:#79c0ff}#tlog .q{color:#d2a8ff}#tlog img{max-width:420px;border-radius:8px;display:block;margin:6px 0}
.tin{display:flex;align-items:center;gap:10px;padding:10px 18px;border-top:1px solid #1d2130}
#tprompt{color:#3fb950;font-weight:700;font-size:18px;min-width:60px}
#tinput{flex:1;background:transparent;border:0;outline:0;color:#fff;font:inherit;font-size:18px;caret-color:#3fb950}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;z-index:10}
.modal .box{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;width:min(520px,92vw);max-height:80vh;overflow:auto}
.modal h3{margin:0 0 10px;font-size:16px}
.file{display:block;width:100%;text-align:right;margin:5px 0}
.box.rules{width:min(820px,94vw);max-height:86vh;line-height:1.8;font-size:15px}
.rules h1{font-size:20px;margin:4px 0 10px}.rules h2{font-size:16px;margin:16px 0 6px;color:var(--acc)}
.rules table{border-collapse:collapse;width:100%;margin:6px 0}.rules td,.rules th{border:1px solid var(--line);padding:5px 8px;text-align:right}
.rules th{background:#2b2f40}.rules code{background:#2b2f40;padding:1px 6px;border-radius:5px;font-family:inherit}
.rules pre{background:#191b24;border:1px solid var(--line);border-radius:8px;padding:10px;white-space:pre-wrap;unicode-bidi:plaintext;font-family:"Segoe UI","Dubai",Tahoma,sans-serif;font-size:15px}
.hint{font-size:12px;color:var(--mut)}
</style></head><body>
<header id="hdr">
  <h1>ضاد <span>IDE</span> <small style="font-size:12px;color:var(--mut)">نسخة __VER__</small></h1>
  <button class="run" id="bRun" title="Ctrl+Enter">▶ شغّل</button>
  <button id="bOpen">📂 فتح</button>
  <button id="bSave" title="Ctrl+S">💾 حفظ</button>
  <button id="bNew">＋ جديد</button>
  <button id="bEx">مثال</button>
  <button id="bIdePro">IDE Pro</button>
  <button id="bRules">📖 القاموس</button>
  <button id="bTerm">⌨ الطرفية</button>
  <span class="state" id="state"></span>
  <input id="fname" value="program.dad" title="اسم الملف">
</header>
<section id="term" hidden>
  <div class="thead"><b>⌨ طرفية الضاد</b><span class="meta">اكتب سطر واضغط Enter — ينفذ على طول والذاكرة تظل · ↑↓ الأسطر السابقة</span>
    <button id="tClear">مسح الشاشة</button><button id="tReset">مسح الذاكرة</button><button id="tBack">↩ المحرر</button></div>
  <div id="tlog"></div>
  <div class="tin"><span id="tprompt">ضاد›</span><input id="tinput" autocomplete="off" spellcheck="false" dir="rtl"></div>
</section>
<main>
  <div class="edwrap"><div class="edbox"><div class="hl" id="hl"></div><textarea id="ed" spellcheck="false" autocomplete="off"></textarea></div><div class="gutter" id="g">1</div></div>
  <div class="out"><div class="outhead"><b>النتائج</b><span id="status" class="meta"></span><span class="hint" style="margin-inline-start:auto">الملفات في: <span id="wdir"></span></span></div><div id="res"><span class="meta">اكتب برنامجك فوق واضغط ▶ شغّل.</span></div></div>
</main>
<div class="modal" id="rmodal"><div class="box rules"><div id="rbody"></div><button id="rClose">إغلاق</button></div></div>
<div class="modal" id="modal"><div class="box"><h3>افتح ملف</h3><div id="flist"></div>
  <p class="hint">أو من مكان ثاني: <input type="file" id="upl" accept=".ضاد,.dad,.txt"></p><button id="mClose">إغلاق</button></div></div>
<script>
const TOKEN="__TOKEN__", WORKDIR=__WORK__;
const ed=document.getElementById('ed'), hl=document.getElementById('hl'), g=document.getElementById('g'), res=document.getElementById('res');
const fname=document.getElementById('fname'), state=document.getElementById('state'), statusEl=document.getElementById('status');
document.getElementById('wdir').textContent=WORKDIR;
let ERRLINE=0, dirty=false;
const esc=t=>String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
async function api(path, body){ const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Dad-Token':TOKEN},body:JSON.stringify(body||{})}); return r.json(); }
// جسر آمن لبرامج الضاد المولدة داخل iframe: ما نعطيها التوكن، فقط أوامر محددة.
window.addEventListener('message', async e=>{
  const d=e.data||{}; if(d.dadBridge!==1) return;
  const map={list:'/list',open:'/open',save:'/save',run:'/run',run_start:'/run_start',run_answer:'/run_answer',run_stop:'/run_stop',build_exe:'/build_exe'};
  const path=map[d.action]; if(!path){ try{e.source.postMessage({dadBridgeReply:1,id:d.id,ok:false,error:'العملية غير مسموحة'},'*')}catch(_){} return; }
  try{ const data=await api(path,d.payload||{}); const ok=!(data&&data.error); e.source.postMessage({dadBridgeReply:1,id:d.id,ok,data,error:data&&data.error},'*'); }
  catch(err){ try{e.source.postMessage({dadBridgeReply:1,id:d.id,ok:false,error:String(err&&err.message||err)},'*')}catch(_){} }
});

// ---------- ألوان
const KW=new Set(['برنامج','نافذة','أضف','عند','ضغط','ضع','امسح','حقل','زر','حلل','اطلب','قل','قول','اطبع','اعرض','اسأل','أسأل','اسال','احسب','احسبلي','أكمل','اكمل','ارسم','رسم','إذا','اذا','لو','وإلا','والا','كرر','أضف','اضف','احفظ','افتح','ثم','لكل','كل','مرات','مرة','إلى','الى','دالة','أرجع','طالما','حاول','عند_خطأ','استورد','صح','خطأ']);
const OPW=new Set(['زائد','ناقص','ضرب','قسمة','على','أكبر','أصغر','من','يساوي','مو','أكثر','أقل','أكبر_من','أصغر_من','لا_يساوي','و','أو','ليس','جذر','مجموع','متوسط','عدد']);
const SPV=new Set(['الناتج','المحتوى','الرد']);
function hlLine(s){ if(!s) return '\u200b';
  const re=/(#.*$)|("[^"]*"?|«[^»]*»?)|([0-9٠-٩]+(?:[.٫][0-9٠-٩]+)?)|([\p{L}_][\p{L}\p{N}_]*)|([^\p{L}\p{N}_"«#]+)/gu; let o='',m;
  while((m=re.exec(s))){ const t=esc(m[0]);
    if(m[1]) o+='<span class="c-com">'+t+'</span>'; else if(m[2]) o+='<span class="c-str">'+t+'</span>';
    else if(m[3]) o+='<span class="c-num">'+t+'</span>';
    else if(m[4]) o+= KW.has(m[4])?'<span class="c-kw">'+t+'</span>':OPW.has(m[4])?'<span class="c-op">'+t+'</span>':SPV.has(m[4])?'<span class="c-var">'+t+'</span>':t;
    else o+=t; } return o; }
function paint(){ const L=ed.value.split('\n'); hl.innerHTML=L.map((l,i)=>'<div class="ln'+(i+1===ERRLINE?' bad':'')+'">'+hlLine(l)+'</div>').join('');
  let t=''; for(let i=1;i<=L.length;i++) t+=i+'\n'; g.textContent=t; sync(); }
function sync(){ hl.scrollTop=ed.scrollTop; hl.scrollLeft=ed.scrollLeft; g.scrollTop=ed.scrollTop; }
function setDirty(d){ dirty=d; state.textContent=d?'● غير محفوظ':'✓ محفوظ'; }
ed.addEventListener('input',()=>{ ERRLINE=0; paint(); setDirty(true); localStorage.setItem('dad_draft',JSON.stringify({n:fname.value,c:ed.value})); });
ed.addEventListener('scroll',sync);
function insertText(t){ ed.focus(); if(!document.execCommand('insertText',false,t)){ const a=ed.selectionStart,b=ed.selectionEnd; ed.setRangeText(t,a,b,'end'); } paint(); setDirty(true); }
ed.addEventListener('keydown',e=>{
  if(e.key==='Tab'){ e.preventDefault(); insertText('    '); }
  else if(e.key==='Enter' && (e.ctrlKey||e.metaKey)){ e.preventDefault(); run(); }
  else if(e.key==='Enter'){ e.preventDefault(); const v=ed.value, p=ed.selectionStart, a=v.lastIndexOf('\n',p-1)+1; const upto=v.slice(a,p);
    let ind=upto.match(/^\s*/)[0]; if(/:\s*$/.test(upto) || /^\s*(إذا|اذا|كرر|لكل|وإلا|والا)\b/.test(upto)) ind+='    '; insertText('\n'+ind); }
});
document.addEventListener('keydown',e=>{ if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){ e.preventDefault(); save(); } });

// ---------- تشغيل
let LIVE=null;
async function run(){
  if(LIVE){ try{ await api('/run_stop',{id:LIVE}); }catch(_){} LIVE=null; }
  res.innerHTML='<span class="meta">يشغّل…</span>'; statusEl.textContent='';
  const t0=performance.now(); let out=''; let r=await api('/run_start',{code:ed.value}); LIVE=r.id;
  while(r.status==='ask'){
    out+=(out&&r.out?'\n':'')+(r.out||'');
    const a=await askLive(out, r.prompt);
    if(a===null){ await api('/run_stop',{id:r.id}); LIVE=null; show({ok:false,out,err:'⚠ وقفت التشغيل.'}, Math.round(performance.now()-t0)); return; }
    r=await api('/run_answer',{id:r.id,answer:a});
  }
  LIVE=null; out+=(out&&r.out?'\n':'')+(r.out||''); r.out=out;
  show(r, Math.round(performance.now()-t0));
}
function askLive(out, prompt){ return new Promise(res2=>{
  res.innerHTML=(out?'<pre>'+esc(out)+'</pre>':'')+'<div class="meta">البرنامج يسألك:</div>';
  const row=document.createElement('div'); row.className='qrow'; row.innerHTML='<label></label><input><button class="run">▶ كمّل</button><button>■ وقّف</button>';
  row.querySelector('label').textContent=prompt||'سؤال'; const inp=row.querySelector('input');
  const [go,stop]=row.querySelectorAll('button'); go.onclick=()=>res2(inp.value); stop.onclick=()=>res2(null);
  inp.onkeydown=e=>{ if(e.key==='Enter'){ e.preventDefault(); res2(inp.value); } };
  res.appendChild(row); res.scrollTop=res.scrollHeight; setTimeout(()=>inp.focus(),30); }); }
function askForm(list){ res.innerHTML='<div class="meta">البرنامج يبي منك:</div>'; const ins=[];
  list.forEach((q,i)=>{ const row=document.createElement('div'); row.className='qrow'; row.innerHTML='<label></label><input>';
    row.querySelector('label').textContent=q; const inp=row.querySelector('input');
    inp.onkeydown=e=>{ if(e.key==='Enter'){ e.preventDefault(); if(i<list.length-1) ins[i+1].focus(); else go(); } }; ins.push(inp); res.appendChild(row); });
  const b=document.createElement('button'); b.className='run'; b.textContent='▶ كمّل'; b.onclick=go; res.appendChild(b);
  function go(){ run(ins.map(x=>x.value)); } setTimeout(()=>ins[0].focus(),30); }
function mediaEl(im){                                  // 1.9.13: صورة / صوت / فيديو
  const d=document.createElement('div'); d.className='img media';
  const cap=document.createElement('div'); cap.className='meta'; cap.textContent=({audio:'🔊 ',video:'🎬 ',image:'🖼 '}[im.kind]||'')+(im.name||'');
  let el;
  if(im.kind==='audio'){ el=document.createElement('audio'); el.controls=true; el.autoplay=true; el.style.width='100%'; }
  else if(im.kind==='video'){ el=document.createElement('video'); el.controls=true; el.autoplay=true; el.style.maxWidth='100%'; el.style.maxHeight='48vh'; }
  else { el=document.createElement('img'); el.alt=im.name||''; }
  el.src=im.src; if(im.kind){ d.appendChild(cap); } d.appendChild(el); return d; }
function show(r, ms){
  statusEl.innerHTML=(r.ok?'<span class="ok">✓ اشتغل</span>':'<span class="err">فيه مشكلة</span>')+' · '+ms+' ms';
  const L=(r.err||'').split('\n'); const fx=L.filter(l=>l.startsWith('✎')); const er=L.filter(l=>!l.startsWith('✎')).join('\n').trim();
  let h='<pre>'+esc((r.out||'').replace(/\s+$/,'')||((r.images&&r.images.length)?'':'ما طبع البرنامج شي.'))+'</pre>';
  if(fx.length) h+='<pre class="fix">'+esc(fx.join('\n'))+'</pre>'; if(er) h+='<pre class="err">'+esc(er)+'</pre>';
  res.innerHTML=h;
  const lm=er.match(/السطر (\d+)/); ERRLINE=(!r.ok&&lm)?+lm[1]:0; paint();
  if(ERRLINE){ const lh=parseFloat(getComputedStyle(ed).lineHeight); ed.scrollTop=Math.max(0,(ERRLINE-3)*lh); sync(); }
  const opts=[]; er.split('\n').forEach(l=>{ const m=l.match(/^\s*\d+\.\s+(.+?)\s*$/); if(m) opts.push(m[1].replace(/\s{2,}=.*$/,'').trim()); });
  if(opts.length){ const box=document.createElement('div'); box.innerHTML='<div class="meta">اضغط اللي تقصده وأشغّله لك:</div>';
    opts.forEach(o=>{ const b=document.createElement('button'); b.className='opt'; b.textContent=o; b.onclick=()=>applyFix(ERRLINE||(lm?+lm[1]:1),o); box.appendChild(b); }); res.appendChild(box); }
  (r.apps||[]).forEach(ap=>{ const d=document.createElement('div'); d.className='app';
    const bar=document.createElement('div'); bar.className='appbar'; bar.innerHTML='<b></b><button>افتح بنافذة كاملة ↗</button>'; bar.querySelector('b').textContent='▣ '+ap.name;
    const fr=document.createElement('iframe'); fr.setAttribute('sandbox','allow-scripts allow-modals'); fr.srcdoc=ap.html;
    bar.querySelector('button').onclick=()=>{ const u=URL.createObjectURL(new Blob([ap.html],{type:'text/html'})); window.open(u,'_blank'); };
    d.appendChild(bar); d.appendChild(fr); res.appendChild(d); });
  (r.images||[]).forEach(im=>res.appendChild(mediaEl(im)));
}
function applyFix(line,text){ const L=ed.value.split('\n'); const i=Math.max(0,Math.min(L.length-1,line-1)); const ind=(L[i]||'').match(/^\s*/)[0];
  L[i]=/^⇥\s*/.test(text)? ind+'    '+text.replace(/^⇥\s*/,'') : ind+text; ed.value=L.join('\n'); ERRLINE=0; paint(); setDirty(true); run(); }

// ---------- ملفات
async function save(){ const r=await api('/save',{name:fname.value,code:ed.value}); if(r.saved){ fname.value=r.name; setDirty(false); statusEl.textContent='انحفظ: '+r.name; } }
async function openDlg(){ const r=await api('/list'); const fl=document.getElementById('flist'); fl.innerHTML='';
  if(!r.files.length) fl.innerHTML='<p class="hint">ما في ملفات محفوظة لين الحين.</p>';
  r.files.forEach(n=>{ const b=document.createElement('button'); b.className='file'; b.textContent='📄 '+n; b.onclick=()=>load(n); fl.appendChild(b); });
  document.getElementById('modal').style.display='flex'; }
async function load(n){ if(dirty && !confirm('فيه تغييرات ما انحفظت. تكمل؟')) return; const r=await api('/open',{name:n});
  if(r.code!==undefined){ ed.value=r.code; fname.value=r.name; ERRLINE=0; paint(); setDirty(false); res.innerHTML='<span class="meta">انفتح '+esc(r.name)+'</span>'; }
  document.getElementById('modal').style.display='none'; }
document.getElementById('upl').onchange=e=>{ const f=e.target.files[0]; if(!f) return; const rd=new FileReader();
  rd.onload=()=>{ ed.value=rd.result; fname.value=f.name; paint(); setDirty(true); document.getElementById('modal').style.display='none'; }; rd.readAsText(f,'utf-8'); };
document.getElementById('mClose').onclick=()=>document.getElementById('modal').style.display='none';
function newFile(){ if(dirty && !confirm('فيه تغييرات ما انحفظت. تمسحها؟')) return; ed.value=''; fname.value='program.dad'; ERRLINE=0; paint(); setDirty(false);
  res.innerHTML='<span class="meta">ملف جديد.</span>'; statusEl.textContent=''; ed.focus(); }
async function example(){ const r=await api('/example'); ed.value=r.code; fname.value='example.dad'; ERRLINE=0; paint(); setDirty(true); }
async function idePro(){ const r=await api('/ide_pro_example'); ed.value=r.code||''; fname.value='aldad_ide_pro.dad'; ERRLINE=0; paint(); setDirty(true); res.innerHTML='<span class="meta">مثال IDE Pro مكتوب بالضاد.</span>'; }
document.getElementById('bRun').onclick=()=>run(); document.getElementById('bSave').onclick=save; document.getElementById('bOpen').onclick=openDlg;
document.getElementById('bNew').onclick=newFile;
function md(t){ const L=t.split('\n'); let o='',inCode=false,inTab=false,inList=false; const inl=s=>esc(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');
  for(const l of L){ if(l.startsWith('```')){ o+=inCode?'</pre>':'<pre>'; inCode=!inCode; continue; } if(inCode){ o+=esc(l)+'\n'; continue; }
    if(/^\|/.test(l)){ if(/^\|[-| ]+\|$/.test(l)) continue; const c=l.split('|').slice(1,-1); o+=(inTab?'':'<table>')+'<tr>'+c.map(x=>(inTab?'<td>':'<th>')+inl(x.trim())+(inTab?'</td>':'</th>')).join('')+'</tr>'; inTab=true; continue; }
    if(inTab){ o+='</table>'; inTab=false; }
    if(/^- /.test(l)){ o+=(inList?'':'<ul>')+'<li>'+inl(l.slice(2))+'</li>'; inList=true; continue; } if(inList){ o+='</ul>'; inList=false; }
    if(/^## /.test(l)) o+='<h2>'+inl(l.slice(3))+'</h2>'; else if(/^# /.test(l)) o+='<h1>'+inl(l.slice(2))+'</h1>'; else if(/^\d+\. /.test(l)) o+='<div>'+inl(l)+'</div>'; else if(l.trim()) o+='<p>'+inl(l)+'</p>'; }
  if(inTab) o+='</table>'; if(inList) o+='</ul>'; return o; }
// ---------- الطرفية
const term=document.getElementById('term'), mainEl=document.querySelector('main'), tlog=document.getElementById('tlog'), tin=document.getElementById('tinput'), tprompt=document.getElementById('tprompt');
let tHist=[], tIdx=0, tBlock=[], tAsk=null;
function tline(text,cls){ const d=document.createElement('div'); d.className='ln '+(cls||''); d.textContent=text; tlog.appendChild(d); tlog.scrollTop=tlog.scrollHeight; return d; }
function tcmd(text){ const d=document.createElement('div'); d.className='ln cmd'; d.innerHTML='<b></b>'; d.querySelector('b').textContent=tBlock.length?'…':'ضاد›'; d.appendChild(document.createTextNode(text)); tlog.appendChild(d); tlog.scrollTop=tlog.scrollHeight; }
function openTerm(){ mainEl.hidden=true; mainEl.style.display='none'; term.hidden=false; if(!tlog.children.length){ tline('طرفية الضاد — مثل الشاشة السودا حقت Python: كل سطر ينفذ على طول.','fx'); tline('جرّب: قل هلا   ·   5 زائد 3   ·   اسأل كم عمرك   ·   احسب العمر ضرب 2','fx'); tline('سطر ينتهي بـ «:» أو يبدأ بـ إذا/كرر/لكل ← يكمل بسطر ثاني، وسطر فاضي ينفذه.','fx'); } tin.focus(); }
function closeTerm(){ term.hidden=true; mainEl.hidden=false; mainEl.style.display=''; ed.focus(); }
function needsMore(l){ const t=l.trim();
  if(/:$/.test(t)) return true;
  if(/^(إذا|اذا|لو)\s*\(.*\)$/.test(t)) return true;
  if(/^(وإلا|والا)$/.test(t)) return true;
  if(/^لكل\s+\S+\s+في\s+\S+$/.test(t)) return true;
  const CMD=/(قل|قول|اطبع|احسب|اسأل|أسأل|ارسم|اطلب|أضف|اضف)/;
  const m=t.match(/^كرر\s*\((.*)\)$/); if(m && !CMD.test(m[1])) return true;
  const m2=t.match(/^كرر\s+(?!\()(.*)$/); if(m2 && !CMD.test(m2[1])) return true;          // كرر 2 مرات
  if(/^(إذا|اذا|لو)\s+(?!\()/.test(t) && !/\sثم\s/.test(t) && /(أكبر|اكبر|أصغر|اصغر|يساوي|أكثر|اكثر|أقل|اقل)/.test(t)) return true;   // إذا العمر أكبر من 18
  return false; }
async function tRun(code){
  let r=await api('/repl',{code});
  while(r.event==='question'){ const answer=await tQuestion(r.prompt); r=await api('/repl_answer',answer===null?{cancel:true}:{answer}); }
  (r.out||'').split('\n').forEach(l=>{ if(l.trim()) tline(l); });
  (r.err||'').split('\n').forEach(l=>{ if(l.trim()) tline(l, l.startsWith('✎')?'fx':'er'); });
  (r.images||[]).forEach(im=>tlog.appendChild(mediaEl(im)));
  tlog.scrollTop=tlog.scrollHeight;
}
function tQuestion(q){ return new Promise(res=>{ tprompt.textContent=q; tprompt.className='q'; tAsk=v=>{ tprompt.textContent='ضاد›'; tprompt.className=''; tAsk=null; res(v); }; tin.focus(); }); }
tin.addEventListener('keydown',async e=>{
  if(e.key==='ArrowUp'){ if(tIdx>0){ tIdx--; tin.value=tHist[tIdx]||''; } e.preventDefault(); return; }
  if(e.key==='ArrowDown'){ if(tIdx<tHist.length){ tIdx++; tin.value=tHist[tIdx]||''; } e.preventDefault(); return; }
  if(e.key==='Tab'){ e.preventDefault(); tin.value+='    '; return; }
  if(e.key!=='Enter') return;
  e.preventDefault(); const v=tin.value; tin.value='';
  if(tAsk){ tAsk(v); return; }
  if(tBlock.length){
    if(v.trim()===''){ const code=tBlock.join('\n'); tBlock=[]; tprompt.textContent='ضاد›'; await tRun(code); return; }
    tcmd(v); tBlock.push(v.startsWith(' ')?v:'    '+v); return;
  }
  if(!v.trim()) return;
  tcmd(v); tHist.push(v); tIdx=tHist.length;
  if(needsMore(v)){ tBlock=[v]; tprompt.textContent='…'; return; }
  await tRun(v);
});
document.getElementById('bTerm').onclick=openTerm; document.getElementById('tBack').onclick=closeTerm;
document.getElementById('tClear').onclick=()=>{ tlog.innerHTML=''; tin.focus(); };
document.getElementById('tReset').onclick=async()=>{ const r=await api('/repl_reset'); tline(r.out||'✓','fx'); tin.focus(); };
document.getElementById('bRules').onclick=async()=>{ const r=await api('/rules'); document.getElementById('rbody').innerHTML=md(r.md); document.getElementById('rmodal').style.display='flex'; };
document.getElementById('rClose').onclick=()=>document.getElementById('rmodal').style.display='none'; document.getElementById('bEx').onclick=example; document.getElementById('bIdePro').onclick=idePro;
// آخر مسودة
try{ const d=JSON.parse(localStorage.getItem('dad_draft')||'null'); if(d&&d.c){ ed.value=d.c; fname.value=d.n||fname.value; setDirty(true);} else { ed.value='قل(ضاد IDE جاهز)\n'; setDirty(false);} }catch(e){ ed.value='قل(ضاد IDE جاهز)\n'; }
paint(); ed.focus();
</script></body></html>'''


def _open_browser(url):
    try:
        if os.name == "nt" and hasattr(os, "startfile"):
            os.startfile(url)
            return
    except Exception:
        pass
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass

def main():
    try:
        frozen = getattr(sys, "frozen", False)
        engine_ok = DAD_RUNNER.exists() if frozen else (DAD.exists() and (HERE / "vnext.py").exists())
        if not engine_ok:
            print("⚠ ملفات محرك الضاد ناقصة.")
            return 2
        port = free_port()
        if not port:
            print("⚠ ما لقيت منفذ محلي فاضي بين 8787 و8836. سكّر أي نسخة ضاد مفتوحة وجرب مرة ثانية.")
            return 3
        srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        url = f"http://127.0.0.1:{port}/"
        print(f"ضاد IDE — نسخة {DAD_VERSION} — شغال على {url}\nالملفات في: {WORK}\nإذا المتصفح ما فتح، انسخ الرابط اللي فوق.\nسكّر هالنافذة عشان توقفه.")
        if "--no-browser" not in sys.argv:
            threading.Timer(0.7, lambda: _open_browser(url)).start()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    except Exception as e:
        try:
            (HERE / "aldad_error.txt").write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8")
        except Exception:
            pass
        print(f"⚠ ما اشتغل ضاد IDE: {type(e).__name__}: {e}")
        print("تم حفظ السبب في ملف aldad_error.txt إذا أمكن.")
        return 10


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
