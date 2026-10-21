import secrets

from flask import  Blueprint, request, jsonify, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
import sqlite3
from utils.validator import create_token
from config import EMAIL


auth_bp = Blueprint('auth',__name__)
#======================================
#LOGIN API
#======================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        with get_db() as conn:
            user = conn.execute("""
                                SELECT id,username,password,user_type,shared_id FROM users WHERE username = ?
                                """,(username,)).fetchone()
        if user and check_password_hash(user["password"],password):
            token_data = {
                "id":user["id"],
                "shared_id":user["shared_id"]
            }
            token = create_token(token_data)
            
            return jsonify({
                "status":"success",
                "message":"Login successful",
                "token":token
            })
            
    return render_template("login.html")

#======================================
#REGISTER API
#======================================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        

        if len(username) < 3 or len(username) > 50:
            return render_template(
                "register.html",
                error="Invalid Username"
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password minimum 8 characters"
            )

        password_hash = generate_password_hash(password)

        try:
            user_type = 'user'
            if EMAIL and username == EMAIL.strip().lower():
                user_type = "admin"
                
            with get_db() as conn:
                user = conn.execute("""
                    SELECT id, username FROM users WHERE username = ?
                    """,(username,)).fetchone()
                
                if user:
                    return redirect("/login")
                shared_id = secrets.token_urlsafe(16)
                conn.execute("""
                    INSERT INTO users (username, password, user_type, shared_id)
                    VALUES (?, ?, ?)
                """, (username, password_hash, user_type,shared_id))

        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="Username already exists"
            )

        return redirect("/login")

    return render_template("register.html")
