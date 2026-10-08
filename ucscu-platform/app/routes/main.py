"""Dashboard, admin (users + approval) and the first-run LAN setup screen."""
import ipaddress
import os
import socket
from datetime import date, datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app)

from .. import login_required, current_user
from ..helpers import notify
from ..integrations import email_configured, printer_configured
from ..models import (db, User, Sacco, CffLoan, CffDeposit, CffInvestment, FinancialReport,
                      ComplianceDeadline, TrainingEvent, StationeryOrder, AuditLog, ROLES,
                      Setting, get_setting, set_setting, log_action)

bp = Blueprint("main", __name__)


# ---------------------------------------------------------------- LAN helpers
def server_lan_ips():
    """Best-effort list of the LAN addresses this server is reachable on."""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ":" in ip:
                continue
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    # fall back to the classic UDP trick to find the primary interface address
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    if not ips:
        ips.append("127.0.0.1")
    return ips


def primary_ip():
    return server_lan_ips()[0]


def _qr_svg(data):
    """Render a QR code as inline SVG using a bundled pure-Python generator.
    Falls back to a simple message if the library is unavailable."""
    try:
        import qrcode
        import qrcode.image.svg as svg
        img = qrcode.make(data, image_factory=svg.SvgPathImage, box_size=10, border=2)
        import io
        buf = io.BytesIO()
        img.save(buf)
        return buf.getvalue().decode("utf-8")
    except Exception:
        return None


# ---------------------------------------------------------------- dashboard
@bp.route("/dashboard")
@login_required()
def dashboard():
    pool_deposits = sum(d.amount for d in CffDeposit.query.all())
    active_loans = CffLoan.query.filter(CffLoan.status.in_(["Disbursed"])).all()
    loans_out = sum(l.outstanding for l in active_loans)
    invested = sum(i.principal for i in CffInvestment.query.filter_by(status="Active").all())
    liquid = pool_deposits - loans_out - invested

    stats = {
        "saccos": Sacco.query.count(),
        "good_standing": Sacco.query.filter_by(good_standing=True).count(),
        "members": db.session.query(db.func.sum(Sacco.members_count)).scalar() or 0,
        "pool_deposits": pool_deposits,
        "loans_outstanding": loans_out,
        "invested": invested,
        "pool_liquid": liquid,
        "pending_loans": CffLoan.query.filter(CffLoan.status.in_(["Applied", "Under review"])).count(),
        "pending_orders": StationeryOrder.query.filter_by(status="Pending").count(),
        "reports": FinancialReport.query.count(),
    }
    deadlines = ComplianceDeadline.query.order_by(ComplianceDeadline.due_date).limit(6).all()
    events = TrainingEvent.query.filter(TrainingEvent.starts_on >= date.today()).order_by(TrainingEvent.starts_on).limit(4).all()
    recent = AuditLog.query.order_by(AuditLog.at.desc()).limit(8).all()
    return render_template("dashboard.html", stats=stats, deadlines=deadlines,
                           events=events, recent=recent)


# ---------------------------------------------------------------- users / approval
@bp.route("/admin/users", methods=["GET", "POST"])
@login_required("admin")
def users():
    if request.method == "POST":
        u = User(username=request.form["username"].strip().lower(),
                 full_name=request.form["full_name"].strip(),
                 role=request.form["role"],
                 status="active",
                 sacco_id=request.form.get("sacco_id") or None)
        u.set_password(request.form["password"])
        db.session.add(u)
        log_action(current_user().username, "Created user %s" % u.username)
        db.session.commit()
        flash("User %s created." % u.username, "ok")
        return redirect(url_for("main.users"))
    pending = User.query.filter_by(status="pending").order_by(User.created_at).all()
    return render_template("users.html", users=User.query.all(),
                           pending=pending, roles=ROLES,
                           saccos=Sacco.query.order_by(Sacco.name).all())


@bp.route("/admin/users/<int:uid>/<action>", methods=["POST"])
@login_required("admin")
def user_action(uid, action):
    u = User.query.get_or_404(uid)
    if action == "approve":
        u.status = "active"
        if request.form.get("role"):
            u.role = request.form["role"]
        notify(u.id, "approval", "Your account has been approved. Welcome!", url_for("social.feed"))
        log_action(current_user().username, "Approved user %s" % u.username)
        flash("%s approved." % u.full_name, "ok")
    elif action == "decline":
        db.session.delete(u)
        log_action(current_user().username, "Declined registration %s" % u.username)
        flash("Registration declined.", "ok")
    elif action == "disable":
        u.status = "disabled"
        log_action(current_user().username, "Disabled user %s" % u.username)
        flash("%s disabled." % u.full_name, "ok")
    elif action == "enable":
        u.status = "active"
        log_action(current_user().username, "Enabled user %s" % u.username)
        flash("%s enabled." % u.full_name, "ok")
    db.session.commit()
    return redirect(url_for("main.users"))


@bp.route("/admin/audit")
@login_required("admin")
def audit():
    return render_template("audit.html", logs=AuditLog.query.order_by(AuditLog.at.desc()).limit(200).all())


# ---------------------------------------------------------------- LAN setup
@bp.route("/setup", methods=["GET", "POST"])
@login_required("admin")
def setup():
    if request.method == "POST":
        keys = ("org_name", "lan_name", "office_cidr", "server_host",
                "printer_host", "printer_port",
                "smtp_host", "smtp_port", "smtp_user", "smtp_password",
                "smtp_from", "smtp_tls")
        for key in keys:
            if key in request.form:
                set_setting(key, request.form.get(key, "").strip())
        set_setting("setup_done", "1")
        log_action(current_user().username, "Updated LAN setup")
        db.session.commit()
        flash("Setup saved. Staff can now reach the server on the LAN.", "ok")
        return redirect(url_for("main.setup"))

    port = request.host.split(":")[1] if ":" in request.host else "80"
    ips = server_lan_ips()
    host = get_setting("server_host") or primary_ip()
    links = ["http://%s:%s/" % (ip, port) for ip in ips]
    join_url = links[0]
    cfg = {
        "org_name": get_setting("org_name", "UCSCU"),
        "lan_name": get_setting("lan_name", ""),
        "office_cidr": get_setting("office_cidr", ""),
        "server_host": host,
        "printer_host": get_setting("printer_host", ""),
        "printer_port": get_setting("printer_port", "9100"),
        "smtp_host": get_setting("smtp_host", ""),
        "smtp_port": get_setting("smtp_port", "25"),
        "smtp_user": get_setting("smtp_user", ""),
        "smtp_password": get_setting("smtp_password", ""),
        "smtp_from": get_setting("smtp_from", ""),
        "smtp_tls": get_setting("smtp_tls", "0"),
        "setup_done": get_setting("setup_done", "0"),
    }
    return render_template("setup.html", cfg=cfg, ips=ips, port=port,
                           links=links, join_url=join_url, qr_svg=_qr_svg(join_url),
                           printer_ok=printer_configured(), email_ok=email_configured())


@bp.route("/setup/test-printer", methods=["POST"])
@login_required("admin")
def test_printer():
    from ..integrations import print_raw
    ok, msg = print_raw(
        "UCSCU Connect test page\nIf you can read this, LAN printing works.\n"
        "Server time: %s" % datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        title="UCSCU Connect")
    log_action(current_user().username, "Test print: %s" % msg)
    db.session.commit()
    flash(msg, "ok" if ok else "error")
    return redirect(url_for("main.setup"))


@bp.route("/setup/qr.svg")
@login_required("admin")
def setup_qr():
    port = request.host.split(":")[1] if ":" in request.host else "80"
    url = "http://%s:%s/" % (primary_ip(), port)
    svg = _qr_svg(url)
    if svg:
        return svg, 200, {"Content-Type": "image/svg+xml"}
    return jsonify({"error": "qr library unavailable", "url": url}), 200


@bp.route("/healthz")
def healthz():
    """Used by the admin setup screen to confirm the server is live on the LAN."""
    return jsonify({"ok": True, "org": get_setting("org_name", "UCSCU"),
                    "ip": primary_ip(), "pending_users": User.query.filter_by(status="pending").count()})
