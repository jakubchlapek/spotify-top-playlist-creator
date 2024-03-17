from auth import app
from db import db

if __name__ == "__main__":
    db.create_all()
    app.run(host='0.0.0.0', debug=True, load_dotenv=True, use_reloader=True)