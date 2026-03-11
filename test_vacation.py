#!/usr/bin/env python3
"""
度假模式测试
"""

import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.framer import FramerType


HOST = "10.0.0.6"
PORT = 10123
REG_VACATION = 0x0027


async def read_vacation():
    """读取度假模式"""
    client = AsyncModbusTcpClient(HOST, port=PORT, framer=FramerType.SOCKET)
    await client.connect()
    result = await client.read_holding_registers(address=REG_VACATION, count=1)
    client.close()
    if result and not result.isError():
        return result.registers[0]
    return None


async def write_vacation(on: bool):
    """写入度假模式"""
    value = 1 if on else 0
    client = AsyncModbusTcpClient(HOST, port=PORT, framer=FramerType.SOCKET)
    await client.connect()
    result = await client.write_register(address=REG_VACATION, value=value)
    client.close()
    return not result.isError()


async def main():
    print("度假模式测试")
    print("=" * 50)
    print(f"网关: {HOST}:{PORT}")
    print(f"寄存器: 0x{REG_VACATION:04X}")
    print()

    # 读取当前状态
    print("【读取当前度假模式状态】")
    status = await read_vacation()
    if status is not None:
        print(f"  当前状态: {'开启' if status == 1 else '关闭'} (0x{status:04X})")
    else:
        print("  读取失败")

    # 测试关闭
    print("\n【测试关闭度假模式】")
    print("  写入: 0x0027 = 0")
    success = await write_vacation(False)
    print(f"  结果: {'成功' if success else '失败'}")

    status = await read_vacation()
    if status is not None:
        print(f"  验证: {'开启' if status == 1 else '关闭'}")

    input("\n按回车继续测试开启...")

    # 测试开启
    print("\n【测试开启度假模式】")
    print("  写入: 0x0027 = 1")
    success = await write_vacation(True)
    print(f"  结果: {'成功' if success else '失败'}")

    status = await read_vacation()
    if status is not None:
        print(f"  验证: {'开启' if status == 1 else '关闭'}")

    print("\n" + "=" * 50)
    print("测试完成！请确认设备端是否有响应")


if __name__ == "__main__":
    asyncio.run(main())
