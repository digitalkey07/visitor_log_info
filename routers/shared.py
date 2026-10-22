
from flask import Blueprint, render_template, abort
from contextlib import closing
from database import get_db

share_bp = Blueprint("share", __name__)


@share_bp.route("/share/<string:shared_id>", methods=["GET"])
def open_share_link(shared_id):

    with closing(get_db()) as conn:
        user = conn.execute("""
            SELECT id, username, shared_id
            FROM users
            WHERE shared_id = ?
        """, (shared_id,)).fetchone()

    if user is None:
        abort(404, description="Invalid or expired share link")

    return render_template(
        "shared_page.html",
        shared_id=user["shared_id"]
    )
