"""Sensor platform per MOM Bus (setup via ConfigEntry)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_COD_FERMATA, CONF_LINE, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MomBusSensor(
                coordinator,
                cod_fermata=entry.data[CONF_COD_FERMATA],
                line_filter=entry.data.get(CONF_LINE) or None,
                name=entry.title,
                unique_id=entry.entry_id,
            )
        ],
        True,
    )


class MomBusSensor(CoordinatorEntity, SensorEntity):
    """Sensore: minuti al prossimo passaggio (linea specifica o tutte)."""

    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:bus-clock"
    _attr_has_entity_name = False

    def __init__(self, coordinator, cod_fermata: str, line_filter: str | None, name: str, unique_id: str) -> None:
        super().__init__(coordinator)
        self._cod_fermata = cod_fermata
        self._line_filter = line_filter
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def _passaggi(self) -> list[dict]:
        data = self.coordinator.data or []
        if self._line_filter:
            return [p for p in data if str(p["line"]) == str(self._line_filter)]
        return data

    @property
    def native_value(self):
        passaggi = self._passaggi
        return passaggi[0]["minutes"] if passaggi else None

    @property
    def extra_state_attributes(self):
        # Lista unica: include anche il prossimo passaggio (indice 0),
        # cosi' non serve piu' controllare stato + "upcoming" separatamente.
        return {"passaggi": self._passaggi[:6]}
