from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import (db, User, Sacco, CffLoan, CffDeposit, CffInvestment, FinancialReport,
                      ComplianceDeadline, TrainingEvent, StationeryOrder, AuditLog, ROLES)

bp = Blueprint("main", __name__)


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


@bp.route("/admin/users", methods=["GET", "POST"])
@login_required("admin")
def users():
    if request.method == "POST":
        u = User(username=request.form["username"].strip(),
                 full_name=request.form["full_name"].strip(),
                 role=request.form["role"],
                 sacco_id=request.form.get("sacco_id") or None)
        u.set_password(request.form["password"])
        db.session.add(u)
        db.session.commit()
        flash(f"User {u.username} created.", "ok")
        return redirect(url_for("main.users"))
    return render_template("users.html", users=User.query.all(),
                           roles=ROLES, saccos=Sacco.query.order_by(Sacco.name).all())


@bp.route("/admin/audit")
@login_required("admin")
def audit():
    return render_template("audit.html", logs=AuditLog.query.order_by(AuditLog.at.desc()).limit(200).all())
