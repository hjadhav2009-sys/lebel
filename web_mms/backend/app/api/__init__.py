from fastapi import APIRouter

from app.api import address_profiles, accounts, consignments, errors, images, imports, inventory, label_formats, print_queue, users

router = APIRouter(prefix="/api/v1")
for child in (inventory.router, imports.router, accounts.router, errors.router, users.router, consignments.router, consignments.line_router, print_queue.router, print_queue.printers_router, address_profiles.router, label_formats.router, images.router):
    router.include_router(child)
