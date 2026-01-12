from typing import Annotated, TypeAlias

from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from model.database import Database
from model.mixin.table import TableViewRequest
from model import Item
from model.item import ItemTypeEnum
from pkg import utils

SessionDep: TypeAlias = Annotated[AsyncSession, Depends(Database.get_session)]
"""数据库会话依赖，用于路由函数中获取数据库会话"""

# 新增：表格视图请求依赖（用于分页排序）
TableViewRequestDep: TypeAlias = Annotated[TableViewRequest, Depends()]
"""分页排序请求依赖，用于 LIST 端点"""


async def get_device_from_cert(
    request: Request,
    session: SessionDep,
) -> Item:
    """
    从 mTLS 客户端证书中提取设备序列号并验证设备。

    客户端证书的 CN (Common Name) 字段应存储设备序列号 (UUID)。
    反向代理（Nginx/Apache）验证证书后，通过 HTTP Header 将 CN 传递给 FastAPI。

    Nginx 配置示例:
        proxy_set_header X-Client-CN $ssl_client_s_dn_cn;

    Apache 配置示例:
        RequestHeader set X-Client-CN "%{SSL_CLIENT_S_DN_CN}s"
    """
    # 从 Header 获取设备序列号（由反向代理注入）
    serial_number = request.headers.get("X-Client-CN")

    if not serial_number:
        utils.raise_unauthorized("Device certificate required")

    # 验证 UUID 格式
    try:
        from uuid import UUID
        serial_uuid = UUID(serial_number)
    except ValueError:
        utils.raise_unauthorized("Invalid device serial number format")

    # 查找设备
    device = await Item.get(session, Item.id == serial_uuid)

    if not device:
        utils.raise_not_found("Device not found")

    if device.type != ItemTypeEnum.esp32:
        utils.raise_forbidden("Not an ESP device")

    return device


DeviceDep: TypeAlias = Annotated[Item, Depends(get_device_from_cert)]
"""设备认证依赖，通过 mTLS 证书验证 ESP 设备"""
