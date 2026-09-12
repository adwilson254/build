from opendbc.car.interfaces import get_interface_attr
from opendbc.car.body.values import CAR as BODY
from opendbc.car.mock.values import CAR as MOCK
from opendbc.car.rivian.values import CAR as RIVIAN

FW_VERSIONS = get_interface_attr('FW_VERSIONS', combine_brands=True, ignore_none=True)
_FINGERPRINTS = get_interface_attr('FINGERPRINTS', combine_brands=True, ignore_none=True)

_DEBUG_ADDRESS = {1880: 8}   # reserved for debug purposes


def is_valid_for_fingerprint(msg, car_fingerprint: dict[int, int]):
  adr = msg.address
  # ignore addresses that are more than 11 bits
  return (adr in car_fingerprint and car_fingerprint[adr] == len(msg.dat)) or adr >= 0x800


def eliminate_incompatible_cars(msg, candidate_cars):
  """Removes cars that could not have sent msg.

     Inputs:
      msg: A cereal/log CanData message from the car.
      candidate_cars: A list of cars to consider.

     Returns:
      A list containing the subset of candidate_cars that could have sent msg.
  """
  compatible_cars = []

  for car_name in candidate_cars:
    car_fingerprints = _FINGERPRINTS[car_name]

    for fingerprint in car_fingerprints:
      # add alien debug address
      if is_valid_for_fingerprint(msg, fingerprint | _DEBUG_ADDRESS):
        compatible_cars.append(car_name)
        break

  return compatible_cars


def all_legacy_fingerprint_cars():
  """Returns a list of all known car strings, FPv1 only."""
  return list(_FINGERPRINTS.keys())


# A dict that maps old platform strings to their latest representations
MIGRATION = {

  # Removal of platform_str, see https://github.com/commaai/openpilot/pull/31868/
  "COMMA BODY": BODY.COMMA_BODY,
  "RIVIAN_R1_GEN1": RIVIAN.RIVIAN_R1,
  "RIVIAN_R1_GEN2": RIVIAN.RIVIAN_R1,

  "mock": MOCK.MOCK,
}
