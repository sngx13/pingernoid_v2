import sqlite3
import logging
from ipaddress import ip_address
from .database import init_db, DB
from .models import Target

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def existing_target(ip_addr: ip_address) -> bool:
    logger.info(f"=> Looking up target IP: {ip_addr}")
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        fetch_results = cur.execute("""SELECT * FROM targets WHERE ip_addr = ?""", (ip_addr,)).fetchall()
        if len(fetch_results) > 0:
            data = fetch_results[0]
            logger.info(f"=> Found existing target IP: {data[0]} in the database...")
            return True
        else:
            logger.info(f"=> Could not find any ICMP probes to the target IP: {ip_addr}")
            return False
    except Exception as e:
        logger.error(f"=> Error: {e} -> {type(e)}")
        return False
    finally:
        con.close()


def add_target(target: Target) -> bool:
    logger.info("=> Attempting to add a target...")
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        exists = existing_target(ip_addr=target.ip_addr)
        if exists:
            logger.info(f"=> Existing probe is already running towards: {target.ip_addr}...")
            return False
        else:
            logger.info(f"=> Adding new ICMP target: {target.ip_addr}")
            cur.execute(
                """INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?)""",
                (str(target.ip_addr), target.count, target.timeout, target.size, target.wait, target.interval),
            )
            con.commit()
            return True
    except Exception as e:
        logger.error(f"=> Error: {e} -> {type(e)}")
        return False
    finally:
        con.close()


def main():
    init_db()
    create_target = Target(ip_addr="8.8.8.8", count=10, timeout=1, size=200, wait=0.05, interval=180)
    target = add_target(target=create_target)
    if target:
        logger.info("=> Successfully added probe...")


if __name__ == "__main__":
    logger.info("=> Starting...")
    main()
