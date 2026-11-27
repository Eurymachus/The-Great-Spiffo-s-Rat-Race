"""Uvicorn with a private cooperative host-stop request."""
from django.core.management.base import BaseCommand
import uvicorn

from operations.process_control import stop_requested


class HostedServer(uvicorn.Server):
    async def on_tick(self, counter):
        if stop_requested():
            self.should_exit = True
        return await super().on_tick(counter)


class Command(BaseCommand):
    help = "Run the loopback hosted web service with cooperative shutdown."

    def add_arguments(self, parser):
        parser.add_argument("--port", type=int, default=8000)

    def handle(self, *args, **options):
        server = HostedServer(uvicorn.Config(
            "config.asgi:application", host="127.0.0.1", port=options["port"],
            proxy_headers=True, forwarded_allow_ips="127.0.0.1",
        ))
        server.run()
