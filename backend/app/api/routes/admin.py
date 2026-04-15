from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.security import require_admin_user
from app.schemas.admin import (
    AdminLookupsResponse,
    NamedLookup,
    NamedLookupCreate,
    WebsiteCreate,
    WebsiteRow,
    WebsiteUpdate,
    StoreCreate,
    StoreRow,
    StoreUpdate,
    ProductFormatCreate,
    ProductFormatRow,
    ProductFormatUpdate,
    ProductUrlActiveUpdate,
    ProductUrlCreate,
    ProductUrlRow,
    ProductUrlUpdate,
    UserCreate,
    UserActiveUpdate,
    UserRow,
    UserUpdate,
)
from app.services.admin_service import (
    create_brand,
    create_category,
    create_website,
    create_store,
    create_product_format,
    create_product_url,
    create_range,
    create_user,
    delete_website,
    delete_store,
    delete_product_format,
    delete_product_url,
    delete_user,
    get_admin_lookups,
    list_websites,
    list_stores,
    list_product_formats,
    list_product_urls,
    list_users,
    update_website,
    update_store,
    set_product_url_active,
    set_user_active,
    update_product_format,
    update_product_url,
    update_user,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_http_error(exc: Exception):
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/lookups", response_model=AdminLookupsResponse)
def admin_lookups(current_user: dict = Depends(require_admin_user)):
    del current_user
    return get_admin_lookups()


@router.get("/websites", response_model=list[WebsiteRow])
def admin_websites(current_user: dict = Depends(require_admin_user)):
    del current_user
    return list_websites()


@router.post("/websites", response_model=WebsiteRow, status_code=status.HTTP_201_CREATED)
def admin_create_website(payload: WebsiteCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_website(payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.put("/websites/{website_id}", response_model=WebsiteRow)
def admin_update_website(website_id: int, payload: WebsiteUpdate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return update_website(website_id, payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.delete("/websites/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_website(website_id: int, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        delete_website(website_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.get("/stores", response_model=list[StoreRow])
def admin_stores(current_user: dict = Depends(require_admin_user)):
    del current_user
    return list_stores()


@router.post("/stores", response_model=StoreRow, status_code=status.HTTP_201_CREATED)
def admin_create_store(payload: StoreCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_store(payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.put("/stores/{store_id}", response_model=StoreRow)
def admin_update_store(store_id: int, payload: StoreUpdate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return update_store(store_id, payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.delete("/stores/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_store(store_id: int, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        delete_store(store_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.post("/lookups/brands", response_model=NamedLookup, status_code=status.HTTP_201_CREATED)
def admin_create_brand(payload: NamedLookupCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_brand(payload.name)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.post("/lookups/categories", response_model=NamedLookup, status_code=status.HTTP_201_CREATED)
def admin_create_category(payload: NamedLookupCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_category(payload.name)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.post("/lookups/ranges", response_model=NamedLookup, status_code=status.HTTP_201_CREATED)
def admin_create_range(payload: NamedLookupCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_range(payload.name)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.get("/product-formats", response_model=list[ProductFormatRow])
def admin_product_formats(current_user: dict = Depends(require_admin_user)):
    del current_user
    return list_product_formats()


@router.post("/product-formats", response_model=ProductFormatRow, status_code=status.HTTP_201_CREATED)
def admin_create_product_format(payload: ProductFormatCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_product_format(payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.put("/product-formats/{product_format_id}", response_model=ProductFormatRow)
def admin_update_product_format(
    product_format_id: int,
    payload: ProductFormatUpdate,
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    try:
        return update_product_format(product_format_id, payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.delete("/product-formats/{product_format_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_product_format(product_format_id: int, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        delete_product_format(product_format_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.get("/product-urls", response_model=list[ProductUrlRow])
def admin_product_urls(current_user: dict = Depends(require_admin_user)):
    del current_user
    return list_product_urls()


@router.post("/product-urls", response_model=ProductUrlRow, status_code=status.HTTP_201_CREATED)
def admin_create_product_url(payload: ProductUrlCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_product_url(payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.put("/product-urls/{product_url_id}", response_model=ProductUrlRow)
def admin_update_product_url(
    product_url_id: int,
    payload: ProductUrlUpdate,
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    try:
        return update_product_url(product_url_id, payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.patch("/product-urls/{product_url_id}/active", response_model=ProductUrlRow)
def admin_set_product_url_active(
    product_url_id: int,
    payload: ProductUrlActiveUpdate,
    current_user: dict = Depends(require_admin_user),
):
    del current_user
    try:
        return set_product_url_active(product_url_id, payload.is_active)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.delete("/product-urls/{product_url_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_product_url(product_url_id: int, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        delete_product_url(product_url_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.get("/users", response_model=list[UserRow])
def admin_users(current_user: dict = Depends(require_admin_user)):
    del current_user
    return list_users()


@router.post("/users", response_model=UserRow, status_code=status.HTTP_201_CREATED)
def admin_create_user(payload: UserCreate, current_user: dict = Depends(require_admin_user)):
    del current_user
    try:
        return create_user(payload.model_dump())
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.put("/users/{user_id}", response_model=UserRow)
def admin_update_user(user_id: int, payload: UserUpdate, current_user: dict = Depends(require_admin_user)):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    try:
        return update_user(user_id, updates, current_user_id=int(current_user["id"]))
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.patch("/users/{user_id}/active", response_model=UserRow)
def admin_set_user_active(user_id: int, payload: UserActiveUpdate, current_user: dict = Depends(require_admin_user)):
    try:
        return set_user_active(user_id, payload.is_active, current_user_id=int(current_user["id"]))
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(user_id: int, current_user: dict = Depends(require_admin_user)):
    try:
        delete_user(user_id, current_user_id=int(current_user["id"]))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:  # noqa: BLE001
        _to_http_error(exc)
