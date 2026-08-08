from fastapi import APIRouter

from app.schemas import CurrentUserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserOut)
def current_user():
    # Secure local-development identity; production IdP integration remains documented work.
    return CurrentUserOut(id=None, email="developer@localhost", display_name="Development User", roles=["Admin"], development=True)
