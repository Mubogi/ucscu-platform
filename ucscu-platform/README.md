# UCSCU Connect — National SACCO Apex Platform

A full-stack web platform for **Uganda Cooperative Savings and Credit Union Limited (UCSCU)**, the national apex body for SACCOs in Uganda. See `PRD.md` for the full product requirements.

## Phase 1 Modules — Apex operations

1. Dashboard — sector-wide KPIs, CFF liquidity, compliance alerts, audit feed
2. SACCO Registry — member SACCO profiles, UMRA licence status, dues invoicing & payments, compliance calendar
3. Central Finance Facility (CFF) — pool deposits, inter-lending (apply → review → board approve → disburse → repay), investments, liquidity alerts
4. PEARLS Reports — quarterly SACCO submissions, automatic WOCCU PEARLS ratios, early-warning flags, CSV export for regulators
5. Training — course catalogue with e-learning lessons, events, registration, attendance & certification
6. Insurance (CIC Africa) — policy register and claims workflow
7. Stationery Shop — branded accounting stationery, stock, ordering and fulfilment
8. Announcements — circulars targeted to all SACCOs or by region (SMS gateway integration point)
9. Governance — board/AGM meetings, agendas, minutes, resolutions with e-voting
10. Admin — user management, full audit log

## Phase 2 Modules — Workplace hub

1. Home feed — a company social feed: post updates, headlines and photos, like, comment; scoped to everyone / staff / board
2. Messages — private 1-to-1 chat with file and image attachments, plus unread notifications
3. Calls — LAN audio/video calls between staff using peer-to-peer WebRTC (no internet required) with mute, camera toggle and screen-ready layout
4. Notifications — live bell counter, toast popups and sound for new messages, comments, likes, calls and announcements
5. Attendance — LAN-gated check-in/out (rejects non-office IPs), field exemption channel, lateness reason capture, leave/absence workflow, meeting attendance registers
6. Visitors — reception register, numbered gate tags with printable passes, check-in/out
7. Spaces (Hub) — internal social-media-style discussion spaces scoped by hierarchy (everyone / staff-only / board-only / SACCO leaders) with threaded replies
8. Whistle — anonymous whistleblowing: no identity stored, token-based status check, case workflow for oversight
9. Doc Space — minutes & documents library with templates (General/Board/AGM/Attendance register); HR & conduct policy summary page
10. Calendar — shared view aggregating meetings, trainings, UMRA deadlines, and approved leave
11. Bulk Messaging — grouped SMS / WhatsApp / Call queue with per-recipient coverage tracking

## Roles

`admin`, `staff`, `board`, `sacco` (member SACCO user), `regulator` (read-only).

## Quick start

```bash
cd ucscu-platform
pip install -r requirements.txt
python run.py
```

Open http://localhost:12000 — the database is created and seeded with realistic demo SACCOs (Wazalendo, KYAPS, etc.) on first run.

### Demo logins

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Administrator |
| `staff` | `staff123` | UCSCU secretariat staff |
| `board` | `board123` | Board member (approves CFF loans, votes) |
| `kyaps` | `sacco123` | SACCO user (KYAPS) |
| `regulator` | `regulator123` | UMRA/BoU observer |

## Stack

Python 3.13 · Flask 3 · SQLAlchemy · SQLite (PostgreSQL-ready) · Tailwind CSS (CDN) · server-rendered Jinja templates. No build step.

## Attendance LAN gating

Check-in/out only succeeds when the request IP falls within the office network (private/LAN IP in demo mode). Set real office CIDR ranges in `OFFICE_NETS` in `app/routes/attendance.py` for production. Field staff and board members use the exemption channel, which is audit-logged.

## Production notes

- PostgreSQL via `DATABASE_URL`; managed secret for `SECRET_KEY`
- MTN MoMo / Airtel Money collection APIs for dues and CFF repayments
- Africa's Talking or Twilio for SMS fan-out of announcements
- S3-compatible object storage for SACCO documents (licences, audits, minutes)
- UMRA e-returns format export
