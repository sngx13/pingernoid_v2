import sqlite3
import logging
import pathlib

DB_FILE = pathlib.Path(__file__).parent / "pingernoid.db"
DB: str = str(DB_FILE)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_system_table() -> None:
    logger.info("=> Creating 'system' table...")
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            """
                CREATE TABLE IF NOT EXISTS system (
                    id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """
        )
        con.commit()
    except Exception as e:
        logger.info(f"=> Error: {e} -> {type(e)}")
    finally:
        con.close()


def create_targets_table() -> None:
    logger.info("=> Creating 'targets' table...")
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            """
                CREATE TABLE IF NOT EXISTS targets (
                    ip_addr TEXT NOT NULL,
                    count INTEGER,
                    timeout INTEGER,
                    size INTEGER,
                    wait REAL,
                    interval INTEGER
                )
            """
        )
        con.commit()
    except Exception as e:
        logger.info(f"=> Error: {e} -> {type(e)}")
    finally:
        con.close()


def create_results_table() -> None:
    logger.info("=> Creating 'results' table...")
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute(
            """
                CREATE TABLE IF NOT EXISTS results (
                    id TEXT,
                    ip_addr TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sent INTEGER,
                    rcvd INTEGER,
                    loss REAL,
                    rtt_min REAL,
                    rtt_avg REAL,
                    rtt_max REAL,
                    PRIMARY KEY (id, timestamp)
                )
            """
        )
        con.commit()
    except Exception as e:
        logger.info(f"=> Error: {e} -> {type(e)}")
    finally:
        con.close()


def init_db():
    logger.info("=> Creating tables...")
    create_system_table()
    create_targets_table()
    create_results_table()
