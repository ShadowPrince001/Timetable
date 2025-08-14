from app import app, init_db

# Initialize database when app starts (for production deployment)
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run()
