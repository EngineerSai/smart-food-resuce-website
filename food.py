
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Food Rescue Network</title>
<style>
:root {
    --green: #08783e;
    --dark: #123c2c;
    --light: #f1f8f1;
    --muted: #63746a;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: "Segoe UI", Arial, sans-serif;
    background: #f5faf6;
    color: var(--dark);
}
header {
    background: white;
    padding: 17px 6%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
    box-shadow: 0 2px 12px #123c2c12;
}
.brand { font-size: 23px; font-weight: 800; }
.brand span { display: block; font-size: 13px; font-weight: 400; }
nav { display: flex; gap: 22px; flex-wrap: wrap; }
nav a { color: var(--dark); text-decoration: none; font-weight: 600; }
nav a:hover { color: var(--green); }
.btn {
    background: var(--green);
    color: white;
    border: 0;
    border-radius: 9px;
    padding: 13px 20px;
    cursor: pointer;
    font-weight: 700;
}
.btn:hover { background: #075d32; }
.hero {
    padding: 65px 7%;
    color: white;
    background: linear-gradient(100deg, #103d29f2, #17663bd9),
                url("https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=1800&q=85")
                center/cover;
}
.hero h1 { font-size: clamp(32px, 5vw, 55px); margin: 0 0 14px; }
.hero h1 span { color: #a8f0a2; }
.hero p { font-size: 18px; line-height: 1.7; max-width: 620px; }
.highlights {
    display: flex;
    gap: 28px;
    flex-wrap: wrap;
    margin-top: 28px;
    font-weight: 600;
}
main {
    max-width: 1400px;
    margin: 30px auto;
    padding: 0 22px;
}
.columns {
    display: grid;
    grid-template-columns: minmax(300px, .85fr) minmax(0, 1.35fr);
    gap: 22px;
    align-items: start;
}
.card {
    background: white;
    border: 1px solid #e1ece2;
    border-radius: 17px;
    overflow: hidden;
    box-shadow: 0 6px 24px #17482b0b;
}
.card-head {
    background: var(--light);
    padding: 22px;
}
.card-head h2 { margin: 0 0 7px; font-size: 23px; }
.card-head p { margin: 0; color: var(--muted); line-height: 1.5; }
.card-body { padding: 23px; }
label {
    display: block;
    margin: 15px 0 7px;
    font-weight: 650;
}
input, select {
    width: 100%;
    padding: 13px;
    border: 1px solid #d5e0d7;
    border-radius: 8px;
    font-size: 15px;
    background: white;
}
input:focus, select:focus {
    outline: 2px solid #75bd8a;
    border-color: var(--green);
}
form .btn { width: 100%; margin-top: 22px; font-size: 16px; }
.list-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}
.search { display: flex; gap: 8px; }
.search input { min-width: 120px; }
.food-item {
    padding: 19px 0;
    border-bottom: 1px solid #e6ede7;
}
.food-item:last-child { border-bottom: 0; }
.food-item h3 { margin: 0 0 10px; }
.details {
    display: flex;
    gap: 10px 20px;
    flex-wrap: wrap;
    color: var(--muted);
    font-size: 14px;
}
.status {
    display: inline-block;
    margin-top: 10px;
    padding: 6px 11px;
    border-radius: 20px;
    background: #e5f7e9;
    color: #08783e;
    font-size: 13px;
    font-weight: 700;
}
.status.requested { background: #fff0d7; color: #8b5600; }
.request-form { margin-top: 10px; }
.request-form .btn { padding: 10px 14px; }
.empty { color: var(--muted); padding: 20px 0; }
.features {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
    margin: 30px 0;
}
.feature {
    padding: 20px;
    background: white;
    border-radius: 12px;
    border: 1px solid #e1ece2;
}
.feature h3 { margin: 0 0 8px; }
.feature p { color: var(--muted); line-height: 1.6; margin: 0; }
footer {
    text-align: center;
    padding: 28px 15px;
    background: #e9f4e9;
    color: var(--dark);
}
@media (max-width: 850px) {
    .columns { grid-template-columns: 1fr; }
    .features { grid-template-columns: repeat(2, 1fr); }
    header { padding: 17px 5%; }
}
@media (max-width: 500px) {
    nav { gap: 12px; }
    .features { grid-template-columns: 1fr; }
    .hero { padding: 40px 6%; }
    main { padding: 0 12px; }
    .card-body { padding: 16px; }
}
</style>
</head>
<body>

<header>
    <div class="brand">🌿 Smart Food
        <span>Rescue Network</span>
    </div>
    <nav>
        <a href="#home">Home</a>
        <a href="#donate">Donate Food</a>
        <a href="#available">Find Food</a>
        <a href="#about">About</a>
    </nav>
    <a class="btn" href="#donate" style="text-decoration:none">Make a Difference</a>
</header>

<section class="hero" id="home">
    <h1>Smart <span>Food Rescue</span> Network</h1>
    <h2>Rescue food. Reduce waste. Help people.</h2>
    <p>Connect food donors with people who need it. Together, we can
       build a hunger-free and sustainable community.</p>
    <div class="highlights">
        <span>♻️ Reduce Food Waste</span>
        <span>🤝 Support Communities</span>
        <span>💚 Help People in Need</span>
    </div>
</section>

<main>
<div class="columns">

<section class="card" id="donate">
    <div class="card-head">
        <h2>🎁 Donate Food</h2>
        <p>Share your surplus food with people who need it most.</p>
    </div>
    <div class="card-body">
        <form action="/donate" method="POST">
            <label for="donor">Donor Name</label>
            <input id="donor" name="donor" placeholder="Enter your name" required>

            <label for="food">Food Name</label>
            <input id="food" name="food_name"
                   placeholder="Rice, Dal, Chapati, Fruits" required>

            <label for="quantity">Quantity</label>
            <input id="quantity" name="quantity"
                   placeholder="e.g. 10 meals or 5 kg" required>

            <label for="city">City</label>
            <select id="city" name="city" required>
                <option value="">Select your city</option>
                <option>Pune</option>
                <option>Latur</option>
                <option>Dharashiv</option>
                <option>Kolhapur</option>
                <option>Bidar</option>
                <option>Murud</option>
                <option>Other</option>
            </select>

            <label for="expiry">Expiry Date &amp; Time</label>
            <input id="expiry" type="datetime-local" name="expiry" required>

            <button class="btn" type="submit">➤ Submit Donation</button>
        </form>
    </div>
</section>

<section class="card" id="available">
    <div class="card-head">
        <div class="list-head">
            <div>
                <h2>🍲 Available Food Donations</h2>
                <p>Find and request food donations.</p>
            </div>
            <div class="search">
                <input id="search" placeholder="Search food or city..."
                       oninput="filterFood()" aria-label="Search donations">
            </div>
        </div>
    </div>
    <div class="card-body" id="food-list">
        {% for food in donations %}
        <article class="food-item"
                 data-search="{{ food['food_name'] }} {{ food['city'] }} {{ food['status'] }}">
            <h3>{{ food['food_name'] }}</h3>
            <div class="details">
                <span>👤 {{ food['donor'] }}</span>
                <span>📍 {{ food['city'] }}</span>
                <span>📦 {{ food['quantity'] }}</span>
                <span>🗓️ {{ food['expiry'] }}</span>
            </div>
            <span class="status {% if food['status'] != 'Available' %}requested{% endif %}">
                {{ food['status'] }}
            </span>
            {% if food['status'] == 'Available' %}
            <form class="request-form" action="/request/{{ food['id'] }}" method="POST">
                <button class="btn" type="submit">Request Food</button>
            </form>
            {% endif %}
        </article>
        {% else %}
        <p class="empty">No donations yet. Be the first to share a meal! 💚</p>
        {% endfor %}
    </div>
</section>

</div>

<section class="features" id="about">
    <article class="feature">
        <h3>💚 Our Mission</h3>
        <p>Reduce food waste and help ensure no one goes hungry.</p>
    </article>
    <article class="feature">
        <h3>🤝 Our Community</h3>
        <p>Connect generous donors with people in need.</p>
    </article>
    <article class="feature">
        <h3>🌱 Our Impact</h3>
        <p>Support a cleaner, healthier, more sustainable future.</p>
    </article>
    <article class="feature">
        <h3>🌍 Join Us</h3>
        <p>Donate food, request available donations, and spread awareness.</p>
    </article>
</section>
</main>

<footer>
    <strong>Smart Food Rescue Network</strong>
    <p>Small actions. Shared meals. A better tomorrow.</p>
</footer>

<script>
function filterFood() {
    const query = document.getElementById("search").value.toLowerCase();
    document.querySelectorAll(".food-item").forEach(item => {
        item.style.display =
            item.dataset.search.toLowerCase().includes(query) ? "" : "none";
    });
}
</script>

</body>
</html>
