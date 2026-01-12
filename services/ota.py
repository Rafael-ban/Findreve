"""OTA 服务层，处理 ESP32/8266 设备的在线升级业务逻辑。"""

from pathlib import Path

from fastapi.responses import FileResponse
from loguru import logger
from pydantic_extra_types.semantic_version import SemanticVersion

from model import Firmware, Item
from model.firmware import ChipTypeEnum, FirmwareCheckUpdateResponse
from middleware.dependencies import SessionDep
from model.item import ItemStatusEnum
from pkg import utils

# 固件存储目录
FIRMWARE_STORAGE_PATH = Path("data/firmware")
FIRMWARE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


async def check_firmware_update(
    session: SessionDep,
    device: Item,
    chip_type: ChipTypeEnum,
    current_version: str,
) -> FirmwareCheckUpdateResponse:
    """
    检查设备是否有可用的固件更新。

    Args:
        session: 数据库会话
        device: 设备对象
        chip_type: 芯片类型
        current_version: 当前版本号

    Returns:
        FirmwareCheckUpdateResponse: 更新检查结果
    """
    # 验证当前版本格式
    try:
        current = SemanticVersion(current_version)
    except ValueError:
        logger.warning(f"Invalid version format from device {device.id}: {current_version}")
        utils.raise_bad_request("Invalid version format")

    # 查找该芯片类型的最新启用固件
    all_firmwares = await Firmware.get(
        session,
        (Firmware.chip_type == chip_type) & (Firmware.is_active == True),
        fetch_mode="all"
    )

    if not all_firmwares:
        return FirmwareCheckUpdateResponse(
            has_update=False,
        )

    # 过滤出比当前版本新的固件
    newer_firmwares = []
    for fw in all_firmwares:
        try:
            fw_version = SemanticVersion(str(fw.version))
            if fw_version > current:
                newer_firmwares.append(fw)
        except ValueError:
            logger.warning(f"Invalid firmware version in database: {fw.version}")
            continue

    if not newer_firmwares:
        return FirmwareCheckUpdateResponse(
            has_update=False,
        )

    # 取最新版本
    latest = max(newer_firmwares, key=lambda fw: SemanticVersion(str(fw.version)))

    return FirmwareCheckUpdateResponse(
        has_update=True,
        latest_version=str(latest.version),
        download_url=f"/api/ota/download/{latest.id}",
        file_size=latest.file_size,
        file_md5=latest.file_md5,
        description=latest.description,
    )


async def get_firmware_file(
    session: SessionDep,
    firmware_id: str,
    device: Item,
) -> FileResponse:
    """
    获取固件文件并更新下载统计。

    Args:
        session: 数据库会话
        firmware_id: 固件ID
        device: 设备对象

    Returns:
        FileResponse: 固件文件响应
    """
    from uuid import UUID

    firmware = await Firmware.get(session, Firmware.id == UUID(firmware_id))

    if not firmware:
        utils.raise_not_found("Firmware not found")

    if not firmware.is_active:
        utils.raise_forbidden("Firmware is not available")

    # 验证芯片类型匹配
    if device.chip_type != firmware.chip_type:
        utils.raise_forbidden("Firmware chip type mismatch")

    # 更新下载计数
    firmware.downloaded_count += 1
    await firmware.save(session)

    file_path = Path(firmware.file_path)
    if not file_path.exists():
        logger.error(f"Firmware file not found: {file_path}")
        utils.raise_internal_error("Firmware file not available")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )


async def update_device_version(
    session: SessionDep,
    device: Item,
    version: str,
) -> None:
    """
    更新设备上报的固件版本。

    Args:
        session: 数据库会话
        device: 设备对象
        version: 版本号字符串
    """
    try:
        SemanticVersion(version)
    except ValueError:
        utils.raise_bad_request("Invalid version format")

    device.version = version
    await device.save(session)
    logger.info(f"Device {device.id} reported version: {version}")


async def report_device_lost(
    session: SessionDep,
    device: Item,
) -> None:
    """
    设备上报丢失状态。

    Args:
        session: 数据库会话
        device: 设备对象
    """
    device.status = ItemStatusEnum.lost
    await device.save(session)
    logger.info(f"Device {device.id} reported as lost")
