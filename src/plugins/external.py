import psutil
import subprocess
import nonebot

from psutil import Popen
from nonebot import export


class ExternalHolder:
    cq_http_path: str = None
    cq_http_cmd: Popen = None
    server_path: str = None
    server_cmd: Popen = None

    def __init__(self):
        self.cq_http_path = nonebot.get_driver().config.cq_http_path
        self.server_path = nonebot.get_driver().config.server_path

    async def start_cq_http(self):
        self.cq_http_cmd = Popen(
            'cmd.exe',
            cwd=self.cq_http_path,
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        self.cq_http_cmd.stdin.write(bytes('go-cqhttp_windows_amd64.exe\n', 'utf-8'))
        self.cq_http_cmd.stdin.flush()

    async def start_server(self):
        self.server_cmd = Popen(
            'cmd.exe',
            cwd=self.server_path,
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        self.server_cmd.stdin.write(bytes('npm run start\n', 'utf-8'))
        self.server_cmd.stdin.flush()

    async def run(self):
        await self.start_cq_http()
        await self.start_server()

    async def reboot_cq_http(self):
        self.cq_http_cmd.terminate()
        await self.start_cq_http()

    async def reboot_server(self):
        self.server_cmd.terminate()
        await self.start_server()

    async def shutdown(self):
        self.cq_http_cmd.terminate()
        self.server_cmd.terminate()


external_dict = export()
external_dict.external_holder = ExternalHolder()
