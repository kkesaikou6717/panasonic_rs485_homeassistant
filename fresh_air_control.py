#!/usr/bin/env python3
"""
新风系统统一控制脚本
实现所有核心功能
"""

import asyncio
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.framer import FramerType

# 配置
HOST = "10.0.0.6"
PORT = 10123
SLAVE = 1

# 寄存器地址
REG_POWER = 0x0020      # 运转状态
REG_MODE = 0x0021        # 运转模式
REG_FAN = 0x0022         # 风量设定
REG_VACATION = 0x0027    # 度假模式
REG_TIME_START = 0x0014  # 时间寄存器起始

# 模式定义
MODE_HEAT_EXCHANGE = 0x00  # 热交换
MODE_NORMAL = 0x01          # 普通换气
MODE_INTERNAL = 0x02        # 内循环
MODE_AUTO = 0x04           # 自动
MODE_SILENT = 0x06         # 静音
MODE_MIX = 0x07            # 混风

MODE_MAP = {
    0: "热交换",
    1: "普通换气",
    2: "内循环",
    4: "自动",
    6: "静音",
    7: "混风",
}

# 风量定义
FAN_LOW = 1   # 弱
FAN_HIGH = 3  # 强

FAN_MAP = {1: "弱", 3: "强"}


class FreshAirController:
    """新风系统控制器"""
    
    def __init__(self):
        self.client = None
    
    async def connect(self) -> bool:
        """连接Modbus网关"""
        self.client = AsyncModbusTcpClient(HOST, port=PORT, framer=FramerType.SOCKET)
        connected = await self.client.connect()
        if connected:
            print(f"✓ 已连接 {HOST}:{PORT}")
        else:
            print(f"✗ 连接失败 {HOST}:{PORT}")
        return connected
    
    async def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
            print("✓ 已断开连接")
    
    async def _write_register(self, address: int, values: list[int]) -> bool:
        """写入寄存器"""
        result = await self.client.write_registers(address=address, values=values)
        if result.isError():
            print(f"✗ 写入失败 0x{address:04X}: {result}")
            return False
        print(f"✓ 写入成功 0x{address:04X} = {values}")
        return True
    
    async def _read_register(self, address: int, count: int = 1):
        """读取寄存器"""
        result = await self.client.read_holding_registers(address=address, count=count)
        if result.isError():
            print(f"✗ 读取失败 0x{address:04X}: {result}")
            return None
        return result.registers
    
    # ==================== 功能实现 ====================
    
    async def power_on(self) -> bool:
        """开启新风"""
        print("\n【开启新风】")
        return await self._write_register(REG_POWER, [1])
    
    async def power_off(self) -> bool:
        """关闭新风"""
        print("\n【关闭新风】")
        return await self._write_register(REG_POWER, [0])
    
    async def set_mode(self, mode: int) -> bool:
        """设置运行模式
        mode: 0=热交换, 1=普通换气, 2=内循环, 4=自动, 6=静音, 7=混风
        """
        mode_name = MODE_MAP.get(mode, "未知")
        print(f"\n【设置模式】{mode_name} (0x{mode:02X})")
        return await self._write_register(REG_MODE, [mode])
    
    async def set_fan_speed(self, speed: int) -> bool:
        """设置风量
        speed: 1=弱, 3=强
        """
        speed_name = FAN_MAP.get(speed, "未知")
        print(f"\n【设置风量】{speed_name} (0x{speed:02X})")
        return await self._write_register(REG_FAN, [speed])
    
    async def vacation_on(self) -> bool:
        """开启度假模式"""
        print("\n【开启度假模式】")
        return await self._write_register(REG_VACATION, [1])
    
    async def vacation_off(self) -> bool:
        """关闭度假模式"""
        print("\n【关闭度假模式】")
        return await self._write_register(REG_VACATION, [0])
    
    async def set_time(self, weekday: int, hour: int, minute: int) -> bool:
        """设置时间
        weekday: 1=周一, 2=周二, ..., 7=周日
        hour: 0-23
        minute: 0-59
        """
        print(f"\n【设置时间】周{weekday} {hour:02d}:{minute:02d}")
        
        values = [
            0xFFFF,                                          # 0x0014: 年(跳过)
            ((minute & 0xFF) << 8) | 0xFF,                # 0x0015: [高=分][低=秒(skip=FF)]
            ((weekday & 0xFF) << 8) | (hour & 0xFF),     # 0x0016: [高=周][低=时]
            0xFFFF,                                          # 0x0017: 月日(跳过)
        ]
        
        print(f"发送数据: {[hex(v) for v in values]}")
        
        return await self._write_register(REG_TIME_START, values)
    
    async def get_sensors(self) -> dict:
        """获取空气质量数据"""
        print("\n【读取空气质量数据】")
        data = {}
        
        # PM2.5 (0x0070-0x0072)
        pm25 = await self._read_register(0x0070, 3)
        if pm25:
            data["pm25_oa"] = pm25[0] if pm25[0] != 0xFFFF else None
            data["pm25_sa"] = pm25[1] if pm25[1] != 0xFFFF else None
            data["pm25_ra"] = pm25[2] if pm25[2] != 0xFFFF else None
        
        # 湿度 (0x0073, 0x0075)
        hum_oa = await self._read_register(0x0073, 1)
        hum_ra = await self._read_register(0x0075, 1)
        data["humidity_oa"] = hum_oa[0] if hum_oa and hum_oa[0] != 0xFFFF else None
        data["humidity_ra"] = hum_ra[0] if hum_ra and hum_ra[0] != 0xFFFF else None
        
        # 温度 (0x0076-0x0078)
        temp = await self._read_register(0x0076, 3)
        if temp:
            def parse_int16(v):
                if v == 0x7FFF or v >= 0xFFFE:
                    return None
                if v & 0x8000:
                    return -(v & 0x7FFF)
                return v
            data["temp_oa"] = parse_int16(temp[0])
            data["temp_sa"] = parse_int16(temp[1])
            data["temp_ra"] = parse_int16(temp[2])
        
        # CO2 (0x007B)
        co2 = await self._read_register(0x007B, 1)
        data["co2_ra"] = co2[0] if co2 else None
        
        # TVOC (0x007E)
        tvoc = await self._read_register(0x007E, 1)
        data["tvoc_ra"] = tvoc[0] if tvoc and tvoc[0] != 0xFFFF else None
        
        return data
    
    def print_sensors(self, data: dict):
        """打印传感器数据"""
        print("\n" + "=" * 50)
        print("【空气质量数据】")
        print("=" * 50)
        
        print("\n【PM2.5】μg/m³")
        print(f"  室外新风: {data.get('pm25_oa', 'N/A')}")
        print(f"  送风: {data.get('pm25_sa', 'N/A')}")
        print(f"  室内回风: {data.get('pm25_ra', 'N/A')}")
        
        print("\n【温度】℃")
        print(f"  室外新风: {data.get('temp_oa', 'N/A')}")
        print(f"  送风: {data.get('temp_sa', 'N/A')}")
        print(f"  室内回风: {data.get('temp_ra', 'N/A')}")
        
        print("\n【湿度】%")
        print(f"  室外新风: {data.get('humidity_oa', 'N/A')}")
        print(f"  室内回风: {data.get('humidity_ra', 'N/A')}")
        
        print("\n【空气质量】")
        print(f"  室内回风CO2: {data.get('co2_ra', 'N/A')} ppm")
        tvoc = data.get('tvoc_ra')
        if tvoc is not None and 0 <= tvoc <= 5:
            levels = ["优", "良", "轻度", "中度", "重度", "严重"]
            print(f"  室内回风TVOC: Level {tvoc} ({levels[tvoc]})")
        else:
            print(f"  室内回风TVOC: N/A")


async def main():
    """主函数 - 交互式测试"""
    controller = FreshAirController()
    
    if not await controller.connect():
        return
    
    try:
        while True:
            print("\n" + "=" * 50)
            print("新风系统控制菜单")
            print("=" * 50)
            print("1. 开启新风")
            print("2. 关闭新风")
            print("3. 设置模式 (热交换/换气/内循环/自动/静音/混风)")
            print("4. 设置风量 (弱/强)")
            print("5. 开启度假模式")
            print("6. 关闭度假模式")
            print("7. 设置时间 (周/时/分)")
            print("8. 获取空气质量数据")
            print("q. 退出")
            print("=" * 50)
            
            choice = input("请选择: ").strip().lower()
            
            if choice == 'q':
                break
            
            elif choice == '1':
                await controller.power_on()
            
            elif choice == '2':
                await controller.power_off()
            
            elif choice == '3':
                print("\n模式: 0=热交换, 1=普通换气, 2=内循环, 4=自动, 6=静音, 7=混风")
                mode = int(input("请输入模式值: "))
                await controller.set_mode(mode)
            
            elif choice == '4':
                print("风量: 1=弱, 3=强")
                speed = int(input("请输入风量值: "))
                await controller.set_fan_speed(speed)
            
            elif choice == '5':
                await controller.vacation_on()
            
            elif choice == '6':
                await controller.vacation_off()
            
            elif choice == '7':
                print("周: 1=周一, 2=周二, ..., 7=周日")
                weekday = int(input("请输入星期(1-7): "))
                hour = int(input("请输入小时(0-23): "))
                minute = int(input("请输入分钟(0-59): "))
                await controller.set_time(weekday, hour, minute)
            
            elif choice == '8':
                data = await controller.get_sensors()
                controller.print_sensors(data)
    
    finally:
        await controller.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
