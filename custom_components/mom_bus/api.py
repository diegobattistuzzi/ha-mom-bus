"""Client per l'endpoint (non ufficiale) GetArriviPartenzePalina2 di myCicero/MOM."""
from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import aiohttp

from .const import (
    BASE_URL,
    DEFAULT_COD_AZIENDA,
    DEFAULT_ID_SISTEMA,
    FERMATE_CORSA_URL,
)

ROME = ZoneInfo("Europe/Rome")
DOTNET_DATE_RE = re.compile(r"/Date\((-?\d+)([+-]\d{4})?\)/")


class MomBusApiError(Exception):
    """Errore generico nella comunicazione con l'API MOM/myCicero."""


def _dotnet_date_to_dt(value: str) -> datetime:
    match = DOTNET_DATE_RE.match(value)
    if not match:
        raise MomBusApiError(f"Formato data inatteso: {value}")
    ms = int(match.group(1))
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(ROME)


def _build_dotnet_date(dt: datetime) -> str:
    ms = int(dt.timestamp() * 1000)
    return f"/Date({ms}+0200)/"


def _build_security_token(dt: datetime) -> str:
    centisecondi = dt.microsecond // 10000
    raw = dt.strftime(f"%m-%d-%Y %H:%M%S{centisecondi:02d}")
    return base64.b64encode(raw.encode()).decode()


async def async_fetch_passaggi(
    session: aiohttp.ClientSession,
    cod_fermata: str,
    cod_azienda: str = DEFAULT_COD_AZIENDA,
    id_sistema: str = DEFAULT_ID_SISTEMA,
) -> list[dict]:
    """Interroga l'API e restituisce la lista di passaggi già "puliti"."""
    now = datetime.now(ROME)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    finestra_fine = now + timedelta(hours=8)

    payload = {
        "CodAzienda": cod_azienda,
        "CodFermata": cod_fermata,
        "CodiceLinea": None,
        "DevicePosition": None,
        "Giorno": _build_dotnet_date(midnight),
        "IdDevice": "DEBUG",
        "IdSistema": id_sistema,
        "Lingua": "it",
        "MaxNumeroPassaggi": {"NumeroRisultati": 20},
        "MaxNumeroPassaggiLinee": {"NumeroRisultati": 0},
        "OraA": _build_dotnet_date(finestra_fine),
        "OraDa": _build_dotnet_date(now),
        "SecurityToken": _build_security_token(now),
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "it-IT,it;q=0.9",
        "client": "tpwebportal;5.5.4",
        "content-type": "application/json",
        "culture": "it-IT",
        "ignore-momo-type": "true",
        "referer": (
            f"https://www.mycicero.it/orari-trasporto/it/timetable/stops/"
            f"{cod_fermata}?systemId={id_sistema}&businessCode={cod_azienda}"
        ),
        "origin": "https://www.mycicero.it",
    }

    try:
        async with session.post(BASE_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            raw = await resp.json(content_type=None)
    except aiohttp.ClientError as err:
        raise MomBusApiError(f"Errore di rete verso myCicero: {err}") from err

    passaggi_raw = (raw.get("Oggetto") or {}).get("Passaggi") or []
    now_local = datetime.now(ROME)

    risultati = []
    for p in passaggi_raw:
        percorso = p.get("Percorso") or {}
        passaggio_dt = _dotnet_date_to_dt(p["DataOraPassaggio"])
        corsa = p.get("Corsa") or {}
        risultati.append({
            "line": percorso.get("Codice"),
            "destination": percorso.get("DestinazioneUtenza"),
            "time": passaggio_dt.strftime("%H:%M"),
            "minutes": round((passaggio_dt - now_local).total_seconds() / 60),
            "delay_minutes": p.get("MinutiScostamento"),
            "realtime": bool(p.get("isPassaggioRealTime")),
            "corsa": corsa.get("Codice"),
            "id_corsa": corsa.get("ID_Corsa"),
            "percorso_codice": percorso.get("Codice"),
            "corsa_data_partenza": corsa.get("DataOraPartenza"),
        })

    risultati.sort(key=lambda r: r["minutes"])
    return risultati


async def async_fetch_fermate_corsa(
    session: aiohttp.ClientSession,
    id_corsa: str,
    percorso_codice: str,
    corsa_data_partenza: str,
    cod_azienda: str = DEFAULT_COD_AZIENDA,
    id_sistema: str = DEFAULT_ID_SISTEMA,
) -> list[dict]:
    """Interroga GetFermateCorsa2 e restituisce l'elenco fermate/orari di una corsa.

    `id_corsa`, `percorso_codice` e `corsa_data_partenza` sono i valori
    "id_corsa", "percorso_codice" e "corsa_data_partenza" già presenti nei
    risultati di `async_fetch_passaggi`.
    """
    now = datetime.now(ROME)
    giorno = _dotnet_date_to_dt(corsa_data_partenza).replace(hour=0, minute=0, second=0, microsecond=0)

    payload = {
        "CodiceAzienda": cod_azienda,
        "CodicePercorso": percorso_codice,
        "Giorno": _build_dotnet_date(giorno),
        "IdCorsa": id_corsa,
        "IdSistema": id_sistema,
        "IdStazioneDiscesa": None,
        "IdStazioneSalita": None,
        "Lingua": "it",
        "SecurityToken": _build_security_token(now),
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "it-IT,it;q=0.9",
        "client": "tpwebportal;5.5.4",
        "content-type": "application/json",
        "culture": "it-IT",
    }

    try:
        async with session.post(
            FERMATE_CORSA_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            raw = await resp.json(content_type=None)
    except aiohttp.ClientError as err:
        raise MomBusApiError(f"Errore di rete verso myCicero: {err}") from err

    fermate_raw = (raw.get("Oggetto") or {}).get("Fermate") or []

    risultati = []
    for f in fermate_raw:
        localita = f.get("Localita") or {}
        orario_dt = _dotnet_date_to_dt(f["Orario"]) if f.get("Orario") else None
        risultati.append({
            "cod_fermata": localita.get("Codice"),
            "name": localita.get("Descrizione"),
            "stop_sequence": localita.get("StopSequence"),
            "time": orario_dt.strftime("%H:%M") if orario_dt else None,
        })

    return risultati
