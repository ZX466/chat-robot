import argparse
import asyncio
import signal
import sys

from loguru import logger


def parse_args():
    parser = argparse.ArgumentParser(description="Zerolan Live Robot")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config.yaml (default: resources/config.yaml)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    # Set custom config path before importing bot (bot.py calls get_config() at import time)
    if args.config:
        from pathlib import Path
        from manager.config_manager import set_default_config_path
        set_default_config_path(Path(args.config))

    from bot import ZerolanLiveRobot
    from manager.config_manager import ConfigGeneratedError

    loop = asyncio.get_running_loop()

    bot = None
    shutdown_event = asyncio.Event()

    def _request_shutdown(signame: str):
        logger.info(f"Received {signame}, shutting down gracefully...")
        shutdown_event.set()

    # Register signal handlers where supported (not on Windows ProactorEventLoop)
    if sys.platform != "win32" or not isinstance(loop, asyncio.ProactorEventLoop):
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _request_shutdown, sig.name)

    try:
        bot = ZerolanLiveRobot()

        async def _run():
            run_task = asyncio.create_task(bot.start())
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            done, pending = await asyncio.wait(
                [run_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

        await _run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except ConfigGeneratedError:
        pass  # Message already printed by config_manager
    except Exception as e:
        logger.exception(e)
        logger.error("❌️ Zerolan Live Robot exited abnormally!")
    finally:
        if bot is not None:
            await bot.stop()


if __name__ == '__main__':
    asyncio.run(main())
