from typing import get_args
from opendbc.car.body.values import CAR as BODY
from opendbc.car.mock.values import CAR as MOCK
from opendbc.car.rivian.values import CAR as RIVIAN

Platform = RIVIAN | MOCK | BODY
BRANDS = get_args(Platform)

PLATFORMS: dict[str, Platform] = {str(platform): platform for brand in BRANDS for platform in brand}
