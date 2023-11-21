# Copyright 2022 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_422_UNPROCESSABLE_ENTITY
)
import traceback
import odoo

from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError


from .context import odoo_env_ctx

_logger = logging.getLogger(__name__)

def extract_traceback(exc: Exception) -> list[str]:
    # extract traceback
    trace_text = ''.join(traceback.format_tb(exc.__traceback__))
    return trace_text.splitlines()

def _rollback(request: Request, reason: str) -> None:
    cr = odoo_env_ctx.get().cr
    if cr is not None:
        _logger.debug("rollback on %s", reason)
        cr.rollback()


async def _odoo_user_error_handler(
    request: Request, exc: odoo.exceptions.UserError
) -> JSONResponse:
    _rollback(request, "UserError")
    return JSONResponse(
        {
            "status_code": HTTP_400_BAD_REQUEST,
            "message": "error",
            "data": {},
            "meta": {},
            "exception": "Access Error",
            "traceback": extract_traceback(exc)
        },
        status_code=HTTP_400_BAD_REQUEST, headers=getattr(exc, "headers", None)
    )


async def _odoo_access_error_handler(
    request: Request, _exc: odoo.exceptions.AccessError
) -> JSONResponse:
    _rollback(request, "AccessError")
    return JSONResponse(
        {
            "status_code": HTTP_403_FORBIDDEN,
            "message": "error",
            "data": {},
            "meta": {},
            "exception": "Access Error",
            "traceback": extract_traceback(_exc)
        },
        status_code=HTTP_403_FORBIDDEN, headers=getattr(_exc, "headers", None)
    )

async def _odoo_missing_error_handler(
    request: Request, _exc: odoo.exceptions.MissingError
) -> JSONResponse:
    _rollback(request, "MissingError")
    return JSONResponse(
        {
            "status_code": HTTP_404_NOT_FOUND,
            "message": "error",
            "data": {},
            "meta": {},
            "exception": "MissingError",
            "traceback": extract_traceback(_exc)
        },
        status_code=HTTP_404_NOT_FOUND, headers=getattr(_exc, "headers", None)
    )


async def _odoo_validation_error_handler(
    request: Request, exc: odoo.exceptions.ValidationError
) -> JSONResponse:
    _rollback(request, "ValidationError")
    return JSONResponse(
        {
            "status_code": HTTP_400_BAD_REQUEST,
            "message": str(exc),
            "data": {},
            "meta": {},
            "exception": {
                "code": type(exc).__name__,
                "message": str(exc),
                "status_code": HTTP_400_BAD_REQUEST,
                "errors": []
            },
            "traceback": extract_traceback(exc)
        },
        status_code=HTTP_400_BAD_REQUEST, headers=getattr(exc, "headers", None)
    )


async def _odoo_http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    _rollback(request, "HTTPException")
    return JSONResponse(
        {
            "status_code": exc.status_code,
            "message": "error",
            "data": {},
            "meta": {},
            "exception": exc.detail,
            "traceback": extract_traceback(exc)
        },
        status_code=exc.status_code, headers=getattr(exc, "headers", None)
    )


async def _odoo_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _rollback(request, "Exception")
    return JSONResponse(
        {
            "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "error",
            "data": {},
            "meta": {},
            "exception": {
                "code": type(exc).__name__,
                "message": str(exc),
                "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
                "errors": []
            },
            "traceback": extract_traceback(exc)
        },
        status_code=500, headers=getattr(exc, "headers", None)
    )


async def _odoo_request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    _rollback(request, "RequestValidationError")
    errors = exc.errors()
    # get all msg from errors
    msg = []
    for err in errors:
        msg.append(err["msg"])
    return JSONResponse(
        {
            "status_code": HTTP_422_UNPROCESSABLE_ENTITY,
            "message": ', '.join(msg),
            "data": {},
            "meta": {},
            "exception": {
                "code": type(exc).__name__,
                "message": str(exc),
                "status_code": HTTP_422_UNPROCESSABLE_ENTITY,
                "errors": exc.errors()
            },
            "traceback": extract_traceback(exc)
        },
        status_code=500, headers=getattr(exc, "headers", None)
    )
