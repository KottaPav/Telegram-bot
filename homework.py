import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def check_tokens():
    """Проверка учетных данных в окружении."""
    if all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    logging.critical('Отсутствуют учетные данные (токен)')
    sys.exit('Отсутствуют учетные данные (токен)')


def send_message(bot, message):
    """Отправка сообщения в Телеграм по ID."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Cообщение "{message}" было оправлено')
    except Exception:
        logging.error(f'Cообщение "{message}" не отправлено.')
        raise Exception(f'Ваше сообщение "{message}" не оправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            logging.error('Ошибка сервера')
            raise Exception('Ошибка сервера')
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise Exception(f'Ошибка при запросе к API: {error}')
    return response.json()


def check_response(response):
    """Проверка ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error(f'Ошибка в типе ответа API: {response}')
        raise TypeError(f'Ошибка в типе ответа API: {response}')
    if not isinstance(response.get('homeworks'), list):
        logging.error(f'Ошибка в типе ответа API: {response}')
        raise TypeError(f'Ошибка в типе ответа API: {response}')
    if 'homeworks' not in response:
        raise Exception('Пустой ответ от API')
    try:
        homework = response.get('homeworks')[0]
    except KeyError:
        logging.error('Отсутствует ключ homeworks')
        raise KeyError('Отсутствует ключ homeworks')
    return homework


def parse_status(homework):
    """Анализ ответа"""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if not homework_name:
        logging.error('Ответ API не содержит ключа "homework_name"')
        raise Exception('Ответ API не содержит ключа "homework_name"')
    if not verdict:
        logging.error(f'Неизвестный статус домашней работы: {homework_status}')
        raise Exception(
            f'Неизвестный статус домашней работы: {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    previous_status = ''

    while True:
        timestamp = int(time.time())
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response.get('homeworks'):
                current_status = response.get('homeworks')[0]
                if previous_status != current_status.get('status'):
                    previous_status = current_status.get('status')
                    message = parse_status(current_status)
                    send_message(bot, message)
                else:
                    logging.debug('Отсутсвие новых статусов')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            send_message(bot, f'Сбой в работе программы: {error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
