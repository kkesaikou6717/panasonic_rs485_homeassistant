"""
Switch实体 - 电源开关和度假模式
"""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL
from .modbus_client import FreshAirModbusClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置switch实体"""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]

    entities = [
        PowerSwitch(coordinator, client, entry.entry_id),
        VacationModeSwitch(client, entry.entry_id),
    ]
    async_add_entities(entities)


class PowerSwitch(SwitchEntity):
    """电源开关"""

    _attr_has_entity_name = True
    _attr_name = "电源"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator, client: FreshAirModbusClient, entry_id: str) -> None:
        self.coordinator = coordinator
        self._client = client
        self._attr_unique_id = f"{entry_id}_power"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "新风系统",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def is_on(self) -> bool | None:
        """返回当前电源状态"""
        data = self.coordinator.data or {}
        run_status = data.get("run_status", 0)
        return run_status != 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """开启电源"""
        success = await self._client.set_power(True)
        if success:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭电源"""
        success = await self._client.set_power(False)
        if success:
            await self.coordinator.async_request_refresh()


class VacationModeSwitch(SwitchEntity):
    """度假模式Switch"""

    _attr_has_entity_name = True
    _attr_name = "度假模式"
    _attr_icon = "mdi:island"

    def __init__(self, client: FreshAirModbusClient, entry_id: str) -> None:
        self._client = client
        self._attr_unique_id = f"{entry_id}_vacation_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "新风系统",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def is_on(self) -> bool | None:
        """返回当前度假模式状态"""
        return self._client.vacation_mode

    async def async_turn_on(self, **kwargs: Any) -> None:
        """开启度假模式"""
        success = await self._client.set_vacation_mode(True)
        if success:
            self._client.vacation_mode = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭度假模式"""
        success = await self._client.set_vacation_mode(False)
        if success:
            self._client.vacation_mode = False
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """更新状态"""
        mode = await self._client.get_vacation_mode()
        self._client.vacation_mode = mode
