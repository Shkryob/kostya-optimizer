from typing import List


class SolarModule:
    def __init__(self, capacity: int):
        self.capacity = capacity


class Surface:
    def __init__(self, shading: float, tilt: float, azimuth: float, max_panels: int):
        self.shading = shading
        self.tilt = tilt
        self.azimuth = azimuth
        self.max_panels = max_panels


class Inverter:
    def __init__(self, production: float, efficiency: float):
        self.production = production
        self.efficiency = efficiency


class Address:
    def __init__(
            self,
            latitude: float,
            longitude: float,
            surfaces: List[Surface],
            solar_module: SolarModule,
            inverter: Inverter
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.surfaces = surfaces
        self.solar_module = solar_module
        self.inverter = inverter
