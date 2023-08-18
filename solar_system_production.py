from models import Address
from timezonefinder import TimezoneFinder
from pvlib import pvsystem, iotools, temperature
from pvlib.location import Location
from pvlib.modelchain import ModelChain


class SolarSystemProductionService:
    def get_production(self, address: Address):
        total_modules = sum(surface.max_panels for surface in address.surfaces)
        local_timezone = self.get_local_timezone(address)
        module_parameters = {
            #  nominal DC power output of a solar module under standard test conditions (STC)
            'pdc0': address.solar_module.capacity,
            # The temperature coefficient of power. Typically -0.002 to -0.005 per degree C. [1/C]
            'gamma_pdc': -0.004,

        }
        inverter_parameters = {'pdc0': address.solar_module.capacity * total_modules}

        temperature_model_parameters = temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']
        location = Location(
            address.latitude,
            address.longitude,
            # name=name,
            # altitude=altitude,
            tz=local_timezone,
        )

        basic_weather = iotools.get_pvgis_tmy(address.latitude, address.longitude)[0]
        arrays = []
        weather_datasets = []

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
            surface_weather = basic_weather.copy()
            shading_coeff = (100 - surface.shading) / 100
            # dni - Direct Normal Irradiance
            surface_weather['dni'] = surface_weather['dni'].apply(lambda x: x * shading_coeff)
            weather_datasets.append(surface_weather)

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
        mc = ModelChain(
            system,
            location,
            aoi_model='physical',
            spectral_model='no_loss',
            losses_model='pvwatts',
        )
        mc.run_model(weather_datasets)
        annual_energy = mc.results.ac.sum()
        annual_energy = annual_energy / 1000  # convert to kWh

        return annual_energy

    def get_local_timezone(self, address: Address) -> str:
        tf = TimezoneFinder()
        return tf.timezone_at(lat=address.latitude, lng=address.longitude)
