"""
Modbus客户端封装（支持断线自动重连与请求重发）
"""

import asyncio
import logging
from typing import Any, Optional

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException, ModbusIOException
try:
    from pymodbus.framer import FramerType
except ImportError:  # pymodbus < 3.7
    from pymodbus.framer import Framer as FramerType

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

# 每个读写操作的尝试次数：第一次失败后重连再发一次
MAX_ATTEMPTS = 2
# 连接/请求超时（秒）
CONNECT_TIMEOUT = 5.0


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

    def _build_client(self) -> AsyncModbusTcpClient:
        """创建 pymodbus 客户端"""
        return AsyncModbusTcpClient(
            self.host,
            port=self.port,
            framer=FramerType.SOCKET,
            timeout=CONNECT_TIMEOUT,
            retries=1,
        )

    def _drop_client(self) -> None:
        """丢弃失效连接"""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.debug("关闭旧连接时出现异常", exc_info=True)
            self._client = None

    async def _ensure_connected(self) -> bool:
        """确保连接存在；连接失效时重建并重连。"""
        if self._client is not None and self._client.connected:
            return True

        self._drop_client()
        self._client = self._build_client()
        try:
            connected = await self._client.connect()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("连接 %s:%s 异常: %s", self.host, self.port, exc)
            connected = False

        if connected:
            _LOGGER.info("已连接 %s:%s", self.host, self.port)
        return connected

    async def connect(self) -> bool:
        """连接Modbus网关"""
        async with self._lock:
            return await self._ensure_connected()

    async def disconnect(self) -> None:
        """断开连接"""
        async with self._lock:
            self._drop_client()
            _LOGGER.info("已断开连接")

    @staticmethod
    def _is_recoverable(err: Optional[BaseException]) -> bool:
        """判断是否为可恢复的通信层错误"""
        return isinstance(
            err, (ConnectionException, ModbusIOException, ConnectionError, OSError, TimeoutError)
        )

    async def _read_once(
        self, address: int, count: int
    ) -> tuple[Optional[list[int]], Optional[BaseException]]:
        """执行一次读请求。成功返回 (寄存器列表, None)，失败返回 (None, 错误)。"""
        try:
            result = await self._client.read_holding_registers(
                address=address,
                count=count,
            )
        except asyncio.CancelledError:
            raise
        except (ModbusException, OSError, TimeoutError) as exc:
            return None, exc
        if result.isError():
            return None, result
        return result.registers, None

    async def _read_single_once(
        self, address: int
    ) -> tuple[Optional[int], Optional[BaseException]]:
        """读取单个寄存器，返回 (值, 错误)。"""
        registers, err = await self._read_once(address, 1)
        if registers is None:
            return None, err
        return registers[0], None

    async def read_register(self, address: int, count: int = 1) -> Optional[list[int]]:
        """读取寄存器，通信失败时重连并重发一次"""
        async with self._lock:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if not await self._ensure_connected():
                    _LOGGER.warning("连接不可用，放弃读取寄存器0x%04X", address)
                    return None

                registers, err = await self._read_once(address, count)
                if registers is not None:
                    return registers

                if attempt < MAX_ATTEMPTS and self._is_recoverable(err):
                    _LOGGER.warning(
                        "读取寄存器0x%04X失败（%s），重连后重试", address, err
                    )
                    self._drop_client()
                    continue

                _LOGGER.error("读取寄存器0x%04X失败: %s", address, err)
                return None
            return None

    async def _write_once(
        self, address: int, values: list[int]
    ) -> tuple[bool, Optional[BaseException]]:
        """执行一次写请求（0x10 多寄存器写入）。"""
        try:
            result = await self._client.write_registers(
                address=address,
                values=values,
            )
        except asyncio.CancelledError:
            raise
        except (ModbusException, OSError, TimeoutError) as exc:
            return False, exc
        if result.isError():
            return False, result
        return True, None

    async def write_register(self, address: int, values: list[int]) -> bool:
        """写入寄存器，通信失败时重连并重发一次"""
        async with self._lock:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if not await self._ensure_connected():
                    _LOGGER.warning("连接不可用，放弃写入寄存器0x%04X", address)
                    return False

                ok, err = await self._write_once(address, values)
                if ok:
                    _LOGGER.debug("成功写入寄存器0x%04X: %s", address, values)
                    return True

                if attempt < MAX_ATTEMPTS and self._is_recoverable(err):
                    _LOGGER.warning(
                        "写入寄存器0x%04X失败（%s），重连后重试", address, err
                    )
                    self._drop_client()
                    continue

                _LOGGER.error("写入寄存器0x%04X失败: %s", address, err)
                return False
            return False

    async def _append_sensor(
        self,
        data: dict[str, Any],
        key: str,
        address: int,
        parser=None,
    ) -> None:
        """读取单个传感器并放入 data；通信层断线时抛错中断本轮。"""
        value, err = await self._read_single_once(address)
        if err is not None and self._is_recoverable(err):
            raise ModbusException(
                f"读取{key}（0x{address:04X}）时连接中断: {err}"
            ) from err
        data[key] = parser(value) if parser else value

    async def read_all_sensors(self) -> dict[str, Any]:
        """读取所有传感器/状态数据（coordinator 每轮采集调用一次）。"""
        async with self._lock:
            if not await self._ensure_connected():
                raise ConnectionError(f"无法连接Modbus网关 {self.host}:{self.port}")

            data: dict[str, Any] = {}

            # 读取运转状态 (0x0020-0x0022)
            status_regs, err = await self._read_once(REG_RUN_STATUS, 3)
            if status_regs is None and err is not None and self._is_recoverable(err):
                raise ModbusException(f"读取状态寄存器失败: {err}") from err
            if status_regs is not None:
                data["run_status"] = status_regs[0]
                data["run_mode"] = status_regs[1]
                data["fan_speed"] = status_regs[2]

            # 环境传感器（每个地址一次读取，解析规则来自 rs485.csv）
            await self._append_sensor(data, "pm25_oa", REG_PM25_OA, self._parse_pm25)
            await self._append_sensor(data, "pm25_sa", REG_PM25_SA, self._parse_pm25)
            await self._append_sensor(data, "pm25_ra", REG_PM25_RA, self._parse_pm25)

            await self._append_sensor(data, "humidity_oa", REG_HUMIDITY_OA, self._parse_humidity)
            await self._append_sensor(data, "humidity_ra", REG_HUMIDITY_RA, self._parse_humidity)

            await self._append_sensor(data, "temp_oa", REG_TEMP_OA, self._parse_temperature)
            await self._append_sensor(data, "temp_sa", REG_TEMP_SA, self._parse_temperature)
            await self._append_sensor(data, "temp_ra", REG_TEMP_RA, self._parse_temperature)

            await self._append_sensor(data, "co2_ra", REG_CO2_RA)
            await self._append_sensor(data, "tvoc_ra", REG_TVOC_RA, self._parse_tvoc)

            # 度假模式
            vacation, verr = await self._read_single_once(REG_VACATION_MODE)
            if verr is not None and self._is_recoverable(verr):
                raise ModbusException(f"读取度假模式失败: {verr}") from verr
            if vacation is not None:
                self.vacation_mode = vacation == 1
                data["vacation_mode"] = self.vacation_mode

            return data

    def _parse_pm25(self, value: int) -> Optional[float]:
        """解析PM2.5值"""
        if value == 0xFFFF or value > 5000:
            return None
        return float(value)

    def _parse_humidity(self, value: int) -> Optional[float]:
        """解析湿度值 - 直接十进制值，0xFFFF表示无数据"""
        if value == 0xFFFF or value > 100:
            return None
        return float(value)

    def _parse_temperature(self, value: int) -> Optional[float]:
        """解析温度值（INT16，寄存器返回的值可能需要除以10）"""
        if value == 0x7FFF or value == 0xFFFF or value >= 0xFFFE:
            return None  # 无有效数据

        # 有符号整数解析（INT16 二进制补码）
        if value & 0x8000:
            temp = value - 0x10000
        else:
            temp = value

        # 检查范围是否合理 (-50 ~ 80°C)
        if temp < -50 or temp > 80:
            return None

        return float(temp)  # 寄存器原值即为整数摄氏度

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
        async with self._lock:
            if not await self._ensure_connected():
                return None
            value, err = await self._read_single_once(REG_VACATION_MODE)
            if value is None:
                return None
            return value == 1

    async def set_vacation_mode(self, on: bool) -> bool:
        """设置度假模式"""
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
        # weekday(): 0=周一, 6=周日 -> 1=周一, 7=周日
        weekday = now.weekday() + 1

        values = [
            0xFFFF,                                          # 0x0014: 年跳过
            ((now.minute & 0xFF) << 8) | 0xFF,           # 0x0015: [高=分][低=秒(skip=FF)]
            ((weekday & 0xFF) << 8) | (now.hour & 0xFF), # 0x0016: [高=周][低=时]
            0xFFFF,                                          # 0x0017: 月日跳过
        ]

        return await self.write_register(0x0014, values)