from enum import Enum


class SpotType(str, Enum):
    REGULAR = "regular"
    DISABLED = "disabled"
    VIP = "vip"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
