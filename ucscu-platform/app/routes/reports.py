import csv, io
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from .. import login_required, current_user
from ..models import db, Sacco, FinancialReport, log_action

bp = Blueprint("reports", __name__, url_prefix="/reports")
FIELDS = ("savings", "loans_outstanding", "delinquent_loans", "total_assets",
          "reserves", "allowance", "cash", "net_income", "members")


def latest_reports():
    """Latest report per SACCO."""
    out = []
    for s in Sacco.query.order_by(Sacco.name).all():
        reps = sorted(s.reports, key=lambda r: r.period, reverse=True)
        if reps:
            out.append((s, reps[0], reps[1] if len(reps) > 1 else None))
    return out


@bp.route("/")
@login_required()
def index():
    rows = []
    for s, rep, prev in latest_reports():
        rows.append({"sacco": s, "report": rep, "pearls": rep.pearls(prev), "flags": rep.flags(prev)})
    agg = {
        "savings": sum(r["report"].savings for r in rows),
        "loans": sum(r["report"].loans_outstanding for r in rows),
        "assets": sum(r["report"].total_assets for r in rows),
        "members": sum(r["report"].members for r in rows),
        "at_risk": sum(1 for r in rows if any(f[1] == "danger" for f in r["flags"])),
    }
    return render_template("reports/index.html", rows=rows, agg=agg)


@bp.route("/submit", methods=["GET", "POST"])
@login_required("staff", "sacco")
def submit():
    me = current_user()
    if request.method == "POST":
        f = request.form
        sacco_id = int(f["sacco_id"])
        if me.role == "sacco" and me.sacco_id != sacco_id:
            flash("You can only submit for your own SACCO.", "error")
            return redirect(url_for("reports.submit"))
        data = {k: int(f.get(k) or 0) for k in FIELDS}
        rep = FinancialReport.query.filter_by(sacco_id=sacco_id, period=f["period"]).first()
        if rep:
            for k, v in data.items():
                setattr(rep, k, v)
            flash(f"Report for {f['period']} updated.", "ok")
        else:
            rep = FinancialReport(sacco_id=sacco_id, period=f["period"], **data)
            db.session.add(rep)
            db.session.flush()
            flash(f"Report for {f['period']} submitted.", "ok")
        log_action(me.username, f"Financial report {f['period']} for {rep.sacco.name}")
        db.session.commit()
        return redirect(url_for("reports.index"))
    saccos = Sacco.query.order_by(Sacco.name).all()
    if me.role == "sacco":
        saccos = [s for s in saccos if s.id == me.sacco_id]
    return render_template("reports/submit.html", saccos=saccos)


@bp.route("/sacco/<int:sid>")
@login_required()
def history(sid):
    s = Sacco.query.get_or_404(sid)
    reps = sorted(s.reports, key=lambda r: r.period)
    return render_template("reports/history.html", s=s, reports=reps)


@bp.route("/export.csv")
@login_required("staff", "board", "regulator")
def export():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["SACCO", "Reg No", "Region", "Period"] + list(FIELDS))
    for s, rep, _ in latest_reports():
        w.writerow([s.name, s.reg_number, s.region, rep.period] + [getattr(rep, k) for k in FIELDS])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=ucscu_sector_report.csv"})
