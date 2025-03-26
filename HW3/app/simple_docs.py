from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html

def add_custom_docs(app: FastAPI) -> None:
    """
    Добавляет простую пользовательскую страницу документации
    
    Args:
        app: Экземпляр FastAPI приложения
    """
    # Отключаем стандартную документацию
    app.docs_url = None
    
    @app.get("/docs", response_class=HTMLResponse)
    async def custom_docs(request: Request) -> HTMLResponse:
        """
        Кастомная страница документации Swagger UI
        """
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - API Documentation",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.18.3/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.18.3/swagger-ui.css",
        )
