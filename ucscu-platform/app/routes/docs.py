from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, Document, MINUTE_TEMPLATES, log_action

bp = Blueprint("docs", __name__, url_prefix="/docs")


@bp.route("/")
@login_required()
def index():
    docs = Document.query.order_by(Document.at.desc()).all()
    return render_template("docs/index.html", docs=docs, templates=MINUTE_TEMPLATES)


@bp.route("/new", methods=["POST"])
@login_required()
def new_doc():
    f = request.form
    tmpl = f.get("template")
    d = Document(title=f["title"], category=f.get("category", "Minutes"),
                 content=MINUTE_TEMPLATES.get(tmpl, f.get("content", "")) if tmpl else f.get("content", ""),
                 created_by=current_user().full_name)
    db.session.add(d)
    log_action(current_user().username, f"Created document '{d.title}'")
    db.session.commit()
    flash("Document created.", "ok")
    return redirect(url_for("docs.view", did=d.id))


@bp.route("/<int:did>", methods=["GET", "POST"])
@login_required()
def view(did):
    d = Document.query.get_or_404(did)
    if request.method == "POST":
        d.content = request.form.get("content", d.content)
        db.session.commit()
        flash("Document updated.", "ok")
        return redirect(url_for("docs.view", did=did))
    return render_template("docs/view.html", d=d)


@bp.route("/policy")
@login_required()
def policy():
    return render_template("docs/policy.html")
