"""
服务定义
"""

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SYNC_TIME = "sync_time"


async def async_setup_services(hass: HomeAssistant) -> None:
    """设置服务"""

    async def sync_time_service(call: ServiceCall) -> None:
        """同步时间服务"""
        # 查找第一个可用的配置条目
        for entry_id_hass, data in hass.data.get(DOMAIN, {}).items():
            coordinator = data.get("coordinator")
            if coordinator:
                client = coordinator.client
                if client:
                    success = await client.sync_time()
                    if success:
                        _LOGGER.info("时间同步成功")
                        await coordinator.async_request_refresh()
                    else:
                        _LOGGER.error("时间同步失败")
                    return

    # 注册服务
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_TIME,
        sync_time_service,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """卸载服务"""
    hass.services.async_remove(DOMAIN, SERVICE_SYNC_TIME)
