
from flask import Blueprint, render_template, request, jsonify
from database import get_db
from utils.validator import validate_token
from config import USER_TYPE

admin_bp = Blueprint("admin", __name__)


def get_admin_from_token():
    """Token validate karke database se current admin verify kare."""
    data = request.get_json(silent=True) or {}
    token = data.get("token")

    if not token:
        return None, (jsonify({
            "status": "error",
            "error": "Login required."
        }), 401)

    token_data = validate_token(token)

    if not token_data or not token_data.get("user_id"):
        return None, (jsonify({
            "status": "error",
            "error": "Invalid or expired token."
        }), 401)

    with get_db() as conn:
        admin = conn.execute("""
            SELECT id, username, user_type
            FROM users
            WHERE id = ? AND user_type = ?
        """, (token_data["user_id"], USER_TYPE)).fetchone()

    if not admin:
        return None, (jsonify({
            "status": "error",
            "error": "Admin access required."
        }), 403)

    return dict(admin), None


def visitor_select_sql():
    """Visitor records ke saath referral owner ka username bhi laaye."""
    return """
        SELECT
            v.id,
            v.ip_address,
            v.page_path,
            v.visited_at,
            v.device_type,
            v.browser,
            v.operating_system,
            v.latitude,
            v.longitude,
            v.accuracy,
            v.share_id,
            u.username AS referrer_username
        FROM visitor_logs AS v
        LEFT JOIN users AS u ON u.shared_id = v.share_id
    """

@admin_bp.route("/admin",methods=["GET"])
def admin():
    return render_template("admin.html")

@admin_bp.route("/admin/dashboard", methods=["POST"])
def admin_dashboard():
    admin, error = get_admin_from_token()
    if error:
        return error

    with get_db() as conn:
        total_users = conn.execute("""
            SELECT COUNT(*) AS total
            FROM users
            WHERE user_type != ?
        """, (USER_TYPE,)).fetchone()["total"]

        total_share_links = conn.execute("""
            SELECT COUNT(*) AS total
            FROM users
            WHERE shared_id IS NOT NULL AND TRIM(shared_id) != ''
        """).fetchone()["total"]

        total_visitors = conn.execute("""
            SELECT COUNT(*) AS total
            FROM visitor_logs
        """).fetchone()["total"]

        users = conn.execute("""
            SELECT
                u.id,
                u.username,
                u.user_type,
                u.shared_id,
                COUNT(v.id) AS visitor_count
            FROM users AS u
            LEFT JOIN visitor_logs AS v ON v.share_id = u.shared_id
            WHERE u.user_type != ?
            GROUP BY u.id, u.username, u.user_type, u.shared_id
            ORDER BY visitor_count DESC, u.id DESC
        """, (USER_TYPE,)).fetchall()

        recent_visitors = conn.execute(
            visitor_select_sql() + """
                ORDER BY v.id DESC
                LIMIT 5
            """
        ).fetchall()

    return jsonify({
        "status": "success",
        "username": admin["username"],
        "total_users": total_users,
        "total_share_links": total_share_links,
        "total_visitors": total_visitors,
        "users": [dict(user) for user in users],
        "recent_visitors": [dict(row) for row in recent_visitors]
    }), 200


@admin_bp.route("/admin/users", methods=["POST"])
def get_registered_users():
    admin, error = get_admin_from_token()
    if error:
        return error

    with get_db() as conn:
        users = conn.execute("""
            SELECT
                u.id,
                u.username,
                u.user_type,
                u.shared_id,
                COUNT(v.id) AS visitor_count
            FROM users AS u
            LEFT JOIN visitor_logs AS v ON v.share_id = u.shared_id
            GROUP BY u.id, u.username, u.user_type, u.shared_id
            ORDER BY u.id DESC
        """).fetchall()

    return jsonify({
        "status": "success",
        "username": admin["username"],
        "users": [dict(user) for user in users],
        "total_users": len(users)
    }), 200


@admin_bp.route("/admin/visitors", methods=["POST"])
def get_all_visitors():
    admin, error = get_admin_from_token()
    if error:
        return error

    with get_db() as conn:
        logs = conn.execute(
            visitor_select_sql() + """
                ORDER BY v.id DESC
                LIMIT 1000
            """
        ).fetchall()

    return jsonify({
        "status": "success",
        "username": admin["username"],
        "logs": [dict(row) for row in logs],
        "total_visitors": len(logs)
    }), 200


@admin_bp.route("/admin/users/<int:user_id>/visitors", methods=["POST"])
def get_user_visitors(user_id):
    admin, error = get_admin_from_token()
    if error:
        return error

    with get_db() as conn:
        user = conn.execute("""
            SELECT id, username, shared_id
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

        if not user:
            return jsonify({
                "status": "error",
                "error": "User not found."
            }), 404

        if not user["shared_id"]:
            logs = []
        else:
            logs = conn.execute(
                visitor_select_sql() + """
                    WHERE v.share_id = ?
                    ORDER BY v.id DESC
                    LIMIT 1000
                """,
                (user["shared_id"],)
            ).fetchall()

    return jsonify({
        "status": "success",
        "username": user["username"],
        "shared_id": user["shared_id"],
        "visitors": [dict(row) for row in logs],
        "total_visitors": len(logs)
    }), 200
