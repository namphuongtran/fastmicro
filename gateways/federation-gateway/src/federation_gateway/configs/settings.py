from settings.settings_manager import SettingsManager

 # Initialize settings
def get_settings() -> SettingsManager:
    """Get application settings singleton."""
    return SettingsManager()