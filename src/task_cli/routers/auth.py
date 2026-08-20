from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from task_cli.dependencies import get_db

from task_cli.schemas_user import (
    UserLogin,
)

from task_cli.user_service import (
    get_user_by_username,
)

from task_cli.security import (
    verify_password,
)

from task_cli.auth import (
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = get_user_by_username(
        db,
        form_data.username
    )


    if not user:

        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )


    if not verify_password(
        form_data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误"
        )


    token = create_access_token(
        {
            "user_id": user.id
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer"
    }