"""
Select实体 - 运行模式和风速选择
"""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FAN_SPEED_MAP,
    MANUFACTURER,
    MODEL,
    RUN_MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)

# 运行模式选项
RUN_MODE_OPTIONS = [
    "热交换",
    "普通换气",
    "内循环",
    "自动",
    "静音",
    "混风",
]

# 运行模式值映射
RUN_MODE_VALUE_MAP = {
    "热交换": 0x0000,
    "普通换气": 0x0001,
    "内循环": 0x0002,
    "自动": 0x0004,
    "静音": 0x0006,
    "混风": 0x0007,
}

# 风速选项
FAN_SPEED_OPTIONS = [
    "低",
    "高",
]

# 风速值映射
FAN_SPEED_VALUE_MAP = {
    "低": 0x0001,
    "高": 0x0003,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置select实体"""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]["client"]

    entities = [
        RunModeSelect(coordinator, client, entry.entry_id),
        FanSpeedSelect(coordinator, client, entry.entry_id),
    ]
    async_add_entities(entities)


class RunModeSelect(SelectEntity):
    """运行模式选择"""

    _attr_has_entity_name = True
    _attr_name = "运行模式"
    _attr_icon = "mdi:hvac"

    def __init__(self, coordinator, client, entry_id: str) -> None:
        self.coordinator = coordinator
        self._client = client
        self._attr_unique_id = f"{entry_id}_run_mode"
        self._attr_options = RUN_MODE_OPTIONS
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "新风系统",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def current_option(self) -> str | None:
        """获取当前运行模式"""
        data = self.coordinator.data or {}
        run_mode = data.get("run_mode", 0)
        return RUN_MODE_MAP.get(run_mode)

    async def async_select_option(self, option: str) -> None:
        """设置运行模式"""
        mode_value = RUN_MODE_VALUE_MAP.get(option, 0x0001)
        success = await self._client.set_mode(mode_value)
        if success:
            # 同时开启设备
            await self._client.set_power(True)
            await self.coordinator.async_request_refresh()


class FanSpeedSelect(SelectEntity):
    """风速选择"""

    _attr_has_entity_name = True
    _attr_name = "风速"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, client, entry_id: str) -> None:
        self.coordinator = coordinator
        self._client = client
        self._attr_unique_id = f"{entry_id}_fan_speed"
        self._attr_options = FAN_SPEED_OPTIONS
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "新风系统",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def current_option(self) -> str | None:
        """获取当前风速"""
        data = self.coordinator.data or {}
        fan_speed = data.get("fan_speed", 0)
        return FAN_SPEED_MAP.get(fan_speed)

    async def async_select_option(self, option: str) -> None:
        """设置风速"""
        speed_value = FAN_SPEED_VALUE_MAP.get(option, 0x0001)
        success = await self._client.set_fan_speed(speed_value)
        if success:
            await self.coordinator.async_request_refresh()
