AgriQuest: AI-Powered Crop Diversification Advisor

Quickstart

1) Create a .env file:
SECRET_KEY=dev-secret
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/agriquest

2) Create DB and admin user:
python create_db.py

3) Run the app:
python app.py

Features

- User sign-up/login (Flask-Login)
- Admin pages for users, farms, recommendations
- Farm profile creation with Leaflet map and soil selector
- NASA POWER climate fetch and summarization
- Market price stub and rule-based recommendations
- Chart.js visualization for price trend

Architecture

- app.py: Flask app factory, blueprint registration
- models.py: User, FarmProfile, Recommendation
- auth.py: auth routes
- farm/: farm profile + recommendation routes and templates
- services/: climate.py, market.py, recommender.py

Notes

- Replace market stub with real API or scraper
- Add API keys as needed, cache responses in DB if required







