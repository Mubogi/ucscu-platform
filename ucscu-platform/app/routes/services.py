from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import (db, Sacco, InsurancePolicy, InsuranceClaim,
                      StationeryProduct, StationeryOrder, log_action)

bp = Blueprint("services", __name__, url_prefix="/services")


# ---------- Insurance (CIC Africa) ----------

@bp.route("/insurance")
@login_required()
def insurance():
    me = current_user()
    policies = InsurancePolicy.query.order_by(InsurancePolicy.id.desc()).all()
    if me.role == "sacco":
        policies = [p for p in policies if p.sacco_id == me.sacco_id]
    claims = InsuranceClaim.query.order_by(InsuranceClaim.filed_on.desc()).all()
    if me.role == "sacco":
        claims = [c for c in claims if c.policy.sacco_id == me.sacco_id]
    return render_template("services/insurance.html", policies=policies, claims=claims,
                           saccos=Sacco.query.order_by(Sacco.name).all())


@bp.route("/insurance/policy", methods=["POST"])
@login_required("staff")
def new_policy():
    f = request.form
    p = InsurancePolicy(sacco_id=int(f["sacco_id"]), policy_type=f["policy_type"],
                        policy_no=f.get("policy_no"), premium=int(f.get("premium") or 0),
                        starts_on=datetime.strptime(f["starts_on"], "%Y-%m-%d").date() if f.get("starts_on") else None,
                        ends_on=datetime.strptime(f["ends_on"], "%Y-%m-%d").date() if f.get("ends_on") else None)
    db.session.add(p)
    log_action(current_user().username, f"Issued {p.policy_type} policy to {p.sacco.name}")
    db.session.commit()
    flash("Policy recorded.", "ok")
    return redirect(url_for("services.insurance"))


@bp.route("/insurance/claim", methods=["POST"])
@login_required("staff", "sacco")
def new_claim():
    f = request.form
    c = InsuranceClaim(policy_id=int(f["policy_id"]), description=f.get("description"),
                       amount=int(f.get("amount") or 0))
    db.session.add(c)
    log_action(current_user().username, f"Insurance claim filed on policy #{c.policy_id}")
    db.session.commit()
    flash("Claim submitted.", "ok")
    return redirect(url_for("services.insurance"))


@bp.route("/insurance/claim/<int:cid>/<status>", methods=["POST"])
@login_required("staff")
def claim_status(cid, status):
    c = InsuranceClaim.query.get_or_404(cid)
    if status in ("Assessed", "Settled", "Declined"):
        c.status = status
        db.session.commit()
        flash(f"Claim {status.lower()}.", "ok")
    return redirect(url_for("services.insurance"))


# ---------- Stationery shop ----------

@bp.route("/shop")
@login_required()
def shop():
    me = current_user()
    orders = StationeryOrder.query.order_by(StationeryOrder.ordered_on.desc()).all()
    if me.role == "sacco":
        orders = [o for o in orders if o.sacco_id == me.sacco_id]
    return render_template("services/shop.html",
                           products=StationeryProduct.query.order_by(StationeryProduct.name).all(),
                           orders=orders, saccos=Sacco.query.order_by(Sacco.name).all())


@bp.route("/shop/product", methods=["POST"])
@login_required("staff")
def new_product():
    f = request.form
    db.session.add(StationeryProduct(name=f["name"], unit=f.get("unit", "piece"),
                                     price=int(f["price"]), stock=int(f.get("stock") or 0)))
    db.session.commit()
    flash("Product added to catalogue.", "ok")
    return redirect(url_for("services.shop"))


@bp.route("/shop/order", methods=["POST"])
@login_required("staff", "sacco")
def order():
    f = request.form
    me = current_user()
    sacco_id = int(f["sacco_id"])
    if me.role == "sacco" and me.sacco_id != sacco_id:
        flash("You can only order for your own SACCO.", "error")
        return redirect(url_for("services.shop"))
    p = StationeryProduct.query.get_or_404(int(f["product_id"]))
    qty = int(f["quantity"])
    if qty > p.stock:
        flash(f"Only {p.stock} {p.unit}(s) of {p.name} in stock.", "error")
        return redirect(url_for("services.shop"))
    o = StationeryOrder(sacco_id=sacco_id, product_id=p.id, quantity=qty)
    db.session.add(o)
    db.session.flush()
    log_action(me.username, f"Stationery order: {qty}x {p.name} for {o.sacco.name}")
    db.session.commit()
    flash(f"Order placed — total {o.total:,} UGX. Awaiting confirmation.", "ok")
    return redirect(url_for("services.shop"))


@bp.route("/shop/order/<int:oid>/<status>", methods=["POST"])
@login_required("staff")
def order_status(oid, status):
    o = StationeryOrder.query.get_or_404(oid)
    if status in ("Confirmed", "Delivered", "Cancelled"):
        if status == "Confirmed" and o.status == "Pending":
            o.product.stock = max(o.product.stock - o.quantity, 0)
        o.status = status
        db.session.commit()
        flash(f"Order {status.lower()}.", "ok")
    return redirect(url_for("services.shop"))
