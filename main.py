from models import Address, Surface, SolarModule
from solar_system_production import SolarSystemProductionService


def test():
    address1 = Address(37.2228043, -121.8778126, [
        Surface(1, 1, 41, 32)
    ], SolarModule(380))
    address2 = Address(37.2228043, -121.8778126, [
        Surface(20, 1, 41, 32)
    ], SolarModule(380))
    prod_service = SolarSystemProductionService()
    print(prod_service.get_production(address1))
    print(prod_service.get_production(address2))


if __name__ == '__main__':
    test()

