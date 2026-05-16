import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.db.connection import get_connection
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.username, u.password_hash, u.full_name, r.name AS role, u.is_active
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE username = %s
                LIMIT 1
                """,
                (payload.username,),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

            user_id, username, password_hash, full_name, role, is_active = row
            if not is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

            is_valid_password = bcrypt.checkpw(payload.password.encode("utf-8"), password_hash.encode("utf-8"))
            if not is_valid_password:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
            conn.commit()

    token = create_access_token(
        payload={"sub": username, "uid": user_id, "role": role},
        secret=settings.AUTH_SECRET,
        expires_minutes=settings.AUTH_TOKEN_EXPIRE_MINUTES,
    )

    return LoginResponse(
        access_token=token,
        user=UserOut(id=user_id, username=username, full_name=full_name, role=role),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        id=current_user["id"],
        username=current_user["username"],
        full_name=current_user.get("full_name"),
        role=current_user["role"],
    )
