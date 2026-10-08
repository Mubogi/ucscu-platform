"""Sign in, self-registration (pending admin approval) and sign out."""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash)

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


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
