import re
import subprocess
from datetime import datetime
from typing import Optional

from .db.crud import PingerRepository
from .db.models import Result, Target


def parse_ping_output(ip_addr: str, output: str) -> Optional[Result]:
    """Parses standard ping output to a Result object."""
    pattern = re.compile(
        r"(\d+)\s+packets\s+transmitted,\s+(\d+)\s+packets\s+received.*?(\d+\.\d+)%\s+packet\s+loss.*?(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(output)
    if match:
        return Result(
            ip_addr=ip_addr,
            timestamp=datetime.now(),
            sent=int(match.group(1)),
            rcvd=int(match.group(2)),
            loss=float(match.group(3)),
            rtt_min=float(match.group(4)),
            rtt_avg=float(match.group(5)),
            rtt_max=float(match.group(6)),
        )
    return None


class PingerService:
    """Handles the business logic for pinging targets."""

    def __init__(self, repo: PingerRepository):
        # Service depends on the Repository, not the Session
        self.repo = repo

    def ready_to_ping(self, target: Target) -> bool:
        """Checks if the required interval has passed since the last ping."""
        print(f"=> Checking whether interval has passed before performing next ICMP test...")
        time_now = datetime.now().replace(microsecond=0)

        previous_result_timestamp = self.repo.get_latest_result_timestamp(target.ip_addr)

        if previous_result_timestamp:
            elapsed_time = time_now - previous_result_timestamp
            if elapsed_time.total_seconds() < target.interval:
                remaining = target.interval - elapsed_time.total_seconds()
                print(f"=> Not enough time has passed for {target.ip_addr}, remaining: {remaining:.2f}s...")
                return False
            else:
                print(f"=> Time has passed since last ICMP test: {elapsed_time} towards {target.ip_addr}")
                return True
        else:
            print(f"=> Unable to find previous ICMP tests for {target.ip_addr}")
            return True

    def ping_target(self, target: Target):
        """Performs the actual ICMP ping test and saves the result via the repository."""
        print(f"=> Attempting to send ICMP probes to: {target.ip_addr}")

        # Check readiness using business logic
        if self.ready_to_ping(target):
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
                # Increase total timeout slightly more than the ping timeout for command overhead
                cmd_output = subprocess.run(
                    cmd, capture_output=True, text=True, check=True, timeout=target.timeout + 10
                )
                print(f"=> ICMP output:\n{cmd_output.stdout}")

                parsed_result = parse_ping_output(target.ip_addr, cmd_output.stdout)

                if parsed_result:
                    print(f"=> Writing ping results to database for: {parsed_result.ip_addr}")
                    # Use the repository method to save the result
                    self.repo.create_result(parsed_result)
                else:
                    print(f"=> Failed to parse ping output for {target.ip_addr}")
            except subprocess.CalledProcessError as e:
                print(f"=> Ping failed for {target.ip_addr}: Return Code {e.returncode}. Stderr: {e.stderr.strip()}")
            except subprocess.TimeoutExpired:
                print(f"=> Ping command timed out for {target.ip_addr} after {target.timeout + 10} seconds.")
            except Exception as e:
                print(f"=> Error during ping: {e} -> {type(e)}")
