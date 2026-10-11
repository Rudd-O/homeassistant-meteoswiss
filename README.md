# homeassistant-meteoswiss (forked)

This is the MeteoSwiss integration for Home Assistant.

## Features

* Interactive setup flow with reasonably good explanations of the
  settings.
* Lets you determine the real-time weather update frequency.
* Lets you customize all entities this integration provides
  (every entity has a unique ID).
* Detects when your real-time weather station has been retired,
  and offers suggestions on how to fix the issue.
* Supports hourly forecasts.
* Supports two different real-time stations: a weather station
  that may not give you rain data, and a precipitation station
  that will give you rain data but may not give you other info.
* Provides the current rain rate and hail risk from the MeteoSwiss
  weather radar at your location (see below).
* Code is much cleaner and works properly.

See below for common issues.

## Installation

### Removal of the obsolete integration

*You only need to do this if you had either Websylv's integration
or an older version of this integration installed and setup.*

* Remove the old integration from your HACS integrations screen.
  * Go into the integration within the HACS integrations screen.
  * Click on the three dots menu at the upper right corner.
  * Select *Remove*.
* Remove the repository from your HACS setup.
  * In the HACS integration screen, click the three dots menu.
  * Delete the integration from the *Custom repositories* dialog.
* Remove the config entry.
  * Write down the names you have given to your existing weather and
    sensor entities.
  * In the Devices & Services settings screen, locate the integration
    configuration entry, then click its three-dots menu.
  * Select *Delete*.
* Stop Home Assistant.
* Change into your Home Assistant configuration directory.
* Verify the folder `custom_components/meteo-swiss` is nonexistent
  under the Home Assistant configuration directory.  Note the dash!
* Start Home Assistant.
* Proceed with installation.
  * Once you get to the setup stage, when you are asked for the
    names of the weather and sensor entities, re-use the same
    names you used before.  Your statistics will then be preserved
    from the old entities managed by the old integration.

### Installation of the updated integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Add this integration as a custom repository to HACS.  If you use
HACS you already know the generic instructions on how to do this.
Here is how it looks like on the add custom repo screen:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/addcustomrepo.png)

Once added as a custom repository, add the integration to your
HACS setup:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/addrepository.png)

Once done you should see a pending restart box:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/pendingrestart.png)

Restart your Home Assistant:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/restart.png)

Now you are ready to add one or more instances of the integration.

## Setup

- First make sure that your Home Assistant's basic setup (latitude, longitude)
  is correct.  This information is used to help you set up the weather station.
  If, however, it is not correct, you can still override it later.

- Get to the Home Asssistant settings screen:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/settings.png)
  
- Then click on "Devices & Services":

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/devicesservices.png)

- Than add a new integration:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/add.png)
  
- Search for *MeteoSwiss* and then proceed:

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/search.png)

- By default the integration will try to determine the best settings for you
  based on your Home zone latitude and longitude (which you can override):

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/latitude.png)

- The next screen will ask you (with a good guess) about your postal code, and update interval.  This information
  will be used by the weather entity — and the name onscreen is what your weather entity will be named after.

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/postalcode.png)

- Finally, you get to select the real-time weather station closest to you
  (a good guess is provided) and name your location.  You can select no
  weather station if you so desire — useful if there is no real-time
  weather station near where you live — in which case the real-time sensor
  data is simply not provided as sensors.  You may also select a real-time
  precipitation station that is different from your weather station, to get
  rain information closer to where you are.

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/weatherstation.png)

- Your task is done and your integration is working.

![enter image description here](https://github.com/Rudd-O/homeassistant-meteoswiss/raw/master/docs/addedandworking.png)

If you are not happy with the settings, in a future release you
will be able to update them.

## How to create a sensor that has the weather forecast data

Here is a sample of a YAML-based trigger-powered template sensor that creates
three different sensors from a service call every fifteen minutes.  From the
sample code below, you are to modify the `entity_id` to match your own weather
entity ID, then place the adjusted code within your Home Assistant's
`configuration.yaml` file (under `template:` as exemplified below), then
restart Home Assistant.

```yaml
# ...
template:
# ...
  - trigger:
      - platform: time_pattern
        minutes: /15
    action:
      - service: weather.get_forecasts
        data:
          type: daily
        target:
          entity_id: weather.meteoswiss
        response_variable: response_forecast_daily
    sensor:
      - name: Tomorrow Max Temp
        unique_id: d1b441ec-e9c6-43f8-a50a-c7c5c42c0ef5
        state: "{{ response_forecast_daily['weather.meteoswiss'].forecast[1].temperature }}"

      - name: Tomorrow Min Temp
        unique_id: b88a351c-8eb7-40ae-8a9e-dcfeaa224551
        state: "{{ response_forecast_daily['weather.meteoswiss'].forecast[1].templow }}"

      - name: Tomorrow Mean Temp
        unique_id: 6344f875-4569-4c3f-ad8d-ad6bccc5bc61
        state: "{{ ((response_forecast_daily['weather.meteoswiss'].forecast[1].temperature) + (response_forecast_daily['weather.meteoswiss'].forecast[1].templow)) /2}}"
```

You can also create a sensor that will have the list of hourly forecasts
as an attribute you can consult:

```yaml
# ...
template:
# ...
  - trigger:
    - platform: state
      entity_id: weather.biasca_circolo_della_riviera_distretto_di_riviera_2
    - platform: homeassistant
      event: start
    - platform: event
      event_type: event_template_reloaded
    action:
      - service: weather.get_forecasts
        data:
          type: hourly
        target:
          entity_id: weather.biasca_circolo_della_riviera_distretto_di_riviera_2
        response_variable: hourly
    sensor:
      - name: Wettervorhersage Biasca Stuendlich
        unique_id: weather_forecast_biasca_hourly
        state: "{{ now().isoformat() }}"
        attributes:
          forecast: "{{ hourly['weather.biasca_circolo_della_riviera_distretto_di_riviera_2'].forecast }}"
```

That one is very useful to retract awnings and other smart home activities.

## Radar sensors

Every configured location gets three sensors from the MeteoSwiss weather
radar, each read from the 1 km square containing the location and updated
every 5 minutes, usually no more than 1 to 2 minutes behind the weather:

* `<forecast name> radar precipitation`: the rain rate in mm/h (product
  RZC).  A precipitation station reports 10 to 25 minutes late, so this is
  the fastest way for an automation to learn that rain has started.
* `<forecast name> radar hail probability`: the probability of hail in %
  (product POH).
* `<forecast name> radar hail size`: the maximum expected hail size in mm
  (product MESHS).  It is 0 unless hail of at least 20 mm is expected.

The `observation_time` attribute is the end of the 5-minute interval that
the value covers.  A sensor goes unavailable when its product has not
published a new image for 20 minutes.

A radar sees what is in the air above you, not what reaches the ground:
very light drizzle can read 0, and rain that evaporates before landing can
read above 0.  To act on it, use a threshold, for example:

```yaml
template:
  - binary_sensor:
      - name: "Raining"
        device_class: moisture
        delay_off:
          minutes: 15
        state: >
          {{ states('sensor.home_radar_precipitation') | float(0) >= 0.1 }}
      - name: "Hail risk"
        state: >
          {{ states('sensor.home_radar_hail_probability') | float(0) >= 50 }}
```

The location is the one you confirmed when setting up the integration
(entries created before these sensors existed use the Home Assistant home
location).  Each new radar image is downloaded once, 20 to 30 kB per
product every 5 minutes.  Disabling all three sensors stops the downloads.

## Troubleshooting
  
In case of problem with the integration, please open an issue on
[this repository](https://github.com/Rudd-O/homeassistant-meteoswiss)
explaining the issue and attaching the logs in debug mode.

To obtain logs, activate the component debug log in your
`configuration.yaml`, and restarting Home Assistant:

```YAML
logger:
  default: warning
  logs:
    # maybe more stuff here[...]
    hamsclient.client: debug
    hamsclientfork.client: debug
    custom_components.meteoswiss: debug
```

## Upgrade notes / known issues

* It used to be mandatory to select a real-time weather station during setup.
  This step (the last setup step) is now optional — you can select no weather
  station if you so desire (tracked in
  [#6](https://github.com/Rudd-O/homeassistant-meteoswiss/issues/6)
  [#5](https://github.com/Rudd-O/homeassistant-meteoswiss/issues/5)).
* Users of older versions of this integration were not getting updates frequently
  enough.  This should be fixed in the latest versions, with the proviso that
  Home Assistant must be restarted after updating this integration.
* Users of older versions of this integration may experience a problem whereby
  the real-time weather sensors provided by the integration don't update,
  and errors on the log appear frequently regarding this issue.  This is caused
  by an older version of the code letting people configure precipitation stations
  as if they were weather stations.  This is no longer possible, but if you
  have this issue, you'll have to upgrade this integration, delete the configuration
  and re-add it — the erroneous station no longer will appear as an option.
* When you upgrade, a number of entities will be created, and a number of other
  entities will be orphaned.  The recommended upgrade path is to delete the
  existing integration, upgrade, restart Home Assistant, and re-add the integration.
  If you don't do this, you will have to delete entities no longer supplied
  by the integration.  This situation is a one-time thing.  The re-setup step
  is necessary because the old integration did not provide unique IDs.
* There is a migration step in the code that is supposed to migrate away
  from `configuration.yaml` setup.  I have not tested it, but you should know
  that this is deprecated and it will raise a repairs issue to remind you
  to delete the old YAML configuration.

## Information sources

Data comes from the MeteoSwiss official data sources.
Forecasts are extracted from the MeteoSwiss API.
Current conditions are from official data files.
Radar sensors read the RZC, POH and MESHS products of the MeteoSwiss open
data (https://opendatadocs.meteoswiss.ch/d-radar-data).

A primer on Swiss weather stations can be found at https://rudd-o.com/meteostations .
Information on the provided values is available at
[https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/info/VQHA80_en.txt](https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/info/VQHA80_en.txt).

### Privacy

This integration uses:

* https://nominatim.openstreetmap.org to guess your post code
* https://data.geo.admin.ch/ for current weather conditions and radar
  images
* https://www.meteosuisse.admin.ch for forecast

## Origins of this work

This was forked from https://github.com/websylv/homeassistant-meteoswiss because
the original author is unresponsive and the original integration was
broken beyond fixing.  Use this in your Home Assistant by deleting
the original integration, then adding this as a custom HACS repo, and
then reinstalling the integration through this repository.

### How to migrate away from websylv's integration

1. First remove any successfully-setup "Meteo Swiss" (note the space) integrations.
2. Remove the integration itself from HACS.
3. Remove the YAML config you might have been using before.
3. Add this repository as a custom integration repo in HACS, then install it to your Home Assistant.  See above for installation instructions.
4. Restart Home Assistant.
4. Now you can add the integration in Devices & Settings.  See above for setup instructions.
