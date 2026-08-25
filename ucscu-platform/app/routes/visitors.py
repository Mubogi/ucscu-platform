import random, string
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, User, Visitor, log_action

bp = Blueprint("visitors", __name__, url_prefix="/visitors")


def _next_tag():
    used = [v.tag_no for v in Visitor.query.filter(Visitor.departed_at.is_(None)).all()]
    for i in range(1, 200):
        tag = f"T-{i:03d}"
        if tag not in used:
            return tag
    return f"T-{random.randint(200, 999)}"


@bp.route("/")
@login_required()
def index():
    on_site = Visitor.query.filter(Visitor.departed_at.is_(None)).order_by(Visitor.arrived_at).all()
    departed = Visitor.query.filter(Visitor.departed_at.isnot(None)).order_by(Visitor.departed_at.desc()).limit(30).all()
    return render_template("visitors/index.html", on_site=on_site, departed=departed,
                           users=User.query.all(), next_tag=_next_tag())


@bp.route("/register", methods=["POST"])
@login_required()
def register():
    f = request.form
    v = Visitor(name=f["name"], organization=f.get("organization"), phone=f.get("phone"),
                tag_no=f.get("tag_no") or _next_tag(),
                host_user_id=int(f["host_user_id"]) if f.get("host_user_id") else None,
                purpose=f.get("purpose"), expected=f.get("expected") == "on",
                items=f.get("items"))
    db.session.add(v)
    db.session.flush()
    log_action(current_user().username, f"Registered visitor {v.name} (tag {v.tag_no})")
    db.session.commit()
    flash(f"Visitor {v.name} checked in — hand them tag {v.tag_no}.", "ok")
    return redirect(url_for("visitors.index"))


@bp.route("/<int:vid>/checkin", methods=["POST"])
@login_required()
def checkin(vid):
    v = Visitor.query.get_or_404(vid)
    if v.departed_at is not None:
        v.departed_at = None
        v.arrived_at = datetime.utcnow()
    db.session.commit()
    flash(f"{v.name} re-checked in.", "ok")
    return redirect(url_for("visitors.index"))


@bp.route("/<int:vid>/checkout", methods=["POST"])
@login_required()
def checkout(vid):
    v = Visitor.query.get_or_404(vid)
    v.departed_at = datetime.utcnow()
    log_action(current_user().username, f"Checked out visitor {v.name} (tag {v.tag_no})")
    db.session.commit()
    flash(f"{v.name} checked out — please collect tag {v.tag_no}.", "ok")
    return redirect(url_for("visitors.index"))


@bp.route("/<int:vid>/tag")
@login_required()
def tag(vid):
    v = Visitor.query.get_or_404(vid)
    return render_template("visitors/tag.html", v=v)
