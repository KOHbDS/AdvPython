from locust import HttpUser, task, between
import random
import string
import json

class URLShortenerUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Выполняется при старте каждого пользователя"""
        username = f"test_user_{random.randint(1000, 9999)}"
        response = self.client.post(
            "/users/",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "password123"
            }
        )
        
        if response.status_code == 400:
            username = f"test_user_{random.randint(10000, 99999)}"
            response = self.client.post(
                "/users/",
                json={
                    "username": username,
                    "email": f"{username}@example.com",
                    "password": "password123"
                }
            )
        
        response = self.client.post(
            "/token",
            data={
                "username": username,
                "password": "password123"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            self.token = None
            print(f"Failed to get token: {response.text}")
    
    @task(3)
    def create_short_link(self):
        """Создание короткой ссылки"""
        if not hasattr(self, 'token') or not self.token:
            return
            
        random_url = f"https://example.com/{self._random_string(10)}"
        random_alias = self._random_string(6)
        
        with self.client.post(
            "/links/shorten",
            json={
                "original_url": random_url,
                "custom_alias": random_alias
            },
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                if not hasattr(self, 'short_codes'):
                    self.short_codes = []
                self.short_codes.append(response.json()["short_code"])
            else:
                response.failure(f"Failed to create short link: {response.text}")
    
    @task(5)
    def get_redirect(self):
        """Переход по короткой ссылке"""
        if hasattr(self, 'short_codes') and self.short_codes:
            short_code = random.choice(self.short_codes)
        else:
            short_code = self._random_string(6)
            
        with self.client.get(
            f"/{short_code}",
            catch_response=True,
            allow_redirects=False
        ) as response:
            if response.status_code == 307:
                response.success()
            elif response.status_code == 404:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(2)
    def get_link_stats(self):
        """Получение статистики по ссылке"""
        if not hasattr(self, 'token') or not self.token or not hasattr(self, 'short_codes') or not self.short_codes:
            return
            
        short_code = random.choice(self.short_codes)
        
        with self.client.get(
            f"/links/{short_code}/stats",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get stats: {response.text}")
    
    @task(1)
    def update_link(self):
        """Обновление ссылки"""
        if not hasattr(self, 'token') or not self.token or not hasattr(self, 'short_codes') or not self.short_codes:
            return
            
        short_code = random.choice(self.short_codes)
        
        with self.client.put(
            f"/links/{short_code}",
            json={
                "original_url": f"https://updated-example.com/{self._random_string(10)}"
            },
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to update link: {response.text}")
    
    def _random_string(self, length):
        """Генерация случайной строки"""
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for _ in range(length))
