from math import e
import re

from flask import  Blueprint, request, jsonify
import ipaddress
from datetime import datetime, timezone
from database import get_db

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

    # Frontend se page path
    page_path = data.get("page_path", "/")

    if not isinstance(page_path, str) or not page_path.startswith("/"):
        return jsonify({"error": "Invalid page path"}), 400

    # Query parameters remove karo
    page_path = page_path.split("?", 1)[0][:500]

    # Client IP
    ip = request.headers.get("CF-Connecting-IP", "").strip()

    if ip:
        try:
            ip = str(ipaddress.ip_address(ip))
        except ValueError:
            ip = None
    else:
        ip = request.remote_addr

    # Browser aur device information
    ua = request.headers.get("User-Agent", "")[:500]
    device, browser, os_name = detect_device(ua)

    visited_at = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:

        # IP ke basis par existing record check
        exist_user = conn.execute("""
            SELECT id
            FROM visitor_logs
            WHERE ip_address = ?
            LIMIT 1
        """, (ip,)).fetchone()

        if exist_user:
            # Existing visitor update
            visitor_id = exist_user["id"]

            conn.execute("""
                UPDATE visitor_logs
                SET visited_at = ?,
                    user_agent = ?,
                    page_path = ?,
                    device_type = ?,
                    browser = ?,
                    operating_system = ?
                WHERE id = ?
            """, (
                visited_at,
                ua,
                page_path,
                device,
                browser,
                os_name,
                visitor_id
            ))

            message = "Existing visitor data updated"

        else:
            # New visitor insert
            cursor = conn.execute("""
                INSERT INTO visitor_logs (
                    ip_address,
                    user_agent,
                    page_path,
                    visited_at,
                    device_type,
                    browser,
                    operating_system
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ip,
                ua,
                page_path,
                visited_at,
                device,
                browser,
                os_name
            ))

            # Naye record ki ID
            visitor_id = cursor.lastrowid

            message = "New visitor data inserted"

    return jsonify({
        "status": "success",
        "message": message,
        "visitor_id": visitor_id
    }), 201



#======================================
#SAVE LOCATION API
#======================================
@track_bp.route("/save-location",methods=["POST"])
def save_location():
    data = request.get_json(silent=True) or {}
    print("= "*10 )
    print("Received Data: ", data)
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    id = data.get("id")
    latitude = data.get("latitude","")
    longitude = data.get("longitude","")
    accuracy = data.get("accuracy")
    map_link = data.get("mapLink","")
    
    print("= "*10 )
    print("Map Link: ", map_link)
    print("= "*10)
    if not id:
        return jsonify({"error": "Visitor ID is required"}), 400
    if not latitude or not longitude:
        return jsonify({"error": "Latitude and Longitude are required"}), 400
    with get_db() as conn:
        conn.execute("""
                     UPDATE visitor_logs SET latitude = ?,longitude = ?, accuracy = ? WHERE id = ?
                     """,(latitude,longitude,accuracy,id))

    
    return jsonify({
        "status":"success",
        "message":"save location"
       
    })