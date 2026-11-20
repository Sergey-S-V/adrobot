from dataclasses import dataclass
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

Payload = dict[str, Any]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ADROBOT_", env_file=None)
    database_url: str = "postgresql+psycopg://adrobot:adrobot@127.0.0.1:55432/adrobot"
    keitaro_base_url: str = "https://keitaro.invalid"
    keitaro_api_key: str = ""


@dataclass
class AppError(Exception):
    message: str
    status: int = 400


class Keitaro:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.client = httpx.Client(
            base_url=settings.keitaro_base_url.rstrip("/") + "/admin_api/v1/",
            headers={"Api-Key": settings.keitaro_api_key},
            transport=transport,
            timeout=30,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self.client.request(method, path.lstrip("/"), **kwargs)
        except httpx.RequestError as exc:
            raise AppError(
                "Нет связи с Keitaro. Проверьте результат в Keitaro перед повтором записи.", 502
            ) from exc
        if response.is_error:
            raise AppError(f"Keitaro вернул HTTP {response.status_code}.", 502)
        try:
            return response.json()
        except ValueError as exc:
            raise AppError("Keitaro вернул некорректный ответ.", 502) from exc

    def close(self) -> None:
        self.client.close()
