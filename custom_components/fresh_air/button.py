"""
Button实体 - 同步时间
"""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置button实体"""
    client = hass.data[DOMAIN][entry.entry_id]["client"]
    entity = SyncTimeButton(client, entry.entry_id)
    async_add_entities([entity])


class SyncTimeButton(ButtonEntity):
    """同步时间按钮"""

    _attr_has_entity_name = True
    _attr_name = "同步时间"
    _attr_icon = "mdi:clock-sync"

    def __init__(self, client, entry_id: str) -> None:
        self._client = client
        self._attr_unique_id = f"{entry_id}_sync_time"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "新风系统",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    async def async_press(self) -> None:
        """同步时间"""
        success = await self._client.sync_time()
        if success:
            _LOGGER.info("时间同步成功")
        else:
            _LOGGER.error("时间同步失败")
