import sqlite3
import subprocess
import re
import logging
from datetime import datetime
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from .database import DB
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
                    str(target.ip_addr),
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
        logger.error(f"=> Error: {e} -> {type(e)}")
    finally:
        con.close()


def ready_to_ping(target: Target) -> bool:
    logger.info(f"=> Checking whether interval has passed before performing next ICMP test...")
    time_now = datetime.now().replace(microsecond=0)
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        data = cur.execute("""SELECT timestamp from results WHERE ip_addr = ?""", (str(target.ip_addr),)).fetchall()
        if data:
            previous_result_timestamp = datetime.strptime(data[-1][0], "%Y-%m-%d %H:%M:%S")
            elapsed_time = time_now - previous_result_timestamp
            if elapsed_time.total_seconds() < target.interval:
                logger.info(
                    f"=> Not enough time has passed since last ICMP test towards the target: {target.ip_addr}, remaining: {target.interval - elapsed_time.total_seconds()} seconds..."
                )
                return False
            else:
                logger.info(
                    f"=> Time has passed since last ICMP test: {elapsed_time} towards the target: {target.ip_addr}"
                )
                return True
        else:
            logger.info(f"=> Unable to find previous ICMP tests for the target: {target.ip_addr}")
            return True
    except Exception as e:
        logger.error(f"=> Error: {e} -> {type(e)}")
        return False
    finally:
        con.close()


def send_ping(target: Target) -> None:
    logger.info(f"=> Attempting to send ICMP probes to: {target.ip_addr}")
    if ready_to_ping(target=target):
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
                str(target.ip_addr),
            ]
            cmd_output = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=target.timeout + 10)
            logger.info(f"=> ICMP output:\n{cmd_output.stdout}")
            add_result(target=target, cmd_output=cmd_output.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"=> Ping failed for {target.ip_addr}: Return Code {e.returncode}. Stderr: {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logger.error(f"=> Ping command timed out for {target.ip_addr} after {target.timeout + 10} seconds.")
        except Exception as e:
            logger.error(f"=> Error: {e} -> {type(e)}")


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    fetch_results = cur.execute("""SELECT ip_addr, count, timeout, size, wait, interval FROM targets""").fetchall()
    if len(fetch_results) > 0:
        targets = [
            Target(ip_addr=ip_addr, count=count, timeout=timeout, size=size, wait=wait, interval=interval)
            for ip_addr, count, timeout, size, wait, interval in fetch_results
        ]
        with ThreadPoolExecutor() as executor:
            executor.map(send_ping, targets)
    else:
        logger.info("=> Targets table either doesn't exist or is empty...")


if __name__ == "__main__":
    main()
