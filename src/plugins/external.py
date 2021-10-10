import subprocess
import nonebot

from psutil import Popen
from nonebot.plugin import export


async def _kill_process(process: Popen):
    subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])


class ExternalHolder:
    cq_http_path: str = None
    cq_http_cmd: Popen = None
    server_path: str = None
    server_cmd: Popen = None

    def __init__(self):
        config = nonebot.get_driver().config
        self.cq_http_path = config.cq_http_path
        self.server_path = config.server_path

    async def start_cq_http(self):
        self.cq_http_cmd = Popen(
            'cmd.exe',
            cwd=self.cq_http_path,
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        self.cq_http_cmd.stdin.write(
            bytes('go-cqhttp_windows_amd64.exe\n', 'utf-8'))
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

    async def startup(self):
        await self.start_cq_http()
        await self.start_server()

    async def reboot_cq_http(self):
        await _kill_process(self.cq_http_cmd)
        await self.start_cq_http()

    async def reboot_server(self):
        await _kill_process(self.server_cmd)
        await self.start_server()

    async def shutdown(self):
        await _kill_process(self.cq_http_cmd)
        await _kill_process(self.server_cmd)


external_dict = export()
external_dict.external_holder = ExternalHolder()
