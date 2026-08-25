import random, string
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, ConfidentialReport, log_action

bp = Blueprint("whistle", __name__, url_prefix="/whistle")


def _token():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


@bp.route("/")
@login_required()
def index():
    me = current_user()
    reports = ConfidentialReport.query.order_by(ConfidentialReport.filed_at.desc()).all() \
        if me.role in ("admin", "staff", "board") else []
    return render_template("whistle/index.html", reports=reports)


@bp.route("/file", methods=["POST"])
@login_required()
def file_report():
    f = request.form
    body = f["body"].strip()
    if not body:
        flash("Report text is required.", "error")
        return redirect(url_for("whistle.index"))
    r = ConfidentialReport(token=_token(), category=f.get("category", "Fraud"), body=body)
    db.session.add(r)
    # Deliberately NOT logging the actor — anonymity by design.
    db.session.commit()
    flash(f"Report filed anonymously. Save this token to check status: {r.token}", "ok")
    return redirect(url_for("whistle.index"))


@bp.route("/status", methods=["POST"])
@login_required()
def status():
    t = request.form["token"].strip()
    r = ConfidentialReport.query.filter_by(token=t).first()
    if r:
        flash(f"Report {t}: status {r.status}"
              + (f" — {r.resolution_note}" if r.resolution_note else ""), "ok")
    else:
        flash("Token not found. Check and try again.", "error")
    return redirect(url_for("whistle.index"))


@bp.route("/report/<int:rid>/<status>", methods=["POST"])
@login_required("admin", "staff")
def set_status(rid, status):
    r = ConfidentialReport.query.get_or_404(rid)
    if status in ("Investigating", "Resolved", "Closed"):
        r.status = status
        r.resolution_note = request.form.get("resolution_note", r.resolution_note)
        log_action(current_user().username, f"Whistleblowing case #{r.id} → {status}")
        db.session.commit()
        flash(f"Case {status.lower()}.", "ok")
    return redirect(url_for("whistle.index"))
