from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import logging
from typing import Dict, List
from utils import find_emails, find_phone_numbers, verify_password, setup_logging
import os
if os.getenv('DOCKER_MODE', 'false').lower() == 'true':
    from ssh_client_docker import SSHClient
else:
    from ssh_client import SSHClient
import threading
from queue import Queue
import time

logger = setup_logging()

class VKBot:
    def __init__(self, token: str, group_id: int):
        self.vk = VkApi(token=token)
        self.longpoll = VkBotLongPoll(self.vk, group_id)
        self.vk_api = self.vk.get_api()
        self.ssh_client = SSHClient()
        self.states: Dict[int, str] = {}
        self.temp_data: Dict[int, dict] = {}
        self.task_queue: Dict[int, Queue] = {}
        self.task_results: Dict[int, dict] = {}

    def create_keyboard(self, buttons: list = None, one_time: bool = False):
        keyboard = VkKeyboard(one_time=one_time)
        if buttons:
            for i, button in enumerate(buttons):
                if i > 0 and i % 2 == 0:
                    keyboard.add_line()
                keyboard.add_button(button, color=VkKeyboardColor.PRIMARY)
        return keyboard.get_keyboard()

    def get_main_keyboard(self):
        buttons = [
            "📧 Найти email",
            "📱 Найти телефон",
            "🔐 Проверить пароль",
            "📊 Мониторинг системы",
            "📋 Логи репликации",
            "📮 Список email из БД",
            "📞 Список телефонов из БД"
        ]
        return self.create_keyboard(buttons)

    def get_monitoring_keyboard(self):
        buttons = [
            "📋 Релиз", "ℹ️ Система",
            "⏱️ Uptime", "💾 Диски",
            "🧠 Память", "📊 CPU",
            "👥 Пользователи", "🔑 Входы",
            "⚠️ Критические", "🔄 Процессы",
            "🔌 Порты", "📦 Пакеты",
            "⚙️ Сервисы", "🏠 Главное меню"
        ]
        return self.create_keyboard(buttons)

    def get_apt_choice_keyboard(self):
        buttons = [
            "📋 Все пакеты",
            "🔍 Поиск пакета",
            "📦 Показать результат",
            "↩️ Назад в мониторинг"
        ]
        return self.create_keyboard(buttons)

    def get_result_keyboard(self):
        buttons = [
            "📦 Показать результат",
            "↩️ Назад в мониторинг"
        ]
        return self.create_keyboard(buttons)

    def get_confirm_keyboard(self):
        buttons = [
            "✅ Да, сохранить",
            "❌ Нет, не сохранять"
        ]
        return self.create_keyboard(buttons, one_time=True)

    def process_task_async(self, user_id: int, task_type: str, data: str = None):
        def worker():
            try:
                if task_type == "all_packages":
                    self.send_message(user_id, "🔄 Начался сбор информации о пакетах. Это может занять до 2 минут...", self.get_result_keyboard())
                    result = self.ssh_client.get_apt_list(timeout=120)
                    if result:
                        self.task_results[user_id] = {"type": "all_packages", "data": result}
                        self.send_message(user_id, "✅ Сбор завершен! Нажмите '📦 Показать результат'.", self.get_result_keyboard())
                    else:
                        self.send_message(user_id, "❌ Не удалось получить список пакетов", self.get_monitoring_keyboard())
                        if user_id in self.states:
                            del self.states[user_id]
                elif task_type == "search_package":
                    result = self.ssh_client.get_apt_list(data)
                    if result and result.strip():
                        if len(result) > 4000:
                            result = result[:4000] + "\n... (обрезано)"
                        self.send_message(user_id, f"📦 Информация о пакете '{data}':\n\n{result}", self.get_monitoring_keyboard())
                    else:
                        self.send_message(user_id, f"❌ Пакет '{data}' не найден.", self.get_monitoring_keyboard())
            except Exception as e:
                logger.error(f"Error in async task: {e}")
                self.send_message(user_id, f"❌ Ошибка: {str(e)}", self.get_monitoring_keyboard())
            finally:
                if user_id in self.task_queue:
                    del self.task_queue[user_id]
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        self.task_queue[user_id] = Queue()

    def send_message(self, user_id: int, message: str, keyboard=None):
        try:
            max_length = 4000
            if len(message) > max_length:
                parts = []
                lines = message.split('\n')
                current_part = ""
                for line in lines:
                    if len(current_part) + len(line) + 1 > max_length:
                        parts.append(current_part)
                        current_part = line
                    else:
                        if current_part:
                            current_part += '\n' + line
                        else:
                            current_part = line
                if current_part:
                    parts.append(current_part)
                for i, part in enumerate(parts):
                    if i < len(parts) - 1:
                        self.vk_api.messages.send(user_id=user_id, message=part, random_id=0)
                    else:
                        self.vk_api.messages.send(user_id=user_id, message=part, keyboard=keyboard, random_id=0)
                    time.sleep(0.1)
            else:
                self.vk_api.messages.send(user_id=user_id, message=message, keyboard=keyboard, random_id=0)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    def show_package_result(self, user_id: int):
        if user_id in self.task_results and self.task_results[user_id]["type"] == "all_packages":
            result = self.task_results[user_id]["data"]
            max_length = 4000
            if len(result) > max_length:
                lines = result.split('\n')
                parts = []
                current_part = ""
                for line in lines:
                    if len(current_part) + len(line) + 1 > max_length:
                        parts.append(current_part)
                        current_part = line
                    else:
                        if current_part:
                            current_part += '\n' + line
                        else:
                            current_part = line
                if current_part:
                    parts.append(current_part)
                total_parts = len(parts)
                self.send_message(user_id, f"📦 Список разделен на {total_parts} частей...", self.get_monitoring_keyboard())
                for i, part in enumerate(parts):
                    header = f"📦 Часть {i+1}/{total_parts}:\n\n"
                    self.send_message(user_id, header + part)
                    if i < total_parts - 1:
                        time.sleep(0.3)
                self.send_message(user_id, f"✅ Вывод завершен. Частей: {total_parts}.", self.get_monitoring_keyboard())
            else:
                self.send_message(user_id, f"📦 Установленные пакеты:\n\n{result}", self.get_monitoring_keyboard())
            del self.task_results[user_id]
            return True
        return False

    def handle_command(self, user_id: int, command: str):
        logger.info(f"Handling command from user {user_id}: {command}")
        if command == "🏠 Главное меню":
            self.states[user_id] = None
            self.send_message(user_id, "Главное меню:", self.get_main_keyboard())
            return
        if command == "↩️ Назад в мониторинг":
            self.states[user_id] = "monitoring"
            self.send_message(user_id, "Меню мониторинга:", self.get_monitoring_keyboard())
            return
        if command == "📦 Показать результат":
            if self.show_package_result(user_id):
                self.states[user_id] = "monitoring"
            else:
                self.send_message(user_id, "❌ Нет сохраненных результатов.", self.get_monitoring_keyboard())
                self.states[user_id] = "monitoring"
            return
        if command == "📧 Найти email":
            self.states[user_id] = "waiting_email_text"
            self.send_message(user_id, "Отправьте текст для поиска email:")
            return
        if command == "📱 Найти телефон":
            self.states[user_id] = "waiting_phone_text"
            self.send_message(user_id, "Отправьте текст для поиска номеров телефонов:")
            return
        if command == "🔐 Проверить пароль":
            self.states[user_id] = "waiting_password"
            self.send_message(user_id, "Отправьте пароль для проверки сложности:")
            return
        if command == "📋 Логи репликации":
            self.handle_get_replication_logs(user_id)
            return
        if command == "📮 Список email из БД":
            self.handle_get_emails(user_id)
            return
        if command == "📞 Список телефонов из БД":
            self.handle_get_phones(user_id)
            return
        monitoring_commands = {
            "📋 Релиз": "get_release", "ℹ️ Система": "get_uname",
            "⏱️ Uptime": "get_uptime", "💾 Диски": "get_df",
            "🧠 Память": "get_free", "📊 CPU": "get_mpstat",
            "👥 Пользователи": "get_w", "🔑 Входы": "get_auths",
            "⚠️ Критические": "get_critical", "🔄 Процессы": "get_ps",
            "🔌 Порты": "get_ss", "⚙️ Сервисы": "get_services"
        }
        if command in monitoring_commands:
            self.send_message(user_id, f"⏳ Выполняется '{command}'...")
            method_name = monitoring_commands[command]
            method = getattr(self.ssh_client, method_name)
            try:
                result = method()
                if result and result.strip():
                    if len(result) > 4000:
                        result = result[:4000] + "\n... (обрезано)"
                    self.send_message(user_id, f"Результат {command}:\n{result}")
                else:
                    self.send_message(user_id, f"❌ Не удалось получить информацию.")
            except Exception as e:
                logger.error(f"Error executing {method_name}: {e}")
                self.send_message(user_id, f"❌ Ошибка: {str(e)}")
            return
        if command == "📦 Пакеты":
            if user_id in self.task_results and self.task_results[user_id]["type"] == "all_packages":
                self.show_package_result(user_id)
                self.states[user_id] = "monitoring"
                return
            else:
                if user_id in self.task_queue:
                    self.send_message(user_id, "⏳ Сбор уже выполняется. Нажмите '📦 Показать результат'", self.get_result_keyboard())
                    return
                self.states[user_id] = "waiting_apt_choice"
                self.send_message(user_id, "Выберите режим:\n\n📋 Все пакеты - полный список\n🔍 Поиск пакета - быстрый поиск", self.get_apt_choice_keyboard())
                return
        if command == "📊 Мониторинг системы":
            self.states[user_id] = "monitoring"
            self.send_message(user_id, "Меню мониторинга:", self.get_monitoring_keyboard())
            return

    def handle_get_replication_logs(self, user_id: int):
        self.send_message(user_id, "⏳ Получаю логи репликации...")
        try:
            logs = self.ssh_client.get_replication_logs()
            if logs and logs.strip():
                self.send_message(user_id, f"📋 Логи репликации:\n\n{logs}", self.get_main_keyboard())
            else:
                self.send_message(user_id, "📋 Логи не найдены или репликация не настроена.", self.get_main_keyboard())
        except Exception as e:
            logger.error(f"Error getting replication logs: {e}")
            self.send_message(user_id, f"❌ Ошибка: {str(e)}", self.get_main_keyboard())

    def handle_get_emails(self, user_id: int):
        self.send_message(user_id, "⏳ Получаю список email из БД...")
        try:
            result = self.ssh_client.get_emails_from_db()
            if result and result.strip():
                self.send_message(user_id, f"📮 Сохраненные email:\n\n{result}", self.get_main_keyboard())
            else:
                self.send_message(user_id, "📭 В БД нет сохраненных email.", self.get_main_keyboard())
        except Exception as e:
            logger.error(f"Error getting emails: {e}")
            self.send_message(user_id, f"❌ Ошибка: {str(e)}", self.get_main_keyboard())

    def handle_get_phones(self, user_id: int):
        self.send_message(user_id, "⏳ Получаю список телефонов из БД...")
        try:
            result = self.ssh_client.get_phones_from_db()
            if result and result.strip():
                self.send_message(user_id, f"📞 Сохраненные номера:\n\n{result}", self.get_main_keyboard())
            else:
                self.send_message(user_id, "📭 В БД нет сохраненных номеров.", self.get_main_keyboard())
        except Exception as e:
            logger.error(f"Error getting phones: {e}")
            self.send_message(user_id, f"❌ Ошибка: {str(e)}", self.get_main_keyboard())

    def handle_text(self, user_id: int, text: str):
        state = self.states.get(user_id)
        logger.info(f"Handling text from user {user_id}: '{text}', state: {state}")
        if state == "waiting_save_confirmation":
            if text == "✅ Да, сохранить":
                data = self.temp_data.get(user_id, {})
                data_type = data.get("type")
                items = data.get("items", [])
                if data_type == "email":
                    success, error = self.ssh_client.insert_emails_batch(items)
                    message = f"✅ Сохранено: {success}, ошибок: {error}"
                elif data_type == "phone":
                    success, error = self.ssh_client.insert_phones_batch(items)
                    message = f"✅ Сохранено: {success}, ошибок: {error}"
                else:
                    message = "❌ Неизвестный тип данных"
                self.send_message(user_id, message, self.get_main_keyboard())
                if user_id in self.temp_data:
                    del self.temp_data[user_id]
                self.states[user_id] = None
            elif text == "❌ Нет, не сохранять":
                self.send_message(user_id, "👌 Данные не сохранены.", self.get_main_keyboard())
                if user_id in self.temp_data:
                    del self.temp_data[user_id]
                self.states[user_id] = None
            else:
                self.send_message(user_id, "Используйте кнопки для ответа.", self.get_confirm_keyboard())
            return
        if state == "waiting_apt_choice":
            if text == "📋 Все пакеты":
                if user_id in self.task_queue:
                    self.send_message(user_id, "⏳ Сбор уже выполняется...", self.get_result_keyboard())
                    return
                self.process_task_async(user_id, "all_packages")
                self.states[user_id] = "waiting_for_result"
                return
            elif text == "🔍 Поиск пакета":
                self.states[user_id] = "waiting_package_search"
                self.send_message(user_id, "🔍 Введите название пакета (например: python, nginx, docker):")
                return
            elif text == "📦 Показать результат":
                if self.show_package_result(user_id):
                    self.states[user_id] = "monitoring"
                else:
                    self.send_message(user_id, "❌ Нет сохраненных результатов.", self.get_apt_choice_keyboard())
                return
            elif text == "↩️ Назад в мониторинг":
                self.states[user_id] = "monitoring"
                self.send_message(user_id, "Меню мониторинга:", self.get_monitoring_keyboard())
                return
            else:
                self.send_message(user_id, "Используйте кнопки меню.", self.get_apt_choice_keyboard())
                return
        if state == "waiting_package_search":
            package_name = text.strip()
            if package_name:
                if user_id in self.task_queue:
                    self.send_message(user_id, "⏳ Подождите, выполняется другая операция...")
                    return
                self.send_message(user_id, f"🔍 Ищу пакет '{package_name}'...")
                self.process_task_async(user_id, "search_package", package_name)
                self.states[user_id] = "monitoring"
            else:
                self.send_message(user_id, "❌ Введите корректное название пакета.")
            return
        if state == "waiting_email_text":
            emails = find_emails(text)
            if emails:
                self.temp_data[user_id] = {"type": "email", "items": emails}
                result = f"📧 Найденные email ({len(emails)}):\n\n" + "\n".join(emails)
                result += "\n\nЖелаете сохранить в БД?"
                self.send_message(user_id, result, self.get_confirm_keyboard())
                self.states[user_id] = "waiting_save_confirmation"
            else:
                self.send_message(user_id, "❌ Email не найдены.", self.get_main_keyboard())
                self.states[user_id] = None
            return
        if state == "waiting_phone_text":
            phones = find_phone_numbers(text)
            if phones:
                self.temp_data[user_id] = {"type": "phone", "items": phones}
                result = f"📱 Найденные номера ({len(phones)}):\n\n" + "\n".join(phones)
                result += "\n\nЖелаете сохранить в БД?"
                self.send_message(user_id, result, self.get_confirm_keyboard())
                self.states[user_id] = "waiting_save_confirmation"
            else:
                self.send_message(user_id, "❌ Номера не найдены.", self.get_main_keyboard())
                self.states[user_id] = None
            return
        if state == "waiting_password":
            strength = verify_password(text)
            self.send_message(user_id, f"Результат: {strength}", self.get_main_keyboard())
            self.states[user_id] = None
            return
        if state == "monitoring":
            self.handle_command(user_id, text)
            return
        if state == "waiting_for_result":
            if text == "📦 Показать результат":
                if self.show_package_result(user_id):
                    self.states[user_id] = "monitoring"
                else:
                    self.send_message(user_id, "⏳ Результат еще не готов...", self.get_result_keyboard())
            elif text == "📦 Пакеты":
                if user_id in self.task_results:
                    self.show_package_result(user_id)
                    self.states[user_id] = "monitoring"
                else:
                    self.send_message(user_id, "⏳ Идет сбор пакетов. Нажмите '📦 Показать результат' позже.", self.get_result_keyboard())
            else:
                self.send_message(user_id, "⏳ Идет сбор. Нажмите '📦 Показать результат'.", self.get_result_keyboard())
            return
        if state is None:
            self.send_message(user_id, "Используйте кнопки меню.", self.get_main_keyboard())

    def start(self):
        logger.info("Bot started")
        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                message = event.object.message
                user_id = message['from_id']
                text = message['text']
                logger.info(f"Received message from {user_id}: {text}")
                if text.lower() in ['начать', 'start', 'привет']:
                    self.send_message(user_id, "Привет! Я бот для поиска информации и мониторинга.\nВыберите действие:", self.get_main_keyboard())
                    continue
                if text in ["📧 Найти email", "📱 Найти телефон", "🔐 Проверить пароль",
                           "📊 Мониторинг системы", "📋 Релиз", "ℹ️ Система",
                           "⏱️ Uptime", "💾 Диски", "🧠 Память", "📊 CPU",
                           "👥 Пользователи", "🔑 Входы", "⚠️ Критические",
                           "🔄 Процессы", "🔌 Порты", "📦 Пакеты",
                           "⚙️ Сервисы", "🏠 Главное меню", "📦 Показать результат",
                           "📋 Логи репликации", "📮 Список email из БД", 
                           "📞 Список телефонов из БД"]:
                    self.handle_command(user_id, text)
                elif text in ["📋 Все пакеты", "🔍 Поиск пакета", "↩️ Назад в мониторинг",
                             "✅ Да, сохранить", "❌ Нет, не сохранять"]:
                    self.handle_text(user_id, text)
                else:
                    self.handle_text(user_id, text)
