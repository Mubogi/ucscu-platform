from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

ROLES = ("admin", "staff", "sacco", "board", "regulator")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sacco = db.relationship("Sacco", backref="users")

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Sacco(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    reg_number = db.Column(db.String(40), unique=True, nullable=False)
    district = db.Column(db.String(80), nullable=False)
    region = db.Column(db.String(40), nullable=False)  # Central/Eastern/Northern/Western
    contact_person = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    umra_licence = db.Column(db.String(60))
    umra_status = db.Column(db.String(20), default="Licensed")  # Licensed/Pending/Unlicensed
    members_count = db.Column(db.Integer, default=0)
    joined_date = db.Column(db.Date, default=date.today)
    good_standing = db.Column(db.Boolean, default=True)
    annual_dues = db.Column(db.BigInteger, default=500000)  # UGX

    dues = db.relationship("DuesPayment", backref="sacco", cascade="all, delete-orphan")
    reports = db.relationship("FinancialReport", backref="sacco", cascade="all, delete-orphan")
    cff_deposits = db.relationship("CffDeposit", backref="sacco", cascade="all, delete-orphan")
    cff_loans = db.relationship("CffLoan", backref="sacco", cascade="all, delete-orphan")
    policies = db.relationship("InsurancePolicy", backref="sacco", cascade="all, delete-orphan")
    orders = db.relationship("StationeryOrder", backref="sacco", cascade="all, delete-orphan")


class DuesPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.BigInteger, nullable=False)
    paid = db.Column(db.BigInteger, default=0)
    paid_on = db.Column(db.Date)
    reference = db.Column(db.String(80))  # MoMo / bank reference

    @property
    def status(self):
        if self.paid >= self.amount:
            return "Paid"
        if self.paid > 0:
            return "Partial"
        return "Unpaid"


class ComplianceDeadline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(60), default="UMRA")  # UMRA/Audit/AGM/Tax

    @property
    def status(self):
        today = date.today()
        if self.due_date < today:
            return "Overdue"
        if (self.due_date - today).days <= 30:
            return "Due soon"
        return "Upcoming"


class CffDeposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    amount = db.Column(db.BigInteger, nullable=False)
    deposited_on = db.Column(db.Date, default=date.today)
    reference = db.Column(db.String(80))


class CffLoan(db.Model):
    STATUSES = ("Applied", "Under review", "Approved", "Disbursed", "Repaid", "Rejected")
    id = db.Column(db.Integer, primary_key=True)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    amount = db.Column(db.BigInteger, nullable=False)
    purpose = db.Column(db.String(255))
    interest_rate = db.Column(db.Float, default=10.0)  # % flat per annum
    term_months = db.Column(db.Integer, default=12)
    status = db.Column(db.String(20), default="Applied")
    applied_on = db.Column(db.Date, default=date.today)
    decided_on = db.Column(db.Date)
    disbursed_on = db.Column(db.Date)
    repayments = db.relationship("CffRepayment", backref="loan", cascade="all, delete-orphan")

    @property
    def total_due(self):
        return int(self.amount * (1 + self.interest_rate / 100 * self.term_months / 12))

    @property
    def total_repaid(self):
        return sum(r.amount for r in self.repayments)

    @property
    def outstanding(self):
        return max(self.total_due - self.total_repaid, 0)


class CffRepayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("cff_loan.id"), nullable=False)
    amount = db.Column(db.BigInteger, nullable=False)
    paid_on = db.Column(db.Date, default=date.today)
    reference = db.Column(db.String(80))


class CffInvestment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument = db.Column(db.String(120), nullable=False)  # e.g. Treasury Bill 91-day
    institution = db.Column(db.String(120))
    principal = db.Column(db.BigInteger, nullable=False)
    rate = db.Column(db.Float, default=0)
    invested_on = db.Column(db.Date, default=date.today)
    matures_on = db.Column(db.Date)
    status = db.Column(db.String(20), default="Active")  # Active/Matured


class FinancialReport(db.Model):
    """Quarterly standardised report submitted by a SACCO (all UGX)."""
    id = db.Column(db.Integer, primary_key=True)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    period = db.Column(db.String(10), nullable=False)  # e.g. 2026-Q2
    submitted_on = db.Column(db.Date, default=date.today)
    savings = db.Column(db.BigInteger, default=0)
    loans_outstanding = db.Column(db.BigInteger, default=0)
    delinquent_loans = db.Column(db.BigInteger, default=0)
    total_assets = db.Column(db.BigInteger, default=0)
    reserves = db.Column(db.BigInteger, default=0)
    allowance = db.Column(db.BigInteger, default=0)  # allowance for loan losses
    cash = db.Column(db.BigInteger, default=0)
    net_income = db.Column(db.BigInteger, default=0)
    members = db.Column(db.Integer, default=0)

    def pearls(self, prev=None):
        a = self.total_assets or 1
        lo = self.loans_outstanding or 1
        ratios = {
            "P_delinquency_coverage": round(100 * self.allowance / (self.delinquent_loans or 1), 1),
            "E_savings_to_assets": round(100 * self.savings / a, 1),
            "E_reserves_to_assets": round(100 * self.reserves / a, 1),
            "A_portfolio_at_risk": round(100 * self.delinquent_loans / lo, 1),
            "R_roa": round(100 * self.net_income / a, 1),
            "L_liquidity": round(100 * self.cash / a, 1),
            "S_asset_growth": round(100 * (self.total_assets - prev.total_assets) / (prev.total_assets or 1), 1) if prev else None,
        }
        return ratios

    def flags(self, prev=None):
        """Early-warning flags against PEARLS-style targets."""
        r = self.pearls(prev)
        out = []
        if r["A_portfolio_at_risk"] > 5:
            out.append(("Portfolio at risk above 5%", "danger"))
        if r["L_liquidity"] < 10:
            out.append(("Liquidity below 10% of assets", "danger"))
        if r["E_reserves_to_assets"] < 10:
            out.append(("Reserves below 10% of assets", "warn"))
        if r["R_roa"] < 0:
            out.append(("Negative return on assets", "danger"))
        if r["S_asset_growth"] is not None and r["S_asset_growth"] < 0:
            out.append(("Assets shrinking", "warn"))
        if not out:
            out.append(("Sound", "ok"))
        return out


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), default="Governance")
    description = db.Column(db.Text)
    lessons = db.relationship("Lesson", backref="course", cascade="all, delete-orphan")
    events = db.relationship("TrainingEvent", backref="course", cascade="all, delete-orphan")


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.Text)
    order = db.Column(db.Integer, default=1)


class TrainingEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    venue = db.Column(db.String(160), default="UCSCU Head Office, Maganjo")
    starts_on = db.Column(db.Date, nullable=False)
    ends_on = db.Column(db.Date)
    capacity = db.Column(db.Integer, default=40)
    fee = db.Column(db.BigInteger, default=0)
    registrations = db.relationship("TrainingRegistration", backref="event", cascade="all, delete-orphan")

    @property
    def seats_taken(self):
        return len(self.registrations)


class TrainingRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("training_event.id"), nullable=False)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    participant = db.Column(db.String(120), nullable=False)
    attended = db.Column(db.Boolean, default=False)
    certified = db.Column(db.Boolean, default=False)
    sacco = db.relationship("Sacco")


class InsurancePolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    policy_type = db.Column(db.String(80), default="Loan Protection")  # via CIC Africa (U) Ltd
    policy_no = db.Column(db.String(60))
    premium = db.Column(db.BigInteger, default=0)
    starts_on = db.Column(db.Date)
    ends_on = db.Column(db.Date)
    status = db.Column(db.String(20), default="Active")
    claims = db.relationship("InsuranceClaim", backref="policy", cascade="all, delete-orphan")


class InsuranceClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey("insurance_policy.id"), nullable=False)
    description = db.Column(db.String(255))
    amount = db.Column(db.BigInteger, default=0)
    filed_on = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="Submitted")  # Submitted/Assessed/Settled/Declined


class StationeryProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(40), default="piece")
    price = db.Column(db.BigInteger, nullable=False)  # UGX
    stock = db.Column(db.Integer, default=0)


class StationeryOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("stationery_product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    ordered_on = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default="Pending")  # Pending/Confirmed/Delivered/Cancelled
    product = db.relationship("StationeryProduct")

    @property
    def total(self):
        return self.quantity * (self.product.price if self.product else 0)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    audience = db.Column(db.String(40), default="All")  # All / region name
    posted_on = db.Column(db.Date, default=date.today)
    author = db.Column(db.String(120), default="UCSCU Secretariat")


class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body_type = db.Column(db.String(60), default="Board")  # Board/Supervisory/AGM/Committee
    meets_on = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(160), default="UCSCU Head Office, Maganjo")
    agenda = db.Column(db.Text)
    minutes = db.Column(db.Text)
    resolutions = db.relationship("Resolution", backref="meeting", cascade="all, delete-orphan")


class Resolution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meeting.id"), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    votes_for = db.Column(db.Integer, default=0)
    votes_against = db.Column(db.Integer, default=0)
    votes_abstain = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="Open")  # Open/Adopted/Rejected


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(80))
    action = db.Column(db.String(255))
    at = db.Column(db.DateTime, default=datetime.utcnow)


def log_action(actor, action):
    db.session.add(AuditLog(actor=actor, action=action))


class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(40), nullable=False)  # Leave / Absence / Late arrival notification
    starts_on = db.Column(db.Date, nullable=False)
    ends_on = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending/Approved/Declined
    decided_by = db.Column(db.String(80))
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="leave_requests")


class CheckInEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # check_in / check_out
    mode = db.Column(db.String(20), nullable=False)  # lan / exemption
    ip = db.Column(db.String(40))
    lateness_reason = db.Column(db.String(255))
    at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", backref="checkins")


class AttendanceMeeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    on_date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(160))


class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("attendance_meeting.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    present = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(255))
    user = db.relationship("User")
    meeting = db.relationship("AttendanceMeeting", backref="records")


class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    organization = db.Column(db.String(160))
    phone = db.Column(db.String(40))
    tag_no = db.Column(db.String(20), nullable=False)
    host_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    purpose = db.Column(db.String(255))
    expected = db.Column(db.Boolean, default=False)
    arrived_at = db.Column(db.DateTime, default=datetime.utcnow)
    departed_at = db.Column(db.DateTime)
    items = db.Column(db.String(255))
    host = db.relationship("User")

    @property
    def onsite(self):
        return self.departed_at is None


class Space(db.Model):
    """Discussion space — a social-media-style channel with hierarchy scoping."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    scope = db.Column(db.String(60), default="all")
    # all | staff_only | board_only | sacco_leaders
    description = db.Column(db.String(255))
    posts = db.relationship("Post", backref="space", cascade="all, delete-orphan")

    def visible_to(self, user):
        if self.scope == "all":
            return True
        if self.scope == "staff_only":
            return user.role in ("admin", "staff", "board")
        if self.scope == "board_only":
            return user.role in ("admin", "board")
        if self.scope == "sacco_leaders":
            return user.role in ("admin", "staff", "board", "sacco")
        return True


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey("space.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")
    replies = db.relationship("Reply", backref="post", cascade="all, delete-orphan")


class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")


def _fmt_time(dt):
    if not dt:
        return ""
    try:
        return dt.strftime("%H:%M")
    except AttributeError:
        return str(dt)


class Broadcast(db.Model):
    """A grouped message (SMS / WhatsApp / Call) with a per-recipient queue."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text)
    channel = db.Column(db.String(20), default="SMS")
    scope = db.Column(db.String(40), default="All")
    created_by = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    queue = db.relationship("BroadcastRecipient", backref="broadcast", cascade="all, delete-orphan")

    @property
    def total(self):
        return len(self.queue)

    @property
    def sent(self):
        return sum(1 for r in self.queue if r.status == "Sent")

    @property
    def failed(self):
        return sum(1 for r in self.queue if r.status == "Failed")

    @property
    def queued(self):
        return sum(1 for r in self.queue if r.status == "Queued")

    @property
    def coverage(self):
        return round(self.sent / self.total * 100) if self.total else 0


class BroadcastRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    broadcast_id = db.Column(db.Integer, db.ForeignKey("broadcast.id"), nullable=False)
    sacco_id = db.Column(db.Integer, db.ForeignKey("sacco.id"), nullable=False)
    phone = db.Column(db.String(40))
    status = db.Column(db.String(20), default="Queued")
    attempts = db.Column(db.Integer, default=0)
    error = db.Column(db.String(160))
    queued_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    sacco = db.relationship("Sacco")


class DirectThread(db.Model):
    """A 1-to-1 conversation between two staff users."""
    id = db.Column(db.Integer, primary_key=True)
    a_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    b_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    a = db.relationship("User", foreign_keys=[a_id])
    b = db.relationship("User", foreign_keys=[b_id])
    messages = db.relationship("DirectMessage", backref="thread", cascade="all, delete-orphan")

    def other(self, user):
        return self.b if user.id == self.a_id else self.a

    @property
    def last(self):
        return self.messages[-1] if self.messages else None


class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("direct_thread.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text)
    attachment_id = db.Column(db.Integer, db.ForeignKey("attachment.id"))
    at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")
    attachment = db.relationship("Attachment", foreign_keys=[attachment_id])

    @property
    def time_label(self):
        return _fmt_time(self.at)


class Attachment(db.Model):
    """Uploaded file (photo, document). Stored on disk under instance/uploads."""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)   # stored name on disk
    original_name = db.Column(db.String(255))
    content_type = db.Column(db.String(120))
    size = db.Column(db.Integer, default=0)
    kind = db.Column(db.String(20), default="file")        # image / file
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def url(self):
        return "/uploads/" + self.filename


class FeedPost(db.Model):
    """A post on the home feed — like a company Facebook page."""
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text)
    attachment_id = db.Column(db.Integer, db.ForeignKey("attachment.id"))
    scope = db.Column(db.String(60), default="all")        # all | staff_only | board_only
    at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")
    attachment = db.relationship("Attachment", foreign_keys=[attachment_id])
    comments = db.relationship("FeedComment", backref="post", cascade="all, delete-orphan")
    likes = db.relationship("FeedLike", backref="post", cascade="all, delete-orphan")

    def visible_to(self, user):
        if self.scope == "all":
            return True
        if self.scope == "staff_only":
            return user.role in ("admin", "staff", "board")
        if self.scope == "board_only":
            return user.role in ("admin", "board")
        return True

    def liked_by(self, user):
        return any(l.user_id == user.id for l in self.likes)

    @property
    def time_label(self):
        return _fmt_time(self.at)


class FeedComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("feed_post.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship("User")

    @property
    def time_label(self):
        return _fmt_time(self.at)


class FeedLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("feed_post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.String(40), default="info")        # message/post/comment/like/call/announcement
    text = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    read = db.Column(db.Boolean, default=False)
    at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def time_label(self):
        return _fmt_time(self.at)


class CallSession(db.Model):
    """LAN audio/video call signalling record. Peers exchange WebRTC offers
    through this table, so calls work with no internet access."""
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(60), unique=True, nullable=False)
    kind = db.Column(db.String(10), default="video")       # audio / video
    caller_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    callee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="ringing")   # ringing/accepted/declined/ended
    offer = db.Column(db.Text)
    answer = db.Column(db.Text)
    caller_ice = db.Column(db.Text)   # JSON array
    callee_ice = db.Column(db.Text)   # JSON array
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    caller = db.relationship("User", foreign_keys=[caller_id])
    callee = db.relationship("User", foreign_keys=[callee_id])


class ConfidentialReport(db.Model):
    """Anonymous whistleblowing case. Author identity is never stored."""
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(12), unique=True, nullable=False)  # for status checks
    category = db.Column(db.String(60), default="Fraud")
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Open")  # Open/Investigating/Resolved/Closed
    filed_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolution_note = db.Column(db.Text)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60), default="Minutes")  # Minutes/Policy/Speech/Template
    content = db.Column(db.Text)
    created_by = db.Column(db.String(80))
    at = db.Column(db.DateTime, default=datetime.utcnow)


MINUTE_TEMPLATES = {
    "General meeting": """1. Meeting called to order and quorum confirmed
2. (Secretary) ____________________________
3. (Chairperson) ____________________________
4. Present: _______________________________
5. Apologies: _____________________________
6. Minute taker: __________________________
7. Agenda adopted
8. Matters arising: _______________________
9. Resolutions passed: ____________________
10. Next meeting date: ____________________""",
    "Board meeting": """1. Call to order and declaration of quorum
2. Conflicts of interest declared: ________
3. Minutes of previous meeting confirmed
4. Management report received
5. Finance/CFF items decided: _____________
6. Resolutions: ___________________________
7. Date of next board meeting: ____________
8. Signed (Chair / Secretary): ____________""",
    "AGM": """1. Notice and quorum verified
2. Annual report presented and adopted
3. Audited accounts received: _____________
4. Elections of office bearers: ___________
5. Resolutions by delegates: ______________
6. Any other business: ____________________
7. Adjournment: ___________________________""",
    "Attendance register": """Name | Role | Check-in time | Signature
1. _______________________________________
2. _______________________________________
3. _______________________________________
4. _______________________________________
5. _______________________________________""",
}
