import paramiko
import logging
from typing import Optional, List
import os
import time

logger = logging.getLogger(__name__)

class SSHClient:
    def __init__(self):
        self.host = os.getenv('RM_HOST')
        self.port = int(os.getenv('RM_PORT', 22))
        self.username = os.getenv('RM_USER')
        self.password = os.getenv('RM_PASSWORD')
        self.client = None

        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', '5432'))
        self.db_name = os.getenv('DB_DATABASE', 'mydb')
        self.db_user = os.getenv('DB_USER', 'db_admin')
        self.db_password = os.getenv('DB_PASSWORD', 'db_admin_password')

        self.db_repl_user = os.getenv('DB_REPL_USER', 'repl_user')
        self.db_repl_password = os.getenv('DB_REPL_PASSWORD', 'repl_password')
        self.db_repl_host = os.getenv('DB_REPL_HOST', 'replica_host')
        self.db_repl_port = os.getenv('DB_REPL_PORT', '5433')

        if not all([self.host, self.username, self.password]):
            logger.error("Missing SSH connection parameters")

        logger.info(f"SSH Client initialized for {self.username}@{self.host}:{self.port}")

    def connect(self, max_retries: int = 3, retry_delay: int = 2) -> bool:
        for attempt in range(max_retries):
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.client.connect(
                    hostname=self.host, port=self.port,
                    username=self.username, password=self.password,
                    timeout=30, allow_agent=False, look_for_keys=False
                )
                logger.info(f"SSH connection established to {self.host}")
                return True
            except Exception as e:
                logger.error(f"SSH connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        return False

    def disconnect(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None

    def ensure_connection(self) -> bool:
        if self.client is None:
            return self.connect()
        try:
            transport = self.client.get_transport()
            if transport is None or not transport.is_active():
                self.disconnect()
                return self.connect()
            return True
        except:
            self.disconnect()
            return self.connect()

    def execute_command(self, command: str, timeout: int = 60) -> Optional[str]:
        if not self.ensure_connection():
            return None
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            return stdout.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return None

    def execute_db_command(self, sql_command: str, timeout: int = 30) -> Optional[str]:
        escaped = sql_command.replace("'", "'\\''")
        command = f"PGPASSWORD='{self.db_password}' psql -h {self.db_host} -p {self.db_port} -U {self.db_user} -d {self.db_name} -c '{escaped}'"
        return self.execute_command(command, timeout)

    def get_release(self): return self.execute_command('lsb_release -a 2>/dev/null || cat /etc/os-release')
    def get_uname(self): return self.execute_command('uname -a')
    def get_uptime(self): return self.execute_command('uptime')
    def get_df(self): return self.execute_command('df -h')
    def get_free(self): return self.execute_command('free -h')
    def get_mpstat(self): return self.execute_command('mpstat 1 1 2>/dev/null || top -bn1 | head -n 5')
    def get_w(self): return self.execute_command('w')
    def get_auths(self): return self.execute_command('last -n 10')
    def get_critical(self): return self.execute_command('journalctl -p crit -n 5 --no-pager 2>/dev/null || echo "No critical logs"')
    def get_ps(self): return self.execute_command('ps aux | head -n 20')
    def get_ss(self): return self.execute_command('ss -tulpn 2>/dev/null || netstat -tulpn 2>/dev/null')
    def get_services(self): return self.execute_command('systemctl list-units --type=service --state=running 2>/dev/null | head -n 20')

    def get_apt_list(self, package: Optional[str] = None, timeout: int = 120) -> Optional[str]:
        if package:
            command = f'dpkg -l | grep -i "{package}" 2>/dev/null || apt list --installed 2>/dev/null | grep -i "{package}"'
        else:
            command = 'dpkg -l 2>/dev/null || apt list --installed 2>/dev/null'
        return self.execute_command(command, timeout)

    def get_replication_logs(self) -> Optional[str]:
        output = "📋 Логи репликации PostgreSQL:\n\n"
        sql = "SELECT usename, application_name, client_addr, state, sync_state, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) as lag_bytes FROM pg_stat_replication;"
        result = self.execute_db_command(sql)
        if result and result.strip():
            output += f"🔄 Активные подключения:\n{result}\n\n"
        else:
            output += "🔄 Нет активных подключений.\n\n"
        sql2 = "SELECT slot_name, slot_type, active, restart_lsn FROM pg_replication_slots;"
        result2 = self.execute_db_command(sql2)
        if result2 and result2.strip():
            output += f"🔌 Слоты репликации:\n{result2}\n\n"
        return output

    def get_emails_from_db(self): return self.execute_db_command("SELECT ID, Email FROM EMAIL ORDER BY ID DESC;")
    def get_phones_from_db(self): return self.execute_db_command("SELECT ID, Phone FROM PHONE ORDER BY ID DESC;")

    def insert_email(self, email: str):
        escaped = email.replace("'", "''")
        return self.execute_db_command(f"INSERT INTO EMAIL (Email) VALUES ('{escaped}') ON CONFLICT (Email) DO NOTHING RETURNING ID;")

    def insert_phone(self, phone: str):
        escaped = phone.replace("'", "''")
        return self.execute_db_command(f"INSERT INTO PHONE (Phone) VALUES ('{escaped}') ON CONFLICT (Phone) DO NOTHING RETURNING ID;")

    def insert_emails_batch(self, emails: List[str]) -> tuple:
        s = 0
        for e in emails:
            r = self.insert_email(e)
            if r and "ERROR" not in str(r) and "Ошибка" not in str(r): s += 1
        return s, len(emails) - s

    def insert_phones_batch(self, phones: List[str]) -> tuple:
        s = 0
        for p in phones:
            r = self.insert_phone(p)
            if r and "ERROR" not in str(r) and "Ошибка" not in str(r): s += 1
        return s, len(phones) - s

    def test_method(self): return "SSH Client работает корректно!"
