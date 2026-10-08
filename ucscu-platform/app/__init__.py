import os
from functools import wraps
from flask import Flask, session, redirect, url_for, request, render_template, flash, abort
from sqlalchemy import inspect, text

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
            if u.status != "active":
                session.clear()
                flash("Your account is not active. Please contact an administrator.", "error")
                return redirect(url_for("auth.login"))
            if roles and u.role not in roles and u.role != "admin":
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


def _ensure_columns(app):
    """Add columns that were introduced after a database was first created.

    SQLite's create_all() never alters existing tables, so an installation made
    before these fields existed would break without this."""
    insp = inspect(db.engine)
    existing_tables = set(insp.get_table_names())
    for model in db.Model.__subclasses__():
        table = model.__tablename__
        if table not in existing_tables:
            continue
        have = {c["name"] for c in insp.get_columns(table)}
        for col in model.__table__.columns:
            if col.name in have:
                continue
            ddl = 'ALTER TABLE "%s" ADD COLUMN "%s" %s' % (
                table, col.name, col.type.compile(db.engine.dialect))
            default = None
            if col.default is not None and getattr(col.default, "arg", None) is not None \
                    and not callable(col.default.arg):
                default = col.default.arg
            elif col.name == "status":
                default = "active"
            try:
                with db.engine.begin() as conn:
                    if default is not None:
                        if isinstance(default, (int, float)):
                            conn.execute(text(ddl + " DEFAULT %s" % default))
                        else:
                            conn.execute(text(ddl + " DEFAULT '%s'" % default))
                    else:
                        conn.execute(text(ddl))
                app.logger.info("Migrated: added %s.%s", table, col.name)
            except Exception as e:  # pragma: no cover - best effort
                app.logger.warning("Could not add %s.%s: %s", table, col.name, e)


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
        pending = 0
        if u:
            from .models import Notification
            unread = Notification.query.filter_by(user_id=u.id, read=False).count()
            if u.role == "admin":
                pending = User.query.filter_by(status="pending").count()
        return {"me": u, "unread_notifications": unread, "pending_users": pending}

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
        _ensure_columns(app)
        if not User.query.first():
            from .seed import seed
            seed()

    return app
