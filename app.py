from flask import Flask, render_template, request, jsonify
from config import SECRET_KEY
from database import create_table,migrate_database
from routers.auth import auth_bp
from routers.admin import admin_bp
from routers.track import track_bp
from routers.user_dashboard import user_bp
from routers.shared import share_bp
# =========================
# Initialize Extensions
# =========================
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
# =========================
# Register Blueprints
# =========================
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(track_bp)
app.register_blueprint(user_bp)
app.register_blueprint(share_bp)
#======================================
#HOME PAGE
#======================================
@app.route("/")
def home():
    return render_template("index.html")
#======================================
#MAIN APPLICATION
#======================================
if __name__ == "__main__":
    create_table() 
    # migrate_database()
    app.run(port=5000,host="0.0.0.0", debug=True)
