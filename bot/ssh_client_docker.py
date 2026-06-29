import psycopg2
import logging
import os
from typing import Optional, List

logger = logging.getLogger(__name__)

class SSHClient:
    def __init__(self):
        self.db_host = os.getenv('DB_HOST', 'db_main')
        self.db_port = int(os.getenv('DB_PORT', '5432'))
        self.db_name = os.getenv('DB_DATABASE', 'mydb')
        self.db_user = os.getenv('DB_USER', 'db_admin')
        self.db_password = os.getenv('DB_PASSWORD', 'db_admin_password')
        self.db_repl_host = os.getenv('DB_REPL_HOST', 'db_replica')
        self.db_repl_port = int(os.getenv('DB_REPL_PORT', '5432'))
        self.db_repl_user = os.getenv('DB_REPL_USER', 'repl_user')
        self.db_repl_password = os.getenv('DB_REPL_PASSWORD', 'repl_password')
        logger.info(f"Docker DB client initialized: {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}")

    def get_connection(self, to_replica: bool = False):
        host = self.db_repl_host if to_replica else self.db_host
        port = self.db_repl_port if to_replica else self.db_port
        user = self.db_repl_user if to_replica else self.db_user
        password = self.db_repl_password if to_replica else self.db_password
        return psycopg2.connect(host=host, port=port, database=self.db_name, user=user, password=password, connect_timeout=10)

    def execute_db_command(self, sql_command: str, to_replica: bool = False) -> Optional[str]:
        try:
            conn = self.get_connection(to_replica)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(sql_command)
            if cur.description:
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                output = " | ".join(cols) + "\n" + "-" * 50 + "\n"
                for row in rows:
                    output += " | ".join(str(val) for val in row) + "\n"
                if not rows:
                    output += "(нет данных)\n"
            else:
                output = f"Выполнено. Затронуто строк: {cur.rowcount}"
            cur.close()
            conn.close()
            return output
        except Exception as e:
            logger.error(f"Database error: {e}")
            return f"❌ Ошибка БД: {str(e)}"

    def get_release(self): return "🐳 Docker контейнер (релиз недоступен)"
    def get_uname(self): return "🐳 Docker контейнер (uname недоступен)"

    def get_uptime(self):
        import subprocess
        r = subprocess.run(['uptime'], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else "Н/Д"

    def get_df(self):
        import subprocess
        r = subprocess.run(['df', '-h'], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else "Н/Д"

    def get_free(self):
        import subprocess
        r = subprocess.run(['free', '-h'], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else "Н/Д"

    def get_mpstat(self):
        try:
            with open('/proc/loadavg', 'r') as f:
                load = f.read().strip()
            with open('/proc/cpuinfo', 'r') as f:
                cpus = len([l for l in f if l.startswith('processor')])
            return f"Load average: {load}\nCPU cores: {cpus}"
        except:
            return "Н/Д"

    def get_w(self):
        import subprocess
        r = subprocess.run(['w'], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else "Н/Д"

    def get_auths(self): return "🐳 Docker контейнер (last недоступен)"
    def get_critical(self): return "🐳 Docker контейнер (journalctl недоступен)"

    def get_ps(self):
        import subprocess
        r = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        return r.stdout[:2000] if r.returncode == 0 else "Н/Д"

    def get_ss(self):
        import subprocess
        r = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else "Н/Д"

    def get_apt_list(self, package=None, timeout=120): return "🐳 Docker контейнер (apt недоступен)"
    def get_services(self): return "🐳 Docker контейнер (systemctl недоступен)"

    def get_replication_logs(self):
        output = "📋 ЛОГИ РЕПЛИКАЦИИ PostgreSQL\n"
        output += "=" * 40 + "\n\n"
        
        sql4 = "SELECT pid, usename, application_name, client_addr, state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;"
        result4 = self.execute_db_command(sql4)
        
        if result4 and result4.strip() and "(нет данных)" not in result4:
            output += "🔄 СТРИМИНГ РЕПЛИКАЦИИ:\n"
            output += "────────────────────────────────────────\n"
            output += result4 + "\n"
        else:
            output += "🔄 Стриминг не активен\n\n"
        
        sql2 = "SELECT slot_name, slot_type, active, restart_lsn FROM pg_replication_slots;"
        result2 = self.execute_db_command(sql2)
        
        if result2 and result2.strip() and "(нет данных)" not in result2:
            output += "🔌 СЛОТЫ РЕПЛИКАЦИИ:\n"
            output += "────────────────────────────────────────\n"
            output += result2 + "\n"
        
        sql3 = "SELECT pg_current_wal_lsn() as current_wal, pg_last_wal_receive_lsn() as last_receive, pg_last_wal_replay_lsn() as last_replay;"
        result3 = self.execute_db_command(sql3)
        if result3 and result3.strip():
            output += "📊 WAL ПОЗИЦИИ:\n"
            output += "────────────────────────────────────────\n"
            output += result3 + "\n\n"
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT pg_is_in_recovery();")
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0] == False:
                output += "✅ Сервер: MASTER (чтение и запись)\n"
            elif row and row[0] == True:
                output += "🔄 Сервер: REPLICA (только чтение)\n"
        except:
            pass
        
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
            if r and "ERROR" not in str(r) and "Ошибка" not in str(r):
                s += 1
        return s, len(emails) - s

    def insert_phones_batch(self, phones: List[str]) -> tuple:
        s = 0
        for p in phones:
            r = self.insert_phone(p)
            if r and "ERROR" not in str(r) and "Ошибка" not in str(r):
                s += 1
        return s, len(phones) - s

    def test_method(self): return "Docker DB Client работает корректно!"
