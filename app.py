"""Flask entry point for AI Resume Screening & Analysis System."""
import os
import io
import uuid
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_file, jsonify
)
from werkzeug.utils import secure_filename

import config
from utils.parser import allowed_file, parse_resume
from utils.analyzer import analyze
from utils.pdf_report import build_pdf

app = Flask(__name__)
app.config.from_object(config)
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# In-memory cache of last analysis (per session id) — keeps demo simple.
_RESULTS = {}


@app.route("/")
def index():
    return render_template("index.html", active="home")


@app.route("/features")
def features():
    return render_template("features.html", active="features")


@app.route("/about")
def about():
    return render_template("about.html", active="about")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("resume")
        jd = (request.form.get("job_description") or "").strip()

        if not file or file.filename == "":
            flash("Please upload a resume file (PDF or DOCX).", "danger")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename, config.ALLOWED_EXTENSIONS):
            flash("Unsupported file type. Upload PDF or DOCX only.", "danger")
            return redirect(url_for("upload"))

        fname = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        fpath = os.path.join(config.UPLOAD_FOLDER, fname)
        file.save(fpath)

        try:
            parsed = parse_resume(fpath)
            result = analyze(parsed, jd)
        except Exception as e:
            flash(f"Failed to analyze resume: {e}", "danger")
            return redirect(url_for("upload"))

        rid = uuid.uuid4().hex
        _RESULTS[rid] = result
        session["rid"] = rid
        session["filename"] = file.filename
        return redirect(url_for("dashboard"))

    return render_template("upload.html", active="upload")


@app.route("/dashboard")
def dashboard():
    rid = session.get("rid")
    result = _RESULTS.get(rid)
    if not result:
        flash("Please upload a resume first.", "warning")
        return redirect(url_for("upload"))
    return render_template(
        "dashboard.html",
        active="dashboard",
        r=result,
        filename=session.get("filename", "resume"),
    )


@app.route("/report.pdf")
def report_pdf():
    rid = session.get("rid")
    result = _RESULTS.get(rid)
    if not result:
        flash("No analysis to export.", "warning")
        return redirect(url_for("upload"))
    pdf_bytes = build_pdf(result)
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name="Resume_Analysis_Report.pdf",
        mimetype="application/pdf",
    )


@app.errorhandler(413)
def too_large(e):
    flash("File too large. Max 10 MB.", "danger")
    return redirect(url_for("upload"))


if __name__ == "__main__":
    app.run(debug=True)
