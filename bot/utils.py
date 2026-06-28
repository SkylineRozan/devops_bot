import re
import logging
import os
from typing import List, Optional, Dict

def setup_logging():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'bot.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def find_emails(text: str) -> List[str]:
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    valid_emails = []
    for email in emails:
        if validate_email(email):
            valid_emails.append(email)
    return list(set(valid_emails))

def validate_email(email: str) -> bool:
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    if re.match(pattern, email):
        if len(email) > 254:
            return False
        if '..' in email:
            return False
        if email.startswith('.') or email.endswith('.'):
            return False
        return True
    return False

def find_phone_numbers(text: str) -> List[str]:
    patterns = [
        r'8\d{10}', r'8\(\d{3}\)\d{7}',
        r'8\s\d{3}\s\d{3}\s\d{2}\s\d{2}',
        r'8\s\(\d{3}\)\s\d{3}\s\d{2}\s\d{2}',
        r'8-\d{3}-\d{3}-\d{2}-\d{2}',
        r'\+7\d{10}', r'\+7\(\d{3}\)\d{7}',
        r'\+7\s\d{3}\s\d{3}\s\d{2}\s\d{2}',
        r'\+7\s\(\d{3}\)\s\d{3}\s\d{2}\s\d{2}',
        r'\+7-\d{3}-\d{3}-\d{2}-\d{2}',
    ]
    phones = []
    for pattern in patterns:
        found = re.findall(pattern, text)
        phones.extend(found)
    normalized_phones = []
    for phone in phones:
        normalized = normalize_phone_number(phone)
        if normalized and normalized not in normalized_phones:
            normalized_phones.append(normalized)
    return normalized_phones

def normalize_phone_number(phone: str) -> Optional[str]:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and (digits.startswith('7') or digits.startswith('8')):
        return f"+7{digits[1:]}"
    elif len(digits) == 10:
        return f"+7{digits}"
    else:
        return None

def verify_password(password: str) -> str:
    score = 0
    feedback = []
    if len(password) < 8:
        return "❌ Пароль простой (слишком короткий, минимум 8 символов)"
    if len(password) >= 12:
        score += 2
        feedback.append("✅ Отличная длина")
    elif len(password) >= 8:
        score += 1
        feedback.append("✅ Хорошая длина")
    if re.search(r'[A-Z]', password):
        score += 1
        feedback.append("✅ Есть заглавные буквы")
    else:
        feedback.append("❌ Нет заглавных букв")
    if re.search(r'[a-z]', password):
        score += 1
        feedback.append("✅ Есть строчные буквы")
    else:
        feedback.append("❌ Нет строчных букв")
    if re.search(r'\d', password):
        score += 1
        feedback.append("✅ Есть цифры")
    else:
        feedback.append("❌ Нет цифр")
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
        feedback.append("✅ Есть спецсимволы")
    else:
        feedback.append("❌ Нет спецсимволов")
    common_patterns = ['123', 'abc', 'qwerty', 'password', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 1
        feedback.append("⚠️ Содержит распространенный паттерн")
    if score >= 5:
        result = "⭐ Пароль сложный"
    elif score >= 3:
        result = "👍 Пароль средний"
    else:
        result = "❌ Пароль простой"
    return f"{result}\n\nДетали:\n" + "\n".join(feedback)

def split_long_message(message: str, max_length: int = 4000) -> List[str]:
    if len(message) <= max_length:
        return [message]
    parts = []
    lines = message.split('\n')
    current_part = ""
    for line in lines:
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part)
            current_part = line
        else:
            if current_part:
                current_part += '\n' + line
            else:
                current_part = line
    if current_part:
        parts.append(current_part)
    return parts
