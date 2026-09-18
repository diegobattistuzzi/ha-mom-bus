<p align="center">
  <img src="assets/banner.png" alt="MyCicero for Home Assistant" width="320">
</p>

# MOM Bus (Mobilità di Marca) for Home Assistant

Unofficial Home Assistant integration that shows the next bus arrivals for a MOM (Mobilità di Marca, Veneto, Italy) stop, using the public (undocumented) API of the [myCicero](https://www.mycicero.it/) portal.

> Unofficial integration, not affiliated with MOM or myCicero/PluService. The APIs used are not publicly documented and may change without notice.

## Features

- Sensor showing minutes until the next bus at a stop, optionally filtered by line.
- Attributes with the list of upcoming arrivals (line, destination, time, delay, whether real-time).
- Configured entirely through the UI (config flow), no YAML required.

## Installation

### Via HACS

1. In HACS, add this repository as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/): `diegobattistuzzi/ha-mom-bus`.
2. Search for "MOM Bus" among the integrations and install it.
3. Restart Home Assistant.

### Manual

Copy the `custom_components/mom_bus` folder into `<config>/custom_components/` and restart Home Assistant.

## Configuration

After installation, go to **Settings → Devices & services → Add integration** and search for "MOM Bus". Enter the stop code (visible in the stop's URL on myCicero) and, optionally, the line code to filter by.

## Disclaimer

Hobby project based on observing myCicero's network traffic. No guarantee of continued functionality.
