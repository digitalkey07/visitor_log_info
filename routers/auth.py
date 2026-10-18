from flask import  Blueprint, request, jsonify, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
import sqlite3
from utils.validator import create_token


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
                                SELECT id,username,password,user_type FROM users WHERE username = ?
                                """,(username,)).fetchone()
        if user and check_password_hash(user["password"],password):
            token = create_token(user["id"])
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
        username = request.form.get("username", "").strip()
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
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO users (username, password, user_type)
                    VALUES (?, ?, ?)
                """, (username, password_hash, "user"))

        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="Username already exists"
            )

        return redirect("/login")

    return render_template("register.html")
