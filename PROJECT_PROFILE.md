# Project Profile — UCSCU Connect

> SACCO Apex Platform & Workplace Hub for Uganda Cooperative Savings and Credit Union Limited.

## 1. Business Overview
- **Owner / Brand:** Jordan Design Hub (JD Hub) — Mubogi Gastavas Jordan Tech Ecosystem
- **Contact:** jordandesignhub@gmail.com · WhatsApp +256 754 687 597
- **Category:** FinTech / SACCO infrastructure + internal ops
- **Status:** prototype
- **Links:** <https://github.com/Mubogi/ucscu-platform> (default branch: ucscu-platform-prototype)

## 2. Problem & Target Market
- **Problem:** UCSCU (national apex for SACCOs) runs apex operations and workplace processes across spreadsheets and paper.
- **Target users:** UCSCU secretariat, member SACCOs, board, regulators (UMRA/BoU).
- **Market context:** Uganda sector context: UMRA licences, PEARLS ratios, CFF inter-lending; LAN-gated attendance for office staff.

## 3. Value Proposition & Features
- Phase 1: Dashboard (sector KPIs, CFF liquidity), SACCO Registry + dues, Central Finance Facility inter-lending workflow
- PEARLS quarterly reports with WOCCU ratios + CSV export for regulators
- Training catalogue, events, registration, certification
- Insurance (CIC Africa) policy/claims; Stationery shop; Announcements (SMS fan-out point); Governance (meetings, e-voting); full Admin & audit log
- Phase 2: LAN-gated Attendance, Visitors register, hierarchy-scoped discussion Hub, anonymous Whistle (whistleblowing), Doc Space, shared Calendar
- Roles: admin, staff, board, sacco, regulator (read-only)

## 4. Business / Monetization Model
- **Pricing:** services-based (B2B institutional)
- **Revenue streams:** Platform licensing/services for UCSCU; prototype stage
- **Payment methods:** Planned: MTN MoMo/Airtel Money collection for dues & CFF repayments

## 5. Tech Stack
| Layer | Tech |
|-------|------|
| Backend | Python 3.13, Flask 3 |
| Frontend | Jinja templates, Tailwind CSS (CDN) |
| Database | SQLAlchemy on SQLite (PostgreSQL-ready) |
| Mobile/Desktop | Web (LAN access for attendance) |
| Deploy | run.py; Postgres via DATABASE_URL for production |

## 6. Roadmap & Status
- **Current milestone:** Feature-complete prototype with demo SACCOs seeded
- **Next steps:** Client demo & pilot; production hardening per notes (SMS gateway, S3 storage, UMRA e-returns export)
- **Known gaps:** Prototype branch only; real payment/SMS integrations pending

## 7. Metrics (optional)
- Users: n/a
- Last updated: 2026-08-26

---
*Template version: 1.0 — kept identical across all JD Hub projects. Update only the content, not the structure.*
