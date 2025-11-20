from ipaddress import IPv4Address
from pydantic import BaseModel


class Target(BaseModel):
    ip_addr: IPv4Address  # IP address
    count: int  # Stop after sending (and receiving) count ECHO_RESPONSE packets.
    timeout: int  # Timeout, in seconds, before ping exits regardless of how many packets have been received.
    size: int  # Number of data bytes to be sent. The default is 56.
    wait: float  # Wait wait seconds between sending each packet (min 0.002).
    interval: int  # How long to wait (in seconds) before repeating the test.
