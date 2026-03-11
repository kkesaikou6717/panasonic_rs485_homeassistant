#!/usr/bin/env python3
"""
测试传感器寄存器读取
"""

import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.framer import FramerType


async def test_sensor_registers():
    """测试传感器寄存器"""
    client = AsyncModbusTcpClient(
        "10.0.0.6",
        port=10123,
        framer=FramerType.SOCKET,
    )
    
    connected = await client.connect()
    if not connected:
        print("连接失败！")
        return
    
    print("已连接，开始读取传感器寄存器...\n")
    
    # 读取温湿度传感器 (0x0073开始)
    print("=== 测试温湿度寄存器 ===")
    result = await client.read_holding_registers(address=0x0073, count=6)
    if result.isError():
        print(f"读取错误: {result}")
    else:
        registers = result.registers
        print(f"原始数据: {[hex(r) for r in registers]}")
        print(f"原始值: {registers}")
        
        # 0x0073: OA湿度
        # 0x0074: (跳过)
        # 0x0075: RA湿度
        # 0x0076: OA温度
        # 0x0077: SA温度
        # 0x0078: RA温度
        
        oa_humidity = registers[0]
        ra_humidity = registers[2]
        oa_temp = registers[3]
        sa_temp = registers[4]
        ra_temp = registers[5]
        
        print(f"\nOA湿度 (0x0073): 原始值={hex(oa_humidity)}, 十进制={oa_humidity}")
        print(f"  如果文档正确，0x0010应=16%，0x002A应=42%")
        
        print(f"\nRA湿度 (0x0075): 原始值={hex(ra_humidity)}, 十进制={ra_humidity}")
        
        # 温度是INT16
        def parse_int16(val):
            if val & 0x8000:
                return -(val & 0x7FFF)
            return val
        
        print(f"\nOA温度 (0x0076): 原始值={hex(oa_temp)}, 十进制={oa_temp}, 解析={parse_int16(oa_temp)}℃")
        print(f"SA温度 (0x0077): 原始值={hex(sa_temp)}, 十进制={sa_temp}, 解析={parse_int16(sa_temp)}℃")
        print(f"RA温度 (0x0078): 原始值={hex(ra_temp)}, 十进制={ra_temp}, 解析={parse_int16(ra_temp)}℃")
    
    # 读取PM2.5 (0x0070开始)
    print("\n\n=== 测试PM2.5寄存器 ===")
    result = await client.read_holding_registers(address=0x0070, count=3)
    if result.isError():
        print(f"读取错误: {result}")
    else:
        registers = result.registers
        print(f"原始数据: {[hex(r) for r in registers]}")
        print(f"OA PM2.5 (0x0070): {registers[0]} μg/m³")
        print(f"SA PM2.5 (0x0071): {registers[1]} μg/m³")
        print(f"RA PM2.5 (0x0072): {registers[2]} μg/m³")
    
    # 读取CO2和TVOC
    print("\n\n=== 测试空气质量寄存器 ===")
    result = await client.read_holding_registers(address=0x007B, count=1)
    if not result.isError():
        print(f"RA CO2 (0x007B): {result.registers[0]} ppm")
    
    result = await client.read_holding_registers(address=0x007E, count=1)
    if not result.isError():
        tvoc = result.registers[0]
        print(f"RA TVOC (0x007E): {hex(tvoc)} = Level {tvoc}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(test_sensor_registers())
