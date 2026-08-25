from datetime import date, timedelta
from .models import (db, User, Sacco, DuesPayment, ComplianceDeadline, CffDeposit, CffLoan,
                     CffRepayment, CffInvestment, FinancialReport, Course, Lesson,
                     TrainingEvent, TrainingRegistration, InsurancePolicy, InsuranceClaim,
                     StationeryProduct, StationeryOrder, Announcement, Meeting, Resolution)

TODAY = date.today()


def seed():
    # ---- Users ----
    admin = User(username="admin", full_name="System Administrator", role="admin")
    admin.set_password("admin123")
    staff = User(username="staff", full_name="Collin Agabalinda", role="staff")
    staff.set_password("staff123")
    board = User(username="board", full_name="Col. Allan Tom Kitanda", role="board")
    board.set_password("board123")
    regulator = User(username="regulator", full_name="UMRA Observer", role="regulator")
    regulator.set_password("regulator123")
    db.session.add_all([admin, staff, board, regulator])

    # ---- SACCOs ----
    saccos_data = [
        ("Wazalendo SACCO", "Reg. 9398", "Kampala", "Central", "Col. Joseph Freddy Onata", 95000, "UMRA/80014", "Licensed", True, 5_000_000),
        ("Kyamuhunga Peoples SACCO (KYAPS)", "Reg. 4412", "Bushenyi", "Western", "Annet Kyomugisha", 12500, "UMRA/80221", "Licensed", True, 1_000_000),
        ("Kigezi Teachers SACCO", "Reg. 5107", "Kabale", "Western", "Pascal Bwambale", 4200, "UMRA/80330", "Licensed", True, 800_000),
        ("Lira Urban Teachers SACCO", "Reg. 6230", "Lira", "Northern", "Aloysious Opiyo", 3100, "UMRA/80412", "Licensed", True, 800_000),
        ("Mbale Growers SACCO", "Reg. 7155", "Mbale", "Eastern", "Harriet Kabasambu", 6800, "UMRA/80501", "Licensed", False, 800_000),
        ("Jinja Market Vendors SACCO", "Reg. 8091", "Jinja", "Eastern", "Zalwango Daphine", 2400, "UMRA/80618", "Pending", True, 500_000),
        ("Gulu United Farmers SACCO", "Reg. 9012", "Gulu", "Northern", "Denis Okello", 1900, None, "Pending", True, 500_000),
        ("Masaka Diocesan SACCO", "Reg. 3345", "Masaka", "Central", "Fr. John Ssebunya", 5600, "UMRA/80755", "Licensed", True, 1_000_000),
    ]
    saccos = []
    for name, reg, district, region, contact, members, umra, umra_status, standing, dues in saccos_data:
        s = Sacco(name=name, reg_number=reg, district=district, region=region,
                  contact_person=contact, phone="+256 7%02d 000 %03d" % (len(saccos) + 12, len(saccos) * 7 % 999),
                  email="info@%s.coop" % name.split()[0].lower().replace("(", "").replace(")", ""),
                  umra_licence=umra, umra_status=umra_status, members_count=members,
                  good_standing=standing, annual_dues=dues,
                  joined_date=date(2008 + len(saccos) % 10, 3, 15))
        db.session.add(s)
        saccos.append(s)
    db.session.flush()

    sacco_user = User(username="kyaps", full_name="Annet Kyomugisha", role="sacco", sacco_id=saccos[1].id)
    sacco_user.set_password("sacco123")
    db.session.add(sacco_user)

    # ---- Dues ----
    for i, s in enumerate(saccos):
        d = DuesPayment(sacco_id=s.id, year=TODAY.year, amount=s.annual_dues)
        if i % 3 == 0:
            d.paid = s.annual_dues
            d.paid_on = TODAY - timedelta(days=40)
            d.reference = f"MTNMOMO-{88000 + i}"
        elif i % 3 == 1:
            d.paid = s.annual_dues // 2
            d.paid_on = TODAY - timedelta(days=20)
            d.reference = f"AIRTEL-{66000 + i}"
        db.session.add(d)

    # ---- Compliance calendar ----
    deadlines = [
        ("UMRA quarterly returns (Q3)", 30, "UMRA"),
        ("External audit reports submission", 60, "Audit"),
        ("Annual General Meetings season closes", 90, "AGM"),
        ("URA tax returns filing", 45, "Tax"),
        ("UMRA licence renewals begin", 15, "UMRA"),
        ("Cooperative day celebrations planning", 120, "AGM"),
    ]
    for title, days, cat in deadlines:
        db.session.add(ComplianceDeadline(title=title, due_date=TODAY + timedelta(days=days - 25), category=cat))

    # ---- CFF ----
    deposits = [(0, 120_000_000), (1, 60_000_000), (2, 25_000_000), (3, 18_000_000),
                (4, 30_000_000), (7, 22_000_000)]
    for idx, amt in deposits:
        db.session.add(CffDeposit(sacco_id=saccos[idx].id, amount=amt,
                                  deposited_on=TODAY - timedelta(days=30 + idx * 5),
                                  reference=f"CFF-DEP-{1000 + idx}"))

    loan1 = CffLoan(sacco_id=saccos[4].id, amount=20_000_000, purpose="On-lending to coffee farmers for harvest season",
                    interest_rate=10, term_months=12, status="Disbursed",
                    applied_on=TODAY - timedelta(days=80), decided_on=TODAY - timedelta(days=70),
                    disbursed_on=TODAY - timedelta(days=65))
    loan2 = CffLoan(sacco_id=saccos[5].id, amount=8_000_000, purpose="Liquidity top-up for market vendor loans",
                    interest_rate=10, term_months=6, status="Under review",
                    applied_on=TODAY - timedelta(days=6))
    loan3 = CffLoan(sacco_id=saccos[6].id, amount=12_000_000, purpose="Agricultural input financing",
                    interest_rate=10, term_months=9, status="Applied",
                    applied_on=TODAY - timedelta(days=2))
    db.session.add_all([loan1, loan2, loan3])
    db.session.flush()
    db.session.add_all([
        CffRepayment(loan_id=loan1.id, amount=4_000_000, paid_on=TODAY - timedelta(days=35), reference="CFF-REP-501"),
        CffRepayment(loan_id=loan1.id, amount=3_000_000, paid_on=TODAY - timedelta(days=5), reference="CFF-REP-502"),
    ])
    db.session.add_all([
        CffInvestment(instrument="91-day Treasury Bill", institution="Bank of Uganda",
                      principal=50_000_000, rate=9.8, invested_on=TODAY - timedelta(days=30),
                      matures_on=TODAY + timedelta(days=61)),
        CffInvestment(instrument="Fixed Deposit", institution="Centenary Bank",
                      principal=30_000_000, rate=11.0, invested_on=TODAY - timedelta(days=100),
                      matures_on=TODAY + timedelta(days=80)),
    ])

    # ---- Financial reports (two quarters for trend) ----
    def report(s, period, savings, loans, delinq, assets, reserves, allowance, cash, income, members):
        db.session.add(FinancialReport(sacco_id=s.id, period=period, savings=savings,
                                       loans_outstanding=loans, delinquent_loans=delinq,
                                       total_assets=assets, reserves=reserves, allowance=allowance,
                                       cash=cash, net_income=income, members=members,
                                       submitted_on=TODAY - timedelta(days=30 if period.endswith("Q1") else 5)))

    report(saccos[0], "2026-Q1", 4_100e6, 3_800e6, 90e6, 5_200e6, 620e6, 95e6, 700e6, 210e6, 94000)
    report(saccos[0], "2026-Q2", 4_300e6, 4_000e6, 100e6, 5_500e6, 660e6, 105e6, 760e6, 230e6, 95000)
    report(saccos[1], "2026-Q1", 9_800e6, 11_200e6, 700e6, 14_000e6, 1_300e6, 350e6, 1_200e6, 480e6, 12300)
    report(saccos[1], "2026-Q2", 10_400e6, 11_900e6, 650e6, 15_000e6, 1_450e6, 400e6, 1_350e6, 520e6, 12500)
    report(saccos[4], "2026-Q1", 2_100e6, 2_900e6, 480e6, 3_600e6, 260e6, 150e6, 220e6, -40e6, 6700)
    report(saccos[4], "2026-Q2", 2_000e6, 3_100e6, 620e6, 3_500e6, 240e6, 180e6, 180e6, -55e6, 6800)
    report(saccos[2], "2026-Q2", 1_800e6, 1_500e6, 60e6, 2_400e6, 300e6, 70e6, 360e6, 90e6, 4200)
    report(saccos[3], "2026-Q2", 1_200e6, 1_400e6, 90e6, 1_800e6, 190e6, 95e6, 210e6, 60e6, 3100)
    report(saccos[7], "2026-Q2", 2_600e6, 2_200e6, 110e6, 3_300e6, 380e6, 115e6, 480e6, 130e6, 5600)

    # ---- Training ----
    c1 = Course(title="SACCO Governance and Board Leadership", category="Governance",
                description="Roles of the board, supervisory committee and management; fiduciary duties; "
                            "cooperative principles in practice.")
    c2 = Course(title="Financial Management and PEARLS Reporting", category="Finance",
                description="Bookkeeping, delinquency management, liquidity planning and how to compute "
                            "and interpret the PEARLS supervisory ratios.")
    c3 = Course(title="Digital Transformation for SACCOs", category="Technology",
                description="Adopting MIS tools, mobile money integration, cyber hygiene and data protection.")
    c4 = Course(title="Women's Mentorship Program", category="Leadership",
                description="Run with ACCOSCA and CDF Canada — building women leaders in the cooperative movement.")
    db.session.add_all([c1, c2, c3, c4])
    db.session.flush()
    db.session.add_all([
        Lesson(course_id=c1.id, order=1, title="The seven cooperative principles",
               content="Voluntary and open membership; democratic member control; member economic participation; "
                       "autonomy and independence; education, training and information; cooperation among cooperatives; "
                       "concern for community. In this lesson we apply each principle to daily SACCO operations."),
        Lesson(course_id=c1.id, order=2, title="Board vs management: who does what",
               content="The board sets policy and hires management; management runs day-to-day operations. "
                       "The supervisory committee provides independent oversight on behalf of members."),
        Lesson(course_id=c2.id, order=1, title="Reading the PEARLS ratios",
               content="PEARLS = Protection, Effective financial structure, Asset quality, Rates of return, "
                       "Liquidity, Signs of growth. Targets: PAR < 5%, liquidity 10-20% of assets, "
                       "reserves >= 10% of assets, positive ROA."),
        Lesson(course_id=c2.id, order=2, title="Managing delinquency",
               content="Measure portfolio at risk honestly, provision for losses, follow up early, "
                       "and never refinance to hide arrears."),
    ])
    e1 = TrainingEvent(course_id=c1.id, starts_on=TODAY + timedelta(days=21),
                       ends_on=TODAY + timedelta(days=23), capacity=40, fee=150_000)
    e2 = TrainingEvent(course_id=c2.id, venue="Maganjo Training Centre",
                       starts_on=TODAY + timedelta(days=35), ends_on=TODAY + timedelta(days=37),
                       capacity=30, fee=200_000)
    e3 = TrainingEvent(course_id=c4.id, venue="UCSCU Head Office, Maganjo",
                       starts_on=TODAY - timedelta(days=10), ends_on=TODAY - timedelta(days=4),
                       capacity=30, fee=0)
    db.session.add_all([e1, e2, e3])
    db.session.flush()
    db.session.add_all([
        TrainingRegistration(event_id=e1.id, sacco_id=saccos[1].id, participant="Annet Kyomugisha"),
        TrainingRegistration(event_id=e1.id, sacco_id=saccos[3].id, participant="Aloysious Opiyo"),
        TrainingRegistration(event_id=e3.id, sacco_id=saccos[0].id, participant="Grace Namono", attended=True, certified=True),
        TrainingRegistration(event_id=e3.id, sacco_id=saccos[5].id, participant="Zalwango Daphine", attended=True, certified=True),
    ])

    # ---- Insurance ----
    p1 = InsurancePolicy(sacco_id=saccos[1].id, policy_type="Loan Protection", policy_no="CIC-UG-2201",
                         premium=8_400_000, starts_on=date(TODAY.year, 1, 1), ends_on=date(TODAY.year, 12, 31))
    p2 = InsurancePolicy(sacco_id=saccos[0].id, policy_type="Life Savings Cover", policy_no="CIC-UG-2202",
                         premium=21_000_000, starts_on=date(TODAY.year, 1, 1), ends_on=date(TODAY.year, 12, 31))
    db.session.add_all([p1, p2])
    db.session.flush()
    db.session.add(InsuranceClaim(policy_id=p1.id, description="Deceased borrower loan write-off — KYAPS member",
                                  amount=2_300_000, filed_on=TODAY - timedelta(days=12)))

    # ---- Stationery ----
    prods = [
        ("Member Passbook", "piece", 3_500, 5000),
        ("General Ledger Book", "piece", 45_000, 300),
        ("Cash Receipt Book (100 leaf)", "piece", 12_000, 1200),
        ("Loan Register", "piece", 38_000, 250),
        ("Share Certificate Book", "piece", 25_000, 400),
        ("Minute Book", "piece", 30_000, 180),
    ]
    for name, unit, price, stock in prods:
        db.session.add(StationeryProduct(name=name, unit=unit, price=price, stock=stock))
    db.session.flush()
    db.session.add_all([
        StationeryOrder(sacco_id=saccos[5].id, product_id=1, quantity=200, status="Delivered"),
        StationeryOrder(sacco_id=saccos[6].id, product_id=3, quantity=50, status="Pending"),
    ])

    # ---- Announcements ----
    db.session.add_all([
        Announcement(title="UMRA licensing deadline reminder",
                     body="All unlicensed SACCOs must regularise their status with UMRA before the end of this "
                          "financial year. UCSCU district focal persons are available to support your application.",
                     audience="All", author="UCSCU Secretariat"),
        Announcement(title="Western Region zonal meeting",
                     body="The Western Region zonal meeting will take place in Mbarara. Agenda: CFF uptake, "
                          "PEARLS reporting quality and digitalisation support.", audience="Western"),
        Announcement(title="New CIC Africa loan protection rates",
                     body="CIC Africa (U) Ltd has revised group loan protection premiums downward for SACCOs "
                          "in good standing. Contact the UCSCU risk desk for a quotation.", audience="All"),
    ])

    # ---- Governance ----
    m = Meeting(title="Q3 Board Meeting", body_type="Board", meets_on=TODAY + timedelta(days=14),
                agenda="1. CFF loan pipeline\n2. Q2 PEARLS sector report\n3. AGM preparations\n4. Budget review")
    m2 = Meeting(title="2026 Annual General Meeting", body_type="AGM",
                 meets_on=TODAY + timedelta(days=60), venue="Hotel Africana, Kampala",
                 agenda="1. Annual report\n2. Audited accounts\n3. Elections\n4. Delegates' resolutions")
    db.session.add_all([m, m2])
    db.session.flush()
    db.session.add_all([
        Resolution(meeting_id=m.id, text="Approve disbursement of pending CFF loans up to UGX 40 million this quarter",
                   votes_for=5, votes_against=1, votes_abstain=1, status="Adopted"),
        Resolution(meeting_id=m.id, text="Adopt the digital platform for quarterly PEARLS reporting by all member SACCOs"),
    ])

    db.session.commit()

    _seed_phase2()
    print("Seeded UCSCU demo data.")


def _seed_phase2():
    """Workplace hub demo data — runs only if spaces don't exist yet."""
    from .models import Space, Post, Visitor, Document
    if Space.query.count() == 0:
        s1 = Space(name="general", scope="all", description="Open to everyone — movement news and chat")
        s2 = Space(name="ucscu-staff", scope="staff_only", description="UCSCU staff and board only")
        s3 = Space(name="board-room", scope="board_only", description="Board & admin only")
        s4 = Space(name="sacco-leaders", scope="sacco_leaders", description="SACCO leaders + staff + board")
        db.session.add_all([s1, s2, s3, s4])
        db.session.flush()
        db.session.add_all([
            Post(space_id=s1.id, author_id=1, body="Welcome to the UCSCU Hub! Use spaces to coordinate across the movement."),
            Post(space_id=s1.id, author_id=2, body="Reminder: Q3 PEARLS reports are due by the 15th. Submit under Reports."),
        ])
    if Visitor.query.count() == 0:
        db.session.add(Visitor(name="Samuel Okot", organization="KYAPS SACCO", phone="+256 701 112233",
                               tag_no="T-001", host_user_id=2, purpose="Dues payment & Q3 report submission",
                               expected=True, items="Laptop bag"))
    db.session.commit()
