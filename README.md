  **BloodBankManagementSystem-BloodBridge**
  # 🩸 BloodBridge – Blood Bank Management System

  

## 📖 Overview

The Blood Bank Management System replaces slow, error-prone paper registers with a centralized digital platform. Donors can register in seconds, hospitals can check blood availability in real time, and administrators get a live dashboard of stock, requests, and donor data — all backed by a secure, structured database.

A full-stack web application built with **HTML · CSS · JavaScript · Python Flask · MySQL**

## 🌐 Live Demo

🔗 **[Visit the Live Website](https://bloodbridge-xr8i.onrender.com)**

Check out the deployed version of the Blood Bank Management System here.

---

## 📁 Project Structure

```
bbms/
├── app.py                  ← Flask backend (routes, auth, DB logic)
├── schema.sql              ← MySQL schema + seed data
├── templates/
│ 
│   ├── index.html          ← Landing page
│   ├── login.html          ← Login
│   ├── signup.html       ← Registration
│   ├  requirements.txt
│   ├── donor_dashboard.html         
│   ├── admin_dashboard.html      
│   ├── hospital_dashboard.html       
└── 

---

## ⚙️ Setup Instructions

### 1. Install Python packages
```bash
cd bbms
pip install -r requirements.txt
```

### 2. Setup MySQL Database
Open MySQL and run:
```bash
mysql -u root -p < schema.sql
```
Or paste `schema.sql` content into MySQL Workbench / phpMyAdmin.

### 3. Configure Database (app.py line ~15)
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'blood_bank_db',
    'user': 'root',
    'password': 'YOUR_MYSQL_PASSWORD'   # ← update this
}
```

### 4. Run the App
```bash
python app.py
```
Open: **http://localhost:5000**

---

## 🔐 Demo Credentials

| Role  | Email                   | Password   |
|-------|-------------------------|------------|
| Admin | admin@bloodbank.com     | admin123   |
| User  | rahul@email.com         | user123    |

---

## ✅ Features

### Admin
- Full dashboard with live inventory chart
- Manage donors (add / delete / search / filter by blood group)
- View & manage all blood requests (approve → auto-deducts inventory / reject)
- Update blood inventory (add or remove units + full transaction log)
- Manage all registered users

### User
- Register / Login
- View blood inventory 
- Edit own profile
-viewdonation list
### hospital
-Resister /login
- Submit blood requests with urgency levels (Normal / Urgent / Critical)
View own request history & status
### System
- SHA-256 password hashing
- Session-based authentication
- Role-based access control (admin vs user)
- Flash messages for all operations
- Responsive design (mobile-friendly)
- Chart.js bar chart for inventory visualization

---

## 🛠 Tech Stack

| Layer    | Technology           |
|----------|---------------------|
| Frontend | HTML5, CSS3, JS (ES6)|
| Backend  | Python 3 + Flask    |
| Database | MySQL 8+            |
| Charts   | Chart.js 4          |
| Icons    | Font Awesome 6      |
| Fonts    | Google Fonts (Syne + DM Sans) |

## 🔮 Future Enhancements

- 📱 Dedicated mobile app
- 📩 SMS/email alerts for urgent blood needs
- 📅 Online donation appointment scheduling
- 🏥 Integration with hospital information systems
- 📍 Location-based blood bank search
- 📈 Advanced analytics & donation trend forecasting


