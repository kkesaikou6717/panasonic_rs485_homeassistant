"""
常量定义
"""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)

# 域名
DOMAIN = "fresh_air"

# 配置项
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE = "slave"

# 更新间隔（秒）
UPDATE_INTERVAL = 30

# 平台
PLATFORMS = ["sensor", "switch", "button", "select"]

# 寄存器地址
REG_RUN_STATUS = 0x0020
REG_RUN_MODE = 0x0021
REG_FAN_SPEED = 0x0022
REG_VACATION_MODE = 0x0027
REG_TEMP_OA = 0x0076
REG_TEMP_SA = 0x0077
REG_TEMP_RA = 0x0078
REG_HUMIDITY_OA = 0x0073
REG_HUMIDITY_RA = 0x0075
REG_PM25_OA = 0x0070
REG_PM25_SA = 0x0071
REG_PM25_RA = 0x0072
REG_CO2_RA = 0x007B
REG_TVOC_RA = 0x007E

# 运行模式映射 (寄存器值 -> 中文显示)
RUN_MODE_MAP = {
    0x0000: "热交换",
    0x0001: "普通换气",
    0x0002: "内循环",
    0x0004: "自动",
    0x0006: "静音",
    0x0007: "混风",
}

# 风量映射 (寄存器值 -> 中文显示)
FAN_SPEED_MAP = {
    0x0001: "低",
    0x0003: "高",
}

# 设备信息
MANUFACTURER = "Fresh Air"
MODEL = "Modbus Ventilation"
