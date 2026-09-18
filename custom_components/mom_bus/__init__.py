"""Integrazione non ufficiale per gli arrivi/partenze real-time di MOM (Mobilità di Marca)."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MomBusApiError, async_fetch_passaggi
from .const import (
    CONF_COD_AZIENDA,
    CONF_COD_FERMATA,
    CONF_ID_SISTEMA,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


class MomBusCoordinator(DataUpdateCoordinator):
    """Interroga periodicamente l'endpoint myCicero per una fermata."""

    def __init__(self, hass: HomeAssistant, cod_fermata: str, cod_azienda: str, id_sistema: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"mom_bus_{cod_fermata}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._session = async_get_clientsession(hass)
        self.cod_fermata = cod_fermata
        self.cod_azienda = cod_azienda
        self.id_sistema = id_sistema

    async def _async_update_data(self) -> list[dict]:
        try:
            return await async_fetch_passaggi(
                self._session, self.cod_fermata, self.cod_azienda, self.id_sistema
            )
        except MomBusApiError as err:
            raise UpdateFailed(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Crea il coordinator per questa voce di configurazione e avvia il primo refresh."""
    coordinator = MomBusCoordinator(
        hass,
        cod_fermata=entry.data[CONF_COD_FERMATA],
        cod_azienda=entry.data[CONF_COD_AZIENDA],
        id_sistema=entry.data[CONF_ID_SISTEMA],
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
