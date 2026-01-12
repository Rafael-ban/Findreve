from typing import Annotated

import jwt
from fastapi import Depends
from jwt import InvalidTokenError
from loguru import logger as l

import JWT
from model import User
from pkg import utils
from middleware.dependencies import SessionDep

async def get_current_user(
        token: Annotated[str, Depends(JWT.oauth2_scheme)],
        session: SessionDep,
) -> User:
    """
    验证用户身份并返回当前用户信息。
    """

    try:
        payload = jwt.decode(token, await JWT.get_secret_key(), algorithms=[JWT.ALGORITHM])
        email = payload.get("sub")
        stored_account = await User.get(session, User.email == email)
        if stored_account is None:
            l.warning("Account not found")
            utils.raise_unauthorized("Login required")
        elif stored_account.email != email:
            l.warning("Email mismatch")
            utils.raise_unauthorized("Login required")
        return stored_account
    except InvalidTokenError:
        utils.raise_unauthorized("Login required")