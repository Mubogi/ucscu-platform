from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, Meeting, Resolution, log_action

bp = Blueprint("governance", __name__, url_prefix="/governance")


@bp.route("/")
@login_required()
def index():
    meetings = Meeting.query.order_by(Meeting.meets_on.desc()).all()
    return render_template("governance/index.html", meetings=meetings, now_date=date.today())


@bp.route("/meeting/new", methods=["POST"])
@login_required("staff")
def new_meeting():
    f = request.form
    m = Meeting(title=f["title"], body_type=f.get("body_type", "Board"),
                meets_on=datetime.strptime(f["meets_on"], "%Y-%m-%d").date(),
                venue=f.get("venue"), agenda=f.get("agenda"))
    db.session.add(m)
    log_action(current_user().username, f"Scheduled meeting: {m.title}")
    db.session.commit()
    flash("Meeting scheduled.", "ok")
    return redirect(url_for("governance.index"))


@bp.route("/meeting/<int:mid>", methods=["GET", "POST"])
@login_required()
def meeting(mid):
    m = Meeting.query.get_or_404(mid)
    if request.method == "POST":
        m.minutes = request.form.get("minutes")
        db.session.commit()
        flash("Minutes saved.", "ok")
        return redirect(url_for("governance.meeting", mid=mid))
    return render_template("governance/meeting.html", m=m)


@bp.route("/meeting/<int:mid>/resolution", methods=["POST"])
@login_required("staff", "board")
def add_resolution(mid):
    db.session.add(Resolution(meeting_id=mid, text=request.form["text"]))
    db.session.commit()
    flash("Resolution proposed.", "ok")
    return redirect(url_for("governance.meeting", mid=mid))


@bp.route("/resolution/<int:rid>/vote/<vote>", methods=["POST"])
@login_required("board")
def vote(rid, vote):
    r = Resolution.query.get_or_404(rid)
    if r.status != "Open":
        flash("Voting is closed on this resolution.", "error")
        return redirect(url_for("governance.meeting", mid=r.meeting_id))
    if vote == "for":
        r.votes_for += 1
    elif vote == "against":
        r.votes_against += 1
    else:
        r.votes_abstain += 1
    log_action(current_user().username, f"Voted '{vote}' on resolution #{rid}")
    db.session.commit()
    return redirect(url_for("governance.meeting", mid=r.meeting_id))


@bp.route("/resolution/<int:rid>/close", methods=["POST"])
@login_required("board")
def close_vote(rid):
    r = Resolution.query.get_or_404(rid)
    r.status = "Adopted" if r.votes_for > r.votes_against else "Rejected"
    db.session.commit()
    flash(f"Resolution {r.status.lower()}.", "ok")
    return redirect(url_for("governance.meeting", mid=r.meeting_id))
