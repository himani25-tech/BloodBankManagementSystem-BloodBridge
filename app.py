from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import json, os, hashlib, datetime

app = Flask(__name__)
app.secret_key = 'bloodbridge_secret_2025'
@app.route('/')
def home():
    return render_template('index.html')

# ── In-memory data store (replace with DB in production) ──────────────────────
USERS = {
    "admin@bloodbridge.in": {
        "password": hashlib.sha256("Admin@123".encode()).hexdigest(),
        "role": "admin", "name": "Admin User", "avatar": "AU"
    },
    "rahul@donor.com": {
        "password": hashlib.sha256("Donor@123".encode()).hexdigest(),
        "role": "donor", "name": "Rahul Sharma", "avatar": "RS",
        "blood_group": "O+", "city": "Bhopal", "phone": "+91 98765 43210",
        "donations": 7, "points": 350, "last_donation": "2025-03-15"
    },
    "hamidia@hospital.com": {
        "password": hashlib.sha256("Hospital@123".encode()).hexdigest(),
        "role": "hospital", "name": "Hamidia Hospital", "avatar": "HH",
        "city": "Bhopal", "verified": True
    }
}

# Shared blood inventory (admin controls, all can see)
INVENTORY = {
    "A+": {"units": 45, "critical": False},
    "A-": {"units": 8, "critical": True},
    "B+": {"units": 62, "critical": False},
    "B-": {"units": 11, "critical": True},
    "AB+": {"units": 23, "critical": False},
    "AB-": {"units": 5, "critical": True},
    "O+": {"units": 78, "critical": False},
    "O-": {"units": 14, "critical": False}
}

# Requests log — hospitals create, admin sees
REQUESTS = [
    {"id": 1, "hospital": "Hamidia Hospital", "blood": "O-", "units": 4, "urgency": "Critical",
     "status": "Approved", "date": "2025-04-28", "note": "Emergency surgery"},
    {"id": 2, "hospital": "Hamidia Hospital", "blood": "A+", "units": 2, "urgency": "Normal",
     "status": "Pending", "date": "2025-04-30", "note": "Scheduled transfusion"},
]

# Donations log — donors create, admin sees
DONATIONS = [
    {"id": 1, "donor": "Rahul Sharma", "blood": "O+", "units": 1, "date": "2025-03-15", "camp": "Bhopal Blood Drive"},
    {"id": 2, "donor": "Rahul Sharma", "blood": "O+", "units": 1, "date": "2024-11-20", "camp": "Red Cross Camp"},
]

# Activity log visible on admin dashboard
ACTIVITY = []

# ── Auth helpers ───────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_activity(actor, action, detail=""):
    ACTIVITY.insert(0, {
        "actor": actor, "action": action, "detail": detail,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(ACTIVITY) > 50:
        ACTIVITY.pop()

# ── Auth routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for(session['role'] + '_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = hashlib.sha256(data.get('password', '').encode()).hexdigest()
        user = USERS.get(email)
        if user and user['password'] == password:
            session['email'] = email
            session['role'] = user['role']
            session['name'] = user['name']
            session['avatar'] = user.get('avatar', '??')
            log_activity(user['name'], 'Logged in', f"Role: {user['role']}")
            return jsonify({"success": True, "redirect": f"/{user['role']}"})
        return jsonify({"success": False, "message": "Invalid email or password"})
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        name = data.get('name', '').strip()
        role = data.get('role', 'donor')
        password = data.get('password', '')
        if email in USERS:
            return jsonify({"success": False, "message": "Email already registered"})
        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters"})
        USERS[email] = {
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "role": role, "name": name,
            "avatar": "".join([w[0].upper() for w in name.split()[:2]]),
            "blood_group": data.get('blood_group', 'O+'),
            "city": data.get('city', ''), "phone": data.get('phone', ''),
            "donations": 0, "points": 0, "last_donation": None,
            "verified": False
        }
        log_activity(name, 'Registered', f"Role: {role}")
        return jsonify({"success": True, "redirect": "/login"})
    return render_template('signup.html')

@app.route('/logout')
def logout():
    name = session.get('name', 'Unknown')
    log_activity(name, 'Logged out')
    session.clear()
    return redirect(url_for('login'))

# ── Dashboard routes ───────────────────────────────────────────────────────────
@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    return render_template('admin_dashboard.html',
        user=USERS[session['email']],
        inventory=INVENTORY,
        requests=REQUESTS,
        donations=DONATIONS,
        activity=ACTIVITY[:20],
        total_donors=len([u for u in USERS.values() if u['role'] == 'donor']),
        total_hospitals=len([u for u in USERS.values() if u['role'] == 'hospital']),
    )

@app.route('/donor')
@login_required
@role_required('donor')
def donor_dashboard():
    user = USERS[session['email']]
    my_donations = [d for d in DONATIONS if d['donor'] == user['name']]
    return render_template('donor_dashboard.html',
        user=user, inventory=INVENTORY, donations=my_donations
    )

@app.route('/hospital')
@login_required
@role_required('hospital')
def hospital_dashboard():
    user = USERS[session['email']]
    my_requests = [r for r in REQUESTS if r['hospital'] == user['name']]
    return render_template('hospital_dashboard.html',
        user=user, inventory=INVENTORY, requests=my_requests
    )

# ── API routes ─────────────────────────────────────────────────────────────────
@app.route('/api/inventory')
@login_required
def api_inventory():
    return jsonify(INVENTORY)

@app.route('/api/inventory/update', methods=['POST'])
@login_required
@role_required('admin')
def api_inventory_update():
    data = request.get_json()
    bg = data.get('blood_group')
    units = int(data.get('units', 0))
    if bg in INVENTORY:
        old = INVENTORY[bg]['units']
        INVENTORY[bg]['units'] = units
        INVENTORY[bg]['critical'] = units < 15
        log_activity(session['name'], 'Updated inventory', f"{bg}: {old} → {units} units")
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/requests', methods=['GET', 'POST'])
@login_required
def api_requests():
    if request.method == 'GET':
        if session['role'] == 'hospital':
            user = USERS[session['email']]
            return jsonify([r for r in REQUESTS if r['hospital'] == user['name']])
        return jsonify(REQUESTS)
    # POST — hospital creates a new request
    data = request.get_json()
    user = USERS[session['email']]
    new_req = {
        "id": len(REQUESTS) + 1,
        "hospital": user['name'],
        "blood": data.get('blood_group'),
        "units": int(data.get('units', 1)),
        "urgency": data.get('urgency', 'Normal'),
        "status": "Pending",
        "date": datetime.date.today().isoformat(),
        "note": data.get('note', '')
    }
    REQUESTS.insert(0, new_req)
    log_activity(user['name'], 'Blood request submitted', f"{new_req['blood']} × {new_req['units']} ({new_req['urgency']})")
    return jsonify({"success": True, "request": new_req})

@app.route('/api/requests/<int:req_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def api_request_status(req_id):
    data = request.get_json()
    status = data.get('status')
    for r in REQUESTS:
        if r['id'] == req_id:
            old = r['status']
            r['status'] = status
            # If approved, deduct from inventory
            if status == 'Approved' and old != 'Approved':
                bg = r['blood']
                if bg in INVENTORY:
                    INVENTORY[bg]['units'] = max(0, INVENTORY[bg]['units'] - r['units'])
                    INVENTORY[bg]['critical'] = INVENTORY[bg]['units'] < 15
            log_activity(session['name'], f'Request #{req_id} → {status}', f"{r['blood']} × {r['units']} for {r['hospital']}")
            return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/api/donate', methods=['POST'])
@login_required
@role_required('donor')
def api_donate():
    data = request.get_json()
    user = USERS[session['email']]
    new_don = {
        "id": len(DONATIONS) + 1,
        "donor": user['name'],
        "blood": user.get('blood_group', data.get('blood_group', 'O+')),
        "units": 1,
        "date": datetime.date.today().isoformat(),
        "camp": data.get('camp', 'Self Donation')
    }
    DONATIONS.insert(0, new_don)
    # Update inventory
    bg = new_don['blood']
    if bg in INVENTORY:
        INVENTORY[bg]['units'] += 1
        INVENTORY[bg]['critical'] = INVENTORY[bg]['units'] < 15
    # Update donor stats
    user['donations'] = user.get('donations', 0) + 1
    user['points'] = user.get('points', 0) + 50
    user['last_donation'] = new_don['date']
    log_activity(user['name'], 'Donated blood', f"{bg} × 1 at {new_don['camp']}")
    return jsonify({"success": True, "donation": new_don, "new_points": user['points']})

@app.route('/api/activity')
@login_required
@role_required('admin')
def api_activity():
    return jsonify(ACTIVITY[:20])

@app.route('/api/stats')
@login_required
def api_stats():
    total_units = sum(v['units'] for v in INVENTORY.values())
    critical = [k for k, v in INVENTORY.items() if v['critical']]
    return jsonify({
        "total_units": total_units,
        "critical_types": critical,
        "total_donors": len([u for u in USERS.values() if u['role'] == 'donor']),
        "total_hospitals": len([u for u in USERS.values() if u['role'] == 'hospital']),
        "pending_requests": len([r for r in REQUESTS if r['status'] == 'Pending']),
        "total_donations": len(DONATIONS)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)