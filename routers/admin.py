
import json
import re

from flask import Blueprint, render_template, request, jsonify

from database import get_db
from utils.validator import validate_token
from config import USER_TYPE


admin_bp = Blueprint("admin", __name__)


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

def get_admin_from_token():
    data = request.get_json(silent=True) or {}
    token = data.get("token")

    if not token:
        return None, (
            jsonify({
                "status": "error",
                "error": "Login required."
            }),
            401
        )

    token_data = validate_token(token)

    if not token_data or not token_data.get("user_id"):
        return None, (
            jsonify({
                "status": "error",
                "error": "Invalid or expired token."
            }),
            401
        )

    with get_db() as conn:
        admin = conn.execute(
            """
            SELECT id, username, user_type
            FROM users
            WHERE id = ? AND user_type = ?
            """,
            (token_data["user_id"], USER_TYPE)
        ).fetchone()

    if not admin:
        return None, (
            jsonify({
                "status": "error",
                "error": "Admin access required."
            }),
            403
        )

    return dict(admin), None


# ============================================================
# COMMON HELPERS
# ============================================================

def visitor_select_sql():
    return """
        SELECT
            v.id,
            v.ip_address,
            v.user_agent,
            v.page_path,
            v.visited_at,
            v.device_type,
            v.browser,
            v.operating_system,
            v.latitude,
            v.longitude,
            v.accuracy,
            v.share_id,
            v.mac_address,
            u.username AS referrer_username
        FROM visitor_logs AS v
        LEFT JOIN users AS u
            ON u.shared_id = v.share_id
    """


def validate_color(value, default):
    if value is None or value == "":
        return default

    if not isinstance(value, str):
        raise ValueError("Invalid color value.")

    value = value.strip()

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError(
            "Colors must use hexadecimal format, e.g. #b83280."
        )

    return value


def prepare_festival_data(data):
    festival_name = data.get("festival_name")
    title = data.get("title")

    if not isinstance(festival_name, str) or not festival_name.strip():
        raise ValueError("Festival name is required.")

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Festival title is required.")

    festival_name = festival_name.strip()
    title = title.strip()

    if len(festival_name) > 100:
        raise ValueError("Festival name cannot exceed 100 characters.")

    if len(title) > 200:
        raise ValueError("Title cannot exceed 200 characters.")

    text_fields = [
        "subtitle",
        "eyebrow",
        "message",
        "image_path",
        "download_text",
        "download_button_text",
        "surprise_button_text",
        "footer_text"
    ]

    result = {
        "festival_name": festival_name,
        "title": title
    }

    for field in text_fields:
        value = data.get(field, "")

        if value is None:
            value = ""

        if not isinstance(value, str):
            raise ValueError(f"{field} must be text.")

        result[field] = value.strip()

    # Wishes must be a JSON array of strings.
    wishes = data.get("wishes", [])

    if isinstance(wishes, str):
        try:
            wishes = json.loads(wishes)
        except json.JSONDecodeError:
            raise ValueError("Wishes must be a valid JSON array.")

    if not isinstance(wishes, list):
        raise ValueError("Wishes must be a list.")

    if not all(isinstance(item, str) for item in wishes):
        raise ValueError("Every wish must be text.")

    result["wishes"] = json.dumps(
        wishes,
        ensure_ascii=False
    )

    result["background_color"] = validate_color(
        data.get("background_color"),
        "#fff4f7"
    )

    result["card_color"] = validate_color(
        data.get("card_color"),
        "#ffffff"
    )

    result["text_color"] = validate_color(
        data.get("text_color"),
        "#333333"
    )

    result["theme_color"] = validate_color(
        data.get("theme_color"),
        "#b83280"
    )

    is_active = data.get("is_active", 1)

    if isinstance(is_active, bool):
        is_active = int(is_active)

    if is_active not in (0, 1):
        raise ValueError("is_active must be 0 or 1.")

    result["is_active"] = is_active

    return result


def get_festival_by_id(conn, festival_id):
    row = conn.execute(
        """
        SELECT *
        FROM uidata
        WHERE id = ?
        """,
        (festival_id,)
    ).fetchone()

    return dict(row) if row else None


# ============================================================
# ADMIN PAGE
# ============================================================

@admin_bp.route("/admin", methods=["GET"])
def admin():
    return render_template("admin.html")


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@admin_bp.route("/admin/dashboard", methods=["POST"])
def admin_dashboard():
    admin_user, error = get_admin_from_token()

    if error:
        return error

    with get_db() as conn:
        total_visitors = conn.execute(
            "SELECT COUNT(*) FROM visitor_logs"
        ).fetchone()[0]

        total_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE user_type = 'user'"
        ).fetchone()[0]

        total_admins = conn.execute(
            "SELECT COUNT(*) FROM users WHERE user_type = ?",
            (USER_TYPE,)
        ).fetchone()[0]

        total_festivals = conn.execute(
            "SELECT COUNT(*) FROM uidata"
        ).fetchone()[0]

        active_festivals = conn.execute(
            "SELECT COUNT(*) FROM uidata WHERE is_active = 1"
        ).fetchone()[0]

        latest_visitors = conn.execute(
            visitor_select_sql()
            + " ORDER BY v.id DESC LIMIT 10"
        ).fetchall()

    return jsonify({
        "status": "success",
        "admin": admin_user,
        "statistics": {
            "total_visitors": total_visitors,
            "total_users": total_users,
            "total_admins": total_admins,
            "total_festivals": total_festivals,
            "active_festivals": active_festivals
        },
        "latest_visitors": [
            dict(row) for row in latest_visitors
        ]
    })


# ============================================================
# USERS LIST
# ============================================================

@admin_bp.route("/admin/users", methods=["POST"])
def admin_users():
    admin_user, error = get_admin_from_token()

    if error:
        return error

    with get_db() as conn:
        users = conn.execute(
            """
            SELECT id, username, user_type, shared_id
            FROM users
            ORDER BY id DESC
            """
        ).fetchall()

    return jsonify({
        "status": "success",
        "users": [dict(row) for row in users]
    })


# ============================================================
# ALL VISITORS
# ============================================================

@admin_bp.route("/admin/visitors", methods=["POST"])
def admin_visitors():
    admin_user, error = get_admin_from_token()

    if error:
        return error

    with get_db() as conn:
        visitors = conn.execute(
            visitor_select_sql()
            + " ORDER BY v.id DESC LIMIT 200"
        ).fetchall()

    return jsonify({
        "status": "success",
        "visitors": [dict(row) for row in visitors]
    })


# ============================================================
# VISITORS BELONGING TO A USER
# ============================================================

@admin_bp.route(
    "/admin/users/<int:user_id>/visitors",
    methods=["POST"]
)
def admin_user_visitors(user_id):
    admin_user, error = get_admin_from_token()

    if error:
        return error

    with get_db() as conn:
        user = conn.execute(
            """
            SELECT id, username, shared_id
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        if not user:
            return jsonify({
                "status": "error",
                "error": "User not found."
            }), 404

        visitors = conn.execute(
            visitor_select_sql()
            + """
            WHERE v.share_id = ?
            ORDER BY v.id DESC
            LIMIT 200
            """,
            (user["shared_id"],)
        ).fetchall()

    return jsonify({
        "status": "success",
        "user": dict(user),
        "visitors": [dict(row) for row in visitors]
    })


# ============================================================
# FESTIVAL MANAGEMENT
# POST /admin/festivals
#
# action=list
# action=create
# action=update
# ============================================================

@admin_bp.route("/admin/festivals", methods=["POST"])
def admin_festivals():
    admin_user, error = get_admin_from_token()

    if error:
        return error

    data = request.get_json(silent=True) or {}
    action = data.get("action")

    # --------------------------------------------------------
    # LIST FESTIVALS
    # --------------------------------------------------------

    if action == "list":
        with get_db() as conn:
            festivals = conn.execute(
                """
                SELECT *
                FROM uidata
                ORDER BY id DESC
                """
            ).fetchall()

        return jsonify({
            "status": "success",
            "festivals": [dict(row) for row in festivals]
        })

    # --------------------------------------------------------
    # CREATE FESTIVAL
    # --------------------------------------------------------

    if action == "create":
        try:
            festival = prepare_festival_data(data)
        except ValueError as exc:
            return jsonify({
                "status": "error",
                "error": str(exc)
            }), 400

        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO uidata (
                    festival_name,
                    title,
                    subtitle,
                    eyebrow,
                    message,
                    image_path,
                    download_text,
                    download_button_text,
                    surprise_button_text,
                    wishes,
                    footer_text,
                    background_color,
                    card_color,
                    text_color,
                    theme_color,
                    is_active
                )
                VALUES (
                    :festival_name,
                    :title,
                    :subtitle,
                    :eyebrow,
                    :message,
                    :image_path,
                    :download_text,
                    :download_button_text,
                    :surprise_button_text,
                    :wishes,
                    :footer_text,
                    :background_color,
                    :card_color,
                    :text_color,
                    :theme_color,
                    :is_active
                )
                """,
                festival
            )

            festival_id = cursor.lastrowid
            created = get_festival_by_id(conn, festival_id)

        return jsonify({
            "status": "success",
            "message": "Festival created successfully.",
            "festival": created
        }), 201

    # --------------------------------------------------------
    # UPDATE FESTIVAL
    # --------------------------------------------------------

    if action == "update":
        festival_id = data.get("id")

        if (
            isinstance(festival_id, bool)
            or not isinstance(festival_id, int)
            or festival_id < 1
        ):
            return jsonify({
                "status": "error",
                "error": "A valid festival ID is required."
            }), 400

        try:
            festival = prepare_festival_data(data)
        except ValueError as exc:
            return jsonify({
                "status": "error",
                "error": str(exc)
            }), 400

        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM uidata WHERE id = ?",
                (festival_id,)
            ).fetchone()

            if not existing:
                return jsonify({
                    "status": "error",
                    "error": "Festival not found."
                }), 404

            conn.execute(
                """
                UPDATE uidata
                SET
                    festival_name = :festival_name,
                    title = :title,
                    subtitle = :subtitle,
                    eyebrow = :eyebrow,
                    message = :message,
                    image_path = :image_path,
                    download_text = :download_text,
                    download_button_text = :download_button_text,
                    surprise_button_text = :surprise_button_text,
                    wishes = :wishes,
                    footer_text = :footer_text,
                    background_color = :background_color,
                    card_color = :card_color,
                    text_color = :text_color,
                    theme_color = :theme_color,
                    is_active = :is_active,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """,
                {**festival, "id": festival_id}
            )

            updated = get_festival_by_id(conn, festival_id)

        return jsonify({
            "status": "success",
            "message": "Festival updated successfully.",
            "festival": updated
        })

    return jsonify({
        "status": "error",
        "error": "Invalid action."
    }), 400


# ============================================================
# TOGGLE FESTIVAL / DELETE FESTIVAL
# POST /admin/festivals/<festival_id>
#
# action=toggle
# action=delete
# ============================================================

@admin_bp.route(
    "/admin/festivals/<int:festival_id>",
    methods=["POST"]
)
def admin_festival_action(festival_id):
    admin_user, error = get_admin_from_token()

    if error:
        return error

    data = request.get_json(silent=True) or {}
    action = data.get("action")

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM uidata WHERE id = ?",
            (festival_id,)
        ).fetchone()

        if not existing:
            return jsonify({
                "status": "error",
                "error": "Festival not found."
            }), 404

        # ----------------------------------------------------
        # ACTIVATE / DEACTIVATE
        # ----------------------------------------------------

        if action == "toggle":
            is_active = data.get("is_active")

            if isinstance(is_active, bool):
                is_active = int(is_active)

            if is_active not in (0, 1):
                return jsonify({
                    "status": "error",
                    "error": "is_active must be 0 or 1."
                }), 400

            conn.execute(
                """
                UPDATE uidata
                SET
                    is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (is_active, festival_id)
            )

            festival = get_festival_by_id(conn, festival_id)

            return jsonify({
                "status": "success",
                "message": (
                    "Festival activated successfully."
                    if is_active
                    else "Festival deactivated successfully."
                ),
                "festival": festival
            })

        # ----------------------------------------------------
        # DELETE FESTIVAL
        # ----------------------------------------------------

        if action == "delete":
            conn.execute(
                "DELETE FROM uidata WHERE id = ?",
                (festival_id,)
            )

            return jsonify({
                "status": "success",
                "message": "Festival deleted successfully."
            })

    return jsonify({
        "status": "error",
        "error": "Invalid action."
    }), 400
