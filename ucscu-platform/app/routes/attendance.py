import ipaddress
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import (db, User, CheckInEvent, LeaveRequest, AttendanceMeeting,
                      AttendanceRecord, get_setting, log_action)

bp = Blueprint("attendance", __name__, url_prefix="/attendance")

# Extra office networks where on-premises check-in is allowed. The primary range is
# set by an admin on the LAN Setup screen; anything listed here is added on top.
OFFICE_NETS = []


def _office_nets():
    """CIDRs that may check in: the admin's LAN Setup range plus OFFICE_NETS."""
    nets = []
    configured = (get_setting("office_cidr") or "").strip()
    if configured:
        nets.extend(part.strip() for part in configured.replace(";", ",").split(",") if part.strip())
    nets.extend(OFFICE_NETS)
    return nets


def _on_office_lan(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    nets = _office_nets()
    if not nets:
        return addr.is_private  # demo behaviour until an admin sets the range
    for n in nets:
        try:
            if addr in ipaddress.ip_network(n, strict=False):
                return True
        except ValueError:
            continue
    return False


@bp.route("/")
@login_required()
def index():
    me = current_user()
    today = datetime.utcnow().date()
    my_events = CheckInEvent.query.filter_by(user_id=me.id).order_by(CheckInEvent.at.desc()).all()
    today_events = [e for e in my_events if e.at.date() == today]
    checked_in = bool(today_events) and today_events[0].kind == "check_in"
    all_users_events = CheckInEvent.query.order_by(CheckInEvent.at.desc()).limit(100).all() \
        if me.role in ("admin", "staff", "board") else []
    leave_reqs = LeaveRequest.query.order_by(LeaveRequest.requested_at.desc()).all()
    if me.role == "sacco":
        leave_reqs = [r for r in leave_reqs if r.user_id == me.id]
    meetings = AttendanceMeeting.query.order_by(AttendanceMeeting.on_date.desc()).limit(10).all()
    return render_template("attendance/index.html", checked_in=checked_in,
                           my_events=my_events[:10], all_events=all_users_events,
                           leave=leave_reqs, meetings=meetings, users=User.query.all())


@bp.route("/checkin/<kind>", methods=["POST"])
@login_required()
def checkin(kind):
    if kind not in ("check_in", "check_out"):
        flash("Unknown event.", "error")
        return redirect(url_for("attendance.index"))
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    if not _on_office_lan(ip):
        flash("You are not on the office LAN — check-in is allowed only from premises network "
              f"(your IP: {ip}).", "error")
        return redirect(url_for("attendance.index"))
    e = CheckInEvent(user_id=current_user().id, kind=kind, mode="lan", ip=ip,
                     lateness_reason=request.form.get("lateness_reason"))
    db.session.add(e)
    log_action(current_user().username, f"{kind} via LAN")
    db.session.commit()
    flash(f"{kind.replace('_', ' ').capitalize()} recorded on premises.", "ok")
    return redirect(url_for("attendance.index"))


@bp.route("/exemption", methods=["POST"])
@login_required()
def exemption():
    """Staff in the field / exempt from premises rule (e.g. board member, field officer)."""
    e = CheckInEvent(user_id=current_user().id, kind="check_in", mode="exemption",
                     ip=request.remote_addr, lateness_reason=request.form.get("lateness_reason"))
    db.session.add(e)
    log_action(current_user().username, "Check-in exemption (field/off-site)")
    db.session.commit()
    flash("Off-premises check-in recorded (exemption).", "ok")
    return redirect(url_for("attendance.index"))


@bp.route("/leave", methods=["POST"])
@login_required()
def leave_request():
    f = request.form
    r = LeaveRequest(user_id=current_user().id, kind=f["kind"],
                     starts_on=datetime.strptime(f["starts_on"], "%Y-%m-%d").date(),
                     ends_on=datetime.strptime(f["ends_on"], "%Y-%m-%d").date(),
                     reason=f["reason"])
    db.session.add(r)
    log_action(current_user().username, f"Requested {r.kind}")
    db.session.commit()
    flash(f"{r.kind} request submitted. Awaiting approval.", "ok")
    return redirect(url_for("attendance.index"))


@bp.route("/leave/<int:lid>/<status>", methods=["POST"])
@login_required("staff", "board", "admin")
def decide(lid, status):
    r = LeaveRequest.query.get_or_404(lid)
    if status in ("Approved", "Declined"):
        r.status = status
        r.decided_by = current_user().username
        log_action(current_user().username, f"Leave request {status.lower()} for {r.user.full_name}")
        db.session.commit()
        flash(f"Request {status.lower()}.", "ok")
    return redirect(url_for("attendance.index"))


@bp.route("/meeting/new", methods=["POST"])
@login_required("staff", "board", "admin")
def new_meeting():
    f = request.form
    m = AttendanceMeeting(title=f["title"],
                          on_date=datetime.strptime(f["on_date"], "%Y-%m-%d").date(),
                          venue=f.get("venue"))
    db.session.add(m)
    db.session.commit()
    flash("Meeting created for attendance tracking.", "ok")
    return redirect(url_for("attendance.meeting", mid=m.id))


@bp.route("/meeting/<int:mid>")
@login_required()
def meeting(mid):
    m = AttendanceMeeting.query.get_or_404(mid)
    users = User.query.all()
    return render_template("attendance/meeting.html", m=m, users=users)


@bp.route("/meeting/<int:mid>/mark", methods=["POST"])
@login_required("staff", "board", "admin")
def mark(mid):
    f = request.form
    m = AttendanceMeeting.query.get_or_404(mid)
    for u in User.query.all():
        key = f"user_{u.id}"
        present = f.get(key) == "on"
        rec = AttendanceRecord.query.filter_by(meeting_id=mid, user_id=u.id).first()
        if not rec:
            rec = AttendanceRecord(meeting_id=mid, user_id=u.id)
            db.session.add(rec)
        rec.present = present
        rec.note = f.get(f"note_{u.id}", rec.note)
    log_action(current_user().username, f"Marked attendance for meeting #{mid}")
    db.session.commit()
    flash("Attendance sheet saved.", "ok")
    return redirect(url_for("attendance.meeting", mid=mid))
