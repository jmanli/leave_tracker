import os
from flask import Flask, redirect, url_for, request, flash, jsonify
from flask_login import current_user
from extensions import db, migrate, login_manager
from config import Config
from models import User, UserRole  # Make sure User and UserRole are imported
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.manager import manager_bp
from routes.__init__ import main_bp
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Ensure upload folder exists
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    @app.before_request
    def check_password_change():
        # List of endpoints that are always accessible
        allowed_endpoints = ['auth.logout', 'auth.change_password', 'static']

        if (current_user.is_authenticated and
            current_user.force_password_change and
            request.endpoint not in allowed_endpoints):
            
            # The 'request.blueprint' check prevents this from firing on favicon.ico etc.
            if request.blueprint is not None and request.blueprint != 'auth':
                flash('You must change your temporary password before you can continue.', 'warning')
                return redirect(url_for('auth.change_password'))


    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(manager_bp)

    # ======================================================================
    # NEW: Define a custom CLI command to seed the database.
    # We do NOT run database queries when the app is created.
    # ======================================================================
    @app.cli.command("db-seed")
    def db_seed():
        """Seeds the database with initial data (like an admin user)."""
        # No need for with app.app_context() here as CLI commands run in one.
        if User.query.filter_by(role=UserRole.ADMIN).first():
            print("Admin user already exists. Skipping seed.")
            return

        print("Creating default admin user...")
        admin_user = User(
            name='Admin User',
            email='admin@example.com',
            role=UserRole.ADMIN
        )
        admin_user.set_password('adminpassword') # CHANGE THIS IN PRODUCTION
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user created: admin@example.com / adminpassword")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)