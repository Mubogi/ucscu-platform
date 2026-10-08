"""Home feed, personal chat, notifications, file uploads and LAN call signalling."""
import json
import os
import secrets
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   jsonify, current_app, send_from_directory, abort)
from werkzeug.utils import secure_filename

from .. import login_required, current_user
from ..helpers import notify
from ..models import (db, User, FeedPost, FeedComment, FeedLike, DirectThread,
                      DirectMessage, Attachment, Notification, CallSession, log_action)

bp = Blueprint("social", __name__)

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
FILE_EXT = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".txt", ".csv", ".odt", ".ods", ".zip")
MAX_UPLOAD = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------- helpers
def upload_dir():
    d = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(d, exist_ok=True)
    return d


def save_upload(file_storage):
    """Persist an uploaded file and return an Attachment row (not yet committed).

    Returns None if there is no file, the extension is not allowed, or it is too big.
    """
    if not file_storage or not file_storage.filename:
        return None
    original = file_storage.filename
    ext = os.path.splitext(original)[1].lower()
    if ext not in IMAGE_EXT + FILE_EXT:
        return None
    stored = secrets.token_hex(12) + ext
    path = os.path.join(upload_dir(), stored)
    file_storage.save(path)
    size = os.path.getsize(path)
    if size > MAX_UPLOAD:
        os.remove(path)
        return None
    kind = "image" if ext in IMAGE_EXT else "file"
    return Attachment(filename=stored, original_name=original,
                      content_type=file_storage.mimetype, size=size,
                      kind=kind, uploaded_by=current_user().id)


def delete_attachment(att):
    """Remove an attachment row and its file from disk."""
    if att is None:
        return
    try:
        path = os.path.join(upload_dir(), att.filename)
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
    db.session.delete(att)


# ---------------------------------------------------------------- uploads
@bp.route("/uploads/<path:name>")
@login_required()
def uploaded_file(name):
    return send_from_directory(upload_dir(), name)


# ---------------------------------------------------------------- home feed
@bp.route("/")
@login_required()
def feed():
    me = current_user()
    posts = [p for p in FeedPost.query.order_by(FeedPost.at.desc()).all() if p.visible_to(me)]
    # right rail: upcoming events + birthdays-style staff list
    people = User.query.order_by(User.full_name).all()
    return render_template("social/feed.html", posts=posts, people=people)


@bp.route("/post", methods=["POST"])
@login_required()
def create_post():
    body = (request.form.get("body") or "").strip()
    photo = request.files.get("photo")
    att = save_upload(photo)
    if photo and photo.filename and att is None:
        flash("That attachment was rejected — it is either too large or not an allowed file type.", "error")
        return redirect(url_for("social.feed"))
    if not body and not att:
        flash("Write something or attach a photo.", "error")
        return redirect(url_for("social.feed"))
    p = FeedPost(author_id=current_user().id, body=body, scope=request.form.get("scope", "all"))
    if att:
        db.session.add(att)
        db.session.flush()
        p.attachment_id = att.id
    db.session.add(p)
    log_action(current_user().username, "Posted on the home feed")
    db.session.commit()
    flash("Posted to the feed.", "ok")
    return redirect(url_for("social.feed"))


@bp.route("/post/<int:pid>/comment", methods=["POST"])
@login_required()
def comment(pid):
    p = FeedPost.query.get_or_404(pid)
    if not p.visible_to(current_user()):
        abort(403)
    body = (request.form.get("body") or "").strip()
    if body:
        db.session.add(FeedComment(post_id=pid, author_id=current_user().id, body=body))
        if p.author_id != current_user().id:
            notify(p.author_id, "comment", f"{current_user().full_name} commented on your post", url_for("social.feed"))
        log_action(current_user().username, "Commented on a feed post")
        db.session.commit()
    return redirect(url_for("social.feed") + f"#post-{pid}")


@bp.route("/post/<int:pid>/like", methods=["POST"])
@login_required()
def like(pid):
    p = FeedPost.query.get_or_404(pid)
    me = current_user()
    if not p.visible_to(me):
        abort(403)
    existing = FeedLike.query.filter_by(post_id=pid, user_id=me.id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(FeedLike(post_id=pid, user_id=me.id))
        if p.author_id != me.id:
            notify(p.author_id, "like", f"{me.full_name} liked your post", url_for("social.feed"))
    log_action(me.username, "Toggled like on a feed post")
    db.session.commit()
    return redirect(url_for("social.feed") + f"#post-{pid}")


@bp.route("/post/<int:pid>/delete", methods=["POST"])
@login_required()
def delete_post(pid):
    p = FeedPost.query.get_or_404(pid)
    if p.author_id != current_user().id and current_user().role != "admin":
        abort(403)
    att = p.attachment
    db.session.delete(p)
    if att:
        delete_attachment(att)
    log_action(current_user().username, "Deleted a feed post")
    db.session.commit()
    flash("Post deleted.", "ok")
    return redirect(url_for("social.feed"))


# ---------------------------------------------------------------- chat
@bp.route("/chat")
@login_required()
def chat():
    me = current_user()
    threads = DirectThread.query.filter(
        db.or_(DirectThread.a_id == me.id, DirectThread.b_id == me.id)).all()
    threads.sort(key=lambda t: (t.last.at if t.last else t.created_at), reverse=True)
    contacts = [u for u in User.query.order_by(User.full_name).all() if u.id != me.id]
    return render_template("social/chat.html", threads=threads, contacts=contacts, active=None)


@bp.route("/chat/<int:uid>")
@login_required()
def chat_with(uid):
    me = current_user()
    other = User.query.get_or_404(uid)
    if other.id == me.id:
        return redirect(url_for("social.chat"))
    t = DirectThread.query.filter(
        db.or_(db.and_(DirectThread.a_id == me.id, DirectThread.b_id == uid),
               db.and_(DirectThread.a_id == uid, DirectThread.b_id == me.id))).first()
    if not t:
        t = DirectThread(a_id=me.id, b_id=uid)
        db.session.add(t)
        db.session.commit()
    threads = DirectThread.query.filter(
        db.or_(DirectThread.a_id == me.id, DirectThread.b_id == me.id)).all()
    threads.sort(key=lambda x: (x.last.at if x.last else x.created_at), reverse=True)
    contacts = [u for u in User.query.order_by(User.full_name).all() if u.id != me.id]
    return render_template("social/chat.html", threads=threads, contacts=contacts, active=t, other=other)


@bp.route("/chat/<int:tid>/send", methods=["POST"])
@login_required()
def send_message(tid):
    me = current_user()
    t = DirectThread.query.get_or_404(tid)
    if me.id not in (t.a_id, t.b_id):
        abort(403)
    body = (request.form.get("body") or "").strip()
    f = request.files.get("file")
    att = save_upload(f)
    if f and f.filename and att is None:
        flash("That file was rejected — it is either too large or not an allowed file type.", "error")
        return redirect(url_for("social.chat_with", uid=t.other(me).id))
    if not body and not att:
        return redirect(url_for("social.chat_with", uid=t.other(me).id))
    msg = DirectMessage(thread_id=tid, author_id=me.id, body=body)
    if att:
        db.session.add(att)
        db.session.flush()
        msg.attachment_id = att.id
    db.session.add(msg)
    other = t.other(me)
    notify(other.id, "message", f"New message from {me.full_name}",
           url_for("social.chat_with", uid=me.id))
    log_action(me.username, f"Sent a direct message to {other.username}")
    db.session.commit()
    return redirect(url_for("social.chat_with", uid=other.id))


# ---------------------------------------------------------------- notifications
@bp.route("/notifications")
@login_required()
def notifications():
    me = current_user()
    items = Notification.query.filter_by(user_id=me.id).order_by(Notification.at.desc()).limit(100).all()
    for n in items:
        n.read = True
    db.session.commit()
    return render_template("social/notifications.html", items=items)


@bp.route("/api/notifications")
@login_required()
def api_notifications():
    me = current_user()
    unread = Notification.query.filter_by(user_id=me.id, read=False).order_by(Notification.at.desc()).all()
    return jsonify({"unread": len(unread),
                    "items": [{"id": n.id, "kind": n.kind, "text": n.text,
                               "link": n.link, "at": n.at.strftime("%H:%M")} for n in unread[:8]]})


@bp.route("/notifications/read", methods=["POST"])
@login_required()
def mark_read():
    me = current_user()
    Notification.query.filter_by(user_id=me.id, read=False).update({"read": True})
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- calls (LAN)
@bp.route("/call/start/<int:uid>")
@login_required()
def call_start(uid):
    me = current_user()
    other = User.query.get_or_404(uid)
    kind = request.args.get("kind", "video")
    room = "r" + secrets.token_hex(8)
    c = CallSession(room=room, kind=kind, caller_id=me.id, callee_id=other.id, status="ringing")
    db.session.add(c)
    notify(other.id, "call", f"{'Video' if kind == 'video' else 'Voice'} call from {me.full_name}", "/call/" + room)
    log_action(me.username, f"Started a {kind} call to {other.username}")
    db.session.commit()
    return redirect(url_for("social.call_room", room=room))


@bp.route("/call/<room>")
@login_required()
def call_room(room):
    me = current_user()
    c = CallSession.query.filter_by(room=room).first_or_404()
    if me.id not in (c.caller_id, c.callee_id):
        abort(403)
    other = c.callee if me.id == c.caller_id else c.caller
    return render_template("social/call.html", call=c, other=other, is_caller=(me.id == c.caller_id))


@bp.route("/api/call/<room>", methods=["GET", "POST"])
@login_required()
def api_call(room):
    me = current_user()
    c = CallSession.query.filter_by(room=room).first_or_404()
    if me.id not in (c.caller_id, c.callee_id):
        abort(403)
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        action = data.get("action")
        if action == "offer":
            c.offer = json.dumps(data.get("offer"))
        elif action == "answer":
            c.answer = json.dumps(data.get("answer"))
            c.status = "accepted"
        elif action == "ice":
            side = "caller" if me.id == c.caller_id else "callee"
            field = "caller_ice" if side == "caller" else "callee_ice"
            existing = json.loads(getattr(c, field) or "[]")
            existing.append(data.get("ice"))
            setattr(c, field, json.dumps(existing))
        elif action == "decline":
            c.status = "declined"
        elif action == "end":
            c.status = "ended"
            c.ended_at = datetime.utcnow()
        db.session.commit()
    state = {
        "status": c.status,
        "kind": c.kind,
        "caller": c.caller.full_name,
        "callee": c.callee.full_name,
        "offer": json.loads(c.offer) if c.offer else None,
        "answer": json.loads(c.answer) if c.answer else None,
        "caller_ice": json.loads(c.caller_ice or "[]"),
        "callee_ice": json.loads(c.callee_ice or "[]"),
    }
    return jsonify(state)


# ---------------------------------------------------------------- search people
@bp.route("/api/people")
@login_required()
def api_people():
    q = request.args.get("q", "").strip().lower()
    users = User.query.order_by(User.full_name).all()
    if q:
        users = [u for u in users if q in (u.full_name or "").lower()
                 or q in (u.username or "").lower() or q in (u.role or "").lower()]
    me = current_user()
    return jsonify([{"id": u.id, "name": u.full_name, "role": u.role,
                     "sacco": u.sacco.name if u.sacco else None,
                     "is_me": u.id == me.id} for u in users[:20]])
