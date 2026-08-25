from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from .. import login_required, current_user
from ..models import db, Space, Post, Reply, log_action

bp = Blueprint("hub", __name__, url_prefix="/hub")


@bp.route("/")
@login_required()
def index():
    me = current_user()
    spaces = [s for s in Space.query.order_by(Space.name).all() if s.visible_to(me)]
    latest = sorted([p for s in spaces for p in s.posts], key=lambda p: p.at, reverse=True)
    return render_template("hub/index.html", spaces=spaces, latest=latest[:15])


@bp.route("/space/<int:sid>")
@login_required()
def space(sid):
    s = Space.query.get_or_404(sid)
    if not s.visible_to(current_user()):
        abort(403)
    posts = sorted(s.posts, key=lambda p: p.at, reverse=True)
    return render_template("hub/space.html", s=s, posts=posts)


@bp.route("/space/<int:sid>/post", methods=["POST"])
@login_required()
def post(sid):
    s = Space.query.get_or_404(sid)
    if not s.visible_to(current_user()):
        abort(403)
    p = Post(space_id=sid, author_id=current_user().id, body=request.form["body"])
    db.session.add(p)
    log_action(current_user().username, f"Posted in space '{s.name}'")
    db.session.commit()
    flash("Posted.", "ok")
    return redirect(url_for("hub.space", sid=sid))


@bp.route("/post/<int:pid>/reply", methods=["POST"])
@login_required()
def reply(pid):
    p = Post.query.get_or_404(pid)
    if not p.space.visible_to(current_user()):
        abort(403)
    db.session.add(Reply(post_id=pid, author_id=current_user().id, body=request.form["body"]))
    db.session.commit()
    return redirect(url_for("hub.space", sid=p.space_id))


@bp.route("/space/new", methods=["POST"])
@login_required("admin", "staff")
def new_space():
    f = request.form
    s = Space(name=f["name"].strip(), scope=f.get("scope", "all"), description=f.get("description"))
    db.session.add(s)
    db.session.commit()
    flash(f"Space '{s.name}' created.", "ok")
    return redirect(url_for("hub.index"))
