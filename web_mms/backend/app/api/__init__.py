from fastapi import APIRouter

from app.api import address_profiles, accounts, auth, consignments, errors, images, imports, inventory, label_formats, print_queue, printer_management, users

router = APIRouter(prefix="/api/v1")
for child in (auth.router,inventory.router, imports.router, accounts.router, errors.router, users.router, consignments.router, consignments.line_router, print_queue.router, print_queue.printers_router, printer_management.router, address_profiles.router, label_formats.router, images.router):
    router.include_router(child)
