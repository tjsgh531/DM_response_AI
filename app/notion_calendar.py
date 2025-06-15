# app/notion_calendar.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

class NotionCalendarClient:
    def __init__(self):
        self.token = os.getenv("NOTION_API_TOKEN")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        self.page_url = "https://api.notion.com/v1/pages"
        self.db_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    # 예약하기
    def create_reservation(self, name: str, contact: str, start: str, end: str, memo: str = "") -> dict:
        """
        예약 정보를 Notion 캘린더에 추가합니다.
        """
        payload = {
            "parent": { "database_id": self.database_id },
            "properties": {
                "이름": {
                    "title": [ { "text": { "content": name } } ]
                },
                "연락처": {
                    "rich_text": [ { "text": { "content": contact } } ]
                },
                "예약일": {
                    "date": { "start": start, "end": end }
                },
                "메모": {
                    "rich_text": [ { "text": { "content": memo } } ]
                }
            }
        }

        response = requests.post(self.page_url, headers=self.headers, json=payload)
        print("📅 예약 생성 응답:", response.status_code)
        return response.json()

    # 예약 가능 시간 찾기
    def query_reservations_by_date(self, date: str) -> list:
        """
        해당 날짜의 예약 목록을 조회합니다.
        :param date: YYYY-MM-DD
        :return: 예약 리스트
        """
        start_of_day = f"{date}T00:00:00+09:00"
        end_of_day = f"{date}T23:59:59+09:00"

        payload = {
            "filter": {
                "property": "예약일",
                "date": {
                    "on_or_after": start_of_day,
                    "on_or_before": end_of_day
                }
            }
        }

        response = requests.post(self.db_url, headers=self.headers, json=payload)
        data = response.json()
        results = []

        for page in data.get("results", []):
            props = page["properties"]
            start = props["예약일"]["date"].get("start", "")
            end = props["예약일"]["date"].get("end", "")
            name = props["이름"]["title"][0]["plain_text"]
            results.append({"name": name, "start": start, "end": end})

        return results

    # 예약 정보 찾기
    def query_reservation_by_customer(self, name: str, contact: str) -> list:
        """
        이름과 연락처로 예약을 조회합니다.
        """
        payload = {
            "filter": {
                "and": [
                    { "property": "이름", "title": { "equals": name } },
                    { "property": "연락처", "rich_text": { "equals": contact } }
                ]
            }
        }

        response = requests.post(self.db_url, headers=self.headers, json=payload)
        return response.json().get("results", [])

    # 예약 변경하기
    def update_reservation(self, name: str, contact: str, old_date: str, old_start: str, new_start: str, new_end: str):
        """
        기존 예약 정보를 찾아 새 날짜 및 시간으로 수정합니다.
        """
        matches = self.query_reservation_by_customer(name, contact)
        for page in matches:
            date_info = page["properties"]["예약일"].get("date", {})
            if date_info.get("start", "").startswith(old_date) and date_info.get("start") == old_start:
                page_id = page["id"]
                payload = {
                    "properties": {
                        "예약일": {
                            "date": {
                                "start": new_start,
                                "end": new_end
                            }
                        }
                    }
                }
                response = requests.patch(f"{self.page_url}/{page_id}", headers=self.headers, json=payload)
                return response.json()

        return {"error": "예약을 찾을 수 없습니다."}

    # 예약 취소 하기
    def cancel_reservation(self, name: str, contact: str, date: str, start: str):
        """
        예약을 찾아서 archive (취소) 처리합니다.
        """
        matches = self.query_reservation_by_customer(name, contact)
        for page in matches:
            date_info = page["properties"]["예약일"].get("date", {})
            if date_info.get("start", "").startswith(date) and date_info.get("start") == start:
                page_id = page["id"]
                response = requests.patch(f"{self.page_url}/{page_id}", headers=self.headers, json={"archived": True})
                return response.json()

        return {"error": "예약을 찾을 수 없습니다."}
