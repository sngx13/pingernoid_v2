import logging
import sqlite3
import socket
from datetime import datetime
from uuid import uuid4
from .database import init_db, DB
import netifaces

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_local_ip_addr():
    netifaces.ifaddresses()


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
                """INSERT INTO system VALUES (?, ?)""",
                (
                    id,
                    str(datetime.now().replace(microsecond=0)),
                ),
            )
            con.commit()
    except Exception as e:
        logger.info(f"=> Error: {e} -> {type(e)}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
