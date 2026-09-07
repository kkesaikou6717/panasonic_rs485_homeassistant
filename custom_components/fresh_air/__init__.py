"""
新风系统集成组件
用于Home Assistant
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
    DOMAIN,
    PLATFORMS,
    UPDATE_INTERVAL,
)
from .modbus_client import FreshAirModbusClient
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

# 时间同步间隔（小时）
TIME_SYNC_INTERVAL_HOURS = 6


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置配置入口"""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave = entry.data.get(CONF_SLAVE, 1)

    # 创建Modbus客户端与数据协调器
    client = FreshAirModbusClient(host, port, slave)
    coordinator = FreshAirCoordinator(hass, entry, client)

    # 存储到hass数据
    # 首次刷新：网关不可达时抛出 ConfigEntryNotReady，由 HA 自动重试
    await coordinator.async_config_entry_first_refresh()

    # 刷新成功后才存储到 hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }
    # 启动自动时间同步
    coordinator.start_time_sync()

    # 设置平台（CoordinatorEntity 会在添加时订阅 coordinator，开启周期轮询）
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 设置服务
    await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载配置入口"""
    data = hass.data[DOMAIN].get(entry.entry_id)
    if data:
        coordinator = data.get("coordinator")
        if coordinator:
            await coordinator.stop_time_sync()
            await coordinator.async_shutdown()

        client = data.get("client")
        if client:
            await client.disconnect()

    # 卸载平台
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    # 检查是否还有其他条目，如果没有则卸载服务
    if not hass.data.get(DOMAIN):
        await async_unload_services(hass)

    return unload_ok


class FreshAirCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """新风系统数据协调器"""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: FreshAirModbusClient,
    ) -> None:
        """初始化协调器"""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self._client = client
        self._time_sync_task = None

    @property
    def client(self) -> FreshAirModbusClient:
        """返回底层 Modbus 客户端"""
        return self._client

    def start_time_sync(self) -> None:
        """启动自动时间同步"""
        if self._time_sync_task is None:
            self._time_sync_task = asyncio.create_task(self._time_sync_loop())
            _LOGGER.info("自动时间同步已启动")

    async def stop_time_sync(self) -> None:
        """停止自动时间同步"""
        if self._time_sync_task is not None:
            self._time_sync_task.cancel()
            try:
                await self._time_sync_task
            except asyncio.CancelledError:
                pass
            self._time_sync_task = None
            _LOGGER.info("自动时间同步已停止")

    async def _time_sync_loop(self) -> None:
        """时间同步循环"""
        while True:
            try:
                # 等待同步间隔
                await asyncio.sleep(TIME_SYNC_INTERVAL_HOURS * 3600)

                # 同步时间
                _LOGGER.info("自动同步时间...")
                success = await self._client.sync_time()
                if success:
                    _LOGGER.info("自动时间同步成功")
                else:
                    _LOGGER.warning("自动时间同步失败")
            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-except
                _LOGGER.error("时间同步异常: %s", e)

    async def _async_update_data(self) -> dict[str, Any]:
        """更新数据"""
        try:
            return await self._client.read_all_sensors()
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.error("更新数据失败: %s", e)
            raise UpdateFailed(f"Modbus数据更新失败: {e}") from e
