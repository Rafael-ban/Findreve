"""OTA API 路由，处理 ESP32/8266 设备的在线升级请求。"""

from fastapi import APIRouter, Query, status
from starlette.status import HTTP_204_NO_CONTENT

from middleware.dependencies import SessionDep, DeviceDep
from model import DefaultResponse
from model.firmware import FirmwareCheckUpdateRequest, FirmwareCheckUpdateResponse
from services import ota as ota_service

Router = APIRouter(prefix='/api/ota', tags=['OTA升级'])


@Router.post(
    path='/check-update',
    summary='检查固件更新',
    description='设备通过 mTLS 认证后查询是否有新版本固件',
    response_model=DefaultResponse,
    response_description='更新检查结果'
)
async def check_update(
    session: SessionDep,
    device: DeviceDep,
    request_data: FirmwareCheckUpdateRequest,
) -> DefaultResponse:
    """
    检查固件更新。

    设备需要提供有效的 mTLS 客户端证书，证书 CN 字段为设备序列号。
    """
    result = await ota_service.check_firmware_update(
        session=session,
        device=device,
        chip_type=request_data.chip_type,
        current_version=request_data.current_version,
    )
    return DefaultResponse(data=result)


@Router.get(
    path='/download/{firmware_id}',
    summary='下载固件包',
    description='下载指定的固件更新包',
)
async def download_firmware(
    session: SessionDep,
    device: DeviceDep,
    firmware_id: str,
):
    """
    下载固件包。

    需要有效的设备证书，且下载会记录统计信息。
    """
    return await ota_service.get_firmware_file(
        session=session,
        firmware_id=firmware_id,
        device=device,
    )


@Router.post(
    path='/report-version',
    summary='上报设备版本',
    description='设备上报当前运行的固件版本',
    status_code=HTTP_204_NO_CONTENT,
    response_description='上报成功'
)
async def report_version(
    session: SessionDep,
    device: DeviceDep,
    version: str = Query(..., description='当前版本号'),
):
    """
    上报设备当前运行的固件版本。
    """
    await ota_service.update_device_version(
        session=session,
        device=device,
        version=version,
    )


@Router.post(
    path='/report-lost',
    summary='上报设备丢失',
    description='设备上报丢失状态',
    status_code=HTTP_204_NO_CONTENT,
    response_description='上报成功'
)
async def report_lost(
    session: SessionDep,
    device: DeviceDep,
):
    """
    设备上报丢失状态（复用现有丢失处理逻辑）。
    """
    await ota_service.report_device_lost(session=session, device=device)
