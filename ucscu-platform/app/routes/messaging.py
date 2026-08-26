from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .. import login_required, current_user
from ..models import db, Sacco, Broadcast, BroadcastRecipient, log_action

bp = Blueprint("messaging", __name__, url_prefix="/messaging")
STAFF = ("staff", "board")
CHANNELS = ("SMS", "WhatsApp", "Call")


@bp.route("/")
@login_required()
def index():
    broadcasts = Broadcast.query.order_by(Broadcast.created_at.desc()).all()
    regions = [r[0] for r in db.session.query(Sacco.region).distinct()]
    members = Sacco.query.order_by(Sacco.name).all()
    return render_template("messaging/index.html", broadcasts=broadcasts,
                           regions=regions, members=members, channels=CHANNELS)


@bp.route("/send", methods=["POST"])
@login_required("staff", "board")
def send():
    f = request.form
    scope_select = f.get("scope_select", "All")

    if scope_select == "Custom":
        ids = request.form.getlist("member_id")
        recipients = Sacco.query.order_by(Sacco.name).all()
        recipients = [m for m in recipients if str(m.id) in ids]
        scope = "Custom"
    elif scope_select == "Region":
        scope = f.get("region", "All")
        recipients = Sacco.query.filter_by(region=scope).order_by(Sacco.name).all()
    else:
        scope = "All"
        recipients = Sacco.query.order_by(Sacco.name).all()

    b = Broadcast(title=f["title"], body=f.get("body"),
                  channel=f.get("channel", "SMS"), scope=scope,
                  created_by=current_user().username)
    db.session.add(b)

    queued = 0
    for m in recipients:
        db.session.add(BroadcastRecipient(broadcast_id=None, broadcast=b,
                                          sacco_id=m.id, phone=m.phone))
        queued += 1

    log_action(current_user().username,
               f"Queued {queued} recipients for {b.channel} broadcast: {b.title} ({b.scope})")
    db.session.commit()
    flash(f"Broadcast queued for {queued} member(s). Process the queue to send.", "ok")
    return redirect(url_for("messaging.detail", bid=b.id))


@bp.route("/<int:bid>")
@login_required()
def detail(bid):
    b = Broadcast.query.get_or_404(bid)
    return render_template("messaging/detail.html", b=b)


@bp.route("/<int:bid>/process", methods=["POST"])
@login_required("staff", "board")
def process(bid):
    """Process the queue: mark queued recipients as sent via the gateway.

    Production hook: replace this loop with Africa's Talking / Twilio API
    calls (sms.send(), voice.call()) and mark failed numbers on API errors.
    """
    b = Broadcast.query.get_or_404(bid)
    sent = failed = 0
    for r in b.queue:
        if r.status != "Queued":
            continue
        r.attempts = (r.attempts or 0) + 1
        # Prefer live number on the member profile; fall back to the queued snapshot only if the record was deleted
        if r.sacco is not None:
            phone = r.sacco.phone
        else:
            phone = r.phone
        if phone:
            r.phone = phone or r.phone
            r.status = "Sent"
            r.sent_at = datetime.utcnow()
            r.error = None
            sent += 1
        else:
            r.status = "Failed"
            r.error = "No phone number on file"
            failed += 1
    log_action(current_user().username,
               f"Processed queue for broadcast #{b.id}: {sent} sent, {failed} failed")
    db.session.commit()
    flash(f"Queue processed — {sent} sent, {failed} failed. Coverage now {b.coverage}%.", "ok")
    return redirect(url_for("messaging.detail", bid=b.id))


@bp.route("/<int:bid>/retry", methods=["POST"])
@login_required("staff", "board")
def retry(bid):
    b = Broadcast.query.get_or_404(bid)
    # Requeue failed attempts (e.g. after a phone number was added to the member profile)
    for r in b.queue:
        if r.status == "Failed":
            r.status = "Queued"
            r.error = None
            r.queued_at = datetime.utcnow()
    db.session.commit()
    flash("Failed recipients requeued.", "ok")
    return redirect(url_for("messaging.detail", bid=b.id))
