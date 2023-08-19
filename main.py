from models import Address, Surface, SolarModule, Inverter
from solar_system_production import SolarSystemProductionService


def test():
    address1 = Address(37.2228043, -121.8778126, [
        Surface(1, 1, 41, 32)
    ], SolarModule(380), Inverter(50000, 0.995))
    print(SolarSystemProductionService(address1).get_production())

    address1 = Address(37.2228043, -121.8778126, [
        Surface(20, 1, 41, 32)
    ], SolarModule(380), Inverter(50000, 0.995))
    print(SolarSystemProductionService(address1).get_production())


if __name__ == '__main__':
    test()

