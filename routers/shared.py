
from pydoc import describe

from flask import Blueprint, render_template, abort, request
from contextlib import closing
from database import get_db

share_bp = Blueprint("share", __name__)


@share_bp.route("/share/<string:shared_id>/<int:ui>", methods=["GET"])
def open_share_link(shared_id, ui):

    if not shared_id or ui <= 0:
        abort(400, description="Invalid request")

    with closing(get_db()) as conn:
        user = conn.execute("""
            SELECT id, username, shared_id
            FROM users
            WHERE shared_id = ?
        """, (shared_id,)).fetchone()

        if user is None:
            abort(404, description="Invalid or expired share link")

        festival = conn.execute("""
            SELECT *
            FROM uidata
            WHERE id = ?
            LIMIT 1
        """, (ui,)).fetchone()

    if festival is None:
        abort(404, description="UI not found")
    festival = dict(festival)
    return render_template(
        "shared_page.html",
        shared_id=user["shared_id"],
        ui_id=ui,
        festival=festival
    )
@share_bp.route("/ui/<int:id>", methods=["GET"])
def get_ui_data(id):
    with closing(get_db()) as conn:
        festival = conn.execute("""
            SELECT *
            FROM uidata
            WHERE id = ? AND is_active = 1
            LIMIT 1
        """, (id,)).fetchone()

    if festival is None:
        return {"status": "error", "message": "UI not found"}, 404

    return {
        "status": "success",
        **dict(festival)
    }
    