from typing import List
import pandas
from models import Address
from timezonefinder import TimezoneFinder
from pvlib import pvsystem, iotools, temperature
from pvlib.location import Location
from pvlib.modelchain import ModelChain


class SolarSystemProductionService:
    # default pvwatts losses
    loses = {
        'soiling': 2,
        'shading': 3,
        'snow': 0,
        'mismatch': 2,
        'wiring': 2,
        'connections': 0.5,
        'lid': 1.5,
        'nameplate_rating': 1,
        'age': 0,
        'availability': 3,
    }

    def __init__(self, address: Address):
        self.address = address

    def get_production(self):
        arrays = self.create_arrays()
        weather_datasets = self.create_weather_datasets()
        system = self.create_system(arrays)
        mc = self.create_model_chain(system)
        mc.run_model(weather_datasets)
        annual_production = mc.results.ac.sum() / 1000

        return {
            'annual_production': annual_production,
            'monthly_production': self.get_monthly_production(mc.results.ac),
        }

    def get_monthly_production(self, ac_result: pandas.Series) -> dict:
        # weather data is fragmented data so we have to combine by month not byt year, month
        return ac_result \
            .groupby([lambda x: x.month]) \
            .sum() \
            .div(1000) \
            .to_dict()

    def create_inverter_parameters(self) -> dict:
        return {
            # Total DC power limit of the inverter
            'pdc0': self.address.inverter.production,
            # (numeric, default 0.96) – Nominal inverter efficiency
            'eta_inv_nom': self.address.inverter.efficiency,
        }

    def create_module_paramenters(self) -> dict:
        return {
            #  nominal DC power output of a solar module under standard test conditions (STC)
            'pdc0': self.address.solar_module.capacity,
            # The temperature coefficient of power. Typically -0.002 to -0.005 per degree C. [1/C]
            'gamma_pdc': -0.004,
        }

    def create_model_chain(self, system: pvsystem.PVSystem) -> ModelChain:
        location = self.create_location()

        return ModelChain(
            system,
            location,
            aoi_model='physical',
            spectral_model='no_loss',
            losses_model='pvwatts',
        )

    def create_location(self) -> Location:
        local_timezone = self.get_local_timezone()

        location = Location(
            self.address.latitude,
            self.address.longitude,
            # name=name,
            # altitude=altitude,
            tz=local_timezone,
        )
        return location

    def create_weather_datasets(self) -> List[pandas.DataFrame]:
        weather_datasets = []
        basic_weather = iotools.get_pvgis_tmy(self.address.latitude, self.address.longitude)[0]

        for surface in self.address.surfaces:
            surface_weather = basic_weather.copy()
            shading_coeff = (100 - surface.shading) / 100
            # dni - Direct Normal Irradiance
            surface_weather['dni'] = surface_weather['dni'].apply(lambda x: x * shading_coeff)

            # comment below two lines to get results as in SAM
            surface_weather['ghi'] = surface_weather['ghi'].apply(
                lambda x: x * shading_coeff)  # Global Horizontal Irradiance
            surface_weather['dhi'] = surface_weather['dhi'].apply(
                lambda x: x * shading_coeff)  # Diffuse Horizontal Irradiance
            weather_datasets.append(surface_weather)

        return weather_datasets

    def create_arrays(self) -> List[pvsystem.Array]:
        arrays = []
        temperature_model_parameters = temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']
        module_parameters = self.create_module_paramenters()

        for surface in self.address.surfaces:
            mount = pvsystem.FixedMount(
                surface_tilt=surface.tilt,
                surface_azimuth=surface.azimuth,
            )
            arrays.append(pvsystem.Array(
                mount=mount,
                module_parameters=module_parameters,
                temperature_model_parameters=temperature_model_parameters,
                strings=surface.max_panels,
                modules_per_string=1
            ))

        return arrays

    def create_system(self, arrays: List[pvsystem.Array]) -> pvsystem.PVSystem:
        inverter_parameters = self.create_inverter_parameters()

        system = pvsystem.PVSystem(
            arrays=arrays,
            inverter_parameters=inverter_parameters,
            strings_per_inverter=1,
            racking_model='open_rack',
            losses_parameters=self.loses,
        )
        system.racking_model = None

        return system

    def get_local_timezone(self) -> str:
        tf = TimezoneFinder()

        return tf.timezone_at(lat=self.address.latitude, lng=self.address.longitude)
