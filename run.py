from app import app, db

# The 'if __name__ == "__main__"' block is no longer needed for Heroku,
# but it's good practice to keep it for local testing.
# Gunicorn will directly access the 'app' object.
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    