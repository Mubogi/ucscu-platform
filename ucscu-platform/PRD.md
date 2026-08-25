# UCSCU Digital Platform — Product Requirements Document

**Product:** UCSCU Apex Platform (working title: *UCSCU Connect*)
**Client:** Uganda Cooperative Savings and Credit Union Limited (UCSCU), Plot 239 Maganjo, Bombo Road, Kampala
**Version:** 1.0 (MVP prototype)
**Date:** August 2026

---

## 1. Background and problem statement

UCSCU is Uganda's national apex body for Savings and Credit Cooperative Societies (SACCOs),
registered in 1972 (Reg. No. 2725) under the Cooperative Societies Act Cap. 112. It is owned
by ~1,370 member SACCOs and provides them with:

- a Central Finance Facility (pooled liquidity, inter-lending, investment)
- training and capacity building
- risk management via CIC Africa (U) Ltd (joint venture with CIC Kenya, inc. 2014)
- branded SACCO accounting stationery
- advocacy and representation before UMRA, Bank of Uganda and government

Today these services run on paper, spreadsheets, phone calls and physical stationery. Data
flows from SACCOs to the apex slowly and unreliably; UCSCU cannot see sector health in real
time; liquidity management is manual; and training reach is limited by geography.

## 2. Goals

1. Give UCSCU a single digital registry of all member SACCOs and their compliance status.
2. Digitise the Central Finance Facility: contributions, inter-lending, investments, liquidity.
3. Collect standardised periodic financial reports from SACCOs and compute PEARLS
   supervisory ratios automatically, with early-warning flags.
4. Deliver and track training (in-person and e-learning) at national scale.
5. Sell stationery and manage insurance records online.
6. Improve communication (announcements, circulars) and governance (meetings, resolutions,
   AGM delegate management).
7. Produce exportable reports for UMRA, Bank of Uganda, UCA and development partners.

## 3. Users and roles

| Role | Who | Key permissions |
|---|---|---|
| Admin | UCSCU system administrator | Everything, user management |
| Staff | UCSCU secretariat staff | Manage all operational modules |
| SACCO user | Staff of a member SACCO | Own profile, submit reports, apply for CFF loans, register for trainings, order stationery, view announcements |
| Board | UCSCU board / supervisory committee | Approvals (CFF loans), resolutions, meetings, read-most access |
| Regulator | UMRA / BoU / Ministry observer | Read-only dashboards and exports |

## 4. Functional requirements by module

### 4.1 Member SACCO registry
- SACCO profile: name, reg. number, district, region, contact persons, membership size,
  savings/loans totals, UMRA licence number and status, join date, good-standing flag.
- Dues/levy invoicing and payment tracking (annual subscription).
- Compliance calendar: deadlines for UMRA returns, audits, AGMs; automatic status
  (upcoming / due / overdue).
- Document vault metadata (constitution, licence, AGM minutes, audit reports).

### 4.2 Central Finance Facility (CFF)
- Pool dashboard: total pool, total deposits, total loans outstanding, liquid balance.
- SACCO deposits into the pool (recorded with mobile-money / bank reference).
- Inter-lending: SACCO loan application → staff review → board approval → disbursement →
  repayment schedule → repayment recording. Interest computed on flat rate.
- Investments of pool funds: instrument, institution, principal, rate, maturity, status.
- Liquidity alerts when pool liquid balance falls below a threshold.

### 4.3 Reporting and PEARLS supervision
- SACCOs submit periodic (quarterly) standardised reports: savings, loans outstanding,
  total assets, reserves, allowances, delinquent loans, cash, income, expenses, members.
- System computes the WOCCU PEARLS ratios:
  - **P**rotection: allowance for loan losses / delinquency coverage
  - **E**ffective financial structure: savings/assets, reserves/assets
  - **A**sset quality: portfolio at risk (delinquent/total loans)
  - **R**ates of return: ROA
  - **L**iquidity: cash/assets
  - **S**igns of growth: asset growth vs previous period
- Early-warning flags vs target thresholds; sector-wide aggregates for advocacy.

### 4.4 Training and capacity building
- Course catalogue; training events with dates, venue/online, capacity, fee.
- Registration by SACCOs; attendance and certificate tracking.
- E-learning lesson content per course.

### 4.5 Insurance (CIC Africa)
- Insurance policies held by SACCOs through CIC: type, premium, cover period, status.
- Claims register with workflow (submitted → assessed → settled/declined).

### 4.6 Stationery e-commerce
- Product catalogue (passbooks, ledger sheets, receipt books, loan registers...).
- Order placement by SACCOs; order workflow (pending → confirmed → delivered);
  invoicing totals in UGX; stock levels.

### 4.7 Communication and advocacy
- Announcements/circulars targeted to all SACCOs or by region.
- Event notices. (SMS gateway integration point — MTN/Airtel — documented for production.)

### 4.8 Governance
- Board and committee meetings: agenda, venue, attendees, minutes.
- Resolutions with e-voting (for/against/abstain) and adoption status.
- AGM delegate register.

## 5. Non-functional requirements

- Mobile-first responsive UI; usable on low bandwidth.
- Role-based access control on every route; full audit trail on financial actions.
- All monetary values in UGX; exportable data (CSV) for regulators.
- SQLite for the prototype; PostgreSQL in production. SMS via Africa's Talking / Twilio
  in production; mobile money via MTN MoMo / Airtel Money APIs.

## 6. Phasing

| Phase | Scope |
|---|---|
| 1 (this prototype) | All 8 modules as a working web app with seed data and role-based auth |
| 2 | Mobile money + SMS integrations, document file storage (S3), UMRA e-returns export |
| 3 | SACCO core-banking integration, BI dashboards, offline field data collection app |

## 7. Success metrics

- % of member SACCOs submitting quarterly reports on time (target ≥ 80%)
- CFF loan turnaround time (target ≤ 14 days application → disbursement)
- Training participants per year (target 5,000+)
- Dues collection rate (target ≥ 90%)
