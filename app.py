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
        "donations": 7, "points": 350, "last_donation": "2025-03-15",
        # ── Extended donor profile info ──
        "dob": "1997-04-12", "gender": "Male", "weight": 72,
        "address": "MP Nagar, Bhopal", "id_proof": "XXXX-XXXX-4521",
        "emergency_contact_name": "Sunita Sharma",
        "emergency_contact_phone": "+91 90000 11223"
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

# ── Donor Verification Pipeline ─────────────────────────────────────────────
# Step 1: Donor submits "I Want to Donate" → sits here as Pending Verification
# Step 2: Admin verifies → donor becomes visible to hospitals as an Available Donor
DONOR_APPLICATIONS = []

# ── Hospital ⇄ Donor Requests ────────────────────────────────────────────────
# Step 3: Hospital sends a request to a specific verified donor
# Step 4: Donor Accepts (schedules) or Rejects → Admin tracks the full pipeline
HOSPITAL_DONOR_REQUESTS = []

# Seed data — mirrors demo credentials so the pipeline isn't empty on first run
DONOR_APPLICATIONS.append({
    "id": 1, "donor_email": "rahul@donor.com", "donor_name": "Rahul Sharma",
    "blood_group": "O+", "phone": "+91 98765 43210", "address": "MP Nagar, Bhopal",
    "city": "Bhopal", "availability_date": "2026-07-15",
    "status": "Verified", "submitted_date": "2026-07-01"
})

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

def generate_donor_code(email):
    """Stable, unique Donor ID used on the printable Acknowledgment / ID card."""
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:10].upper()
    return f"BB-{digest}"

def generate_verification_code(email, donations):
    """Short code tying the card to this donor's current donation count, so a
    reused/old printout can be told apart from the donor's latest status."""
    raw = f"{email.strip().lower()}|{donations}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8].upper()

def log_activity(actor, action, detail=""):
    ACTIVITY.insert(0, {
        "actor": actor, "action": action, "detail": detail,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(ACTIVITY) > 50:
        ACTIVITY.pop()

# ── AI-Powered Donor Matching Engine ────────────────────────────────────────────
# Rule-based compatibility + eligibility + reliability model that scores every
# verified donor against a hospital's blood requirement (0-100). This powers the
# "Smart Match" ranking hospitals see instead of a plain unsorted donor list.
BLOOD_COMPATIBILITY = {
    "O-":  ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],  # universal donor
    "O+":  ["O+", "A+", "B+", "AB+"],
    "A-":  ["A-", "A+", "AB-", "AB+"],
    "A+":  ["A+", "AB+"],
    "B-":  ["B-", "B+", "AB-", "AB+"],
    "B+":  ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}

def donor_eligibility(email):
    """Returns (is_eligible, days_since_last, message) based on the 90-day donation rule."""
    user = USERS.get(email, {})
    last = user.get('last_donation')
    if not last:
        return True, None, "First-time donor — eligible"
    try:
        last_date = datetime.date.fromisoformat(last)
        days = (datetime.date.today() - last_date).days
        if days < 90:
            return False, days, f"Not yet eligible — {90 - days} day(s) remaining"
        return True, days, f"Eligible — {days} days since last donation"
    except Exception:
        return True, None, "Eligible"

def ai_match_score(donor_app, needed_blood_group=None, hospital_city=None):
    """
    AI-Powered Donor Matching Engine
    Scores a verified donor application against a hospital's requirement using:
      • Blood-type compatibility (exact match > medically compatible)
      • 90-day donation eligibility window
      • Geographic proximity (same city)
      • Donor reliability (donation history)
    Returns a dict with score (0-100), a human label, and the reasons behind it.
    """
    bg = donor_app['blood_group']
    reasons = []

    if needed_blood_group:
        if bg == needed_blood_group:
            score = 60
            reasons.append("Exact blood group match")
        elif needed_blood_group in BLOOD_COMPATIBILITY.get(bg, []):
            score = 40
            reasons.append("Medically compatible blood group")
        else:
            return {"score": 0, "label": "Not Compatible", "reasons": ["Blood group not compatible with requirement"], "eligible": False}
    else:
        score = 50
        reasons.append("General availability")

    eligible, days, elig_msg = donor_eligibility(donor_app['donor_email'])
    if eligible:
        score += 15
    reasons.append(elig_msg)

    if hospital_city and donor_app.get('city', '').strip().lower() == hospital_city.strip().lower():
        score += 15
        reasons.append(f"Located in {donor_app.get('city')} — same city as hospital")

    user = USERS.get(donor_app['donor_email'], {})
    donations_count = user.get('donations', 0)
    reliability_bonus = min(donations_count * 2, 10)
    score += reliability_bonus
    if donations_count > 0:
        reasons.append(f"{donations_count} prior successful donation(s)")

    score = max(0, min(round(score), 100))
    if score >= 85:
        label = "Excellent Match"
    elif score >= 65:
        label = "Good Match"
    elif score >= 40:
        label = "Fair Match"
    else:
        label = "Low Match"

    return {"score": score, "label": label, "reasons": reasons, "eligible": eligible}

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
            "verified": False,
            # ── Extended profile info (mainly used by donors) ──
            "dob": data.get('dob', ''),
            "gender": data.get('gender', ''),
            "weight": data.get('weight', ''),
            "address": data.get('address', ''),
            "id_proof": data.get('id_proof', ''),
            "emergency_contact_name": data.get('emergency_contact_name', ''),
            "emergency_contact_phone": data.get('emergency_contact_phone', '')
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
        donor_applications=DONOR_APPLICATIONS,
        donor_requests=HOSPITAL_DONOR_REQUESTS,
    )

@app.route('/donor')
@login_required
@role_required('donor')
def donor_dashboard():
    user = USERS[session['email']]
    my_donations = [d for d in DONATIONS if d['donor'] == user['name']]
    my_applications = [a for a in DONOR_APPLICATIONS if a['donor_email'] == session['email']]
    my_incoming_requests = [r for r in HOSPITAL_DONOR_REQUESTS if r['donor_email'] == session['email']]
    latest_application = my_applications[0] if my_applications else None
    donor_code = generate_donor_code(session['email'])
    verification_code = generate_verification_code(session['email'], user.get('donations', 0))
    is_verified_donor = any(a['status'] == 'Verified' for a in my_applications)
    return render_template('donor_dashboard.html',
        user=user, inventory=INVENTORY, donations=my_donations,
        my_applications=my_applications, latest_application=latest_application,
        incoming_requests=my_incoming_requests,
        donor_code=donor_code, verification_code=verification_code,
        issue_date=datetime.date.today().isoformat(),
        is_verified_donor=is_verified_donor
    )

@app.route('/hospital')
@login_required
@role_required('hospital')
def hospital_dashboard():
    user = USERS[session['email']]
    my_requests = [r for r in REQUESTS if r['hospital'] == user['name']]
    verified_donors = [a for a in DONOR_APPLICATIONS if a['status'] == 'Verified']
    my_donor_requests = [r for r in HOSPITAL_DONOR_REQUESTS if r['hospital_email'] == session['email']]
    return render_template('hospital_dashboard.html',
        user=user, inventory=INVENTORY, requests=my_requests,
        verified_donors=verified_donors, donor_requests=my_donor_requests
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

# ── Donor Verification & Hospital-Donor Request APIs ────────────────────────────

@app.route('/api/donor/apply', methods=['POST'])
@login_required
@role_required('donor')
def api_donor_apply():
    """Step 1: Donor submits 'I Want to Donate' → goes to Admin as Pending Verification."""
    data = request.get_json()
    user = USERS[session['email']]
    new_app = {
        "id": len(DONOR_APPLICATIONS) + 1,
        "donor_email": session['email'],
        "donor_name": user['name'],
        "blood_group": data.get('blood_group', user.get('blood_group', 'O+')),
        "phone": data.get('phone', user.get('phone', '')),
        "address": data.get('address', ''),
        "city": data.get('city', user.get('city', '')),
        "availability_date": data.get('availability_date', ''),
        "status": "Pending Verification",
        "submitted_date": datetime.date.today().isoformat()
    }
    DONOR_APPLICATIONS.insert(0, new_app)
    log_activity(user['name'], 'Submitted donation request', f"{new_app['blood_group']} · awaiting admin verification")
    return jsonify({"success": True, "application": new_app})


@app.route('/api/admin/donor-applications/<int:app_id>/verify', methods=['POST'])
@login_required
@role_required('admin')
def api_admin_verify_donor(app_id):
    """Step 2: Admin verifies (or rejects) a donor application. Only verified donors become visible to hospitals."""
    data = request.get_json()
    status = data.get('status')  # 'Verified' or 'Rejected'
    for a in DONOR_APPLICATIONS:
        if a['id'] == app_id:
            a['status'] = status
            log_activity(session['name'], f'Donor application #{app_id} → {status}', f"{a['donor_name']} ({a['blood_group']})")
            return jsonify({"success": True})
    return jsonify({"success": False, "message": "Application not found"})


@app.route('/api/hospital/verified-donors')
@login_required
@role_required('hospital')
def api_hospital_verified_donors():
    """Step 2→3: Hospital browses the Verified Donor pool, ranked by the AI Matching Engine."""
    needed_bg = request.args.get('blood_group')
    hospital = USERS[session['email']]
    pool = [a for a in DONOR_APPLICATIONS if a['status'] == 'Verified']
    results = []
    for a in pool:
        match = ai_match_score(a, needed_blood_group=needed_bg, hospital_city=hospital.get('city'))
        results.append({**a, "match": match})
    results.sort(key=lambda x: x['match']['score'], reverse=True)
    return jsonify(results)


@app.route('/api/hospital/request-donor', methods=['POST'])
@login_required
@role_required('hospital')
def api_hospital_request_donor():
    """Step 3: Hospital sends a request to a specific verified donor."""
    data = request.get_json()
    donor_email = data.get('donor_email')
    donor_app = next((a for a in DONOR_APPLICATIONS if a['donor_email'] == donor_email and a['status'] == 'Verified'), None)
    if not donor_app:
        return jsonify({"success": False, "message": "Donor not found or not verified"})
    hospital = USERS[session['email']]
    new_req = {
        "id": len(HOSPITAL_DONOR_REQUESTS) + 1,
        "hospital_email": session['email'],
        "hospital_name": hospital['name'],
        "donor_email": donor_email,
        "donor_name": donor_app['donor_name'],
        "blood_group": data.get('blood_group', donor_app['blood_group']),
        "units": int(data.get('units', 1)),
        "status": "Waiting for Donor Response",
        "request_date": datetime.date.today().isoformat(),
        "appointment_date": None,
        "notes": data.get('notes', '')
    }
    HOSPITAL_DONOR_REQUESTS.insert(0, new_req)
    log_activity(hospital['name'], 'Requested a verified donor', f"{donor_app['donor_name']} ({new_req['blood_group']})")
    return jsonify({"success": True, "request": new_req})


@app.route('/api/donor/requests/<int:req_id>/respond', methods=['POST'])
@login_required
@role_required('donor')
def api_donor_respond(req_id):
    """Step 4: Donor accepts (schedules an appointment) or rejects a hospital's request."""
    data = request.get_json()
    action = data.get('action')  # 'accept' or 'reject'
    user = USERS[session['email']]
    for r in HOSPITAL_DONOR_REQUESTS:
        if r['id'] == req_id and r['donor_email'] == session['email']:
            if action == 'accept':
                r['status'] = 'Accepted'
                r['appointment_date'] = data.get('appointment_date') or datetime.date.today().isoformat()
                log_activity(user['name'], f'Accepted hospital request #{req_id}', f"{r['hospital_name']} · appointment {r['appointment_date']}")
            else:
                r['status'] = 'Rejected'
                log_activity(user['name'], f'Declined hospital request #{req_id}', r['hospital_name'])
            return jsonify({"success": True, "request": r})
    return jsonify({"success": False, "message": "Request not found"})


@app.route('/api/admin/donor-requests/<int:req_id>/complete', methods=['POST'])
@login_required
@role_required('admin')
def api_admin_complete_donation(req_id):
    """Final step: Admin marks a scheduled donation as completed — updates inventory, donor stats and donation log."""
    for r in HOSPITAL_DONOR_REQUESTS:
        if r['id'] == req_id:
            if r['status'] != 'Accepted':
                return jsonify({"success": False, "message": "Request must be Accepted before it can be completed"})
            r['status'] = 'Completed'
            bg = r['blood_group']
            new_don = {
                "id": len(DONATIONS) + 1, "donor": r['donor_name'], "blood": bg,
                "units": r['units'], "date": datetime.date.today().isoformat(),
                "camp": f"Hospital Request — {r['hospital_name']}"
            }
            DONATIONS.insert(0, new_don)
            if bg in INVENTORY:
                INVENTORY[bg]['units'] += r['units']
                INVENTORY[bg]['critical'] = INVENTORY[bg]['units'] < 15
            donor_user = USERS.get(r['donor_email'])
            if donor_user:
                donor_user['donations'] = donor_user.get('donations', 0) + 1
                donor_user['points'] = donor_user.get('points', 0) + 50
                donor_user['last_donation'] = new_don['date']
            log_activity(session['name'], f'Donation completed for request #{req_id}', f"{r['donor_name']} → {r['hospital_name']} ({bg} × {r['units']})")
            return jsonify({"success": True})
    return jsonify({"success": False, "message": "Request not found"})


@app.route('/api/donor/my-requests')
@login_required
@role_required('donor')
def api_donor_my_requests():
    return jsonify([r for r in HOSPITAL_DONOR_REQUESTS if r['donor_email'] == session['email']])


@app.route('/api/donor/profile/photo', methods=['POST'])
@login_required
@role_required('donor')
def api_donor_photo_upload():
    """Stores a donor's profile photo (as a data URI) so it can show on their
    dashboard, profile, and Acknowledgment / ID card."""
    data = request.get_json()
    photo = data.get('photo', '')
    if not photo.startswith('data:image/'):
        return jsonify({"success": False, "message": "Please upload a valid image file"})
    # Rough size guard — base64 is ~1.37x the raw bytes; cap around 3MB raw.
    if len(photo) > 4_200_000:
        return jsonify({"success": False, "message": "Image is too large. Please use a photo under 3MB."})
    user = USERS[session['email']]
    user['photo'] = photo
    log_activity(user['name'], 'Updated profile photo')
    return jsonify({"success": True, "photo": photo})


@app.route('/api/donor/profile/update', methods=['POST'])
@login_required
@role_required('donor')
def api_donor_profile_update():
    """Lets a donor fill in / edit their extended profile info (used on the
    Acknowledgment card and shared with hospitals for identity verification)."""
    data = request.get_json()
    user = USERS[session['email']]
    editable_fields = [
        'phone', 'city', 'address', 'dob', 'gender', 'weight',
        'id_proof', 'emergency_contact_name', 'emergency_contact_phone'
    ]
    for field in editable_fields:
        if field in data:
            user[field] = data[field]
    log_activity(user['name'], 'Updated profile information')
    return jsonify({"success": True, "user": {k: user.get(k) for k in editable_fields}})


@app.route('/api/donor/acknowledgment')
@login_required
@role_required('donor')
def api_donor_acknowledgment():
    """Returns the data needed to render/print the donor's Acknowledgment / ID card."""
    user = USERS[session['email']]
    return jsonify({
        "name": user['name'],
        "blood_group": user.get('blood_group'),
        "city": user.get('city'),
        "phone": user.get('phone'),
        "donations": user.get('donations', 0),
        "last_donation": user.get('last_donation'),
        "photo": user.get('photo'),
        "donor_code": generate_donor_code(session['email']),
        "verification_code": generate_verification_code(session['email'], user.get('donations', 0)),
        "issue_date": datetime.date.today().isoformat(),
        "is_verified_donor": any(
            a['status'] == 'Verified' for a in DONOR_APPLICATIONS
            if a['donor_email'] == session['email']
        )
    })


# ── BloodBridge Assistant (rule-based donor chatbot) ────────────────────────
def chatbot_reply(user, email, message):
    """
    Lightweight, rule-based assistant for the donor dashboard. Answers common
    questions using the donor's own live data (eligibility, donor ID, points,
    requests, inventory) plus general blood-donation knowledge — no external
    API calls, so it works instantly and offline.
    """
    import re
    msg = (message or "").strip().lower()
    name_first = user['name'].split()[0] if user.get('name') else "there"

    def has(*keywords):
        """Substring match — good for catching donate/donation/donated with one root."""
        return any(k in msg for k in keywords)

    def has_word(*keywords):
        """Whole-word match — used for short greeting words so 'hi' doesn't
        match inside 'which', 'this', etc."""
        return any(re.search(r'(?<![a-z])' + re.escape(k) + r'(?![a-z])', msg) for k in keywords)

    # Greeting (whole-word match only)
    if has_word("hi", "hii", "helo", "hello", "hey", "namaste", "namaskar"):
        return (f"Hi {name_first}! 👋 I'm the BloodBridge Assistant. Ask me about your "
                f"eligibility, Donor ID, blood group compatibility, hospital requests, "
                f"reward points, or how the donation process works.")

    # Eligibility
    if has("eligib", "kab", "next donation", "donate kar sakta", "donate kar sakti",
           "90 day", "90 din", "kitne din"):
        eligible, days, elig_msg = donor_eligibility(email)
        if eligible:
            return f"✅ Good news — you're currently eligible to donate. {elig_msg}."
        return f"⏳ {elig_msg}. The standard gap between donations is 90 days."

    # Donor ID / Acknowledgment card
    if has("donor id", "donor code", "id card", "acknowledgment", "ack card", "my id"):
        code = generate_donor_code(email)
        return (f"🪪 Your Donor ID is <b>{code}</b>. It's permanent and never changes. "
                f"The rest of your Acknowledgment Card (photo, blood group, donation count, "
                f"last donation date) updates automatically — check the "
                f"<b>Acknowledgment Card</b> tab in the sidebar.")

    # Blood group compatibility
    if has("compatib", "kis blood group", "which blood group", "blood group can", "donate to",
           "universal donor", "universal recipient", "matching group"):
        bg = user.get('blood_group')
        if bg and bg in BLOOD_COMPATIBILITY:
            can_give = ", ".join(BLOOD_COMPATIBILITY[bg])
            return (f"🩸 Your blood group is <b>{bg}</b>. You can donate to: <b>{can_give}</b>.<br>"
                    f"Quick reference: O− is the universal donor (can give to anyone), "
                    f"and AB+ is the universal recipient (can receive from anyone).")
        return ("🩸 Blood compatibility depends on both ABO type and Rh factor. "
                "O− is the universal donor; AB+ is the universal recipient. "
                "Add your blood group in My Profile for a personalized answer.")

    # Points / rewards
    if has("points", "reward"):
        return (f"⭐ You currently have <b>{user.get('points', 0)}</b> reward points from "
                f"<b>{user.get('donations', 0)}</b> completed donation(s). Every completed "
                f"donation earns +50 points.")

    # Donation history / count
    if has("history", "kitni baar", "how many donation", "total donation"):
        last = user.get('last_donation') or "no donations recorded yet"
        return (f"📜 You've donated <b>{user.get('donations', 0)}</b> time(s) so far. "
                f"Last donation: <b>{last}</b>. Full history is in the "
                f"<b>Donation History</b> tab.")

    # Inventory (checked before hospital-requests so a generic word like
    # "status" in "inventory status" doesn't get swallowed by the request intent)
    if has("inventory", "stock", "units available", "blood available"):
        critical = [bg for bg, v in INVENTORY.items() if v['critical']]
        if critical:
            return (f"🧪 Current inventory has low stock in: <b>{', '.join(critical)}</b>. "
                    f"Check the <b>Blood Inventory</b> tab for full unit counts.")
        return "🧪 Inventory levels look healthy across all blood groups right now. Check the <b>Blood Inventory</b> tab for exact units."

    # Hospital requests status
    if has("request", "hospital request", "appointment", "donor request"):
        my_requests = [r for r in HOSPITAL_DONOR_REQUESTS if r['donor_email'] == email]
        if not my_requests:
            return ("📭 You don't have any hospital requests right now. Once you're a "
                    "Verified Donor, hospitals may send you a request that you can Accept "
                    "or Reject from the <b>Hospital Requests</b> tab.")
        pending = [r for r in my_requests if r['status'] == 'Waiting for Donor Response']
        if pending:
            r = pending[0]
            return (f"🏥 You have a pending request from <b>{r['hospital_name']}</b> for "
                    f"{r['blood_group']} ({r['units']} unit(s)). Please respond from the "
                    f"<b>Hospital Requests</b> tab.")
        latest = my_requests[0]
        return (f"🏥 Your latest request from <b>{latest['hospital_name']}</b> is currently "
                f"<b>{latest['status']}</b>. Check the <b>Hospital Requests</b> tab for details.")

    # How to donate / process
    if has("how to donate", "kaise donate", "process", "steps", "kaise kare", "become a donor",
           "verified donor"):
        return ("📝 Here's how it works: 1) Submit <b>Become a Verified Donor</b> with your "
                "details. 2) Admin verifies you. 3) Hospitals can then find and request you "
                "via the AI Matching Engine. 4) You Accept or Reject each request. 5) After "
                "the actual donation, Admin marks it Completed — your stats update "
                "automatically.")

    # After-donation care
    if has("after donat", "care", "rest", "precaution", "recover"):
        return ("💧 After donating: drink plenty of fluids, eat a light nutritious meal, keep "
                "the bandage on for 4-6 hours, and avoid heavy exercise or alcohol for 24 "
                "hours. If you feel dizzy, sit or lie down with your feet raised.")

    # Thanks / bye
    if has("thank", "thanks", "bye", "goodbye"):
        return "🙏 You're welcome! Thank you for being a blood donor — you're saving lives."

    # Fallback
    return ("🤔 I can help with: eligibility &amp; next donation date, your Donor ID / "
            "Acknowledgment Card, blood group compatibility, reward points, donation history, "
            "hospital request status, inventory, the donation process, or after-donation care. "
            "Try asking about one of these!")


@app.route('/api/donor/chatbot', methods=['POST'])
@login_required
@role_required('donor')
def api_donor_chatbot():
    data = request.get_json()
    message = data.get('message', '')
    user = USERS[session['email']]
    reply = chatbot_reply(user, session['email'], message)
    return jsonify({"success": True, "reply": reply})


if __name__ == '__main__':
    app.run(debug=True)