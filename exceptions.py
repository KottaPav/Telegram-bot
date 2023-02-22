class APIRequestException(Exception):
    """Ошибка при запросе к API."""
    pass


class APIResponseException(Exception):
    """Ошибка ответа API."""
    pass


class DecodeJSONException(Exception):
    """Ошибка форматирования ответа."""
    pass


class MessageDeliveryException(Exception):
    """Сообщение не доставлено."""
    pass


class ProgramCrashException(Exception):
    """Сбой в работе программы."""
    pass
