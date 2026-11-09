from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.booking import router as booking_router
from app.api.cases import router as cases_router
from app.api.documents import router as documents_router
from app.api.lawyer_profiles import router as lawyer_profiles_router
from app.api.lawyers import router as lawyers_router
from app.api.notifications import router as notifications_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(booking_router)
app.include_router(cases_router)
app.include_router(documents_router)
app.include_router(lawyer_profiles_router)
app.include_router(lawyers_router)
app.include_router(notifications_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Faisla-PK LegalTech API is running successfully"}
