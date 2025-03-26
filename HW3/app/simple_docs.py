from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html
from typing import Optional

def add_custom_docs(app: FastAPI, title_suffix: Optional[str] = "API Documentation") -> None:
    """
    Добавляет простую пользовательскую страницу документации
    
    Args:
        app: Экземпляр FastAPI приложения
        title_suffix: Суффикс для заголовка документации
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
            title=f"{app.title} - {title_suffix}",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.1.0/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.1.0/swagger-ui.css",
        )
    
    @app.get("/test-docs", response_class=HTMLResponse)
    async def test_docs() -> HTMLResponse:
        """
        Простая тестовая HTML-страница для проверки рендеринга
        """
        html_content = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>Test Documentation</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <h1>Test Documentation Page</h1>
                <p>If you can see this page, HTML rendering works correctly.</p>
                <script>
                    console.log('JavaScript is working!');
                    document.body.style.backgroundColor = '#f0f0f0';
                </script>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)
