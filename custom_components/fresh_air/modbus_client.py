"""
Modbus客户端封装
"""

import asyncio
import logging
from typing import Any, Optional

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType

from .const import (
    REG_CO2_RA,
    REG_FAN_SPEED,
    REG_HUMIDITY_OA,
    REG_HUMIDITY_RA,
    REG_PM25_OA,
    REG_PM25_RA,
    REG_PM25_SA,
    REG_RUN_MODE,
    REG_RUN_STATUS,
    REG_TEMP_OA,
    REG_TEMP_RA,
    REG_TEMP_SA,
    REG_TVOC_RA,
    REG_VACATION_MODE,
)

_LOGGER = logging.getLogger(__name__)


class FreshAirModbusClient:
    """新风系统Modbus客户端"""

    def __init__(self, host: str, port: int, slave: int = 1):
        """初始化客户端"""
        self.host = host
        self.port = port
        self.slave = slave
        self._client: Optional[AsyncModbusTcpClient] = None
        self._lock = asyncio.Lock()
        self.vacation_mode: Optional[bool] = None

    @property
    def connected(self) -> bool:
        """检查连接状态"""
        return self._client is not None and self._client.connected

    async def connect(self) -> bool:
        """连接Modbus网关"""
        try:
            self._client = AsyncModbusTcpClient(
                self.host,
                port=self.port,
                framer=FramerType.SOCKET,
            )
            connected = await self._client.connect()
            if connected:
                _LOGGER.info("已连接到 %s:%s", self.host, self.port)
            else:
                _LOGGER.error("无法连接到 %s:%s", self.host, self.port)
            return connected
        except Exception as e:
            _LOGGER.error("连接异常: %s", e)
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            self._client.close()
            self._client = None
            _LOGGER.info("已断开连接")

    async def read_register(self, address: int, count: int = 1) -> Optional[list[int]]:
        """读取寄存器"""
        async with self._lock:
            try:
                if not self.connected:
                    _LOGGER.warning("未连接，无法读取寄存器")
                    return None

                result = await self._client.read_holding_registers(
                    address=address,
                    count=count,
                )
                if result.isError():
                    _LOGGER.error("读取寄存器0x%04X错误: %s", address, result)
                    return None
                return result.registers
            except ModbusException as e:
                _LOGGER.error("Modbus异常: %s", e)
                return None
            except Exception as e:
                _LOGGER.error("读取寄存器异常: %s", e)
                return None

    async def write_register(self, address: int, values: list[int]) -> bool:
        """写入寄存器（多寄存器写入0x10）"""
        async with self._lock:
            try:
                if not self.connected:
                    _LOGGER.warning("未连接，无法写入寄存器")
                    return False

                result = await self._client.write_registers(
                    address=address,
                    values=values,
                )
                if result.isError():
                    _LOGGER.error("写入寄存器0x%04X错误: %s", address, result)
                    return False
                _LOGGER.debug("成功写入寄存器0x%04X: %s", address, values)
                return True
            except ModbusException as e:
                _LOGGER.error("Modbus异常: %s", e)
                return False
            except Exception as e:
                _LOGGER.error("写入寄存器异常: %s", e)
                return False

    async def read_all_sensors(self) -> dict[str, Any]:
        """读取所有传感器数据"""
        data = {}

        # 读取运转状态 (0x0020-0x0022)
        status_data = await self.read_register(REG_RUN_STATUS, 3)
        if status_data:
            data["run_status"] = status_data[0]
            data["run_mode"] = status_data[1]
            data["fan_speed"] = status_data[2]

        # 读取PM2.5 (0x0070, 0x0071, 0x0072)
        data["pm25_oa"] = self._parse_pm25(await self._read_single(REG_PM25_OA))
        data["pm25_sa"] = self._parse_pm25(await self._read_single(REG_PM25_SA))
        data["pm25_ra"] = self._parse_pm25(await self._read_single(REG_PM25_RA))

        # 读取湿度 (0x0073, 0x0075)
        data["humidity_oa"] = self._parse_humidity(await self._read_single(REG_HUMIDITY_OA))
        data["humidity_ra"] = self._parse_humidity(await self._read_single(REG_HUMIDITY_RA))

        # 读取温度 (0x0076, 0x0077, 0x0078)
        data["temp_oa"] = self._parse_temperature(await self._read_single(REG_TEMP_OA))
        data["temp_sa"] = self._parse_temperature(await self._read_single(REG_TEMP_SA))
        data["temp_ra"] = self._parse_temperature(await self._read_single(REG_TEMP_RA))

        # 读取CO2 (0x007B)
        data["co2_ra"] = await self._read_single(REG_CO2_RA)

        # 读取TVOC (0x007E)
        data["tvoc_ra"] = self._parse_tvoc(await self._read_single(REG_TVOC_RA))

        return data

    async def _read_single(self, address: int) -> Optional[int]:
        """读取单个寄存器的值"""
        result = await self.read_register(address, 1)
        if result:
            return result[0]
        return None

    def _parse_pm25(self, value: int) -> Optional[float]:
        """解析PM2.5值"""
        if value == 0xFFFF or value > 5000:
            return None
        return float(value)

    def _parse_humidity(self, value: int) -> Optional[float]:
        """解析湿度值 - 直接十进制值，0xFFFF表示无数据"""
        if value == 0xFFFF:
            return None
        if value > 100:
            return None
        return float(value)

    def _parse_temperature(self, value: int) -> Optional[float]:
        """解析温度值（INT16，寄存器返回的值可能需要除以10）
        - 正值直接返回
        - 0x7FFF = 无有效数据
        - 0xFFFE/0xFFFD = 传感器无效
        - 0xFFFF = 无有效数据
        """
        # 检查无效值
        if value == 0x7FFF or value == 0xFFFF or value >= 0xFFFE:
            return None  # 无有效数据
        
        # 有符号整数解析
        if value & 0x8000:
            # 负数
            temp = -(value & 0x7FFF)
        else:
            # 正数
            temp = value
        
        # 检查范围是否合理 (-50 ~ 80°C)
        if temp < -50 or temp > 80:
            return None
        
        return float(temp / 10.0)  # 一位小数

    def _parse_tvoc(self, value: int) -> Optional[int]:
        """解析TVOC值 - Level 0-5"""
        if value == 0xFFFF or value > 5:
            return None
        return value

    async def set_power(self, on: bool) -> bool:
        """设置电源开关"""
        value = 1 if on else 0
        return await self.write_register(REG_RUN_STATUS, [value])

    async def set_mode(self, mode: int) -> bool:
        """设置运行模式"""
        return await self.write_register(REG_RUN_MODE, [mode])

    async def set_fan_speed(self, speed: int) -> bool:
        """设置风量"""
        return await self.write_register(REG_FAN_SPEED, [speed])

    async def get_vacation_mode(self) -> Optional[bool]:
        """获取度假模式状态"""
        value = await self._read_single(REG_VACATION_MODE)
        if value is None:
            return None
        return value == 1

    async def set_vacation_mode(self, on: bool) -> bool:
        """设置度假模式
        on: True=开启, False=关闭
        """
        value = 1 if on else 0
        return await self.write_register(REG_VACATION_MODE, [value])

    async def sync_time(self) -> bool:
        """同步网络时间
        寄存器格式：
        0x0014: 年 (跳过=0xFFFF)
        0x0015: [高=分][低=秒(skip=0xFF)]
        0x0016: [高=周(1-7)][低=时(0-23)]
        0x0017: [高=月(1-12)][低=日(1-31)]
        """
        import datetime

        now = datetime.datetime.now()
        # weekday(): 0=周一, 6=周日
        weekday = (now.weekday() + 1) % 7  # 转换为: 1=周一, 7=周日

        values = [
            0xFFFF,                                          # 0x0014: 年跳过
            ((now.minute & 0xFF) << 8) | 0xFF,           # 0x0015: [高=分][低=秒(skip=FF)]
            ((weekday & 0xFF) << 8) | (now.hour & 0xFF), # 0x0016: [高=周][低=时]
            0xFFFF,                                          # 0x0017: 月日跳过
        ]

        return await self.write_register(0x0014, values)
