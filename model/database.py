# ~/models/database.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator, ClassVar
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from .migration import migration

# 加载环境变量
load_dotenv('.env')

# 获取 DEBUG 配置
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

ASYNC_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data.db")

engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=DEBUG,  # 根据 DEBUG 配置决定是否输出 SQL 日志
    connect_args={
        "check_same_thread": False
    } if ASYNC_DATABASE_URL.startswith("sqlite") else {},
    future=True,
    # pool_size=POOL_SIZE,
    # max_overflow=64,
)

_async_session_factory = sessionmaker(engine, class_=AsyncSession)


# 数据库类
class Database:
    """
    数据库管理类（单例模式）

    从 foxline 项目移植的改进版本，支持：
    - ClassVar 单例模式
    - 触发器 SQL 支持
    - 优雅关闭
    """
    engine: ClassVar[AsyncEngine | None] = None
    _async_session_factory: ClassVar[sessionmaker | None] = None

    def __init__(
        self,
        db_path: str = "data.db",  # db_path 数据库文件路径，默认为 data.db
    ):
        # 保持向后兼容：实例化时使用全局 engine
        self.db_path = db_path

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """获取数据库引擎"""
        return engine

    @staticmethod
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency to get a database session."""
        async with _async_session_factory() as session:
            yield session

    @staticmethod
    @asynccontextmanager
    async def session_context() -> AsyncGenerator[AsyncSession, None]:
        """
        提供异步上下文管理器用于直接获取数据库会话

        使用示例:
        >>> async with Database.session_context() as session:
                # 执行数据库操作
                pass
        """
        async with _async_session_factory() as session:
            yield session

    async def init_db(
        self,
        trigger_sqls: list[tuple[str, str, str]] | None = None,
    ):
        """
        创建数据库结构

        Args:
            trigger_sqls: 触发器SQL语句列表，每个元素为 (function_sql, drop_trigger_sql, create_trigger_sql)
        """
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

            # 创建触发器（如果提供）
            if trigger_sqls:
                for function_sql, drop_trigger_sql, create_trigger_sql in trigger_sqls:
                    await conn.exec_driver_sql(function_sql)
                    await conn.exec_driver_sql(drop_trigger_sql)
                    await conn.exec_driver_sql(create_trigger_sql)

        # For internal use, create a temporary context manager
        async with self.session_context() as session:
            await migration(session)  # 执行迁移脚本

    @classmethod
    async def close(cls):
        """
        优雅地关闭数据库连接引擎。

        仅应在应用结束时调用。

        这会释放引擎维护的所有数据库连接池资源。
        在应用程序关闭时调用此方法是一个好习惯。
        """
        if engine:
            await engine.dispose()
