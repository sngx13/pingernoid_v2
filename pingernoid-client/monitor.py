import sqlite3
import subprocess
import re
import logging
from datetime import datetime
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from .database import init_db, DB
from .models import Target

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def add_result(target: Target, cmd_output: str) -> None:
    logger.info(f"=> Adding result of {target.ip_addr} to the database...")
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        pattern = re.compile(
            r"(\d+)\s+packets\s+transmitted,\s+(\d+)\s+packets\s+received.*?(\d+\.\d+)%\s+packet\s+loss.*?(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(cmd_output)
        if match:
            cur.execute(
                """INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid4()),
                    target.ip_addr,
                    str(datetime.now().replace(microsecond=0)),
                    int(match.group(1)),  # SENT
                    int(match.group(2)),  # RCVD
                    float(match.group(3)),  # LOSS,
                    float(match.group(4)),  # MIN,
                    float(match.group(5)),  # AVG
                    float(match.group(6)),  # MAX
                ),
            )
            con.commit()
        else:
            logger.warning("=> Could not parse output using REGEX patern match!")
    except Exception as e:
        logger.error(f"=> Error: {e} -> {e.stderr}!")
    finally:
        con.close()


def send_ping(target: Target) -> None:
    logger.info(f"=> Attempting to send ICMP probes to: {target.ip_addr}")
    try:
        cmd = [
            "ping",
            "-c",
            str(target.count),
            "-t",
            str(target.timeout),
            "-s",
            str(target.size),
            "-i",
            str(target.wait),
            target.ip_addr,
        ]
        cmd_output = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=target.timeout + 10)
        logger.info(f"=> ICMP output:\n{cmd_output.stdout}")
        add_result(target=target, cmd_output=cmd_output.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"=> Ping failed for {target.ip_addr}: Return Code {e.returncode}. Stderr: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"=> Ping command timed out for {target.ip_addr} after {target.timeout + 10} seconds.")


def main():
    init_db()
    con = sqlite3.connect(DB)
    cur = con.cursor()
    fetch_results = cur.execute("""SELECT ip_addr, count, timeout, size, wait, interval FROM targets""").fetchall()
    if len(fetch_results) > 0:
        targets = [
            Target(ip_addr, count, timeout, size, wait, interval)
            for ip_addr, count, timeout, size, wait, interval in fetch_results
        ]
        with ThreadPoolExecutor() as executor:
            executor.map(send_ping, targets)
    else:
        logger.info("=> Targets table either doesn't exist or is empty...")


if __name__ == "__main__":
    main()
