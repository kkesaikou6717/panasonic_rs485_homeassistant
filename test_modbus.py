#!/usr/bin/env python3
"""
新风系统Modbus测试脚本
分步测试：控制和环境读取
"""

import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.framer import FramerType


# Modbus配置
GATEWAY_HOST = "10.0.0.6"
GATEWAY_PORT = 10123
SLAVE_ID = 1  # 从站地址

# 寄存器地址
REG_POWER = 0x0020     # 电源开关
REG_MODE = 0x0021       # 运行模式
REG_FAN = 0x0022       # 风量设定
REG_TIME_START = 0x0014 # 时间设定起始地址

# 模式定义
MODE_HEAT_EXCHANGE = 0x0000  # 热交换
MODE_NORMAL = 0x0001          # 普通换气
MODE_INTERNAL = 0x0002         # 内循环
MODE_AUTO = 0x0004            # 自动
MODE_SILENT = 0x0006          # 静音
MODE_MIX = 0x0007             # 混风

MODE_MAP = {
    MODE_HEAT_EXCHANGE: "热交换",
    MODE_NORMAL: "普通换气",
    MODE_INTERNAL: "内循环",
    MODE_AUTO: "自动",
    MODE_SILENT: "静音",
    MODE_MIX: "混风",
}

# 风量定义
FAN_LOW = 0x0001   # 弱
FAN_HIGH = 0x0003  # 强

FAN_MAP = {
    FAN_LOW: "弱",
    FAN_HIGH: "强",
}


class FreshAirTester:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        self.client = AsyncModbusTcpClient(
            GATEWAY_HOST,
            port=GATEWAY_PORT,
            framer=FramerType.SOCKET,
        )
        connected = await self.client.connect()
        return connected
    
    async def disconnect(self):
        if self.client:
            self.client.close()
    
    async def read_register(self, address, count=1):
        result = await self.client.read_holding_registers(
            address=address,
            count=count,
        )
        if result.isError():
            return None
        return result.registers
    
    async def write_register(self, address, values):
        result = await self.client.write_registers(
            address=address,
            values=values,
        )
        if result.isError():
            return False
        return True
    
    async def set_power(self, on: bool):
        """设置电源开关"""
        value = 1 if on else 0
        return await self.write_register(REG_POWER, [value])
    
    async def set_mode(self, mode: int):
        """设置运行模式"""
        return await self.write_register(REG_MODE, [mode])
    
    async def set_fan_speed(self, speed: int):
        """设置风量"""
        return await self.write_register(REG_FAN, [speed])
    
    async def set_time(self, year, month, day, hour, minute, second, weekday):
        """设置网络时间
        weekday: 1=周一, 2=周二, ..., 7=周日
        """
        values = [
            0xFFFF,  # 年：跳过
            (second & 0xFF) | ((minute & 0xFF) << 8),  # 秒|分
            (hour & 0xFF) | ((weekday & 0xFF) << 8),   # 时|周
            (day & 0xFF) | ((month & 0xFF) << 8),     # 日|月
        ]
        return await self.write_register(REG_TIME_START, values)
    
    async def read_env_sensors(self):
        """读取环境传感器"""
        data = {}
        
        # PM2.5
        pm25 = await self.read_register(0x0070, 3)
        if pm25:
            data["pm25_oa"] = pm25[0]
            data["pm25_sa"] = pm25[1]
            data["pm25_ra"] = pm25[2]
        
        # 湿度
        hum = await self.read_register(0x0073, 1)
        hum_ra = await self.read_register(0x0075, 1)
        if hum:
            data["humidity_oa"] = hum[0]
        if hum_ra:
            data["humidity_ra"] = hum_ra[0]
        
        # 温度
        temp = await self.read_register(0x0076, 3)
        if temp:
            data["temp_oa"] = self._parse_int16(temp[0])
            data["temp_sa"] = self._parse_int16(temp[1])
            data["temp_ra"] = self._parse_int16(temp[2])
        
        # CO2/TVOC
        co2 = await self.read_register(0x007B, 1)
        tvoc = await self.read_register(0x007E, 1)
        if co2:
            data["co2_ra"] = co2[0]
        if tvoc:
            data["tvoc_ra"] = tvoc[0]
        
        return data
    
    def _parse_int16(self, value):
        """解析INT16温度值"""
        # 0xFFFE/0xFFFF/0x7FFF = 传感器无效
        if value == 0x7FFF or value >= 0xFFFE:
            return None
        if value & 0x8000:
            return -(value & 0x7FFF)
        return value
    
    async def read_status(self):
        """读取运转状态"""
        status = await self.read_register(REG_POWER, 3)
        if status:
            return {
                "power": status[0],
                "mode": status[1],
                "fan": status[2],
            }
        return None


async def step1_power_on(tester):
    """步骤1：打开新风电源"""
    print("\n" + "=" * 50)
    print("步骤1：打开新风电源")
    print("=" * 50)
    print("指令: 写入0x0020 = 1 (开启)")
    input("按回车键执行...")
    
    success = await tester.set_power(True)
    if success:
        print("✓ 电源开启成功")
    else:
        print("✗ 电源开启失败")
    
    # 验证
    status = await tester.read_status()
    if status:
        print(f"当前状态: 电源={'开' if status['power']==1 else '关'}")
    return success


async def step2_set_mode(tester):
    """步骤2：设置为换气模式"""
    print("\n" + "=" * 50)
    print("步骤2：设置为普通换气模式")
    print("=" * 50)
    print("指令: 写入0x0021 = 0x0001 (普通换气)")
    input("按回车键执行...")
    
    success = await tester.set_mode(MODE_NORMAL)
    if success:
        print("✓ 模式设置成功")
    else:
        print("✗ 模式设置失败")
    
    status = await tester.read_status()
    if status:
        mode_name = MODE_MAP.get(status["mode"], f"未知({status['mode']})")
        print(f"当前模式: {mode_name}")
    return success


async def step3_fan_low(tester):
    """步骤3：设置为弱风"""
    print("\n" + "=" * 50)
    print("步骤3：设置风量为弱")
    print("=" * 50)
    print("指令: 写入0x0022 = 0x0001 (弱风)")
    input("按回车键执行...")
    
    success = await tester.set_fan_speed(FAN_LOW)
    if success:
        print("✓ 风量设置成功")
    else:
        print("✗ 风量设置失败")
    
    status = await tester.read_status()
    if status:
        fan_name = FAN_MAP.get(status["fan"], f"未知({status['fan']})")
        print(f"当前风量: {fan_name}")
    return success


async def step4_fan_high(tester):
    """步骤4：设置为强风"""
    print("\n" + "=" * 50)
    print("步骤4：设置风量为强")
    print("=" * 50)
    print("指令: 写入0x0022 = 0x0003 (强风)")
    input("按回车键执行...")
    
    success = await tester.set_fan_speed(FAN_HIGH)
    if success:
        print("✓ 风量设置成功")
    else:
        print("✗ 风量设置失败")
    
    status = await tester.read_status()
    if status:
        fan_name = FAN_MAP.get(status["fan"], f"未知({status['fan']})")
        print(f"当前风量: {fan_name}")
    return success


async def step5_read_env(tester):
    """步骤5：读取环境信息"""
    print("\n" + "=" * 50)
    print("步骤5：读取环境传感器数据")
    print("=" * 50)
    print("指令: 读取0x0070-0x007E寄存器")
    input("按回车键执行...")
    
    data = await tester.read_env_sensors()
    
    print("\n【PM2.5传感器】")
    print(f"  OA(新风): {data.get('pm25_oa', 'N/A')} μg/m³")
    print(f"  SA(送风): {data.get('pm25_sa', 'N/A')} μg/m³")
    print(f"  RA(回风): {data.get('pm25_ra', 'N/A')} μg/m³")
    
    print("\n【温湿度】")
    print(f"  OA温度: {data.get('temp_oa', 'N/A')}℃")
    print(f"  SA温度: {data.get('temp_sa', 'N/A')}℃")
    print(f"  RA温度: {data.get('temp_ra', 'N/A')}℃")
    print(f"  OA湿度: {data.get('humidity_oa', 'N/A')}%")
    print(f"  RA湿度: {data.get('humidity_ra', 'N/A')}%")
    
    print("\n【空气质量】")
    print(f"  RA CO2: {data.get('co2_ra', 'N/A')} ppm")
    tvoc = data.get("tvoc_ra")
    if tvoc is not None and tvoc <= 5:
        levels = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]
        print(f"  RA TVOC: Level {tvoc} ({levels[tvoc]})")
    else:
        print(f"  RA TVOC: 无有效数据")
    
    return data


async def step6_set_time(tester):
    """步骤6：设置为周二04:20"""
    print("\n" + "=" * 50)
    print("步骤6：设置时间为周二 04:20:00")
    print("=" * 50)
    print("指令: 写入0x0014-0x0017")
    print("  0x0014: 年=跳过")
    print("  0x0015: 秒=0x00, 分=0x14(20)")
    print("  0x0016: 时=0x04(4), 周=0x02(周二)")
    print("  0x0017: 日=跳过, 月=跳过")
    input("按回车键执行...")
    
    success = await tester.set_time(
        year=0xFFFF,    # 跳过
        month=0xFFFF,   # 跳过
        day=0xFFFF,     # 跳过
        hour=4,         # 04:20
        minute=20,
        second=0,
        weekday=2,     # 周二
    )
    
    if success:
        print("✓ 时间设置成功")
    else:
        print("✗ 时间设置失败")
    
    return success


async def step7_sync_now(tester):
    """步骤7：同步当前时间"""
    import datetime
    
    print("\n" + "=" * 50)
    print("步骤7：同步当前系统时间")
    print("=" * 50)
    
    now = datetime.datetime.now()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  星期: {now.weekday() + 1}")
    print("指令: 写入当前时间到0x0014-0x0017")
    input("按回车键执行...")
    
    success = await tester.set_time(
        year=0xFFFF,
        month=now.month,
        day=now.day,
        hour=now.hour,
        minute=now.minute,
        second=now.second,
        weekday=now.weekday() + 1,
    )
    
    if success:
        print(f"✓ 时间同步成功: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("✗ 时间同步失败")
    
    return success


async def main():
    tester = FreshAirTester()
    
    print("新风系统Modbus测试")
    print(f"网关: {GATEWAY_HOST}:{GATEWAY_PORT}")
    print()
    
    # 连接
    if not await tester.connect():
        print("连接失败！")
        return
    
    print("已连接Modbus网关")
    print()
    
    try:
        # 步骤1: 开启电源
        await step1_power_on(tester)
        input("\n继续下一步请按回车...")
        
        # 步骤2: 设置为换气模式
        await step2_set_mode(tester)
        input("\n继续下一步请按回车...")
        
        # 步骤3: 设置为弱风
        await step3_fan_low(tester)
        input("\n继续下一步请按回车...")
        
        # 步骤4: 设置为强风
        await step4_fan_high(tester)
        input("\n继续下一步请按回车...")
        
        # 步骤5: 读取环境信息
        await step5_read_env(tester)
        input("\n继续下一步请按回车...")
        
        # 步骤6: 设置为周二04:20
        await step6_set_time(tester)
        input("\n继续下一步请按回车...")
        
        # 步骤7: 同步当前时间
        await step7_sync_now(tester)
        
        print("\n" + "=" * 50)
        print("测试完成！")
        print("=" * 50)
        
    finally:
        await tester.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
