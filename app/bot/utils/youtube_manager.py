import json
import os
import time

import aiohttp
import httpx
import aiofiles
from typing import Dict, Any, List


class YouTubeManager:
    @staticmethod
    async def download_video_from_telegram(file_id: str, bot, user_id: int) -> str:
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        download_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"

        timestamp = int(time.time())
        local_path = f"/tmp/video_{user_id}_{timestamp}.mp4"

        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as resp:
                if resp.status != 200:
                    raise Exception("Не удалось скачать видео из Telegram")
                data = await resp.read()

        async with aiofiles.open(local_path, "wb") as f:
            await f.write(data)

        return local_path


    @staticmethod
    async def upload_to_all_accounts(
        video_file_path: str,
        template_data: Dict[str, Any],
        youtube_accounts: List[Dict[str, str]],
        video_duration_sec: int,
        video_width: int,
        video_height: int
    ) -> List[Dict[str, Any]]:

        if isinstance(template_data, str):
            template_data = json.loads(template_data)

        results = []

        is_short = template_data.get("publish_as_short", False)
        if video_duration_sec <= 60 and video_height > video_width:
            is_short = True

        returned_json = {
            "snippet": {
                "title": template_data.get("title", "Пустое"),
                "description": template_data.get("description", "Описание..."),
                "tags": template_data.get("tags", []),
                "categoryId": template_data.get("category_id", 22),
                "defaultLanguage": template_data.get("language", "ru"),
                "liveBroadcastContent": "none"
            },
            "status": {
                "privacyStatus": template_data.get("privacy_status", "public"),
                "embeddable": template_data.get("allow_embedding", True),
                "license": template_data.get("license", "youtube"),
                "selfDeclaredMadeForKids": template_data.get("made_for_kids", False)
            }
        }

        if is_short:
            returned_json["snippet"]["title"] = returned_json["snippet"]["title"] + " #Shorts"

        params = {
            "uploadType": "resumable",
            "part": "snippet,status"
        }

        async with httpx.AsyncClient(timeout=None) as client:
            for account in youtube_accounts:
                access_token = account.get("access_token")
                account_name = account.get("account_name", "unknown")

                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8"
                }

                try:
                    resp = await client.post(
                        "https://www.googleapis.com/upload/youtube/v3/videos",
                        headers=headers,
                        params=params,
                        data=returned_json
                    )
                    resp.raise_for_status()
                    upload_url = resp.headers.get("Location")
                    if not upload_url:
                        results.append({
                            "account": account_name,
                            "success": False,
                            "error": "Не удалось получить URL для загрузки видео"
                        })
                        continue

                    # Загружаем видео
                    video_headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "video/mp4"
                    }

                    async with aiofiles.open(video_file_path, "rb") as f:
                        video_data = await f.read()

                    upload_resp = await client.put(
                        upload_url,
                        headers=video_headers,
                        content=video_data
                    )
                    upload_resp.raise_for_status()
                    result_json = upload_resp.json()

                    results.append({
                        "account": account_name,
                        "success": True,
                        "video_id": result_json.get("id"),
                        "is_short": is_short,
                        "response": result_json
                    })

                except httpx.HTTPStatusError as e:
                    results.append({
                        "account": account_name,
                        "success": False,
                        "error": f"HTTP ошибка {e.response.status_code}",
                        "details": e.response.text
                    })
                except httpx.RequestError as e:
                    results.append({
                        "account": account_name,
                        "success": False,
                        "error": f"Ошибка запроса: {str(e)}"
                    })
                except Exception as e:
                    results.append({
                        "account": account_name,
                        "success": False,
                        "error": f"Неизвестная ошибка: {str(e)}"
                    })

        try:
            os.remove(video_file_path)
        except Exception:
            pass

        return results





