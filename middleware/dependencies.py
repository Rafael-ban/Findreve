from typing import Annotated, TypeAlias

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from model.database import Database
from model.mixin.table import TableViewRequest

SessionDep: TypeAlias = Annotated[AsyncSession, Depends(Database.get_session)]
"""数据库会话依赖，用于路由函数中获取数据库会话"""

# 新增：表格视图请求依赖（用于分页排序）
TableViewRequestDep: TypeAlias = Annotated[TableViewRequest, Depends()]
"""分页排序请求依赖，用于 LIST 端点"""
