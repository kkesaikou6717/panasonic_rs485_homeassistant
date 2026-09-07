"""Fresh Air Modbus 客户端测试（本地模拟 Modbus TCP 网关）。"""

import asyncio
import sys
from pathlib import Path

import pytest
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server.async_io import ModbusTcpServer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import importlib.util
import types

_FA_ROOT = ROOT / "custom_components" / "fresh_air"
_cc_pkg = types.ModuleType("custom_components")
_cc_pkg.__path__ = [str(ROOT / "custom_components")]
_fa_pkg = types.ModuleType("custom_components.fresh_air")
_fa_pkg.__path__ = [str(_FA_ROOT)]
sys.modules["custom_components"] = _cc_pkg
sys.modules["custom_components.fresh_air"] = _fa_pkg

def _load_submodule(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

const_module = _load_submodule("custom_components.fresh_air.const", _FA_ROOT / "const.py")
mc_module = _load_submodule("custom_components.fresh_air.modbus_client", _FA_ROOT / "modbus_client.py")
FreshAirModbusClient = mc_module.FreshAirModbusClient
HOST = "127.0.0.1"
PORT = 15023


def build_context():
    """构建模拟松下新风寄存器的数据存储。"""
    block = ModbusSequentialDataBlock(0, [0] * 256)
    slave = ModbusSlaveContext(hr=block, zero_mode=True)
    return ModbusServerContext(slaves=slave, single=True)


def set_hr(context, address, values):
    """写保持寄存器（function code 3）。"""
    context[0].setValues(3, address, values)


def get_hr(context, address, count=1):
    """读保持寄存器。"""
    return context[0].getValues(3, address, count=count)


_server_handle: dict = {}

async def start_server(context):
    """启动模拟网关（直接管理任务，避免全局 ServerAsyncStop 的长等待）。"""
    server = ModbusTcpServer(context=context, address=(HOST, PORT))
    _server_handle["server"] = server
    _server_handle["task"] = asyncio.create_task(server.serve_forever())
    await asyncio.sleep(0.2)


async def stop_server():
    """停止模拟网关。"""
    server = _server_handle.pop("server", None)
    task = _server_handle.pop("task", None)
    if server:
        try:
            await asyncio.wait_for(server.shutdown(), timeout=5)
        except Exception:
            pass
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    await asyncio.sleep(0.1)

@pytest.fixture(autouse=True)
def fast_timeout(monkeypatch):
    """测试时缩短连接超时，避免失败用例等待过久。"""
    monkeypatch.setattr(mc_module, "CONNECT_TIMEOUT", 0.8)


def test_parse_temperature_two_complement():
    """INT16 补码温度解析。"""
    client = FreshAirModbusClient(HOST, PORT, 1)
    assert client._parse_temperature(0x0032) == 50.0         # 50 -> 50
    assert client._parse_temperature(0xFFE2) == -30.0        # -30 -> -30
    assert client._parse_temperature(0xFFCE) == -50.0        # -50 -> -50
    assert client._parse_temperature(0x7FFF) is None
    assert client._parse_temperature(0xFFFF) is None
    assert client._parse_temperature(0xFFFE) is None


def test_parse_invalid_sensor_values():
    """无数据值统一转换为 None。"""
    client = FreshAirModbusClient(HOST, PORT, 1)
    assert client._parse_pm25(0x03E7) == 999.0
    assert client._parse_pm25(0xFFFF) is None
    assert client._parse_humidity(0x0064) == 100.0
    assert client._parse_humidity(0xFFFF) is None
    assert client._parse_tvoc(5) == 5
    assert client._parse_tvoc(0xFFFF) is None


def test_read_all_sensors_roundtrip():
    async def scenario():
        context = build_context()
        # 状态与运行参数
        set_hr(context, 0x0020, [1, 0x0004, 0x0001])  # 运转=1, 模式=自动, 风量=低
        # PM2.5 / 湿度 / 温度 / CO2 / TVOC / 度假
        set_hr(context, 0x0070, [12, 34, 56])
        set_hr(context, 0x0073, [42])
        set_hr(context, 0x0075, [55])
        set_hr(context, 0x0076, [23, 0xFFE2, 25])   # 23 / -30 / 25
        set_hr(context, 0x007B, [800])
        set_hr(context, 0x007E, [2])
        set_hr(context, 0x0027, [1])

        await start_server(context)
        client = FreshAirModbusClient(HOST, PORT, 1)
        try:
            assert await client.connect() is True
            data = await client.read_all_sensors()
        finally:
            await client.disconnect()
            await stop_server()

        assert data["run_status"] == 1
        assert data["run_mode"] == 0x0004
        assert data["fan_speed"] == 0x0001
        assert data["pm25_oa"] == 12.0
        assert data["pm25_sa"] == 34.0
        assert data["pm25_ra"] == 56.0
        assert data["humidity_oa"] == 42.0
        assert data["humidity_ra"] == 55.0
        assert data["temp_oa"] == 23.0
        assert data["temp_sa"] == -30.0
        assert data["temp_ra"] == 25.0
        assert data["co2_ra"] == 800
        assert data["tvoc_ra"] == 2
        assert data["vacation_mode"] is True

    asyncio.run(scenario())


def test_control_writes_registers():
    async def scenario():
        context = build_context()
        await start_server(context)
        client = FreshAirModbusClient(HOST, PORT, 1)
        try:
            assert await client.connect() is True

            assert await client.set_power(True) is True
            assert await client.set_mode(0x0001) is True
            assert await client.set_fan_speed(0x0003) is True
            assert await client.set_vacation_mode(True) is True
            assert await client.sync_time() is True
        finally:
            await client.disconnect()
            await stop_server()

        assert get_hr(context, 0x0020)[0] == 1
        assert get_hr(context, 0x0021)[0] == 0x0001
        assert get_hr(context, 0x0022)[0] == 0x0003
        assert get_hr(context, 0x0027)[0] == 1
        time_regs = get_hr(context, 0x0015, 3)
        assert time_regs[0] & 0xFF == 0xFF
        assert 0 <= (time_regs[0] >> 8) <= 59
        assert 0 <= (time_regs[1] & 0xFF) <= 23
        assert 1 <= (time_regs[1] >> 8) <= 7
        assert time_regs[2] == 0xFFFF

    asyncio.run(scenario())


def test_reconnect_after_gateway_restart():
    async def scenario():
        context = build_context()
        set_hr(context, 0x0020, [1, 0, 0])
        await start_server(context)
        client = FreshAirModbusClient(HOST, PORT, 1)
        try:
            assert await client.connect() is True
            assert (await client.read_register(0x0020, 1))[0] == 1

            # 模拟网关断电：停止服务，写入应失败
            await stop_server()
            assert await client.set_power(False) is False

            # 模拟网关恢复：下一次读写应自动重连并成功
            set_hr(context, 0x0020, [1, 0, 0])
            await start_server(context)
            registers = await client.read_register(0x0020, 1)
            assert registers is not None
            assert registers[0] == 1
        finally:
            await client.disconnect()
            await stop_server()

    asyncio.run(scenario())


def test_read_all_sensors_recovers_after_restart():
    async def scenario():
        context = build_context()
        set_hr(context, 0x0020, [1, 0x0004, 0x0001])
        await start_server(context)
        client = FreshAirModbusClient(HOST, PORT, 1)
        try:
            data = await client.read_all_sensors()
            assert data["run_status"] == 1

            # 网关停机期间，采集应失败（抛异常而不是返回假数据）
            await stop_server()
            with pytest.raises(Exception):
                await client.read_all_sensors()

            # 网关恢复后，同一 client 无需重建即可重新采集
            set_hr(context, 0x0020, [0, 0x0004, 0x0001])
            await start_server(context)
            data = await client.read_all_sensors()
            assert data["run_status"] == 0
        finally:
            await client.disconnect()
            await stop_server()

    asyncio.run(scenario())