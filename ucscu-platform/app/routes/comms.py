from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, Announcement, log_action

bp = Blueprint("comms", __name__, url_prefix="/comms")


@bp.route("/")
@login_required()
def index():
    me = current_user()
    items = Announcement.query.order_by(Announcement.posted_on.desc()).all()
    if me.role == "sacco" and me.sacco:
        region = me.sacco.region
        items = [a for a in items if a.audience in ("All", region)]
    return render_template("comms/index.html", items=items)


@bp.route("/post", methods=["POST"])
@login_required("staff", "board")
def post():
    f = request.form
    a = Announcement(title=f["title"], body=f.get("body"),
                     audience=f.get("audience", "All"), author=current_user().full_name)
    db.session.add(a)
    log_action(current_user().username, f"Posted announcement: {a.title}")
    db.session.commit()
    # Production hook: fan out via Africa's Talking / Twilio SMS to member SACCO contacts.
    flash("Announcement published. (SMS gateway integration point for production.)", "ok")
    return redirect(url_for("comms.index"))
