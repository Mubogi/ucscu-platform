from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, Sacco, CffDeposit, CffLoan, CffRepayment, CffInvestment, log_action

bp = Blueprint("cff", __name__, url_prefix="/cff")

LOW_LIQUIDITY_THRESHOLD = 50_000_000  # UGX


def pool_state():
    deposits = sum(d.amount for d in CffDeposit.query.all())
    disbursed = CffLoan.query.filter_by(status="Disbursed").all()
    loans_out = sum(l.outstanding for l in disbursed)
    invested = sum(i.principal for i in CffInvestment.query.filter_by(status="Active").all())
    return {"deposits": deposits, "loans_out": loans_out, "invested": invested,
            "liquid": deposits - loans_out - invested}


@bp.route("/")
@login_required()
def index():
    state = pool_state()
    loans = CffLoan.query.order_by(CffLoan.applied_on.desc()).all()
    deposits = CffDeposit.query.order_by(CffDeposit.deposited_on.desc()).limit(20).all()
    investments = CffInvestment.query.order_by(CffInvestment.invested_on.desc()).all()
    me = current_user()
    my_loans = [l for l in loans if me.role != "sacco" or l.sacco_id == me.sacco_id]
    return render_template("cff/index.html", state=state, loans=my_loans,
                           deposits=deposits, investments=investments,
                           threshold=LOW_LIQUIDITY_THRESHOLD,
                           saccos=Sacco.query.order_by(Sacco.name).all())


@bp.route("/deposit", methods=["POST"])
@login_required("staff", "sacco")
def deposit():
    sacco_id = int(request.form["sacco_id"])
    me = current_user()
    if me.role == "sacco" and me.sacco_id != sacco_id:
        flash("You can only deposit for your own SACCO.", "error")
        return redirect(url_for("cff.index"))
    d = CffDeposit(sacco_id=sacco_id, amount=int(request.form["amount"]),
                   reference=request.form.get("reference"))
    db.session.add(d)
    log_action(me.username, f"CFF deposit UGX {d.amount:,} by {d.sacco.name}")
    db.session.commit()
    flash("Deposit recorded.", "ok")
    return redirect(url_for("cff.index"))


@bp.route("/apply", methods=["POST"])
@login_required("staff", "sacco")
def apply():
    sacco_id = int(request.form["sacco_id"])
    me = current_user()
    if me.role == "sacco" and me.sacco_id != sacco_id:
        flash("You can only apply for your own SACCO.", "error")
        return redirect(url_for("cff.index"))
    l = CffLoan(sacco_id=sacco_id, amount=int(request.form["amount"]),
                purpose=request.form.get("purpose"),
                interest_rate=float(request.form.get("interest_rate") or 10),
                term_months=int(request.form.get("term_months") or 12))
    db.session.add(l)
    log_action(me.username, f"CFF loan application UGX {l.amount:,} by {l.sacco.name}")
    db.session.commit()
    flash("Loan application submitted for review.", "ok")
    return redirect(url_for("cff.index"))


@bp.route("/loan/<int:lid>/<action>", methods=["POST"])
@login_required("staff", "board")
def loan_action(lid, action):
    l = CffLoan.query.get_or_404(lid)
    me = current_user()
    transitions = {
        "review": ("Applied", "Under review", "staff"),
        "approve": ("Under review", "Approved", "board"),
        "reject": (("Applied", "Under review"), "Rejected", ("staff", "board")),
        "disburse": ("Approved", "Disbursed", "staff"),
    }
    if action not in transitions:
        flash("Unknown action.", "error")
        return redirect(url_for("cff.index"))
    required_from, new_status, who = transitions[action]
    if me.role not in (who if isinstance(who, tuple) else (who,)) and me.role != "admin":
        flash(f"Only {who} can {action} a loan.", "error")
        return redirect(url_for("cff.index"))
    allowed_from = required_from if isinstance(required_from, tuple) else (required_from,)
    if l.status not in allowed_from:
        flash(f"Cannot {action} a loan in status '{l.status}'.", "error")
        return redirect(url_for("cff.index"))
    l.status = new_status
    if action in ("approve", "reject"):
        l.decided_on = date.today()
    if action == "disburse":
        l.disbursed_on = date.today()
    log_action(me.username, f"CFF loan #{l.id} ({l.sacco.name}) {action}d")
    db.session.commit()
    flash(f"Loan {action}d.", "ok")
    return redirect(url_for("cff.index"))


@bp.route("/loan/<int:lid>/repay", methods=["POST"])
@login_required("staff", "sacco")
def repay(lid):
    l = CffLoan.query.get_or_404(lid)
    amount = int(request.form["amount"])
    db.session.add(CffRepayment(loan_id=lid, amount=amount,
                                reference=request.form.get("reference")))
    if l.total_repaid + amount >= l.total_due:
        l.status = "Repaid"
    log_action(current_user().username, f"CFF repayment UGX {amount:,} on loan #{lid}")
    db.session.commit()
    flash("Repayment recorded.", "ok")
    return redirect(url_for("cff.index"))


@bp.route("/invest", methods=["POST"])
@login_required("staff")
def invest():
    f = request.form
    i = CffInvestment(instrument=f["instrument"], institution=f.get("institution"),
                      principal=int(f["principal"]), rate=float(f.get("rate") or 0),
                      matures_on=datetime.strptime(f["matures_on"], "%Y-%m-%d").date() if f.get("matures_on") else None)
    db.session.add(i)
    log_action(current_user().username, f"CFF invested UGX {i.principal:,} in {i.instrument}")
    db.session.commit()
    flash("Investment recorded.", "ok")
    return redirect(url_for("cff.index"))


@bp.route("/invest/<int:iid>/mature", methods=["POST"])
@login_required("staff")
def mature(iid):
    i = CffInvestment.query.get_or_404(iid)
    i.status = "Matured"
    db.session.commit()
    flash("Investment marked as matured.", "ok")
    return redirect(url_for("cff.index"))
