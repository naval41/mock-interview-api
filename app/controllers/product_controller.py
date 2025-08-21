from fastapi import APIRouter
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/products", tags=["Products"])

# All product endpoints are commented out for now as per request.
# @router.post("/", ...)
# async def create_product(...):
#     ...
# @router.get("/", ...)
# async def get_products(...):
#     ...
# @router.get("/category/{category}", ...)
# async def get_products_by_category(...):
#     ...
# @router.get("/search", ...)
# async def search_products(...):
#     ...
# @router.get("/my-products", ...)
# async def get_my_products(...):
#     ...
# @router.get("/{product_id}", ...)
# async def get_product(...):
#     ...
# @router.put("/{product_id}", ...)
# async def update_product(...):
#     ...
# @router.delete("/{product_id}", ...)
# async def delete_product(...):
#     ...