from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .. import login_required, current_user
from ..models import db, Sacco, DuesPayment, ComplianceDeadline, log_action

bp = Blueprint("saccos", __name__, url_prefix="/saccos")
STAFF = ("staff", "board", "regulator")


@bp.route("/")
@login_required()
def index():
    q = Sacco.query
    region = request.args.get("region")
    standing = request.args.get("standing")
    search = request.args.get("q", "").strip()
    if region:
        q = q.filter_by(region=region)
    if standing == "good":
        q = q.filter_by(good_standing=True)
    elif standing == "bad":
        q = q.filter_by(good_standing=False)
    if search:
        q = q.filter(Sacco.name.ilike(f"%{search}%"))
    regions = [r[0] for r in db.session.query(Sacco.region).distinct()]
    return render_template("saccos/index.html", saccos=q.order_by(Sacco.name).all(), regions=regions)


@bp.route("/new", methods=["GET", "POST"])
@login_required("staff")
def new():
    if request.method == "POST":
        f = request.form
        s = Sacco(name=f["name"], reg_number=f["reg_number"], district=f["district"],
                  region=f["region"], contact_person=f.get("contact_person"),
                  phone=f.get("phone"), email=f.get("email"),
                  umra_licence=f.get("umra_licence"), umra_status=f.get("umra_status", "Pending"),
                  members_count=int(f.get("members_count") or 0),
                  annual_dues=int(f.get("annual_dues") or 500000))
        db.session.add(s)
        db.session.flush()
        db.session.add(DuesPayment(sacco_id=s.id, year=date.today().year, amount=s.annual_dues))
        log_action(current_user().username, f"Registered SACCO {s.name}")
        db.session.commit()
        flash(f"{s.name} registered and dues invoice created.", "ok")
        return redirect(url_for("saccos.detail", sid=s.id))
    return render_template("saccos/form.html", sacco=None)


@bp.route("/<int:sid>")
@login_required()
def detail(sid):
    s = Sacco.query.get_or_404(sid)
    me = current_user()
    if me.role == "sacco" and me.sacco_id != sid:
        return redirect(url_for("saccos.detail", sid=me.sacco_id))
    return render_template("saccos/detail.html", s=s)


@bp.route("/<int:sid>/edit", methods=["GET", "POST"])
@login_required("staff")
def edit(sid):
    s = Sacco.query.get_or_404(sid)
    if request.method == "POST":
        f = request.form
        for field in ("name", "reg_number", "district", "region", "contact_person",
                      "phone", "email", "umra_licence", "umra_status"):
            setattr(s, field, f.get(field, getattr(s, field)))
        s.members_count = int(f.get("members_count") or 0)
        s.annual_dues = int(f.get("annual_dues") or 0)
        s.good_standing = f.get("good_standing") == "on"
        db.session.commit()
        flash("SACCO profile updated.", "ok")
        return redirect(url_for("saccos.detail", sid=sid))
    return render_template("saccos/form.html", sacco=s)


@bp.route("/<int:sid>/dues/<int:did>/pay", methods=["POST"])
@login_required("staff", "sacco")
def pay_dues(sid, did):
    d = DuesPayment.query.get_or_404(did)
    amount = int(request.form["amount"])
    d.paid = (d.paid or 0) + amount
    d.paid_on = date.today()
    d.reference = request.form.get("reference")
    log_action(current_user().username, f"Recorded dues payment UGX {amount:,} for {d.sacco.name}")
    db.session.commit()
    flash("Dues payment recorded.", "ok")
    return redirect(url_for("saccos.detail", sid=sid))


@bp.route("/api/search")
@login_required()
def api_search():
    """Member picker for transactions — filter by name, reg number, district or phone."""
    q = request.args.get("q", "").strip()
    query = Sacco.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Sacco.name.ilike(like),
                   Sacco.reg_number.ilike(like),
                   Sacco.district.ilike(like),
                   Sacco.contact_person.ilike(like),
                   Sacco.phone.ilike(like)))
    return jsonify([
        {"id": s.id, "name": s.name, "reg_number": s.reg_number,
         "district": s.district, "region": s.region,
         "phone": s.phone, "email": s.email}
        for s in query.order_by(Sacco.name).all()])


@bp.route("/compliance")
@login_required()
def compliance():
    items = ComplianceDeadline.query.order_by(ComplianceDeadline.due_date).all()
    return render_template("saccos/compliance.html", items=items)


@bp.route("/compliance/new", methods=["POST"])
@login_required("staff")
def new_deadline():
    db.session.add(ComplianceDeadline(
        title=request.form["title"], category=request.form["category"],
        due_date=datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()))
    db.session.commit()
    flash("Compliance deadline added.", "ok")
    return redirect(url_for("saccos.compliance"))
