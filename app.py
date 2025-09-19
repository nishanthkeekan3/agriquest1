import os
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from models import db, User
from auth import auth_bp
from admin_login.routes import admin_bp
from farm import farm_bp
from flask_login import LoginManager, login_required

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    app.logger.setLevel(logging.DEBUG)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(farm_bp)

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    # Global error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.error(f'404 Error: {error}')
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500 Error: {error}')
        db.session.rollback()
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Unhandled Exception: {e}', exc_info=True)
        return render_template('error.html', 
                             error_code=500, 
                             error_message=f"Error: {str(e)}"), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)