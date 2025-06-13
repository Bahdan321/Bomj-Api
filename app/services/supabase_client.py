import os
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Any, Optional
from sqlalchemy import insert, text, Table, MetaData
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession,
)


class SupabaseAsyncClient:
    echo: bool = True
    echo_pool: bool = True
    pool_size: int = 15
    max_overflow: int = 200

    # Параметры для настройки миграций Alembic
    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }

    # Асинхронный движок и фабрика сессий
    engine: AsyncEngine = None
    session_factory: async_sessionmaker[AsyncSession] = None
    metadata = MetaData()

    class Config:
        arbitrary_types_allowed = True  # Разрешаем использовать произвольные типы (AsyncEngine, async_sessionmaker)

    def __init__(self):
        # Инициализация движка и сессий при создании объекта
        self.engine = create_async_engine(
            url=self.DATABASE_URL,
            echo=self.echo,
            echo_pool=self.echo_pool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            execution_options={
                "assume_static_server_version": "17.0"  # Укажите версию PostgreSQL вручную
            },
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        """Закрытие подключения к базе данных"""
        await self.engine.dispose()

    async def get_session(self) -> AsyncSession:
        """Получение сессии для работы с базой данных"""
        async with self.session_factory() as session:
            return session

    async def session_getter(self) -> AsyncGenerator[AsyncSession, None]:
        """Асинхронный генератор сессий для использования в контексте async for"""
        session = None
        try:
            session = await self.get_session()
            yield session
        except Exception as e:
            print(f"Error in session_getter: {e}")
            if session:
                await session.rollback()
            raise
        finally:
            if session:
                await session.close()

    async def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Вставка одной записи в таблицу"""
        async with self.session_factory() as session:
            # Используем текстовый SQL вместо инспекции таблицы
            columns = ", ".join(data.keys())
            placeholders = ", ".join(f":{key}" for key in data.keys())
            query = text(
                f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
            )
            result = await session.execute(query, data)
            await session.commit()
            return dict(result.mappings().first())

    async def bulk_insert(
        self, table_name: str, data_list: List[Dict[str, Any]]
    ) -> None:
        """Массовая вставка записей в таблицу"""
        if not data_list:
            return

        async with self.session_factory() as session:
            # Используем текстовый SQL вместо инспекции таблицы
            # Предполагаем, что все словари в data_list имеют одинаковые ключи
            columns = ", ".join(data_list[0].keys())

            # Создаем запрос для массовой вставки
            values_placeholders = []
            for i, data in enumerate(data_list):
                placeholders = ", ".join(f":{key}_{i}" for key in data.keys())
                values_placeholders.append(f"({placeholders})")

            values_sql = ", ".join(values_placeholders)
            query_text = f"INSERT INTO {table_name} ({columns}) VALUES {values_sql}"

            # Подготавливаем параметры для запроса
            params = {}
            for i, data in enumerate(data_list):
                for key, value in data.items():
                    params[f"{key}_{i}"] = value

            # Выполняем запрос
            query = text(query_text)
            await session.execute(query, params)
            await session.commit()

    @property
    def DATABASE_URL(self) -> str:
        SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
        if not SUPABASE_DB_URL:
            raise RuntimeError(
                "Set SUPABASE_DB_URL env var with full connection string"
            )

        return SUPABASE_DB_URL


supabase_client = SupabaseAsyncClient()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in supabase_client.session_getter():
        yield session
