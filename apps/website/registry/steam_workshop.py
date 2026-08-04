import json
from django.conf import settings
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STEAM_WORKSHOP_DETAILS_URL = (
    "https://api.steampowered.com/ISteamRemoteStorage/"
    "GetPublishedFileDetails/v1/"
)
PROJECT_ZOMBOID_APP_ID = 108600
STEAM_WORKSHOP_QUERY_URL = (
    "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
)


class SteamWorkshopError(Exception):
    pass


def fetch_project_zomboid_workshop_item(workshop_id):
    body = urlencode(
        {"itemcount": "1", "publishedfileids[0]": str(workshop_id)}
    ).encode("ascii")
    request = Request(
        STEAM_WORKSHOP_DETAILS_URL,
        data=body,
        headers={"User-Agent": "TGSRR-Website/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SteamWorkshopError(
            "Steam could not validate that Workshop item. Please try again later."
        ) from exc

    details = payload.get("response", {}).get("publishedfiledetails", [])
    item = details[0] if details else {}
    if str(item.get("publishedfileid", "")) != str(workshop_id) or item.get("result") != 1:
        raise SteamWorkshopError("That Steam Workshop item could not be found.")
    if int(item.get("consumer_app_id") or 0) != PROJECT_ZOMBOID_APP_ID:
        raise SteamWorkshopError("That Workshop item is not for Project Zomboid.")
    return {
        "workshop_id": str(workshop_id),
        "title": str(item.get("title") or f"Workshop item {workshop_id}")[:255],
        "steam_url": (
            "https://steamcommunity.com/sharedfiles/filedetails/"
            f"?id={workshop_id}"
        ),
        "preview_url": str(item.get("preview_url") or "")[:1000],
        "creator_steam_id": str(item.get("creator") or "")[:32],
    }


def search_project_zomboid_workshop_items(search_text, *, limit=8):
    api_key = settings.STEAM_WEB_API_KEY
    if not api_key:
        raise SteamWorkshopError(
            "Workshop name search is temporarily unavailable. Paste a Workshop ID or URL instead."
        )
    query = urlencode(
        {
            "key": api_key,
            "query_type": "12",
            "page": "1",
            "cursor": "*",
            "numperpage": str(limit),
            "creator_appid": str(PROJECT_ZOMBOID_APP_ID),
            "appid": str(PROJECT_ZOMBOID_APP_ID),
            "search_text": str(search_text),
            "filetype": "0",
            "return_short_description": "true",
            "return_previews": "true",
        }
    )
    request = Request(
        f"{STEAM_WORKSHOP_QUERY_URL}?{query}",
        headers={"User-Agent": "TGSRR-Website/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SteamWorkshopError(
            "Steam could not search the Workshop. Please try again later."
        ) from exc

    results = []
    for item in payload.get("response", {}).get("publishedfiledetails", []):
        workshop_id = str(item.get("publishedfileid") or "")
        if (
            not workshop_id.isdigit()
            or int(item.get("consumer_appid") or 0) != PROJECT_ZOMBOID_APP_ID
        ):
            continue
        results.append(
            {
                "workshop_id": workshop_id,
                "title": str(item.get("title") or f"Workshop item {workshop_id}")[:255],
                "steam_url": (
                    "https://steamcommunity.com/sharedfiles/filedetails/"
                    f"?id={workshop_id}"
                ),
                "preview_url": str(item.get("preview_url") or "")[:1000],
                "creator_steam_id": str(item.get("creator") or "")[:32],
            }
        )
    return results
