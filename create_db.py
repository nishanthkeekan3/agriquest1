from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.password_hash = generate_password_hash('adminpass')
        db.session.add(admin)
        db.session.commit()
        print("Created admin account: username=admin password=adminpass")
    else:
        print("Admin user already exists")
