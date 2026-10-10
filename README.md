# SmartFoodRescue

A Flask web app that connects surplus food from restaurants, bakeries and caterers with NGOs and volunteers.

## Features
- Three roles: **Donor**, **NGO**, **Volunteer**, with secure login (hashed passwords, CSRF protection)
- **Smart matching engine**: every listing gets a 0-100 score from urgency, distance (haversine) and batch size
- Full lifecycle: Available → Claimed → On the way → Delivered (plus auto-expiry, cancel, release)
- Filters, search and sorting (smart match, expiring soon, nearest, largest batch)
- Live **impact dashboard**: meals, kg, CO₂e estimate, 7-day chart, donor leaderboard
- JSON API: `/api/listings?lat=..&lng=..` and `/api/stats`
- SQLite database, no extra services needed

## Run
```bash
pip install -r requirements.txt
python app.py seed     # optional demo data
python app.py          # open http://127.0.0.1:5000
```
Demo logins (password `demo1234`): `donor@demo.com`, `bakery@demo.com`, `ngo@demo.com`, `volunteer@demo.com`

## Configuration (environment variables)
`SECRET_KEY`, `PORT`, `FLASK_DEBUG=1`, `DEFAULT_LAT`, `DEFAULT_LNG` (map centre for seed data / distance fallback)

## Production notes
Run behind gunicorn (`gunicorn app:app`) with HTTPS and set a strong `SECRET_KEY`.
