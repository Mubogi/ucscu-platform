from datetime import date
from flask import Blueprint, render_template
from .. import login_required
from ..models import (Meeting, TrainingEvent, ComplianceDeadline, LeaveRequest, User,
                      MeetingRoom)

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@bp.route("/")
@login_required()
def index():
    events = []
    for m in Meeting.query.all():
        events.append({"date": m.meets_on, "title": m.title, "kind": "Meeting", "kind_class": "b-info"})
    for t in TrainingEvent.query.all():
        events.append({"date": t.starts_on, "title": t.course.title, "kind": "Training",
                       "kind_class": "b-ok"})
    for room in MeetingRoom.query.filter_by(status="open").all():
        events.append({"date": room.created_at.date(), "title": "Meeting room: " + room.title,
                       "kind": "Live meeting", "kind_class": "b-info"})
    for c in ComplianceDeadline.query.all():
        events.append({"date": c.due_date, "title": c.title, "kind": c.category, "kind_class": "b-danger"})
    for r in LeaveRequest.query.filter_by(status="Approved").all():
        events.append({"date": r.starts_on, "title": f"{r.user.full_name} — {r.kind}",
                       "kind": "Leave", "kind_class": "b-warn"})
    events.sort(key=lambda e: e["date"])
    return render_template("calendar.html", events=events, today=date.today())
