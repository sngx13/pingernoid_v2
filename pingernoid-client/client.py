import logging
import sqlite3
import requests
from datetime import datetime
from uuid import uuid4
from .database import init_db, DB
import netifaces
from ipaddress import ip_address

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_public_ip_addr() -> ip_address:
    logger.info("=> Attempting to find public IP address...")
    url = "https://api.ipify.org?format=json"
    response = requests.get(url)
    if response.status_code == 200:
        ip_addr = response.json().get("ip")
        logger.info(f"=> Outbound Internet access from this host is associated with the following IP: {ip_addr}")
        return ip_addr


def get_local_ip_addr() -> ip_address:
    logger.info("=> Attempting to find local IP address...")
    interface_with_gateway = netifaces.gateways().get("default")[netifaces.AF_INET]
    if interface_with_gateway:
        interface_name = interface_with_gateway[1]
        ip_addr = netifaces.ifaddresses(interface_name)[netifaces.AF_INET][0].get("addr")
        logger.info(f"=> Found the following IP: {ip_addr} associated with: {interface_name} interface...")
        return ip_addr


def main():
    try:
        init_db()
        con = sqlite3.connect(DB)
        cur = con.cursor()
        fetch_results = cur.execute("""SELECT id FROM system""").fetchall()
        if fetch_results:
            id = fetch_results[0][0]
            logger.info(f"=> System is warm starting... existing id: {id}")
        else:
            id = str(uuid4())
            logger.info(f"=> System is cold starting... generating new id: {id}")
            cur.execute(
                """INSERT INTO system VALUES (?, ?, ?, ?)""",
                (id, str(datetime.now().replace(microsecond=0)), get_local_ip_addr(), get_public_ip_addr()),
            )
            con.commit()
    except Exception as e:
        logger.info(f"=> Error: {e} -> {type(e)}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
