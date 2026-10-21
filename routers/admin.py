
from flask import Blueprint, request, jsonify, render_template
from database import get_db
from utils.validator import validate_token

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
            WHERE id = ? AND user_type = 'admin'
        """, (token_data["user_id"],)).fetchone()

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
