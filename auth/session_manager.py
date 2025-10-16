#!/usr/bin/env python3
"""
セッション管理システム
"""
import uuid
import sqlite3
from typing import Optional
from datetime import datetime, timedelta


class SessionManager:
    """セッション管理クラス"""

    def __init__(self, db_path: str = "users.db"):
        """
        セッション管理システムを初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self.session_duration = timedelta(hours=8)  # セッション有効期間

    def create_session(self, user_id: int) -> str:
        """
        新しいセッションを作成

        Args:
            user_id: ユーザーID

        Returns:
            セッションID
        """
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + self.session_duration

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 既存の有効なセッションを無効化
            cursor.execute('''
                UPDATE sessions SET is_active = 0
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))

            # 新しいセッションを作成
            cursor.execute('''
                INSERT INTO sessions (id, user_id, expires_at)
                VALUES (?, ?, ?)
            ''', (session_id, user_id, expires_at.isoformat()))

            conn.commit()

        return session_id

    def validate_session(self, session_id: str) -> Optional[int]:
        """
        セッションを検証

        Args:
            session_id: セッションID

        Returns:
            有効な場合ユーザーID、無効な場合None
        """
        if not session_id:
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT user_id, expires_at FROM sessions
                WHERE id = ? AND is_active = 1
            ''', (session_id,))

            result = cursor.fetchone()

            if result:
                user_id, expires_at_str = result
                expires_at = datetime.fromisoformat(expires_at_str)

                # セッションの有効期限をチェック
                if datetime.now() < expires_at:
                    return user_id
                # 期限切れセッションを無効化
                self.destroy_session(session_id)

            return None

    def destroy_session(self, session_id: str) -> bool:
        """
        セッションを破棄

        Args:
            session_id: セッションID

        Returns:
            破棄成功時True
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE sessions SET is_active = 0
                WHERE id = ?
            ''', (session_id,))

            conn.commit()
            return cursor.rowcount > 0

    def destroy_user_sessions(self, user_id: int) -> bool:
        """
        ユーザーの全セッションを破棄

        Args:
            user_id: ユーザーID

        Returns:
            破棄成功時True
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE sessions SET is_active = 0
                WHERE user_id = ?
            ''', (user_id,))

            conn.commit()
            return cursor.rowcount > 0

    def extend_session(self, session_id: str) -> bool:
        """
        セッションの有効期限を延長

        Args:
            session_id: セッションID

        Returns:
            延長成功時True
        """
        new_expires_at = datetime.now() + self.session_duration

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE sessions
                SET expires_at = ?
                WHERE id = ? AND is_active = 1
            ''', (new_expires_at.isoformat(), session_id))

            conn.commit()
            return cursor.rowcount > 0

    def cleanup_expired_sessions(self) -> int:
        """
        期限切れセッションをクリーンアップ

        Returns:
            削除されたセッション数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE sessions
                SET is_active = 0
                WHERE expires_at < ? AND is_active = 1
            ''', (datetime.now().isoformat(),))

            conn.commit()
            return cursor.rowcount

    def get_active_sessions_count(self, user_id: int) -> int:
        """
        ユーザーのアクティブセッション数を取得

        Args:
            user_id: ユーザーID

        Returns:
            アクティブセッション数
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COUNT(*) FROM sessions
                WHERE user_id = ? AND is_active = 1 AND expires_at > ?
            ''', (user_id, datetime.now().isoformat()))

            return cursor.fetchone()[0]
