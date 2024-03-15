from auth import app
import requests

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, load_dotenv=True, use_reloader=True)