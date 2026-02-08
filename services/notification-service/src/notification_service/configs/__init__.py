"""Notification service configuration re-exports."""

from notification_service.configs.settings import (
    NotificationServiceSettings,
    get_settings,
)

__all__ = ["NotificationServiceSettings", "get_settings"]
