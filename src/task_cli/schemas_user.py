
from task_cli.dependencies import get_db
from pydantic import BaseModel, EmailStr



class UserCreate(BaseModel):

    username: str

    email: EmailStr

    password: str



class UserRead(BaseModel):

    id: int

    username: str

    email: EmailStr

class UserLogin(BaseModel):
    username: str
    password: str
