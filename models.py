from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    farm_profiles = db.relationship('FarmProfile', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class FarmProfile(db.Model):
    __tablename__ = "farm_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    location_name = db.Column(db.String(255))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    soil_type = db.Column(db.String(100), nullable=False)
    climate_inputs = db.Column(db.JSON)  # optional manual inputs or cached API results
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    recommendations = db.relationship('Recommendation', backref='farm', cascade='all, delete-orphan', lazy=True)


class Recommendation(db.Model):
    __tablename__ = "recommendations"
    id = db.Column(db.Integer, primary_key=True)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm_profiles.id'), nullable=False)
    crop_name = db.Column(db.String(150), nullable=False)

    # Scores/estimates
    market_demand_score = db.Column(db.Float)  # 0-1 or 0-100 scale
    profitability_estimate = db.Column(db.Float)  # revenue - cost (per hectare)
    cost_estimate = db.Column(db.Float)  # estimated cost (per hectare)

    ecological_impact = db.Column(db.String(255))  # short summary
    rationale = db.Column(db.Text)  # explanation of why recommended
    data = db.Column(db.JSON)  # raw details: prices, weather stats, features
    created_at = db.Column(db.DateTime, server_default=db.func.now())
