"""
Sensor实体
"""

import logging
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


# 传感器配置
SENSORS = [
    # 室外新风 (Outdoor Air)
    {
        "key": "temp_oa",
        "name": "室外新风温度",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "humidity_oa",
        "name": "室外新风湿度",
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "icon": "mdi:water-percent",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "pm25_oa",
        "name": "室外新风PM2.5",
        "device_class": SensorDeviceClass.PM25,
        "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "icon": "mdi:air-filter",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    # 送风 (Supply Air)
    {
        "key": "temp_sa",
        "name": "送风温度",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "pm25_sa",
        "name": "送风PM2.5",
        "device_class": SensorDeviceClass.PM25,
        "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "icon": "mdi:air-filter",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    # 室内回风 (Return Air)
    {
        "key": "temp_ra",
        "name": "室内回风温度",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "humidity_ra",
        "name": "室内回风湿度",
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "icon": "mdi:water-percent",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "pm25_ra",
        "name": "室内回风PM2.5",
        "device_class": SensorDeviceClass.PM25,
        "unit": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "icon": "mdi:air-filter",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "co2_ra",
        "name": "室内回风CO2",
        "device_class": SensorDeviceClass.CO2,
        "unit": "ppm",
        "icon": "mdi:molecule-co2",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "tvoc_ra",
        "name": "室内回风TVOC",
        "device_class": None,
        "unit": "level",
        "icon": "mdi:chemical-weapon",
        "state_class": SensorStateClass.MEASUREMENT,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置sensor平台"""
    entry_id = config_entry.entry_id
    coordinator = hass.data[DOMAIN][entry_id]["coordinator"]

    entities = []
    for sensor_config in SENSORS:
        entity = FreshAirSensor(coordinator, config_entry, sensor_config)
        entities.append(entity)

    async_add_entities(entities)


class FreshAirSensor(SensorEntity):
    """新风系统传感器实体"""

    def __init__(self, coordinator, config_entry, sensor_config) -> None:
        """初始化实体"""
        super().__init__()
        self.coordinator = coordinator
        self._config = sensor_config
        self._key = sensor_config["key"]

        self._attr_has_entity_name = True
        self._attr_name = sensor_config["name"]
        self._attr_unique_id = f"{config_entry.entry_id}_{self._key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "新风系统",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

        self._attr_device_class = sensor_config.get("device_class")
        self._attr_native_unit_of_measurement = sensor_config.get("unit")
        self._attr_icon = sensor_config.get("icon")
        self._attr_state_class = sensor_config.get("state_class")

    @property
    def available(self) -> bool:
        """检查是否可用"""
        return self.coordinator.last_update_success

    @property
    def data(self) -> dict[str, Any]:
        """获取协调器数据"""
        return self.coordinator.data or {}

    @property
    def native_value(self) -> Optional[Any]:
        """获取传感器值"""
        value = self.data.get(self._key)
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """额外属性"""
        attrs = {}
        if self._key == "tvoc_ra" and self.native_value is not None:
            level = self.native_value
            level_names = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]
            attrs["空气质量"] = level_names[min(level, 5)] if level <= 5 else "未知"
        return attrs
