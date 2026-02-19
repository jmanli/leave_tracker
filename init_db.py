"""
Database initialization script for Render deployment.
This script automatically creates tables and seeds the admin user.
Runs during the build process since shell access is not available on free tier.
"""
import os
from app import app
from extensions import db
from models import User, UserRole

def init_database():
    """Initialize database with tables and admin user"""
    with app.app_context():
        try:
            # Create all tables
            print("🔄 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Check if admin already exists
            admin = User.query.filter_by(email='admin@company.com').first()
            
            if not admin:
                print("🔄 Creating default admin user...")
                admin = User(
                    name='System Administrator',
                    email='admin@company.com',
                    role=UserRole.ADMIN
                )
                admin.set_password('Admin123!')
                admin.force_password_change = True
                
                db.session.add(admin)
                db.session.commit()
                
                print("=" * 60)
                print("✅ Admin user created successfully!")
                print("=" * 60)
                print("📧 Email: admin@company.com")
                print("🔑 Password: Admin123!")
                print("⚠️  IMPORTANT: Change this password on first login!")
                print("=" * 60)
            else:
                print("ℹ️  Admin user already exists. Skipping creation.")
                
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            raise

if __name__ == '__main__':
    print("🚀 Starting database initialization...")
    init_database()
    print("✅ Database initialization complete!")
