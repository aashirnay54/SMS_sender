import csv
import io
import os
import subprocess
import threading
import time
import random
import uuid

import openpyxl
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory job store: { job_id: { 'results': [...], 'total': N, 'done': bool } }
jobs: dict = {}


# ── Column fuzzy-finder ─────────────────────────────────────────────────────

def _find_col(row: dict, *keywords: str) -> str:
    """Return the first value whose lowercased key contains any keyword, in priority order."""
    lower = {k.lower(): v for k, v in row.items()}
    for kw in keywords:
        for k, v in lower.items():
            if kw in k:
                return v
    return ""


# ── AppleScript sender ──────────────────────────────────────────────────────

def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def send_via_messages(phone: str, message: str) -> tuple[bool, str]:
    """Send a message through macOS Messages app via AppleScript."""
    p = _escape(phone.strip())
    m = _escape(message.strip())

    # Try iMessage first, fall back to SMS
    for svc_type in ("iMessage", "SMS"):
        script = f'''
tell application "Messages"
    set svc to first service whose service type = {svc_type}
    set bud to buddy "{p}" of svc
    send "{m}" to bud
end tell
'''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, ""

    return False, result.stderr.strip()


# ── Background send worker ───────────────────────────────────────────────────

def _send_worker(job_id: str, messages: list[dict], delay: float):
    for i, msg in enumerate(messages):
        phone   = msg.get("phone", "").strip()
        message = msg.get("message", "").strip()
        name    = msg.get("name", "Unknown")

        if not phone or not message:
            jobs[job_id]["results"].append({
                "index": i, "name": name, "phone": phone,
                "success": False, "error": "Missing phone or message"
            })
        else:
            success, error = send_via_messages(phone, message)
            jobs[job_id]["results"].append({
                "index": i, "name": name, "phone": phone,
                "success": success, "error": error
            })

        if i < len(messages) - 1 and delay > 0:
            time.sleep(delay)

    jobs[job_id]["done"] = True


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    resp = app.make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/parse-csv", methods=["POST"])
def parse_csv():
    """Parse uploaded CSV or Excel file and return headers + rows."""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = file.filename or ""
    ext      = os.path.splitext(filename)[1].lower()

    if ext in (".xlsx", ".xls"):
        wb      = openpyxl.load_workbook(io.BytesIO(file.read()), read_only=True, data_only=True)
        ws      = wb.active
        raw     = list(ws.iter_rows(values_only=True))
        if not raw:
            return jsonify({"error": "Empty spreadsheet"}), 400
        headers = [str(c).strip() if c is not None else "" for c in raw[0]]
        rows    = [
            {headers[i]: (str(cell).strip() if cell is not None else "")
             for i, cell in enumerate(row)}
            for row in raw[1:]
        ]
    else:
        content = file.read().decode("utf-8-sig")
        reader  = csv.DictReader(io.StringIO(content))
        headers = list(reader.fieldnames or [])
        rows    = [dict(r) for r in reader]

    return jsonify({"headers": headers, "rows": rows, "count": len(rows)})


@app.route("/preview", methods=["POST"])
def preview():
    """Generate preview messages from template(s) + CSV data."""
    data      = request.get_json()
    templates = data.get("templates", [])
    rows      = data.get("rows", [])

    # Support legacy single-template callers
    if not templates:
        t = data.get("template", "")
        if t:
            templates = [t]
    if not templates:
        return jsonify({"error": "No template provided"}), 400

    previews = []
    for row in rows:
        clean = {k.strip(): v.strip() for k, v in row.items() if k}
        phone = _find_col(clean, "phone") or ""
        name  = _find_col(clean, "first", "name") or "Unknown"
        tpl_idx = random.randrange(len(templates))
        tpl     = templates[tpl_idx]
        try:
            message = tpl.format(**clean)
            previews.append({"name": name, "phone": phone, "message": message, "error": None, "template_idx": tpl_idx})
        except KeyError as e:
            previews.append({"name": name, "phone": phone, "message": "", "error": f"Missing variable: {e}", "template_idx": tpl_idx})

    return jsonify({"previews": previews})


@app.route("/send", methods=["POST"])
def start_send():
    """Start a background send job; return job_id for polling."""
    data     = request.get_json()
    messages = data.get("messages", [])
    delay    = float(data.get("delay", 2.0))

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"results": [], "total": len(messages), "done": False}

    thread = threading.Thread(target=_send_worker, args=(job_id, messages, delay), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id: str):
    """Poll for send progress."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "results": job["results"],
        "total":   job["total"],
        "done":    job["done"],
        "sent":    len(job["results"])
    })


if __name__ == "__main__":
    print("\n  iMessage Bulk Sender — http://localhost:5001\n")
    app.run(debug=False, port=5001)
