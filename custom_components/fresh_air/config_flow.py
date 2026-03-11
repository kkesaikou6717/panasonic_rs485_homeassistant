"""
配置流程
"""

import ipaddress
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_SLAVE, DOMAIN


class FreshAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """新风系统配置流程"""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """用户配置步骤"""
        errors = {}

        if user_input is not None:
            # 验证输入
            host = user_input[CONF_HOST]
            try:
                ipaddress.ip_address(host)
            except ValueError:
                errors[CONF_HOST] = "invalid_ip"

            if not errors:
                # 测试连接
                try:
                    from .modbus_client import FreshAirModbusClient

                    client = FreshAirModbusClient(
                        host=user_input[CONF_HOST],
                        port=user_input[CONF_PORT],
                        slave=user_input.get(CONF_SLAVE, 1),
                    )
                    connected = await client.connect()
                    await client.disconnect()

                    if not connected:
                        errors["base"] = "connection_failed"
                except Exception:
                    errors["base"] = "connection_failed"

            if not errors:
                # 创建配置条目
                return self.async_create_entry(
                    title="新风系统",
                    data=user_input,
                )

        # 显示配置表单
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=10123): int,
                vol.Optional(CONF_SLAVE, default=1): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """导入配置"""
        return self.async_create_entry(
            title="新风系统",
            data=user_input,
        )
