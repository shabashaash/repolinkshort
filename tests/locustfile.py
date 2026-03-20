import random
import string
import os
from locust import HttpUser, task, between, events

def _random_url() -> str:
    slug = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"https://example.com/{slug}"

def _random_alias() -> str:
    return "alias-" + "".join(random.choices(string.ascii_lowercase, k=8))

class AnonymousLinkUser(HttpUser):
    wait_time = between(0.5, 2)
    weight = 3

    def on_start(self):
        self.short_codes: list[str] = []

    @task(3)
    def create_short_link(self):
        payload = {"original_url": _random_url()}
        with self.client.post(
            "/api/links/shorten",
            json=payload,
            catch_response=True,
            name="POST /api/links/shorten",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                sc = data.get("short_code")
                if sc:
                    self.short_codes.append(sc)
                resp.success()
            elif resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(5)
    def follow_short_link(self):
        if not self.short_codes:
            return
        sc = random.choice(self.short_codes)
        with self.client.get(
            f"/api/links/{sc}",
            allow_redirects=False,
            catch_response=True,
            name="GET /api/links/{short_code}",
        ) as resp:
            if resp.status_code in (200, 301, 302, 307, 308, 404, 410):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(2)
    def get_link_stats(self):
        if not self.short_codes:
            return
        sc = random.choice(self.short_codes)
        with self.client.get(
            f"/api/links/{sc}/stats",
            catch_response=True,
            name="GET /api/links/{short_code}/stats",
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

class AuthenticatedLinkUser(HttpUser):
    wait_time = between(1, 3)
    weight = 1

    def on_start(self):
        self.token: str | None = None
        self.managed_codes: list[str] = []
        self._login()

    def _login(self):
        email = os.getenv("LOCUST_USER_EMAIL", "loadtest@example.com")
        password = os.getenv("LOCUST_USER_PASSWORD", "loadtest_password")
        resp = self.client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            name="POST /api/auth/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")

    @property
    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(3)
    def create_and_track(self):
        payload = {
            "original_url": _random_url(),
            "project": "loadtest",
        }
        with self.client.post(
            "/api/links/shorten",
            json=payload,
            headers=self._auth,
            catch_response=True,
            name="POST /api/links/shorten [auth]",
        ) as resp:
            if resp.status_code == 200:
                sc = resp.json().get("short_code")
                if sc:
                    self.managed_codes.append(sc)
                resp.success()
            elif resp.status_code in (401, 422):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task(2)
    def update_link(self):
        if not self.managed_codes:
            return
        sc = random.choice(self.managed_codes)
        with self.client.put(
            f"/api/links/{sc}",
            json={"original_url": _random_url()},
            headers=self._auth,
            catch_response=True,
            name="PUT /api/links/{short_code}",
        ) as resp:
            if resp.status_code in (200, 400, 401, 422):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task(1)
    def delete_link(self):
        if not self.managed_codes:
            return
        sc = self.managed_codes.pop()
        with self.client.delete(
            f"/api/links/{sc}",
            headers=self._auth,
            catch_response=True,
            name="DELETE /api/links/{short_code}",
        ) as resp:
            if resp.status_code in (200, 400, 401):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")

    @task(2)
    def list_user_links(self):
        with self.client.get(
            "/api/links/user/links",
            headers=self._auth,
            catch_response=True,
            name="GET /api/links/user/links",
        ) as resp:
            if resp.status_code in (200, 401):
                resp.success()
            else:
                resp.failure(f"Unexpected {resp.status_code}")