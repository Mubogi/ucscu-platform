"""Small shared helpers that several blueprints need."""
from .models import db, Notification


def notify(user_id, kind, text, link=None):
    """Queue an in-app notification for a user."""
    if user_id is None:
        return
    db.session.add(Notification(user_id=user_id, kind=kind, text=text, link=link))
