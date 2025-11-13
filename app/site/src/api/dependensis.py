from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.database.core import get_session


SessionDeep = Annotated[AsyncSession, Depends(get_session)]
