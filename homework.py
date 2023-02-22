import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
import json.decoder

from exceptions import APIRequestException, APIResponseException,\
    DecodeJSONException, MessageDeliveryException,\
    ProgramCrashException


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


def check_tokens():
    """Проверка учетных данных в окружении."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщения в Телеграм по ID."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Cообщение "{message}" было оправлено')
    except Exception:
        logging.error(f'Cообщение "{message}" не отправлено.')
        raise MessageDeliveryException(
            f'Ваше сообщение "{message}" не оправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            logging.error('Ошибка сервера')
            raise APIResponseException('Ошибка сервера')
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise APIRequestException(f'Ошибка при запросе к API: {error}')
    try:
        return response.json()
    except json.decoder.JSONDecodeError:
        raise DecodeJSONException('Ошибка форматирования ответа')


def check_response(response):
    """Проверка ответ API на соответствие документации."""
    if 'homeworks' not in response:
        logging.error('Отсутствует ключ homeworks')
        raise TypeError('Отсутствует ключ homeworks')
    if not isinstance(response, dict):
        logging.error(f'Ошибка в типе ответа API: {response}')
        raise TypeError(f'Ошибка в типе ответа API: {response}')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        logging.error(f'Ошибка в типе ответа API: {response}')
        raise TypeError(f'Ошибка в типе ответа API: {response}')
    homework = homeworks[0]
    return homework


def parse_status(homework):
    """Анализ ответа."""
    if 'homework_name' not in homework:
        logging.error('Отсутствует ключ homework_name')
        raise KeyError('Отсутствует ключ homework_name')
    if 'status' not in homework:
        logging.error('Отсутствует ключ homework_status')
        raise KeyError('Отсутствует ключ homework_status')
    if not isinstance(homework, dict):
        logging.error(f'Ошибка в типе ответа API: {homework}')
        raise TypeError(f'Ошибка в типе ответа API: {homework}')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if not verdict:
        logging.error(f'Неизвестный статус домашней работы: {homework_status}')
        raise KeyError(
            f'Неизвестный статус домашней работы: {homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Отсутствуют учетные данные (токен)')
        sys.exit('Отсутствуют учетные данные (токен)')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    previous_status = ''

    while True:
        timestamp = int(time.time())
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response['homeworks']:
                current_status = response['homeworks'][0]
                if previous_status != current_status['status']:
                    previous_status = current_status['status']
                    message = parse_status(current_status)
                    send_message(bot, message)
                else:
                    logging.debug('Отсутсвие новых статусов')
        except ProgramCrashException as error:
            logging.error(f'Сбой в работе программы: {error}')
            send_message(bot, f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO)
    main()
