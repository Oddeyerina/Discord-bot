import os

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from auth import check_password, require_session, signer

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginInput(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginInput, response: Response) -> dict[str, str]:
    if not check_password(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    response.set_cookie("dcbot_session", signer().dumps(body.username), httponly=True,
                        samesite="lax", secure=os.getenv("COOKIE_SECURE") == "true",
                        max_age=86400, path="/")
    return {"username": body.username}


@router.post("/logout")
def logout(response: Response, _: str = Depends(require_session)) -> dict[str, bool]:
    response.delete_cookie("dcbot_session", path="/")
    return {"ok": True}


@router.get("/me")
def me(username: str = Depends(require_session)) -> dict[str, str]:
    return {"username": username}
