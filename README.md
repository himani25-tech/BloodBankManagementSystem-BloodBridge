# 🩸 BloodBridge – Blood Bank Management System

A full-stack web application built with **HTML · CSS · JavaScript · Python Flask**

---
## 🌐 Live Demo
🔗 **[https://bloodbridge-xr8i.onrender.com](https://bloodbridge-xr8i.onrender.com)**

>  See [🔐 Demo Credentials](#-demo-credentials) below to log in and try it out.
## 📁 Project Structure

```
bbms/
├── app.py                  ← Flask backend (routes, auth, AI matching, DB logic)
├── schema.sql               ← MySQL schema + seed data (optional, for production DB)
├── requirements.txt
├── Procfile
├── templates/
│   ├── index.html           ← Landing page
│   ├── login.html           ← Login
│   ├── signup.html          ← Registration
│   ├── donor_dashboard.html
│   ├── admin_dashboard.html
│   └── hospital_dashboard.html
```

---

## ⚙️ Setup Instructions

### 1. Install Python packages
```bash
cd bbms
pip install -r requirements.txt
```

### 2. Run the App
```bash
python app.py
```
Open: **http://localhost:5000**

> The app ships with an in-memory data store (`app.py`) so it runs out of the box with
> no database setup. `schema.sql` is included if you want to wire up a real MySQL
> database for production instead.

---

## 🔐 Demo Credentials

| Role     | Email                     | Password     |
|----------|---------------------------|---------------|
| Admin    | admin@bloodbridge.in      | Admin@123     |
| Donor    | rahul@donor.com           | Donor@123     |
| Hospital | hamidia@hospital.com      | Hospital@123  |

---

## 🔗 Donor Verification & Hospital Request Pipeline

BloodBridge follows a real-world blood bank workflow instead of a flat donor list:

```
Donor → Admin Verification → Hospital View (AI Matched) → Hospital Request → Donor Accept/Reject → Donation Completed
```

1. **Donor submits "I Want to Donate"** — blood group, phone, address, city, availability
   date. Sits as `Pending Verification` under *Become a Verified Donor*.
2. **Admin verifies** the donor from *Verify Donors*. Only verified donors are exposed to
   hospitals — this blocks fake entries and spam requests.
3. **Hospital browses Verified Donors**, ranked by an **AI-Powered Donor Matching Engine**
   (`ai_match_score()` in `app.py`) that scores each donor 0–100 using:
   - Exact vs. medically-compatible blood group (standard donor/recipient compatibility chart)
   - The 90-day donation eligibility window
   - Same-city proximity to the hospital
   - Donor reliability (past donation history)
4. **Hospital requests a specific donor** → status `Waiting for Donor Response`.
5. **Donor Accepts** (sets an appointment date) or **Rejects** from *Hospital Requests*.
6. **Admin marks the donation Completed** from *Donation Pipeline* — this auto-updates
   blood inventory, the donor's stats/points, and the donation log.

### Dashboard-wise visibility

| Information            | Donor | Admin | Hospital |
|-------------------------|:---:|:---:|:---:|
| New Donation Request    | ✅ | ✅ | ❌ |
| Pending Verification    | ✅ | ✅ | ❌ |
| Verified Donors         | ✅ | ✅ | ✅ |
| Hospital Request        | ✅ | ✅ | ✅ |
| Donation Completed      | ✅ | ✅ | ✅ |

Admin sits at the center of the pipeline as the verification gate — hospitals only ever
see donors who have already been checked out, which keeps the network free of fake
entries and spam requests, much closer to how real blood banks operate.

---

## ✅ Features

### Admin
- Full dashboard with live inventory chart
- **Verify Donors** — approve or reject donor applications before they become visible to hospitals
- **Donation Pipeline** — end-to-end traceability of every hospital ⇄ donor request, with a one-click "Mark Completed"
- View & manage all blood requests (approve → auto-deducts inventory / reject)
- Update blood inventory (add or remove units + full activity log)
- View registered hospitals and donors

### Donor
- Register / Login
- Submit "I Want to Donate" for admin verification
- Log a donation directly at a camp/location
- Accept or decline incoming hospital requests, and schedule an appointment
- View blood inventory (read-only) and eligibility checker
- View own donation history and profile

### Hospital
- Register / Login
- **AI-Matched Verified Donors** — search and rank real, admin-verified donors by
  compatibility, eligibility, city proximity and reliability, then request one directly
- Submit blood requests with urgency levels (Normal / Urgent / Critical)
- Track sent donor requests and their status/appointment
- View own blood-request history & status

### System
- SHA-256 password hashing
- Session-based authentication
- Role-based access control (admin / donor / hospital)
- Rule-based **AI donor-matching engine** — blood compatibility × eligibility × proximity × reliability, computed live per hospital request
- Responsive, mobile-friendly UI across all three dashboards

---

## 🛠 Tech Stack

| Layer    | Technology            |
|----------|------------------------|
| Frontend | HTML5, CSS3, JS (ES6) |
| Backend  | Python 3 + Flask       |
| Database | MySQL 8+ (optional, see `schema.sql`) |
| Fonts    | Google Fonts (Syne + DM Sans) |
