"""固件包数据模型，用于 ESP32/8266 OTA 在线升级功能。"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, String, Text

from .base import SQLModelBase, UUIDTableBase

if TYPE_CHECKING:
    from .user import User


class ChipTypeEnum(StrEnum):
    """ESP 芯片类型枚举"""
    esp32 = 'esp32'
    esp8266 = 'esp8266'
    esp32s2 = 'esp32s2'
    esp32s3 = 'esp32s3'
    esp32c3 = 'esp32c3'


class FirmwareBase(SQLModelBase):
    chip_type: ChipTypeEnum = Field(index=True)
    """芯片类型"""

    version: str = Field(sa_type=String(64), index=True)
    """固件版本号，遵循语义化版本规范"""

    file_path: str
    """固件文件存储路径"""

    file_size: int
    """固件文件大小（字节）"""

    file_md5: str = Field(max_length=32)
    """固件文件 MD5 校验值"""

    description: str | None = Field(default=None, sa_type=Text)
    """固件更新说明"""

    is_active: bool = Field(default=True, index=True)
    """是否启用该固件版本"""


class Firmware(FirmwareBase, UUIDTableBase, table=True):
    """固件包表"""

    uploaded_by_id: UUID = Field(foreign_key='user.id', ondelete='RESTRICT')
    """上传者用户ID"""

    downloaded_count: int = Field(default=0)
    """下载次数统计"""

    uploaded_at: datetime = Field(default_factory=datetime.now)
    """上传时间"""

    uploaded_by: 'User' = Relationship(back_populates='firmwares')


# DTO 定义

class FirmwareDataResponse(FirmwareBase):
    """固件信息响应"""
    id: UUID
    """固件ID"""

    downloaded_count: int
    """下载次数"""

    uploaded_at: datetime
    """上传时间"""

    download_url: str | None = None
    """下载地址"""


class FirmwareDataResponseAdmin(FirmwareDataResponse):
    """固件信息响应（管理员）"""
    uploaded_by_id: UUID
    """上传者ID"""


class FirmwareUploadRequest(SQLModelBase):
    """固件上传请求"""
    chip_type: ChipTypeEnum
    """芯片类型"""

    version: str
    """版本号字符串"""

    description: str | None = None
    """更新说明"""


class FirmwareCheckUpdateRequest(SQLModelBase):
    """设备检查更新请求"""
    chip_type: ChipTypeEnum
    """芯片类型"""

    current_version: str
    """当前版本号"""


class FirmwareCheckUpdateResponse(SQLModelBase):
    """检查更新响应"""
    has_update: bool
    """是否有可用更新"""

    latest_version: str | None = None
    """最新版本号"""

    download_url: str | None = None
    """下载地址"""

    file_size: int | None = None
    """文件大小"""

    file_md5: str | None = None
    """文件MD5"""

    description: str | None = None
    """更新说明"""
