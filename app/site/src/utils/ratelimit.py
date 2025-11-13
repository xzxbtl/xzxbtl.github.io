from collections import defaultdict
from datetime import time
from functools import wraps
from fastapi import Request
from app.shared.logs.logg import logger
from app.site.src.shared_path import templates


def rate_limit(max_calls: int, time_frame: int):
    """
    Ограничение на количество вызовов для пользователя
    :param max_calls:
    :param time_frame:
    :return:
    """

    def decorator(func):
        calls = defaultdict(list)

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            now = time()

            calls_in_frame = [call for call in calls[client_ip] if call > now - time_frame]
            calls[client_ip] = calls_in_frame

            if len(calls_in_frame) >= max_calls:
                logger.warning(msg=f'Rate Limit Exceeded: {len(calls_in_frame)}, user_id - {client_ip}')

                return templates.TemplateResponse(
                    "errors.html",
                    {"request": request, "message": "Вы слишком часто отправляете запросы. Подождите немного."},
                    status_code=429
                )

            calls[client_ip].append(now)
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
