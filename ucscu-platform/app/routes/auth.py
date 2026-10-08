"""Sign in, self-registration (pending admin approval) and sign out."""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)

from .. import login_required
from ..models import db, User, get_setting, log_action
from ..helpers import notify

bp = Blueprint("auth", __name__)


def _server_url():
    from .main import primary_ip
    port = request.host.split(":")[1] if ":" in request.host else "80"
    return "http://%s:%s/" % (primary_ip(), port)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"].strip()).first()
        if u and u.check_password(request.form["password"]):
            if u.status == "pending":
                flash("Your account is awaiting administrator approval.", "error")
                return render_template("login.html", server_url=_server_url())
            if u.status == "disabled":
                flash("This account has been disabled. Contact an administrator.", "error")
                return render_template("login.html", server_url=_server_url())
            session["uid"] = u.id
            flash("Welcome back, %s." % u.full_name, "ok")
            if u.role == "admin" and get_setting("setup_done") != "1":
                flash("First-time setup: confirm your office network and share the connect link.", "ok")
                return redirect(url_for("main.setup"))
            return redirect(request.args.get("next") or url_for("social.feed"))
        flash("Invalid username or password.", "error")
    return render_template("login.html", server_url=_server_url())


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        username = (f.get("username") or "").strip().lower()
        full_name = (f.get("full_name") or "").strip()
        password = f.get("password") or ""
        confirm = f.get("confirm") or ""

        if not username or not full_name or not password:
            flash("All fields are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
        else:
            u = User(username=username, full_name=full_name, role="staff",
                     status="pending", email=f.get("email"),
                     department=f.get("department"))
            u.set_password(password)
            db.session.add(u)
            db.session.flush()
            # tell every active admin there is something to approve
            for admin in User.query.filter_by(role="admin", status="active").all():
                notify(admin.id, "approval",
                       "New account request: %s (%s)" % (full_name, username),
                       url_for("main.users"))
            log_action(username, "Self-registered, awaiting approval")
            db.session.commit()
            return render_template("register_pending.html", full_name=full_name)
    return render_template("register.html")


@bp.route("/profile", methods=["GET", "POST"])
@login_required()
def profile():
    from .. import current_user
    me = current_user()
    if request.method == "POST":
        f = request.form
        me.full_name = (f.get("full_name") or me.full_name).strip()
        me.email = (f.get("email") or "").strip()
        me.department = (f.get("department") or "").strip()
        me.phone = (f.get("phone") or "").strip()
        current = f.get("current_password") or ""
        new = f.get("new_password") or ""
        if new:
            if not me.check_password(current):
                flash("Current password is incorrect.", "error")
                return redirect(url_for("auth.profile"))
            if len(new) < 6:
                flash("New password must be at least 6 characters.", "error")
                return redirect(url_for("auth.profile"))
            me.set_password(new)
            log_action(me.username, "Changed own password")
            flash("Password changed.", "ok")
        else:
            log_action(me.username, "Updated own profile")
            flash("Profile updated.", "ok")
        db.session.commit()
        return redirect(url_for("auth.profile"))
    return render_template("profile.html", me=me)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
