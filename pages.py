from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def render(request: Request, name: str, **context):
    return templates.TemplateResponse(request=request, name=name, context=context)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return render(request, "index.html", title="PocketSmart AI")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render(request, "login.html", title="Login")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render(request, "register.html", title="Register")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return render(request, "dashboard.html", title="Dashboard")


@router.get("/planner/{planner}", response_class=HTMLResponse)
async def planner(request: Request, planner: str):
    if planner not in {"home", "party", "jewelry"}:
        return render(request, "404.html", title="Not found")
    return render(request, "planner.html", title=f"{planner.title()} Planner", planner=planner)


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    return render(request, "history.html", title="History")
