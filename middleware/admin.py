from typing import Annotated
from fastapi import Depends

from model.user import UserTypeEnum
from .user import get_current_user
from pkg import utils
from model import User
from middleware.dependencies import SessionDep

# 验证是否为管理员
async def is_admin(
        user: Annotated[User, Depends(get_current_user)],
) -> User:
    '''
    验证是否为管理员。
    
    使用方法：
    >>> APIRouter(dependencies=[Depends(is_admin)])
    '''
    
    if user.role == UserTypeEnum.normal_user:
        utils.raise_forbidden("Admin access required")
    else:
        return user
    
async def is_super_admin(
        user: Annotated[User, Depends(is_admin)],
) -> User:
    '''
    验证是否为超级管理员。
    
    使用方法：
    >>> APIRouter(dependencies=[Depends(is_super_admin)])
    '''

    if user.role != UserTypeEnum.super_admin:
        utils.raise_forbidden("Super admin access required")
    else:
        return user