import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import settings

load_dotenv()
PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_RETRY_TIME = settings.RETRY_TIME
ENDPOINT = settings.ENDPOINT
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправляет сообщение."""
    logger.info(f"Начало отправки сообщения: {message}")
    bot_message = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    if not bot_message:
        raise telegram.TelegramError("Сообщение не отправлено")
    else:
        logger.info(f"Сообщение отправлено: {message}")


def get_api_answer(current_timestamp):
    """Выполняет запрос к API."""
    timestamp = current_timestamp or int(time.time())
    params = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params={"from_date": timestamp}
    )
    try:
        homework_statuses = requests.get(**params)
    except Exception as error:
        logger.error(f"Ошибка при запросе к API: {error}")
    else:
        if homework_statuses.status_code != HTTPStatus.OK:
            error_message = "Статус страницы не равен 200"
            raise requests.HTTPError(error_message)
        return homework_statuses.json()


def check_response(response):
    """Проверяет полученный ответ на корректность."""
    logger.info("Ответ от сервера получен")
    homeworks_response = response['homeworks']
    logger.info("Список домашних работ получен")
    if not homeworks_response:
        message_status = ("Отсутствует статус homeworks")
        raise LookupError(message_status)
    if not isinstance(homeworks_response, list):
        message_list = ("Невернй тип входящих данных")
        raise TypeError(message_list)
    if 'homeworks' not in response.keys():
        message_homeworks = 'Ключ "homeworks" отсутствует в словаре'
        raise KeyError(message_homeworks)
    if 'current_date' not in response.keys():
        message_current_date = 'Ключ "current_date" отсутствует в словаре'
        raise KeyError(message_current_date)
    return homeworks_response


def parse_status(homework):
    """Извлекает статус работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = HOMEWORK_VERDICTS[homework_status]
    if not verdict:
        message_verdict = "Такого статуса нет в словаре"
        raise KeyError(message_verdict)
    if homework_status not in HOMEWORK_VERDICTS:
        message_homework_status = "Такого статуса не существует"
        raise KeyError(message_homework_status)
    if "homework_name" not in homework:
        message_homework_name = "Такого имени не существует"
        raise KeyError(message_homework_name)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for token in tokens:
        if token is None:
            logger.critical(f'Отсутствует переменная окружения: {token}')
            return False
    return True


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            else:
                logger.debug('Статус не изменился')
            current_timestamp = current_timestamp
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            try:
                send_message(bot, message)
            except Exception:
                not_send_message = 'Не удалось отправить сообщение об ошибке'
                logging.error(not_send_message)
        finally:
            time.sleep(TELEGRAM_RETRY_TIME)


if __name__ == "__main__":
    logging.basicConfig(
        format=('%(asctime)s'
                '%(name)s'
                '%(levelname)s'
                '%(message)s'
                '%(funcName)s'
                '%(lineno)d'),
        level=logging.INFO,
        filename="program.log",
        filemode="w",
    )
    main()
