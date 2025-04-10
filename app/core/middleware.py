from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import json
from typing import Callable
from app.utils.logger import log_api_request, log_security_event
from app.core.config import settings
import traceback
import uuid

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Логирование успешного запроса
            user_id = None
            if "Authorization" in request.headers:
                # Извлечение user_id из токена
                pass  # TODO: Реализовать извлечение user_id
            
            log_api_request(
                request.method,
                str(request.url),
                response.status_code,
                user_id,
                duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            error_id = str(uuid.uuid4())
            
            # Логирование ошибки
            log_security_event(
                "error",
                f"Error ID: {error_id}, Path: {request.url}, Error: {str(e)}"
            )
            
            # Формирование ответа с ошибкой
            error_response = {
                "error_id": error_id,
                "message": "An error occurred",
                "detail": str(e) if settings.DEBUG else "Internal server error"
            }
            
            if settings.DEBUG:
                error_response["traceback"] = traceback.format_exc()
            
            return JSONResponse(
                status_code=500,
                content=error_response
            )

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Логирование входящего запроса
        body = await request.body()
        try:
            body_json = json.loads(body) if body else {}
        except:
            body_json = {}
            
        log_data = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": body_json,
            "client": request.client.host
        }
        
        response = await call_next(request)
        return response

class ResponseValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Проверка заголовков безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response 