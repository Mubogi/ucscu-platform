from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, Sacco, Course, Lesson, TrainingEvent, TrainingRegistration, log_action

bp = Blueprint("training", __name__, url_prefix="/training")


@bp.route("/")
@login_required()
def index():
    courses = Course.query.order_by(Course.title).all()
    events = TrainingEvent.query.order_by(TrainingEvent.starts_on.desc()).all()
    return render_template("training/index.html", courses=courses, events=events)


@bp.route("/course/<int:cid>")
@login_required()
def course(cid):
    c = Course.query.get_or_404(cid)
    lessons = sorted(c.lessons, key=lambda l: l.order)
    return render_template("training/course.html", c=c, lessons=lessons)


@bp.route("/course/new", methods=["POST"])
@login_required("staff")
def new_course():
    c = Course(title=request.form["title"], category=request.form.get("category", "Governance"),
               description=request.form.get("description"))
    db.session.add(c)
    db.session.commit()
    flash("Course created.", "ok")
    return redirect(url_for("training.course", cid=c.id))


@bp.route("/course/<int:cid>/lesson", methods=["POST"])
@login_required("staff")
def add_lesson(cid):
    c = Course.query.get_or_404(cid)
    db.session.add(Lesson(course_id=cid, title=request.form["title"],
                          content=request.form.get("content"),
                          order=len(c.lessons) + 1))
    db.session.commit()
    flash("Lesson added.", "ok")
    return redirect(url_for("training.course", cid=cid))


@bp.route("/event/new", methods=["POST"])
@login_required("staff")
def new_event():
    f = request.form
    e = TrainingEvent(course_id=int(f["course_id"]), venue=f.get("venue"),
                      starts_on=datetime.strptime(f["starts_on"], "%Y-%m-%d").date(),
                      ends_on=datetime.strptime(f["ends_on"], "%Y-%m-%d").date() if f.get("ends_on") else None,
                      capacity=int(f.get("capacity") or 40), fee=int(f.get("fee") or 0))
    db.session.add(e)
    db.session.commit()
    flash("Training event scheduled.", "ok")
    return redirect(url_for("training.index"))


@bp.route("/event/<int:eid>/register", methods=["POST"])
@login_required("staff", "sacco")
def register(eid):
    e = TrainingEvent.query.get_or_404(eid)
    me = current_user()
    sacco_id = int(request.form["sacco_id"])
    if me.role == "sacco" and me.sacco_id != sacco_id:
        flash("You can only register participants from your own SACCO.", "error")
        return redirect(url_for("training.index"))
    if e.seats_taken >= e.capacity:
        flash("This event is full.", "error")
        return redirect(url_for("training.index"))
    db.session.add(TrainingRegistration(event_id=eid, sacco_id=sacco_id,
                                        participant=request.form["participant"]))
    log_action(me.username, f"Training registration for event #{eid}")
    db.session.commit()
    flash("Participant registered.", "ok")
    return redirect(url_for("training.event", eid=eid))


@bp.route("/event/<int:eid>")
@login_required()
def event(eid):
    e = TrainingEvent.query.get_or_404(eid)
    saccos = Sacco.query.order_by(Sacco.name).all()
    return render_template("training/event.html", e=e, saccos=saccos)


@bp.route("/registration/<int:rid>/mark", methods=["POST"])
@login_required("staff")
def mark(rid):
    r = TrainingRegistration.query.get_or_404(rid)
    field = request.form["field"]
    if field == "attended":
        r.attended = not r.attended
        if not r.attended:
            r.certified = False
    elif field == "certified" and r.attended:
        r.certified = not r.certified
    db.session.commit()
    return redirect(url_for("training.event", eid=r.event_id))
