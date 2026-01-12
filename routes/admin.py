from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from starlette.status import HTTP_204_NO_CONTENT

from middleware.admin import is_admin
from middleware.dependencies import SessionDep
from model import User, DefaultResponse
from model.firmware import ChipTypeEnum
from services import admin as admin_service

Router = APIRouter(
    prefix='/api/admin', 
    tags=['管理员 Admin'],
    dependencies=[Depends(is_admin)]
)

@Router.get(
    path='/',
    summary='验证管理员身份',
    description='返回管理员身份验证结果',
    response_model=DefaultResponse,
    response_description='当前为管理员'
)
async def verity_admin() -> DefaultResponse:
    '''
    使用 API 验证是否为管理员。
    
    - 若为管理员，返回 `True`
    - 若不是管理员，抛出 `401` 错误
    '''
    return DefaultResponse(data=True)

@Router.get(
    path='api/admin/settings',
    summary='获取设置项',
    description='获取设置项, 留空则获取所有',
    response_model=DefaultResponse,
    response_description='设置项列表'
)
async def get_settings(
    session: SessionDep,
    name: str | None = None
) -> DefaultResponse:
    data = await admin_service.fetch_settings(session=session, name=name)
    return DefaultResponse(data=data)


@Router.put(
    path='api/admin/settings',
    summary='更新设置项',
    description='更新设置项',
    response_model=DefaultResponse,
    response_description='更新结果'
)
async def update_settings(
    session: SessionDep,
    name: str,
    value: str
) -> DefaultResponse:
    result = await admin_service.update_setting_value(session=session, name=name, value=value)
    return DefaultResponse(data=result)


# 固件管理接口

@Router.post(
    path='/firmware',
    summary='上传固件包',
    description='管理员上传新的固件更新包',
    status_code=HTTP_204_NO_CONTENT,
    response_description='上传成功'
)
async def upload_firmware(
    session: SessionDep,
    admin: Annotated[User, Depends(is_admin)],
    chip_type: ChipTypeEnum = Form(..., description='芯片类型'),
    version: str = Form(..., description='版本号'),
    description: str | None = Form(None, description='更新说明'),
    file: UploadFile = File(..., description='固件文件'),
):
    """
    上传固件包。

    支持的文件格式：.bin
    文件大小限制：4MB
    """
    await admin_service.upload_firmware(
        session=session,
        admin=admin,
        chip_type=chip_type,
        version=version,
        description=description,
        file=file,
    )


@Router.get(
    path='/firmwares',
    summary='获取固件列表',
    description='获取已上传的固件列表',
    response_model=DefaultResponse,
    response_description='固件列表'
)
async def list_firmwares(
    session: SessionDep,
    admin: Annotated[User, Depends(is_admin)],
    chip_type: ChipTypeEnum | None = Query(None, description='筛选芯片类型'),
    is_active: bool | None = Query(None, description='筛选启用状态'),
) -> DefaultResponse:
    """
    获取固件列表。
    """
    result = await admin_service.list_firmwares(
        session=session,
        chip_type=chip_type,
        is_active=is_active,
    )
    return DefaultResponse(data=result)


@Router.delete(
    path='/firmware/{firmware_id}',
    summary='删除固件',
    description='删除指定的固件包',
    status_code=HTTP_204_NO_CONTENT,
    response_description='删除成功'
)
async def delete_firmware(
    session: SessionDep,
    admin: Annotated[User, Depends(is_admin)],
    firmware_id: UUID,
):
    """
    删除固件包。
    """
    await admin_service.delete_firmware(
        session=session,
        firmware_id=firmware_id,
    )


@Router.patch(
    path='/firmware/{firmware_id}/status',
    summary='切换固件状态',
    description='启用或禁用固件',
    status_code=HTTP_204_NO_CONTENT,
    response_description='操作成功'
)
async def toggle_firmware_status(
    session: SessionDep,
    admin: Annotated[User, Depends(is_admin)],
    firmware_id: UUID,
    is_active: bool = Query(..., description='目标状态'),
):
    """
    切换固件启用状态。
    """
    await admin_service.toggle_firmware_status(
        session=session,
        firmware_id=firmware_id,
        is_active=is_active,
    )
