"""
Logger de conversaciones para el piloto.
Guarda cada interaccion usuario-bot en la tabla conversation_log.
"""

from .db import db_client


def log_conversation(session_id: str, user_message: str, bot_response: str = None,
                     intent: str = None, confidence: float = None):
    """Guarda un mensaje de conversacion en la BD."""
    if not db_client:
        return
    conn = db_client.get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO conversation_log (session_id, user_message, bot_response, intent, confidence)
               VALUES (%s, %s, %s, %s, %s)""",
            (session_id, user_message, bot_response, intent, confidence)
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error logging conversation: {e}")
        conn.rollback()
    finally:
        conn.close()


def log_feedback(session_id: str, rating: int, comment: str = None,
                 last_user_message: str = None, last_bot_response: str = None):
    """Guarda feedback de un usuario en la BD."""
    if not db_client:
        return
    conn = db_client.get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO feedback (session_id, rating, comment, last_user_message, last_bot_response)
               VALUES (%s, %s, %s, %s, %s)""",
            (session_id, rating, comment, last_user_message, last_bot_response)
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error logging feedback: {e}")
        conn.rollback()
    finally:
        conn.close()
