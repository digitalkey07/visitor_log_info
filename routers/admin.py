
from flask import Blueprint, request, jsonify, render_template
from database import get_db
from utils.validator import validate_token
from config import USER_TYPE

admin_bp = Blueprint("admin", __name__)


# ======================================
# ADMIN PAGE + VISITOR DATA API
# ======================================
@admin_bp.route("/admin", methods=["GET", "POST"])
def admin():

    # GET: HTML page open karo
    if request.method == "GET":
        return render_template("admin.html")

    # POST: Token receive karo
    data = request.get_json(silent=True) or {}
    token = data.get("token")

    if not token:
        return jsonify({
            "error": "Login required."
        }), 401

    # Token validate karo
    token_data = validate_token(token)

    if not token_data:
        return jsonify({
            "error": "Invalid or expired token."
        }), 401

    # Database mein admin verify karo
    with get_db() as conn:

        user = conn.execute("""
            SELECT id, username, user_type
            FROM users
            WHERE id = ? AND user_type = ?
        """, (token_data["user_id"],USER_TYPE)).fetchone()

        if not user:
            return jsonify({
                "error": "Admin access required."
            }), 403

        # Latest 200 visitor records
        logs = conn.execute("""
            SELECT
                id,
                ip_address,
                latitude,
                longitude,
                accuracy,
                page_path,
                visited_at,
                device_type,
                browser,
                operating_system
            FROM visitor_logs
            ORDER BY id DESC
            LIMIT 200
        """).fetchall()

        visitor_logs = [dict(log) for log in logs]

    return jsonify({
        "status": "success",
        "username": user["username"],
        "logs": visitor_logs
    }), 200
# ======================================
# ADMIN PAGE + USER DATA API
# ======================================
@admin_bp.route("/admin/users", methods=["POST"])
def get_registered_users():
    data = request.get_json(silent=True) or {}
    token = data.get("token")

    if not token:
        return jsonify({
            "status": "error",
            "error": "Login required"
        }), 401

    token_data = validate_token(token)

    if not token_data:
        return jsonify({
            "status": "error",
            "error": "Invalid or expired token"
        }), 401

    with get_db() as conn:
        admin_user = conn.execute("""
            SELECT id, username, user_type
            FROM users
            WHERE id = ? AND user_type = ?
        """, (token_data["user_id"],USER_TYPE)).fetchone()

        if not admin_user:  
            return jsonify({
                "status": "error",
                "error": "Admin access required"
            }), 403

        users = conn.execute("""
            SELECT id, username, user_type, shared_id
            FROM users
            ORDER BY id DESC
        """).fetchall()

    return jsonify({
        "status": "success",
        "users": [dict(user) for user in users],
        "total_users": len(users)
    }), 200