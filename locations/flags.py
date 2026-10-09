import logging

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage


logger = logging.getLogger(__name__)


def flag_filename(value):
    """Принимаем имя файла и прежний формат flags/имя, сохраняем только имя."""
    filename = value.strip().removeprefix("flags/")
    if not filename or filename in {".", ".."} or any(char in filename for char in "/\\?#%"):
        raise ValueError("Enter only the flag filename, e.g. kosovo.png.")
    return filename


def flag_image_url(value):
    """Проверяем исходную статику локально, а на проде — манифест и собранный файл."""
    path = f"flags/{flag_filename(value)}"
    if settings.DEBUG:
        exists = bool(finders.find(path))
    else:
        # Отсутствие записи в манифесте само по себе вызывает ValueError.
        exists = staticfiles_storage.exists(staticfiles_storage.stored_name(path))
    if not exists:
        raise ValueError(f"Flag image not found: {path}")
    return staticfiles_storage.url(path)


def safe_flag_image_url(value):
    """Недоступный флаг не должен мешать отображению страницы."""
    if not value:
        return ""
    try:
        return flag_image_url(value)
    except (ValueError, OSError):
        logger.warning("Custom flag unavailable: %s", value, exc_info=True)
        return ""
