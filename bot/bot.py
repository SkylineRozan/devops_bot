import os
import sys
from dotenv import load_dotenv
from utils import setup_logging

logger = setup_logging()
load_dotenv()
logger.info("Переменные окружения загружены")

try:
    from commands import VKBot
    logger.info("Модуль commands импортирован успешно")
except ImportError as e:
    logger.error(f"Ошибка импорта commands: {e}")
    print(f"Ошибка импорта: {e}")
    sys.exit(1)

def check_environment():
    print("\n=== Проверка переменных окружения ===")
    token = os.getenv('VK_TOKEN')
    if token:
        print(f"✓ VK_TOKEN: {token[:20]}...")
    else:
        print("✗ VK_TOKEN не найден!")
        return False
    db_params = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_DATABASE']
    for param in db_params:
        value = os.getenv(param)
        if value:
            print(f"✓ {param}: {value}")
        else:
            print(f"⚠ {param}: не установлен")
    return True

def main():
    print("\n" + "="*50)
    print("ЗАПУСК VK БОТА")
    print("="*50)

    if not check_environment():
        print("\n❌ Ошибка: проверьте файл .env")
        return

    token = os.getenv('VK_TOKEN')
    group_id_str = os.getenv('GROUP_ID')
    
    if group_id_str:
        try:
            group_id = int(group_id_str.strip())
            print(f"\n✓ Используем GROUP_ID из .env: {group_id}")
        except ValueError:
            print("❌ Неверный GROUP_ID в .env файле")
            return
    else:
        print("\n=== ИНФОРМАЦИЯ О ГРУППЕ ===")
        print("Вам нужно узнать ID вашей группы ВКонтакте.")
        print("1. Перейдите в вашу группу")
        print("2. Нажмите 'Управление'")
        print("3. ID группы будет в URL: https://vk.com/club123456789")
        print("   где 123456789 - это ID группы")
        try:
            group_id = int(input("\nВведите ID группы: ").strip())
        except ValueError:
            print("❌ Неверный ID группы")
            return

    print(f"\nИспользуем group_id: {group_id}")
    print("\nСоздание экземпляра бота...")
    
    try:
        bot = VKBot(token, group_id)
        print("✓ Бот создан успешно")
    except Exception as e:
        print(f"❌ Ошибка создания бота: {e}")
        logger.error(f"Error creating bot: {e}", exc_info=True)
        return

    print("\n" + "="*50)
    print("БОТ ЗАПУЩЕН")
    print("Для проверки отправьте сообщение в группу ВК")
    print("Нажмите Ctrl+C для остановки")
    print("="*50 + "\n")

    try:
        bot.start()
    except KeyboardInterrupt:
        print("\n\nБот остановлен пользователем")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Critical error: {e}", exc_info=True)
        print("\nПроверьте лог-файл: logs/bot.log")

if __name__ == "__main__":
    main()
