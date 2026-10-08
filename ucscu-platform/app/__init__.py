import os
from functools import wraps
from flask import Flask, session, redirect, url_for, request, render_template, flash, abort

from .models import db, User


def current_user():
    uid = session.get("uid")
    return User.query.get(uid) if uid else None


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                return redirect(url_for("auth.login", next=request.path))
            if roles and u.role not in roles and u.role != "admin":
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ucscu-dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "ucscu.db"))
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from .routes.auth import bp as auth_bp
    from .routes.main import bp as main_bp
    from .routes.saccos import bp as saccos_bp
    from .routes.cff import bp as cff_bp
    from .routes.reports import bp as reports_bp
    from .routes.training import bp as training_bp
    from .routes.services import bp as services_bp
    from .routes.comms import bp as comms_bp
    from .routes.governance import bp as governance_bp
    from .routes.attendance import bp as attendance_bp
    from .routes.visitors import bp as visitors_bp
    from .routes.hub import bp as hub_bp
    from .routes.whistle import bp as whistle_bp
    from .routes.docs import bp as docs_bp
    from .routes.calendar import bp as calendar_bp
    from .routes.social import bp as social_bp
    from .routes.messaging import bp as messaging_bp

    for bp in (auth_bp, main_bp, saccos_bp, cff_bp, reports_bp,
               training_bp, services_bp, comms_bp, governance_bp,
               attendance_bp, visitors_bp, hub_bp, whistle_bp, docs_bp,
               calendar_bp, social_bp, messaging_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        u = current_user()
        unread = 0
        if u:
            from .models import Notification
            unread = Notification.query.filter_by(user_id=u.id, read=False).count()
        return {"me": u, "unread_notifications": unread}

    @app.template_filter("ugx")
    def ugx(v):
        try:
            return "UGX {:,.0f}".format(int(v or 0))
        except (TypeError, ValueError):
            return "UGX 0"

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    with app.app_context():
        db.create_all()
        if not User.query.first():
            from .seed import seed
            seed()

    return app
