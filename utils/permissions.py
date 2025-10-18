# utils/permissions.py

def is_admin(user_info):
    """
    ユーザー情報を受け取り、管理者（admin）かどうかを判定します。
    """
    return user_info and user_info.get('role') == 'admin'

def can_access_student(user_info, student_info):
    """
    ログインユーザーが特定の生徒データにアクセスできるかを判定します。
    - 管理者は常にアクセス可能です。
    - 一般ユーザーは、自分がその生徒の「メイン講師」または「サブ講師」である場合にアクセス可能です。

    Args:
        user_info (dict): ログイン中のユーザー情報。
        student_info (dict): 対象生徒の'data'オブジェクト（偏差値や講師名を含む）。
    """
    if not user_info or not student_info:
        return False

    # 管理者なら無条件で許可
    if is_admin(user_info):
        return True

    # 一般ユーザーの場合、担当講師か確認
    username = user_info.get('username')
    if username:
        # メイン講師リストまたはサブ講師リストにユーザー名が含まれているかを確認
        is_main = username in student_info.get('main_instructors', [])
        is_sub = username in student_info.get('sub_instructors', [])
        if is_main or is_sub:
            return True

    return False