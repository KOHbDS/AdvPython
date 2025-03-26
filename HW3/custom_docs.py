from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

def setup_custom_docs(app: FastAPI):
    # Сохраняем оригинальную документацию для использования
    original_docs = app.routes[app.docs_url]
    original_redoc = app.routes[app.redoc_url]
    
    # Удаляем стандартные маршруты документации
    app.docs_url = None
    app.redoc_url = None
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html(request: Request):
        """
        Пользовательская страница Swagger UI с CDN-ресурсами
        """
        root_path = request.scope.get("root_path", "").rstrip("/")
        openapi_url = f"{root_path}/openapi.json"
        
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html(request: Request):
        """
        Пользовательская страница ReDoc с CDN-ресурсами
        """
        root_path = request.scope.get("root_path", "").rstrip("/")
        openapi_url = f"{root_path}/openapi.json"
        
        return get_redoc_html(
            openapi_url=openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        )
