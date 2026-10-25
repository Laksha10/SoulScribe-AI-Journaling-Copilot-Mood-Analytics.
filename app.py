#app.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_mail import Mail
import os
from db.connection import db, mail as mail_ref
from db.models import User


# Route blueprints
from routes.user_settings import user_settings_bp
from routes.thread import thread_bp
from routes.auth import auth_bp
from routes.predict import predict_bp
from routes.emotion_monitor import emotion_monitor_bp
from routes.timeline import timeline_bp
from routes.emotion_arc import emotion_arc_bp
from routes.session import session_bp

load_dotenv()
print("LOADED DB URL:", os.getenv("DATABASE_URL"))

app = Flask(__name__)
CORS(app)

# Secret key and DB config
app.secret_key = os.getenv("SECRET_KEY", "super-secret")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Init extensions
db.init_app(app)
mail = Mail(app)
mail_ref.init_app(app)
migrate = Migrate(app, db)

# Register routes
app.register_blueprint(predict_bp)
app.register_blueprint(thread_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(emotion_monitor_bp)
app.register_blueprint(timeline_bp)
app.register_blueprint(emotion_arc_bp)
app.register_blueprint(session_bp)
app.register_blueprint(user_settings_bp)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5050)
