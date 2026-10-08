from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..models import db, User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"].strip()).first()
        if u and u.check_password(request.form["password"]):
            session["uid"] = u.id
            flash(f"Welcome back, {u.full_name}.", "ok")
            return redirect(request.args.get("next") or url_for("social.feed"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
