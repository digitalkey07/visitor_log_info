from flask import  Blueprint, request, jsonify, render_template
from database import get_db
from utils.validator import validate_token


admin_bp = Blueprint('admin',__name__)

#======================================
#ADMIN PAGE
#======================================
@admin_bp.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not token:
            return jsonify({"error": "Invalid request"}), 405
        tokenData = validate_token(token)
        if not tokenData:
            return jsonify({"error": "Invalid or expired token"}), 403
        else:
            
            with get_db() as conn:
                user = conn.execute("""
                                    SELECT id,username,user_type FROM users WHERE id = ? AND user_type = 'admin'
                                    """,(tokenData["user_id"],)).fetchone()
                if not user:
                    return jsonify({"error": "Unauthorized access"}), 403
                logs = conn.execute("""
                    SELECT id, ip_address, latitude, longitude, accuracy, page_path, visited_at,
                        device_type, browser, operating_system
                    FROM visitor_logs
                    ORDER BY id DESC
                    LIMIT 200
                """).fetchall()
            return render_template("admin.html", logs=logs)
    return jsonify({"error": "Invalid request method"}), 405   