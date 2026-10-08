from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..helpers import notify
from ..models import db, User, Announcement, log_action

bp = Blueprint("comms", __name__, url_prefix="/comms")


def _audience_users(audience):
    users = User.query.filter_by(status="active").all()
    if audience in ("All", "", None):
        return users
    return [u for u in users if u.sacco and u.sacco.region == audience]


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
    db.session.flush()
    me = current_user()
    for u in _audience_users(a.audience):
        if u.id == me.id:
            continue
        notify(u.id, "announcement", "New announcement: %s" % a.title,
               url_for("comms.index"))
    log_action(me.username, f"Posted announcement: {a.title}")
    db.session.commit()
    # Production hook: fan out via Africa's Talking / Twilio SMS to member SACCO contacts.
    flash("Announcement published. Staff have been notified. (SMS gateway integration point for production.)", "ok")
    return redirect(url_for("comms.index"))
