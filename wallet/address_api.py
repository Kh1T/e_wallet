"""Server-side client for the USP Cambodia address API.

The bearer token remains on the Django server; it is never sent to the browser.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings


class AddressAPIError(Exception):
    """The USP address service could not complete a request."""


def get_address_data(path: str):
    if not settings.BUNLI_ADDRESS_API_TOKEN:
        raise AddressAPIError('USP_ADDRESS_API_TOKEN is not configured.')

    request = Request(
        f"{settings.BUNLI_ADDRESS_API_URL}/{path.lstrip('/')}",
        headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {settings.BUNLI_ADDRESS_API_TOKEN}',
        },
        method='GET',
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        raise AddressAPIError(f'USP address service returned HTTP {exc.code}.') from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise AddressAPIError('USP address service is unavailable or returned invalid JSON.') from exc


def get_provinces():
    return get_address_data('/addresses/provinces')


def get_districts(province: str):
    return get_address_data(f'/addresses/provinces/{quote(str(province), safe="")}/districts')


def get_communes(district: str):
    return get_address_data(f'/addresses/districts/{quote(str(district), safe="")}/communes')


def get_villages(commune: str):
    return get_address_data(f'/addresses/communes/{quote(str(commune), safe="")}/villages')
