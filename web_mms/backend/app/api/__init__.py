from fastapi import APIRouter

from app.api import accounts, consignments, errors, images, imports, inventory, print_queue, users

router = APIRouter(prefix="/api/v1")
for child in (inventory.router, imports.router, accounts.router, errors.router, users.router, consignments.router, print_queue.router, images.router):
    router.include_router(child)
