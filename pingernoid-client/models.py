from dataclasses import dataclass
from ipaddress import ip_address
from ipaddress import ip_address, AddressValueError


@dataclass
class Target:
    ip_addr: ip_address  # IP address
    count: int  # Stop after sending (and receiving) count ECHO_RESPONSE packets.
    timeout: int  # Timeout, in seconds, before ping exits regardless of how many packets have been received.
    size: int  # Number of data bytes to be sent. The default is 56.
    wait: float  # Wait wait seconds between sending each packet (min 0.002).
    interval: int  # How long to wait (in seconds) before repeating the test.

    def __post_init__(self):
        try:
            self.ip_addr = ip_address(self.ip_addr)
        except AddressValueError as e:
            raise ValueError(f"=> Invalid IP address format provided for Target: {self.ip_addr}") from e
        except TypeError as e:
            raise TypeError(f"=> IP address must be a string or bytes: {self.ip_addr}") from e
