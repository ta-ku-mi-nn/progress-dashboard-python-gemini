from flask import session

def get_current_user():
    """
    Flaskのセッションから現在のログインユーザー情報を取得します。
    """
    return session.get('user_info', None)