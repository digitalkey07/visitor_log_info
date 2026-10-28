from math import e
import re

from flask import  Blueprint, request, jsonify
import ipaddress
from datetime import datetime, timezone
from database import get_db
from config import USER_TYPE

track_bp = Blueprint('track',__name__)


def detect_device(ua):
    ua = ua.lower()
    print(ua)

    if "ipad" in ua or "tablet" in ua:
        device = "Tablet"
    elif any(x in ua for x in ("mobile", "android", "iphone")):
        device = "Mobile"
    else:
        device = "Desktop / Unknown"

    if "edg/" in ua:
        browser = "Microsoft Edge"
    elif "opr/" in ua:
        browser = "Opera"
    elif "firefox/" in ua:
        browser = "Firefox"
    elif "chrome/" in ua and "chromium" not in ua:
        browser = "Chrome"
    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"
    else:
        browser = "Other / Unknown"

    if "windows" in ua:
        os_name = "Windows"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS / iPadOS"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Other / Unknown"

    return device, browser, os_name
#======================================
#TRACKING API
#======================================
@track_bp.route("/track", methods=["POST"])
def track_visitor():
    data = request.get_json(silent=True) or {}

    # --------------------------------------------------
    # 1. SHARED ID REQUIRED
    # --------------------------------------------------

    shared_id = data.get("shared_id")
    visitor_id = data.get("visitor_id")

    if not isinstance(shared_id, str) or not shared_id.strip():
        return jsonify({
            "status": "error",
            "message": "Shared ID is required"
        }), 400

    shared_id = shared_id.strip()

    # --------------------------------------------------
    # 2. CHECK SHARE ID IN DATABASE
    # --------------------------------------------------

    with get_db() as conn:
        owner = conn.execute("""
            SELECT id
            FROM users
            WHERE shared_id = ?
              AND user_type != ?
            LIMIT 1
        """, (shared_id, USER_TYPE)).fetchone()

        if owner is None:
            return jsonify({
                "status": "error",
                "message": "Invalid share link"
            }), 404

        # --------------------------------------------------
        # 3. VALIDATE PAGE PATH
        # --------------------------------------------------

        page_path = data.get("page_path", "/")

        if (
            not isinstance(page_path, str)
            or not page_path.startswith("/")
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid page path"
            }), 400

        page_path = page_path.split("?", 1)[0][:500]

        # --------------------------------------------------
        # 4. GET IP ADDRESS
        # --------------------------------------------------
        print("Remote Address:", request.remote_addr)
        print("X-Forwarded-For:", request.headers.get("X-Forwarded-For"))
        print("CF-Connecting-IP:", request.headers.get("CF-Connecting-IP"))
        print("X-Real-IP:", request.headers.get("X-Real-IP"))
        ip = request.headers.get("X-Real-IP")

        if ip:
            try:
                ip = str(ipaddress.ip_address(ip))
            except ValueError:
                ip = None

        # --------------------------------------------------
        # 5. DEVICE / BROWSER INFORMATION
        # --------------------------------------------------

        ua = request.headers.get("User-Agent", "")[:500]
        device, browser, os_name = detect_device(ua)

        visited_at = datetime.now(timezone.utc).isoformat()

        # --------------------------------------------------
        # 6. SAVE VISITOR UNDER THIS SHARE OWNER
        # --------------------------------------------------

        try:
            visitor_id = int(visitor_id) if visitor_id is not None else 0
        except (ValueError, TypeError):
            visitor_id = 0

        exist_visitor = None
        if visitor_id >0:
            exist_visitor = conn.execute("""
                SELECT id, ip_address
                FROM visitor_logs
                WHERE share_id = ? AND id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (shared_id, visitor_id)).fetchone()

        if exist_visitor is not None:
            visitor_id = exist_visitor["id"]
            conn.execute("""
                UPDATE visitor_logs
                SET ip_address = ?,
                    user_agent = ?,
                    page_path = ?,
                    visited_at = ?,
                    device_type = ?,
                    browser = ?,
                    operating_system = ?
                    WHERE id = ?
                    AND share_id = ?
            """, (
                ip,
                ua,
                page_path,
                visited_at,
                device,
                browser,
                os_name,
                visitor_id,
                shared_id
            ))

            action = "updated"

        

        else:
            cursor = conn.execute("""
            INSERT INTO visitor_logs (
                ip_address,
                user_agent,
                page_path,
                visited_at,
                device_type,
                browser,
                operating_system,
                share_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ip,
                ua,
                page_path,
                visited_at,
                device,
                browser,
                os_name,
                shared_id
            ))

            visitor_id = cursor.lastrowid
            action = "inserted"

            return jsonify({
            "status": "success",
            "message": "Visitor recorded successfully",
            "visitor_id": visitor_id,
            "action": action
            }), 200



#======================================
#SAVE LOCATION API
#======================================
@track_bp.route("/save-location", methods=["POST"])
def save_location():
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({
            "status": "error",
            "message": "No data provided"
        }), 400

    visitor_id = data.get("id")
    shared_id = data.get("shared_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    accuracy = data.get("accuracy")

    # ------------------------------------------
    # 1. REQUIRED FIELDS
    # ------------------------------------------

    if not isinstance(shared_id, str) or not shared_id.strip():
        return jsonify({
            "status": "error",
            "message": "Shared ID is required"
        }), 400

    shared_id = shared_id.strip()

    if visitor_id is None:
        return jsonify({
            "status": "error",
            "message": "Visitor ID is required"
        }), 400

    try:
        visitor_id = int(visitor_id)
        latitude = float(latitude)
        longitude = float(longitude)

        if accuracy is not None:
            accuracy = float(accuracy)

        if not (-90 <= latitude <= 90):
            raise ValueError()

        if not (-180 <= longitude <= 180):
            raise ValueError()

        if accuracy is not None and accuracy < 0:
            raise ValueError()

    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Invalid location data"
        }), 400

    # ------------------------------------------
    # 2. VERIFY SHARE ID AND VISITOR OWNERSHIP
    # ------------------------------------------

    with get_db() as conn:
        owner = conn.execute("""
            SELECT id
            FROM users
            WHERE shared_id = ?
            LIMIT 1
        """, (shared_id,)).fetchone()

        if owner is None:
            return jsonify({
                "status": "error",
                "message": "Invalid shared ID"
            }), 404

        visitor = conn.execute("""
            SELECT id
            FROM visitor_logs
            WHERE id = ?
              AND share_id = ?
        """, (visitor_id, shared_id)).fetchone()

        if visitor is None:
            return jsonify({
                "status": "error",
                "message": "Visitor does not belong to this share link"
            }), 403

        # ------------------------------------------
        # 3. UPDATE LOCATION
        # ------------------------------------------

        conn.execute("""
            UPDATE visitor_logs
            SET latitude = ?,
                longitude = ?,
                accuracy = ?
            WHERE id = ?
              AND share_id = ?
        """, (
            latitude,
            longitude,
            accuracy,
            visitor_id,
            shared_id
        ))

    return jsonify({
        "status": "success",
        "message": "Location saved successfully",
        "visitor_id": visitor_id
    }), 200
