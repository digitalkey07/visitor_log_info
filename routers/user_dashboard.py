
import json
from contextlib import closing

from flask import Blueprint, render_template, request, jsonify, abort

from database import get_db
from utils.validator import validate_token
from config import USER_TYPE


user_bp = Blueprint("user_dashboard", __name__)


# ============================================================
# AUTHENTICATE NORMAL USER
# ============================================================

def get_current_user():
    data = request.get_json(silent=True) or {}
    token = data.get("token")

    if not token:
        return None, (jsonify({
            "status": "error",
            "message": "Login required."
        }), 401)

    try:
        token_data = validate_token(token)
    except Exception:
        token_data = None

    if not isinstance(token_data, dict):
        return None, (jsonify({
            "status": "error",
            "message": "Invalid or expired token."
        }), 401)

    user_id = token_data.get("user_id", token_data.get("id"))

    if user_id is None:
        return None, (jsonify({
            "status": "error",
            "message": "User ID missing from token."
        }), 401)

    with closing(get_db()) as conn:
        row = conn.execute("""
            SELECT id, username, user_type, shared_id
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

    if row is None:
        return None, (jsonify({
            "status": "error",
            "message": "User not found."
        }), 401)

    user = dict(row)

    if user["user_type"] == USER_TYPE:
        return None, (jsonify({
            "status": "error",
            "message": "Normal user account required."
        }), 403)

    if not user.get("shared_id"):
        return None, (jsonify({
            "status": "error",
            "message": "Share ID is not configured."
        }), 409)

    return user, None


# ============================================================
# FETCH VISITORS FOR CURRENT USER
# ============================================================

def fetch_visitors(shared_id, limit=None, search=""):
    sql = """
        SELECT
            id,
            ip_address,
            mac_address,
            page_path,
            visited_at,
            device_type,
            browser,
            operating_system,
            latitude,
            longitude,
            accuracy,
            share_id
        FROM visitor_logs
        WHERE share_id = ?
    """

    params = [shared_id]

    if search:
        sql += """
            AND (
                COALESCE(ip_address, '') LIKE ?
                OR COALESCE(page_path, '') LIKE ?
                OR COALESCE(browser, '') LIKE ?
                OR COALESCE(operating_system, '') LIKE ?
                OR COALESCE(device_type, '') LIKE ?
            )
        """
        term = f"%{search}%"
        params.extend([term] * 5)

    sql += " ORDER BY id DESC"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    with closing(get_db()) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


# ============================================================
# DASHBOARD PAGE
# ============================================================

@user_bp.route("/dashboard", methods=["GET"])
def user_dashboard_page():
    return render_template("user_dashboard.html")


# ============================================================
# USER PROFILE API
# POST /user/profile
# ============================================================

@user_bp.route("/user/profile", methods=["POST"])
def user_profile():
    user, error = get_current_user()

    if error:
        return error

    return jsonify({
        "status": "success",
        "profile": {
            "id": user["id"],
            "username": user["username"],
            "user_type": user["user_type"],
            "shared_id": user["shared_id"]
        }
    }), 200


# ============================================================
# USER DASHBOARD API
# POST /user/dashboard
# ============================================================

@user_bp.route("/user/dashboard", methods=["POST"])
def user_dashboard_data():
    user, error = get_current_user()

    if error:
        return error

    with closing(get_db()) as conn:
        total = conn.execute("""
            SELECT COUNT(*) AS total
            FROM visitor_logs
            WHERE share_id = ?
        """, (user["shared_id"],)).fetchone()["total"]

    recent = fetch_visitors(
        shared_id=user["shared_id"],
        limit=5
    )

    return jsonify({
        "status": "success",
        "username": user["username"],
        "user_type": user["user_type"],
        "share_id": user["shared_id"],
        "total_visitors": total,
        "recent_visitors": recent
    }), 200


# ============================================================
# ACTIVE FESTIVALS API
# POST /user/festivals
# ============================================================

@user_bp.route("/user/festivals", methods=["POST"])
def user_festivals():
    user, error = get_current_user()

    if error:
        return error

    with closing(get_db()) as conn:
        rows = conn.execute("""
            SELECT
                id,
                festival_name,
                title,
                subtitle,
                eyebrow
            FROM uidata
            WHERE is_active = 1
            ORDER BY festival_name COLLATE NOCASE ASC
        """).fetchall()

    return jsonify({
        "status": "success",
        "festivals": [dict(row) for row in rows]
    }), 200


# ============================================================
# USER VISITORS API
# POST /user/visitors
# ============================================================

@user_bp.route("/user/visitors", methods=["POST"])
def user_visitors_data():
    user, error = get_current_user()

    if error:
        return error

    data = request.get_json(silent=True) or {}
    search = data.get("search", "")

    if not isinstance(search, str):
        return jsonify({
            "status": "error",
            "message": "Invalid search value."
        }), 400

    visitors = fetch_visitors(
        shared_id=user["shared_id"],
        search=search.strip()[:100]
    )

    return jsonify({
        "status": "success",
        "total_visitors": len(visitors),
        "visitors": visitors
    }), 200

