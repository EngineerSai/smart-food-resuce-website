"""
SmartFoodRescue - connect surplus food from restaurants, caterers and stores
with NGOs and volunteers before it goes to waste.

Run:
    pip install -r requirements.txt
    python app.py seed      # optional demo data (password for all demo users: demo1234)
    python app.py           # http://127.0.0.1:5000
"""
import math
import os
import secrets
import sqlite3
import sys
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smartfoodrescue.db")
SECRET_FILE = os.path.join(BASE_DIR, ".secret_key")

DEFAULT_LAT = float(os.environ.get("DEFAULT_LAT", "18.5204"))
DEFAULT_LNG = float(os.environ.get("DEFAULT_LNG", "73.8567"))

CATEGORIES = ["Cooked meals", "Bakery", "Fruits & veg", "Packaged food", "Dairy", "Beverages", "Other"]
DIETS = ["Veg", "Non-veg", "Vegan", "Mixed"]
ROLES = {"donor": "Donor (restaurant / caterer / store)",
         "ngo": "NGO / shelter / community kitchen",
         "volunteer": "Volunteer (pickup & delivery)"}
CO2_KG_PER_SERVING = 1.0     # rough estimate of CO2e avoided per meal rescued
KG_PER_SERVING = 0.4

STATUS_LABELS = {"available": "Available", "claimed": "Claimed", "picked_up": "On the way",
                 "delivered": "Delivered", "expired": "Expired", "cancelled": "Cancelled"}


def _secret_key():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    if not os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "w") as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_FILE) as f:
        return f.read().strip()


app = Flask(__name__)
app.secret_key = _secret_key()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, org TEXT, email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL, role TEXT NOT NULL, phone TEXT,
    lat REAL, lng REAL, created TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS listings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL, category TEXT NOT NULL, diet TEXT NOT NULL,
    servings INTEGER NOT NULL, address TEXT NOT NULL,
    lat REAL NOT NULL, lng REAL NOT NULL,
    expires_at TEXT NOT NULL, notes TEXT,
    status TEXT NOT NULL DEFAULT 'available',
    claimed_by INTEGER REFERENCES users(id),
    volunteer_id INTEGER REFERENCES users(id),
    created TEXT NOT NULL, delivered_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status, expires_at);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    db.commit()
    db.close()


def now():
    return datetime.now().replace(microsecond=0)


def iso(dt):
    return dt.isoformat(timespec="minutes")


def parse(s):
    return datetime.fromisoformat(s)


# --------------------------------------------------------------------------- #
# Smart matching engine
# --------------------------------------------------------------------------- #
def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def match_score(hours_left, dist_km, servings):
    """0-100 score. Urgent + close + larger batches rank first."""
    urgency = max(0.0, 1 - hours_left / 24)          # closer to expiry -> higher
    proximity = 1 / (1 + (dist_km or 0) / 5)         # halves at 5 km
    size = min(servings / 100, 1)
    return round(100 * (0.45 * urgency + 0.40 * proximity + 0.15 * size))


def urgency_label(hours_left):
    if hours_left <= 2:
        return "critical"
    if hours_left <= 6:
        return "high"
    if hours_left <= 12:
        return "medium"
    return "low"


def fmt_left(hours_left):
    if hours_left <= 0:
        return "expired"
    if hours_left < 1:
        return f"{int(hours_left * 60)} min left"
    if hours_left < 48:
        return f"{hours_left:.1f} h left"
    return f"{int(hours_left // 24)} days left"


def enrich(row, user=None):
    d = dict(row)
    hours_left = (parse(d["expires_at"]) - now()).total_seconds() / 3600
    d["hours_left"] = hours_left
    d["left_text"] = fmt_left(hours_left)
    d["urgency"] = urgency_label(hours_left)
    d["status_label"] = STATUS_LABELS.get(d["status"], d["status"])
    d["co2"] = round(d["servings"] * CO2_KG_PER_SERVING, 1)
    ulat = user["lat"] if user and user["lat"] is not None else DEFAULT_LAT
    ulng = user["lng"] if user and user["lng"] is not None else DEFAULT_LNG
    d["distance"] = round(haversine_km(ulat, ulng, d["lat"], d["lng"]), 1)
    d["score"] = match_score(max(hours_left, 0), d["distance"], d["servings"])
    return d


def expire_old():
    db = get_db()
    db.execute("UPDATE listings SET status='expired' WHERE status='available' AND expires_at < ?",
               (iso(now()),))
    db.commit()


# --------------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------------- #
def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    if "user" not in g:
        g.user = get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return g.user


def login_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                flash("Please log in to continue.", "info")
                return redirect(url_for("login", next=request.path))
            if roles and u["role"] not in roles:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco


@app.before_request
def csrf_protect():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST" and request.form.get("csrf") != session["csrf"]:
        abort(400, "Invalid CSRF token")


@app.context_processor
def inject():
    return dict(me=current_user(), csrf=session.get("csrf", ""), STATUS_LABELS=STATUS_LABELS,
                ROLES=ROLES, CATEGORIES=CATEGORIES, DIETS=DIETS, now_iso=iso(now()))


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, msg="You don't have access to this page."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, msg="We couldn't find that page."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, msg=str(getattr(e, "description", "Bad request"))), 400


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
def impact_stats():
    db = get_db()
    row = db.execute("""SELECT COALESCE(SUM(servings),0) s, COUNT(*) n FROM listings
                        WHERE status='delivered'""").fetchone()
    meals, deliveries = row["s"], row["n"]
    active = db.execute("SELECT COUNT(*) c, COALESCE(SUM(servings),0) s FROM listings WHERE status='available'").fetchone()
    donors = db.execute("SELECT COUNT(DISTINCT donor_id) c FROM listings").fetchone()["c"]
    ngos = db.execute("SELECT COUNT(*) c FROM users WHERE role='ngo'").fetchone()["c"]
    vols = db.execute("SELECT COUNT(*) c FROM users WHERE role='volunteer'").fetchone()["c"]
    return dict(meals=meals, deliveries=deliveries, kg=round(meals * KG_PER_SERVING),
                co2=round(meals * CO2_KG_PER_SERVING), active=active["c"], active_servings=active["s"],
                donors=donors, ngos=ngos, volunteers=vols)


# --------------------------------------------------------------------------- #
# Routes: public
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    expire_old()
    u = current_user()
    rows = get_db().execute("""SELECT l.*, d.name donor_name, d.org donor_org FROM listings l
                               JOIN users d ON d.id=l.donor_id WHERE l.status='available'""").fetchall()
    items = sorted((enrich(r, u) for r in rows), key=lambda x: -x["score"])[:3]
    return render_template("index.html", stats=impact_stats(), featured=items)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name, email = f.get("name", "").strip(), f.get("email", "").strip().lower()
        pw, role = f.get("password", ""), f.get("role", "")
        if not name or "@" not in email or len(pw) < 8 or role not in ROLES:
            flash("Please fill all fields. Password needs at least 8 characters.", "error")
            return render_template("register.html", form=f)
        try:
            lat = float(f["lat"]) if f.get("lat") else None
            lng = float(f["lng"]) if f.get("lng") else None
        except ValueError:
            lat = lng = None
        db = get_db()
        try:
            cur = db.execute("""INSERT INTO users(name,org,email,password,role,phone,lat,lng,created)
                                VALUES(?,?,?,?,?,?,?,?,?)""",
                             (name, f.get("org", "").strip(), email, generate_password_hash(pw), role,
                              f.get("phone", "").strip(), lat, lng, iso(now())))
            db.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
            return render_template("register.html", form=f)
        session.clear()
        session["uid"] = cur.lastrowid
        flash("Welcome aboard! Thank you for fighting food waste.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u and check_password_hash(u["password"], request.form.get("password", "")):
            session.clear()
            session["uid"] = u["id"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/impact")
def impact():
    db = get_db()
    leaders = db.execute("""SELECT u.name, u.org, SUM(l.servings) meals, COUNT(*) n FROM listings l
                            JOIN users u ON u.id=l.donor_id WHERE l.status='delivered'
                            GROUP BY u.id ORDER BY meals DESC LIMIT 5""").fetchall()
    days = []
    for i in range(6, -1, -1):
        day = (now() - timedelta(days=i)).date()
        s = db.execute("""SELECT COALESCE(SUM(servings),0) s FROM listings
                          WHERE status='delivered' AND substr(delivered_at,1,10)=?""", (day.isoformat(),)).fetchone()["s"]
        days.append(dict(label=day.strftime("%a"), value=s))
    peak = max([d["value"] for d in days] + [1])
    for d in days:
        d["pct"] = round(100 * d["value"] / peak)
    cats = db.execute("""SELECT category, SUM(servings) s FROM listings WHERE status='delivered'
                         GROUP BY category ORDER BY s DESC""").fetchall()
    return render_template("impact.html", stats=impact_stats(), leaders=leaders, days=days, cats=cats)


# --------------------------------------------------------------------------- #
# Routes: listings
# --------------------------------------------------------------------------- #
@app.route("/listings")
def listings():
    expire_old()
    u = current_user()
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("category", "")
    diet = request.args.get("diet", "")
    sort = request.args.get("sort", "smart")
    max_km = request.args.get("km", type=float)
    rows = get_db().execute("""SELECT l.*, d.name donor_name, d.org donor_org FROM listings l
                               JOIN users d ON d.id=l.donor_id WHERE l.status='available'""").fetchall()
    items = [enrich(r, u) for r in rows]
    if q:
        items = [i for i in items if q in (i["title"] + i["address"] + (i["donor_org"] or "")).lower()]
    if cat:
        items = [i for i in items if i["category"] == cat]
    if diet:
        items = [i for i in items if i["diet"] == diet]
    if max_km:
        items = [i for i in items if i["distance"] <= max_km]
    keys = {"smart": lambda i: -i["score"], "expiry": lambda i: i["hours_left"],
            "distance": lambda i: i["distance"], "servings": lambda i: -i["servings"]}
    items.sort(key=keys.get(sort, keys["smart"]))
    return render_template("listings.html", items=items, args=request.args)


@app.route("/listings/new", methods=["GET", "POST"])
@login_required("donor")
def new_listing():
    u = current_user()
    if request.method == "POST":
        f = request.form
        try:
            servings = int(f["servings"])
            expires = datetime.fromisoformat(f["expires_at"])
            lat, lng = float(f["lat"]), float(f["lng"])
        except (KeyError, ValueError):
            flash("Please check servings, expiry time and location.", "error")
            return render_template("new_listing.html", form=f, default=(DEFAULT_LAT, DEFAULT_LNG))
        title, address = f.get("title", "").strip(), f.get("address", "").strip()
        if (not title or not address or servings < 1 or servings > 5000 or expires <= now()
                or f.get("category") not in CATEGORIES or f.get("diet") not in DIETS):
            flash("Please complete every field with valid values (expiry must be in the future).", "error")
            return render_template("new_listing.html", form=f, default=(DEFAULT_LAT, DEFAULT_LNG))
        db = get_db()
        cur = db.execute("""INSERT INTO listings(donor_id,title,category,diet,servings,address,lat,lng,
                            expires_at,notes,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                         (u["id"], title, f["category"], f["diet"], servings, address, lat, lng,
                          iso(expires), f.get("notes", "").strip(), iso(now())))
        db.commit()
        flash("Listing published. Nearby NGOs are being matched!", "success")
        return redirect(url_for("listing_detail", lid=cur.lastrowid))
    return render_template("new_listing.html", form={}, default=(u["lat"] or DEFAULT_LAT, u["lng"] or DEFAULT_LNG))


def _get_listing(lid):
    row = get_db().execute("""SELECT l.*, d.name donor_name, d.org donor_org, d.phone donor_phone,
                              n.name ngo_name, n.org ngo_org, n.phone ngo_phone,
                              v.name vol_name, v.phone vol_phone
                              FROM listings l JOIN users d ON d.id=l.donor_id
                              LEFT JOIN users n ON n.id=l.claimed_by
                              LEFT JOIN users v ON v.id=l.volunteer_id WHERE l.id=?""", (lid,)).fetchone()
    if not row:
        abort(404)
    return row


@app.route("/listings/<int:lid>")
def listing_detail(lid):
    expire_old()
    u = current_user()
    item = enrich(_get_listing(lid), u)
    steps = ["available", "claimed", "picked_up", "delivered"]
    step_idx = steps.index(item["status"]) if item["status"] in steps else -1
    return render_template("detail.html", item=item, steps=steps, step_idx=step_idx)


@app.route("/listings/<int:lid>/<action>", methods=["POST"])
@login_required()
def listing_action(lid, action):
    u = current_user()
    db = get_db()
    it = _get_listing(lid)
    st = it["status"]
    ok, msg = False, "That action isn't available right now."

    if action == "claim" and u["role"] == "ngo" and st == "available" and parse(it["expires_at"]) > now():
        db.execute("UPDATE listings SET status='claimed', claimed_by=? WHERE id=? AND status='available'", (u["id"], lid))
        ok, msg = True, "Claimed! A volunteer can now accept the pickup."
    elif action == "volunteer" and u["role"] == "volunteer" and st == "claimed" and not it["volunteer_id"]:
        db.execute("UPDATE listings SET volunteer_id=? WHERE id=? AND volunteer_id IS NULL", (u["id"], lid))
        ok, msg = True, "You're the delivery hero for this one!"
    elif action == "picked_up" and st == "claimed" and u["id"] in (it["volunteer_id"], it["claimed_by"]):
        db.execute("UPDATE listings SET status='picked_up' WHERE id=?", (lid,))
        ok, msg = True, "Marked as picked up."
    elif action == "delivered" and st == "picked_up" and u["id"] in (it["volunteer_id"], it["claimed_by"]):
        db.execute("UPDATE listings SET status='delivered', delivered_at=? WHERE id=?", (iso(now()), lid))
        ok, msg = True, f"{it['servings']} meals delivered. Thank you!"
    elif action == "cancel" and st in ("available", "claimed") and u["id"] == it["donor_id"]:
        db.execute("UPDATE listings SET status='cancelled' WHERE id=?", (lid,))
        ok, msg = True, "Listing cancelled."
    elif action == "release" and st == "claimed" and u["id"] == it["claimed_by"]:
        db.execute("UPDATE listings SET status='available', claimed_by=NULL, volunteer_id=NULL WHERE id=?", (lid,))
        ok, msg = True, "Claim released; listing is available again."
    db.commit()
    flash(msg, "success" if ok else "error")
    return redirect(url_for("listing_detail", lid=lid))


@app.route("/dashboard")
@login_required()
def dashboard():
    expire_old()
    u = current_user()
    db = get_db()
    base = """SELECT l.*, d.name donor_name, d.org donor_org FROM listings l
              JOIN users d ON d.id=l.donor_id """
    if u["role"] == "donor":
        rows = db.execute(base + "WHERE l.donor_id=? ORDER BY l.created DESC", (u["id"],)).fetchall()
    elif u["role"] == "ngo":
        rows = db.execute(base + "WHERE l.claimed_by=? ORDER BY l.created DESC", (u["id"],)).fetchall()
    else:
        rows = db.execute(base + "WHERE l.volunteer_id=? ORDER BY l.created DESC", (u["id"],)).fetchall()
    mine = [enrich(r, u) for r in rows]
    delivered = [m for m in mine if m["status"] == "delivered"]
    summary = dict(total=len(mine), meals=sum(m["servings"] for m in delivered),
                   co2=round(sum(m["co2"] for m in delivered)),
                   active=len([m for m in mine if m["status"] in ("available", "claimed", "picked_up")]))
    tasks = []
    if u["role"] == "volunteer":
        rows = db.execute(base + "WHERE l.status='claimed' AND l.volunteer_id IS NULL").fetchall()
        tasks = sorted((enrich(r, u) for r in rows), key=lambda x: -x["score"])
    return render_template("dashboard.html", mine=mine, summary=summary, tasks=tasks)


# --------------------------------------------------------------------------- #
# JSON API
# --------------------------------------------------------------------------- #
@app.route("/api/listings")
def api_listings():
    expire_old()
    u = current_user()
    lat, lng = request.args.get("lat", type=float), request.args.get("lng", type=float)
    fake = {"lat": lat, "lng": lng} if lat is not None and lng is not None else u
    rows = get_db().execute("""SELECT l.*, d.name donor_name, d.org donor_org FROM listings l
                               JOIN users d ON d.id=l.donor_id WHERE l.status='available'""").fetchall()
    items = sorted((enrich(r, fake) for r in rows), key=lambda x: -x["score"])
    keep = ("id", "title", "category", "diet", "servings", "address", "lat", "lng", "expires_at",
            "donor_org", "score", "distance", "urgency", "left_text")
    return jsonify([{k: i[k] for k in keep} for i in items])


@app.route("/api/stats")
def api_stats():
    return jsonify(impact_stats())


# --------------------------------------------------------------------------- #
# Demo data
# --------------------------------------------------------------------------- #
def seed():
    init_db()
    db = sqlite3.connect(DB_PATH)
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        print("Database already has data; skipping seed.")
        return
    pw = generate_password_hash("demo1234")
    t = now()
    users = [
        ("Aarav Mehta", "Spice Garden Restaurant", "donor@demo.com", "donor", DEFAULT_LAT + .010, DEFAULT_LNG + .008),
        ("Sneha Kulkarni", "Fresh Crust Bakery", "bakery@demo.com", "donor", DEFAULT_LAT - .020, DEFAULT_LNG + .015),
        ("Rahul Joshi", "Annapurna Community Kitchen", "ngo@demo.com", "ngo", DEFAULT_LAT + .005, DEFAULT_LNG - .010),
        ("Priya Nair", "", "volunteer@demo.com", "volunteer", DEFAULT_LAT, DEFAULT_LNG),
    ]
    for n, o, e, r, la, ln in users:
        db.execute("INSERT INTO users(name,org,email,password,role,lat,lng,created) VALUES(?,?,?,?,?,?,?,?)",
                   (n, o, e, pw, r, la, ln, iso(t)))
    rows = [
        (1, "Veg biryani & raita", "Cooked meals", "Veg", 60, "MG Road, Spice Garden", .010, .008, 3, "Packed in food-grade containers."),
        (1, "Dal, rice & chapati combos", "Cooked meals", "Veg", 35, "MG Road, Spice Garden", .010, .008, 8, ""),
        (2, "Assorted bread & buns", "Bakery", "Veg", 80, "Baner Road, Fresh Crust", -.020, .015, 5, "End of day unsold bread."),
        (2, "Fruit crates (bananas, apples)", "Fruits & veg", "Vegan", 120, "Baner Road, Fresh Crust", -.020, .015, 20, "Slightly bruised, fully edible."),
        (1, "Paneer wraps", "Packaged food", "Veg", 25, "MG Road, Spice Garden", .010, .008, 1.5, "Eat within 2 hours."),
    ]
    for did, ti, ca, di, se, ad, la, ln, hrs, no in rows:
        db.execute("""INSERT INTO listings(donor_id,title,category,diet,servings,address,lat,lng,expires_at,notes,created)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                   (did, ti, ca, di, se, ad, DEFAULT_LAT + la, DEFAULT_LNG + ln, iso(t + timedelta(hours=hrs)), no, iso(t)))
    for i, (se, ca) in enumerate([(50, "Cooked meals"), (40, "Bakery"), (90, "Cooked meals"), (30, "Fruits & veg")]):
        d = t - timedelta(days=i + 1)
        db.execute("""INSERT INTO listings(donor_id,title,category,diet,servings,address,lat,lng,expires_at,status,
                      claimed_by,volunteer_id,created,delivered_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (1 if i % 2 == 0 else 2, "Past rescue", ca, "Veg", se, "City", DEFAULT_LAT, DEFAULT_LNG,
                    iso(d), "delivered", 3, 4, iso(d - timedelta(hours=5)), iso(d)))
    db.commit()
    db.close()
    print("Seeded. Logins: donor@demo.com, bakery@demo.com, ngo@demo.com, volunteer@demo.com  /  demo1234")


init_db()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed()
    else:
        app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
