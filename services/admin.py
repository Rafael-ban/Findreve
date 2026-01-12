"""
管理员相关业务逻辑。
"""

import hashlib
from pathlib import Path
from typing import Iterable, List
from uuid import UUID

from fastapi import UploadFile
from loguru import logger
from pydantic_extra_types.semantic_version import SemanticVersion

from middleware.dependencies import SessionDep
from model import Firmware, User, Setting, SettingResponse
from model.firmware import ChipTypeEnum, FirmwareDataResponseAdmin
from pkg import utils

# 固件存储目录
FIRMWARE_STORAGE_PATH = Path("data/firmware")
FIRMWARE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# 文件大小限制 4MB
MAX_FIRMWARE_SIZE = 4 * 1024 * 1024


async def fetch_settings(
    session: SessionDep,
    name: str | None = None,
) -> List[SettingResponse]:
    """
    按名称获取设置项，默认返回全部。
    """
    data: list[SettingResponse] = []

    if name:
        setting = await Setting.get(session, Setting.name == name)
        if setting:
            data.append(SettingResponse.model_validate(setting))
        else:
            utils.raise_not_found("Setting not found")
    else:
        settings: Iterable[Setting] | None = await Setting.get(session, fetch_mode="all")
        if settings:
            data = [SettingResponse.model_validate(s) for s in settings]

    return data


async def update_setting_value(
    session: SessionDep,
    name: str,
    value: str,
) -> bool:
    """
    更新设置项的值。
    """
    setting = await Setting.get(session, Setting.name == name)
    if not setting:
        utils.raise_not_found("Setting not found")

    setting.value = value
    await Setting.save(session)

    return True


def _calculate_md5(file_path: Path) -> str:
    """计算文件的 MD5 值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


async def upload_firmware(
    session: SessionDep,
    admin: User,
    chip_type: ChipTypeEnum,
    version: str,
    description: str | None,
    file: UploadFile,
) -> None:
    """
    上传固件包。

    Args:
        session: 数据库会话
        admin: 管理员用户
        chip_type: 芯片类型
        version: 版本号
        description: 更新说明
        file: 上传的文件
    """
    # 验证版本号格式
    try:
        version_obj = SemanticVersion(version)
    except ValueError:
        utils.raise_bad_request("Invalid semantic version format")

    # 验证文件扩展名
    if not file.filename or not file.filename.endswith('.bin'):
        utils.raise_bad_request("Only .bin files are supported")

    # 检查是否已存在相同芯片类型和版本的固件
    from sqlalchemy import and_
    existing = await Firmware.get(
        session,
        and_(
            Firmware.chip_type == chip_type,
            Firmware.version == str(version_obj)
        )
    )
    if existing:
        utils.raise_conflict(f"Firmware {chip_type} v{version} already exists")

    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 验证文件大小
    if file_size > MAX_FIRMWARE_SIZE:
        utils.raise_bad_request(f"File size exceeds {MAX_FIRMWARE_SIZE} bytes")

    if file_size == 0:
        utils.raise_bad_request("Empty file")

    # 生成文件名
    safe_filename = f"{chip_type}_{version}_{file.filename}"
    file_path = FIRMWARE_STORAGE_PATH / safe_filename

    # 写入文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 计算 MD5
    file_md5 = _calculate_md5(file_path)

    # 创建数据库记录
    firmware = Firmware(
        chip_type=chip_type,
        version=str(version_obj),
        file_path=str(file_path),
        file_size=file_size,
        file_md5=file_md5,
        description=description,
        uploaded_by_id=admin.id,
    )

    await Firmware.add(session, firmware)
    logger.info(f"Admin {admin.email} uploaded firmware {chip_type} v{version}")


async def list_firmwares(
    session: SessionDep,
    chip_type: ChipTypeEnum | None,
    is_active: bool | None,
) -> List[FirmwareDataResponseAdmin]:
    """
    获取固件列表。

    Args:
        session: 数据库会话
        chip_type: 筛选芯片类型
        is_active: 筛选启用状态

    Returns:
        固件列表
    """
    from sqlalchemy import and_

    conditions = []

    if chip_type:
        conditions.append(Firmware.chip_type == chip_type)
    if is_active is not None:
        conditions.append(Firmware.is_active == is_active)

    if conditions:
        results = await Firmware.get(session, and_(*conditions), fetch_mode="all")
    else:
        results = await Firmware.get(session, fetch_mode="all")

    if not results:
        return []

    return [FirmwareDataResponseAdmin.model_validate(fw) for fw in results]


async def delete_firmware(
    session: SessionDep,
    firmware_id: UUID,
) -> None:
    """
    删除固件包。

    Args:
        session: 数据库会话
        firmware_id: 固件ID
    """
    firmware = await Firmware.get(session, Firmware.id == firmware_id)
    if not firmware:
        utils.raise_not_found("Firmware not found")

    # 删除文件
    file_path = Path(firmware.file_path)
    if file_path.exists():
        file_path.unlink()

    # 删除数据库记录
    await Firmware.delete(session, firmware)


async def toggle_firmware_status(
    session: SessionDep,
    firmware_id: UUID,
    is_active: bool,
) -> None:
    """
    切换固件启用状态。

    Args:
        session: 数据库会话
        firmware_id: 固件ID
        is_active: 目标状态
    """
    firmware = await Firmware.get(session, Firmware.id == firmware_id)
    if not firmware:
        utils.raise_not_found("Firmware not found")

    firmware.is_active = is_active
    await firmware.save(session)
