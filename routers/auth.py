import secrets

from flask import  Blueprint, request, jsonify, render_template, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
import sqlite3
from utils.validator import create_token
from config import EMAIL,USER_TYPE


auth_bp = Blueprint('auth',__name__)
#======================================
#LOGIN API
#======================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    # JSON request receive karo
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "status": "error",
            "error": "Username and password are required."
        }), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({
            "status": "error",
            "error": "Invalid username."
        }), 400

    if len(password) < 8:
        return jsonify({
            "status": "error",
            "error": "Invalid username or password."
        }), 401

    with get_db() as conn:
        user = conn.execute("""
            SELECT id, username, password, user_type, shared_id
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

    # Username/password verify karo
    if not user or not check_password_hash(user["password"], password):
        return jsonify({
            "status": "error",
            "error": "Invalid username or password."
        }), 401

    # Encrypted token create karo
    token_data = {
        "id": user["id"],
        "shared_id": user["shared_id"]
    }

    token = create_token(token_data)

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "user_type": user["user_type"]
        }
    }), 200


# ======================================
# REGISTER API
# ======================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    # JSON data receive karo
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip().lower()
    password = data.get("password", "")
  

    if not username or not password:
        return jsonify({
            "error": "Username and password are required."
        }), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({
            "error": "Username must be 3 to 50 characters."
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must be at least 8 characters."
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with get_db() as conn:

            # Check existing username
            user = conn.execute("""
                SELECT id FROM users
                WHERE username = ?
            """, (username,)).fetchone()

            if user:
                return jsonify({
                    "error": "Username already exists."
                }), 409
     
            # Default user role
            user_type = "user"
            # NOTE: Email ko username ke roop mein use karne se
                # admin role automatic dena tabhi safe hai jab
                # email ownership verify ki gayi ho.
                # Public registration mein user_type = "user" rakho.
            if EMAIL and EMAIL == username:
                user_type = USER_TYPE

    

            shared_id = secrets.token_urlsafe(16)

            conn.execute("""
                INSERT INTO users (
                    username,
                    password,
                    user_type,
                    shared_id
                )
                VALUES (?, ?, ?, ?)
            """, (
                username,
                password_hash,
                user_type,
                shared_id
            ))

        return jsonify({
            "status": "success",
            "message": "Registration successful."
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "Username already exists."
        }), 409

    except sqlite3.Error:
      
        return jsonify({
            "error": "Database error. Please try again."
        }), 500

@auth_bp.route("/logout",methods=["POST"])
def logout():
    return jsonify({"status":"success","message":"logout successfully"}),200