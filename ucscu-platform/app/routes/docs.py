"""Doc Space — rich-text documents (bold/italic/lists/tables) plus file uploads."""
import os
import secrets
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   current_app, send_from_directory, abort, Response)

from .. import login_required, current_user
from ..models import db, Document, Attachment, MINUTE_TEMPLATES, log_action

bp = Blueprint("docs", __name__, url_prefix="/docs")

DOC_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
           ".txt", ".csv", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".odt", ".ods")


def _upload_dir():
    d = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(d, exist_ok=True)
    return d


def _template_to_html(name):
    """Turn a plain-text minute template into simple HTML paragraphs."""
    text = MINUTE_TEMPLATES.get(name, "")
    return "".join("<p>%s</p>" % line for line in text.split("\n"))


@bp.route("/")
@login_required()
def index():
    docs = Document.query.order_by(Document.at.desc()).all()
    return render_template("docs/index.html", docs=docs, templates=MINUTE_TEMPLATES)


@bp.route("/new", methods=["POST"])
@login_required()
def new_doc():
    f = request.form
    title = (f.get("title") or "").strip()
    if not title:
        flash("A document title is required.", "error")
        return redirect(url_for("docs.index"))
    tmpl = f.get("template")
    content = _template_to_html(tmpl) if tmpl else (f.get("content", "") or "")
    d = Document(title=title, category=f.get("category", "Minutes"),
                 content=content, content_type="richtext",
                 created_by=current_user().full_name)
    db.session.add(d)
    log_action(current_user().username, "Created document '%s'" % d.title)
    db.session.commit()
    flash("Document created.", "ok")
    return redirect(url_for("docs.view", did=d.id))


@bp.route("/upload", methods=["POST"])
@login_required()
def upload():
    """Upload an existing file into Doc Space."""
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Choose a file to upload.", "error")
        return redirect(url_for("docs.index"))
    original = file.filename
    ext = os.path.splitext(original)[1].lower()
    if ext not in DOC_EXT:
        flash("That file type is not allowed. Allowed: %s" % ", ".join(DOC_EXT), "error")
        return redirect(url_for("docs.index"))
    stored = secrets.token_hex(12) + ext
    path = os.path.join(_upload_dir(), stored)
    file.save(path)
    size = os.path.getsize(path)
    if size > 25 * 1024 * 1024:
        os.remove(path)
        flash("File is larger than 25 MB.", "error")
        return redirect(url_for("docs.index"))
    att = Attachment(filename=stored, original_name=original,
                     content_type=file.mimetype, size=size,
                     kind="image" if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp") else "file",
                     uploaded_by=current_user().id)
    db.session.add(att)
    db.session.flush()
    d = Document(title=request.form.get("title") or original,
                 category=request.form.get("category", "File"),
                 content_type="file", attachment_id=att.id,
                 created_by=current_user().full_name)
    db.session.add(d)
    log_action(current_user().username, "Uploaded document '%s'" % d.title)
    db.session.commit()
    flash("File uploaded to Doc Space.", "ok")
    return redirect(url_for("docs.view", did=d.id))


@bp.route("/file/<int:aid>")
@login_required()
def file(aid):
    a = Attachment.query.get_or_404(aid)
    return send_from_directory(_upload_dir(), a.filename,
                               as_attachment=request.args.get("download") == "1",
                               download_name=a.original_name)


@bp.route("/<int:did>", methods=["GET", "POST"])
@login_required()
def view(did):
    d = Document.query.get_or_404(did)
    if request.method == "POST":
        d.content = request.form.get("content", d.content)
        d.updated_at = datetime.utcnow()
        log_action(current_user().username, "Edited document '%s'" % d.title)
        db.session.commit()
        flash("Document saved.", "ok")
        return redirect(url_for("docs.view", did=did))
    return render_template("docs/view.html", d=d)


@bp.route("/<int:did>/export")
@login_required()
def export_html(did):
    """Download the document as a standalone file that opens in Word."""
    d = Document.query.get_or_404(did)
    if d.is_file:
        return redirect(url_for("docs.file", aid=d.attachment_id, download=1))
    html = """<!doctype html><html><head><meta charset="utf-8"><title>%s</title>
<style>body{font-family:Georgia,serif;max-width:800px;margin:40px auto;line-height:1.5}
table{border-collapse:collapse}td,th{border:1px solid #999;padding:6px}</style></head>
<body><h1>%s</h1><p><i>%s &middot; %s</i></p><hr>%s</body></html>""" % (
        d.title, d.title, d.category, d.created_by, d.content or "")
    return Response(html, mimetype="application/msword",
                    headers={"Content-Disposition": 'attachment; filename="%s.doc"' % d.title})


@bp.route("/<int:did>/delete", methods=["POST"])
@login_required()
def delete(did):
    d = Document.query.get_or_404(did)
    if current_user().role not in ("admin", "staff") and d.created_by != current_user().full_name:
        abort(403)
    att = d.attachment
    db.session.delete(d)
    if att:
        _delete_file(att)
    log_action(current_user().username, "Deleted document '%s'" % d.title)
    db.session.commit()
    flash("Document deleted.", "ok")
    return redirect(url_for("docs.index"))


def _delete_file(att):
    """Remove an attachment row and its file from disk."""
    try:
        path = os.path.join(_upload_dir(), att.filename)
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
    db.session.delete(att)


@bp.route("/policy")
@login_required()
def policy():
    return render_template("docs/policy.html")
