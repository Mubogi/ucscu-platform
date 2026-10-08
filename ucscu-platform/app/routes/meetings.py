"""Multi-person LAN meeting rooms.

Peers form a full mesh: every participant negotiates a direct WebRTC connection
with every other participant. Signalling is stored in GroupSignal rows, so the
whole thing works with no internet access.
"""
import json
import secrets
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   jsonify, abort)

from .. import login_required, current_user
from ..helpers import notify
from ..models import (db, User, MeetingRoom, MeetingParticipant, GroupSignal, log_action)

bp = Blueprint("meetings", __name__, url_prefix="/meetings")


@bp.route("/")
@login_required()
def index():
    me = current_user()
    open_rooms = MeetingRoom.query.filter_by(status="open").order_by(
        MeetingRoom.created_at.desc()).all()
    recent = MeetingRoom.query.filter_by(status="ended").order_by(
        MeetingRoom.ended_at.desc()).limit(10).all()
    people = [u for u in User.query.filter_by(status="active").order_by(User.full_name).all()
              if u.id != me.id]
    return render_template("social/meetings.html", open_rooms=open_rooms,
                           recent=recent, people=people)


@bp.route("/new", methods=["POST"])
@login_required()
def create():
    me = current_user()
    title = (request.form.get("title") or "Meeting").strip() or "Meeting"
    kind = request.form.get("kind", "video")
    m = MeetingRoom(room="m" + secrets.token_hex(8), title=title, kind=kind, host_id=me.id)
    db.session.add(m)
    db.session.flush()
    for uid in request.form.getlist("invite"):
        try:
            uid = int(uid)
        except ValueError:
            continue
        if uid != me.id:
            notify(uid, "call", "%s invited you to a meeting: %s" % (me.full_name, title),
                   url_for("meetings.room", room=m.room))
    log_action(me.username, "Started a meeting room: %s" % title)
    db.session.commit()
    return redirect(url_for("meetings.room", room=m.room))


@bp.route("/<room>")
@login_required()
def room(room):
    me = current_user()
    m = MeetingRoom.query.filter_by(room=room).first_or_404()
    p = MeetingParticipant.query.filter_by(room_id=m.id, user_id=me.id).first()
    if not p:
        db.session.add(MeetingParticipant(room_id=m.id, user_id=me.id))
        db.session.commit()
    elif p.left_at is not None:
        p.left_at = None
        db.session.commit()
    return render_template("social/meeting.html", room=m, me=me)


@bp.route("/<room>/leave", methods=["POST"])
@login_required()
def leave(room):
    me = current_user()
    m = MeetingRoom.query.filter_by(room=room).first_or_404()
    p = MeetingParticipant.query.filter_by(room_id=m.id, user_id=me.id).first()
    if p and p.left_at is None:
        p.left_at = datetime.utcnow()
    if m.host_id == me.id:
        m.status = "ended"
        m.ended_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/<room>/end", methods=["POST"])
@login_required()
def end(room):
    me = current_user()
    m = MeetingRoom.query.filter_by(room=room).first_or_404()
    if m.host_id != me.id and me.role != "admin":
        abort(403)
    m.status = "ended"
    m.ended_at = datetime.utcnow()
    log_action(me.username, "Ended meeting room: %s" % m.title)
    db.session.commit()
    flash("Meeting ended.", "ok")
    return redirect(url_for("meetings.index"))


@bp.route("/api/<room>/members")
@login_required()
def api_members(room):
    me = current_user()
    m = MeetingRoom.query.filter_by(room=room).first_or_404()
    members = [{"id": p.user_id, "name": p.user.full_name,
                "host": p.user_id == m.host_id, "is_me": p.user_id == me.id}
               for p in m.active_members]
    return jsonify({"status": m.status, "kind": m.kind, "title": m.title,
                    "members": members, "host_id": m.host_id})


@bp.route("/api/<room>/signal", methods=["GET", "POST"])
@login_required()
def api_signal(room):
    me = current_user()
    m = MeetingRoom.query.filter_by(room=room).first_or_404()

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        try:
            peer = int(data.get("peer"))
        except (TypeError, ValueError):
            return jsonify({"error": "peer required"}), 400
        if peer == me.id:
            return jsonify({"error": "cannot signal yourself"}), 400
        low, high = sorted((me.id, peer))
        sig = GroupSignal.query.filter_by(room_id=m.id, from_id=low, to_id=high).first()
        if not sig:
            sig = GroupSignal(room_id=m.id, from_id=low, to_id=high, from_ice="[]", to_ice="[]")
            db.session.add(sig)
            db.session.flush()
        mine = "from" if me.id == low else "to"
        action = data.get("action")
        if action == "offer":
            setattr(sig, mine + "_ice", "[]")
            sig.offer = json.dumps(data.get("offer"))
        elif action == "answer":
            sig.answer = json.dumps(data.get("answer"))
        elif action == "ice":
            field = mine + "_ice"
            existing = json.loads(getattr(sig, field) or "[]")
            existing.append(data.get("ice"))
            setattr(sig, field, json.dumps(existing))
        db.session.commit()
        return jsonify({"ok": True})

    out = []
    sigs = GroupSignal.query.filter_by(room_id=m.id).filter(
        db.or_(GroupSignal.from_id == me.id, GroupSignal.to_id == me.id)).all()
    for sig in sigs:
        low_is_me = sig.from_id == me.id
        out.append({
            "peer": sig.to_id if low_is_me else sig.from_id,
            "offer": json.loads(sig.offer) if sig.offer else None,
            "answer": json.loads(sig.answer) if sig.answer else None,
            "peer_ice": json.loads((sig.to_ice if low_is_me else sig.from_ice) or "[]"),
            "i_am_offerer": low_is_me,
        })
    return jsonify({"status": m.status, "signals": out})
