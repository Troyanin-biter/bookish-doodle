import asyncio
import atexit
import ctypes
import logging
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from db.database import db
from handlers import help as help_handler
from handlers import journal, motivation, pomodoro, profile, start, stats, tasks
from middlewares.tracking import ActivityMiddleware
from services.scheduler import setup_scheduler

LOCK_PATH = Path(__file__).resolve().parent / "data" / "bot.lock"
_lock_fd: int | None = None


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False

    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        process_query_limited_information, False, pid
    )
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def _acquire_single_instance_lock():
    global _lock_fd
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _try_open():
        return os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    try:
        _lock_fd = _try_open()
    except FileExistsError:
        existing_pid = 0
        try:
            existing_pid = int(LOCK_PATH.read_text(encoding="utf-8").strip())
        except Exception:
            pass

        if existing_pid and not _pid_exists(existing_pid):
            LOCK_PATH.unlink(missing_ok=True)
            _lock_fd = _try_open()
        else:
            pid_text = str(existing_pid) if existing_pid else "unknown"
            raise RuntimeError(
                f"Another bot instance is already running (pid={pid_text})."
            )

    os.write(_lock_fd, str(os.getpid()).encode("utf-8"))
    os.fsync(_lock_fd)


def _release_single_instance_lock():
    global _lock_fd
    try:
        if _lock_fd is not None:
            os.close(_lock_fd)
            _lock_fd = None
        LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    log = logging.getLogger("bot")

    await db.init()
    log.info("Database ready: %s", db.db_path)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.middleware(ActivityMiddleware())
    dp.callback_query.middleware(ActivityMiddleware())

    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(stats.router)
    dp.include_router(profile.router)
    dp.include_router(pomodoro.router)
    dp.include_router(motivation.router)
    dp.include_router(journal.router)
    dp.include_router(help_handler.router)

    setup_scheduler(bot)

    log.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        _acquire_single_instance_lock()
    except RuntimeError as e:
        print(str(e))
        sys.exit(0)

    atexit.register(_release_single_instance_lock)
    try:
        asyncio.run(main())
    finally:
        _release_single_instance_lock()

