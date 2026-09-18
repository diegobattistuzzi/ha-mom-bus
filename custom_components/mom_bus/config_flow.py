"""Config flow per MOM Bus."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MomBusApiError, async_fetch_passaggi
from .const import (
    CONF_COD_AZIENDA,
    CONF_COD_FERMATA,
    CONF_ID_SISTEMA,
    CONF_LINE,
    DEFAULT_COD_AZIENDA,
    DEFAULT_ID_SISTEMA,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COD_FERMATA): str,
        vol.Optional(CONF_LINE, default=""): str,
        vol.Optional(CONF_NAME, default=""): str,
    }
)

STEP_ADVANCED_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_COD_AZIENDA, default=DEFAULT_COD_AZIENDA): str,
        vol.Optional(CONF_ID_SISTEMA, default=DEFAULT_ID_SISTEMA): str,
    }
)


async def _validate_stop(hass: HomeAssistant, cod_fermata: str, cod_azienda: str, id_sistema: str) -> None:
    """Verifica che la fermata esista e risponda, sollevando MomBusApiError altrimenti."""
    session = async_get_clientsession(hass)
    # Una chiamata di prova; se la fermata non esiste l'API risponde comunque
    # con lista vuota, quindi qui verifichiamo solo che la richiesta vada a buon fine.
    await async_fetch_passaggi(session, cod_fermata, cod_azienda, id_sistema)


class MomBusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione da UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cod_fermata = user_input[CONF_COD_FERMATA].strip()
            line = user_input.get(CONF_LINE, "").strip() or None

            unique_id = f"{DEFAULT_COD_AZIENDA}_{cod_fermata}_{line or 'all'}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            self._user_input = {
                CONF_COD_FERMATA: cod_fermata,
                CONF_LINE: line,
                CONF_NAME: user_input.get(CONF_NAME, "").strip() or None,
            }
            return await self.async_step_advanced()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            cod_azienda = user_input.get(CONF_COD_AZIENDA, DEFAULT_COD_AZIENDA).strip()
            id_sistema = user_input.get(CONF_ID_SISTEMA, DEFAULT_ID_SISTEMA).strip()
            cod_fermata = self._user_input[CONF_COD_FERMATA]

            try:
                await _validate_stop(self.hass, cod_fermata, cod_azienda, id_sistema)
            except MomBusApiError:
                _LOGGER.exception("Errore validando la fermata %s", cod_fermata)
                errors["base"] = "cannot_connect"
            else:
                line = self._user_input[CONF_LINE]
                default_name = f"Bus fermata {cod_fermata}" + (f" linea {line}" if line else "")
                title = self._user_input[CONF_NAME] or default_name

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_COD_FERMATA: cod_fermata,
                        CONF_LINE: line,
                        CONF_COD_AZIENDA: cod_azienda,
                        CONF_ID_SISTEMA: id_sistema,
                        CONF_NAME: title,
                    },
                )

        return self.async_show_form(
            step_id="advanced", data_schema=STEP_ADVANCED_SCHEMA, errors=errors
        )
