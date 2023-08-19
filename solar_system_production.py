from typing import List
import pandas
from models import Address
from timezonefinder import TimezoneFinder
from pvlib import pvsystem, iotools, temperature
from pvlib.location import Location
from pvlib.modelchain import ModelChain


class SolarSystemProductionService:
    def get_production(self, address: Address):
        module_parameters = self.create_module_paramenters(address)
        total_modules = sum(surface.max_panels for surface in address.surfaces)
        inverter_parameters = {'pdc0': address.solar_module.capacity * total_modules}
        location = self.create_location(address)

        arrays = self.create_arrays(address, module_parameters)
        weather_datasets = self.create_wather_datasets(address)
        system = self.create_system(arrays, inverter_parameters)
        mc = self.create_model_chain(location, system)
        mc.run_model(weather_datasets)
        annual_energy = mc.results.ac.sum()
        annual_energy = annual_energy / 1000  # convert to kWh

        #for
        #mc.results.ac.between_time()

        return annual_energy

    def create_module_paramenters(self, address: Address) -> dict:
        module_parameters = {
            #  nominal DC power output of a solar module under standard test conditions (STC)
            'pdc0': address.solar_module.capacity,
            # The temperature coefficient of power. Typically -0.002 to -0.005 per degree C. [1/C]
            'gamma_pdc': -0.004,
        }
        return module_parameters

    def create_model_chain(self, location: Location, system: pvsystem.PVSystem) -> ModelChain:
        return ModelChain(
            system,
            location,
            aoi_model='physical',
            spectral_model='no_loss',
            losses_model='pvwatts',
        )

    def create_location(self, address: Address) -> Location:
        local_timezone = self.get_local_timezone(address)

        location = Location(
            address.latitude,
            address.longitude,
            # name=name,
            # altitude=altitude,
            tz=local_timezone,
        )
        return location

    def create_wather_datasets(self, address: Address) -> List[pandas.DataFrame]:
        weather_datasets = []
        basic_weather = iotools.get_pvgis_tmy(address.latitude, address.longitude)[0]

        for surface in address.surfaces:
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

    def create_arrays(self, address: Address, module_parameters: dict) -> List[pvsystem.Array]:
        arrays = []
        temperature_model_parameters = temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']

        for surface in address.surfaces:
            mount = pvsystem.FixedMount(
                surface_tilt=surface.tilt,
                surface_azimuth=surface.azimuth,
            )
            arrays.append(pvsystem.Array(
                mount=mount,
                module_parameters=module_parameters,
                temperature_model_parameters=temperature_model_parameters,
                modules_per_string=surface.max_panels,
            ))

        return arrays

    def create_system(self, arrays: List[pvsystem.Array], inverter_parameters: dict) -> pvsystem.PVSystem:
        system = pvsystem.PVSystem(
            arrays=arrays,
            inverter_parameters=inverter_parameters,
            racking_model='open_rack',
            losses_parameters={  # default pvwatts losses
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
        )
        system.racking_model = None

        return system

    def get_local_timezone(self, address: Address) -> str:
        tf = TimezoneFinder()

        return tf.timezone_at(lat=address.latitude, lng=address.longitude)
