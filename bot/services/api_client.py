from typing import Any, Dict, Optional

import requests  # библиотека для HTTP запросов

from config import BACKEND_URL


class HabitTrackerApiClient:
    """
    Клиент для отправки HTTP запросов к FastAPI backend.

    Инкапсулирует все запросы к API в одном месте.
    Вместо того чтобы писать requests.post(...) везде по коду,
    используем api_client.login_user(...).
    """

    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url

    @staticmethod
    def _safe_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return {}

    @staticmethod
    def _build_auth_headers(access_token: str) -> Dict[str, str]:
        """
        Строит заголовок авторизации.
        Все защищённые endpoints требуют: Authorization: Bearer <token>
        """
        return {"Authorization": f"Bearer {access_token}"}

    def register_user(
        self,
        telegram_id: int,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        POST /auth/register — регистрация пользователя.

        requests.post(url, json={...}) отправляет JSON в теле запроса.
        Возвращаем словарь с status_code и data для обработки в хендлере.
        """
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={
                "telegram_id": telegram_id,
                "username": username,
                "password": password,
            },
            timeout=10,  # если backend не ответил за 10 сек → ошибка
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def login_user(
        self,
        telegram_id: int,
        password: str,
    ) -> Dict[str, Any]:
        """POST /auth/login — вход. При успехе возвращает JWT токен."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"telegram_id": telegram_id, "password": password},
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def get_all_habits(self, access_token: str) -> Dict[str, Any]:
        """
        GET /habits — список привычек.
        Передаём токен в заголовке для авторизации.
        """
        response = requests.get(
            f"{self.base_url}/habits",
            headers=self._build_auth_headers(access_token),
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def create_habit(
        self,
        access_token: str,
        title: str,
        description: Optional[str] = None,
        target_completions: int = 21,
    ) -> Dict[str, Any]:
        """POST /habits — создать привычку."""
        response = requests.post(
            f"{self.base_url}/habits",
            headers=self._build_auth_headers(access_token),
            json={
                "title": title,
                "description": description,
                "target_completions": target_completions,
            },
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def update_habit(
        self,
        access_token: str,
        habit_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        target_completions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        PUT /habits/{habit_id} — обновить привычку.
        Собираем только переданные (не None) поля в payload.
        """
        update_payload = {}
        if title is not None:
            update_payload["title"] = title
        if description is not None:
            update_payload["description"] = description
        if target_completions is not None:
            update_payload["target_completions"] = target_completions

        response = requests.put(
            f"{self.base_url}/habits/{habit_id}",
            headers=self._build_auth_headers(access_token),
            json=update_payload,
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def delete_habit(self, access_token: str, habit_id: int) -> Dict[str, Any]:
        """DELETE /habits/{habit_id} — удалить привычку. Ответ 204 = без тела."""
        response = requests.delete(
            f"{self.base_url}/habits/{habit_id}",
            headers=self._build_auth_headers(access_token),
            timeout=10,
        )
        return {"status_code": response.status_code}

    def complete_habit_today(
        self,
        access_token: str,
        habit_id: int,
    ) -> Dict[str, Any]:
        """POST /habits/{habit_id}/complete — отметить выполненной."""
        response = requests.post(
            f"{self.base_url}/habits/{habit_id}/complete",
            headers=self._build_auth_headers(access_token),
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def set_notification_time(
        self,
        access_token: str,
        notification_time: Optional[str],
    ) -> Dict[str, Any]:
        """PUT /users/me/notification-time — задать время уведомления."""
        response = requests.put(
            f"{self.base_url}/users/me/notification-time",
            headers=self._build_auth_headers(access_token),
            json={"notification_time": notification_time},
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}

    def get_current_user(self, access_token: str) -> Dict[str, Any]:
        """GET /users/me — профиль пользователя (нужен планировщику)."""
        response = requests.get(
            f"{self.base_url}/users/me",
            headers=self._build_auth_headers(access_token),
            timeout=10,
        )
        return {"status_code": response.status_code, "data": self._safe_json(response)}


# Один глобальный экземпляр — все хендлеры используют его
# from services.api_client import api_client
api_client = HabitTrackerApiClient()