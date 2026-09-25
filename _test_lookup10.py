import asyncio
import time

from app.providers.topup.provider import RealTopUpProvider

UID = "8848921527"


async def main() -> None:
    provider = RealTopUpProvider()
    ok = 0
    for i in range(1, 11):
        t0 = time.monotonic()
        try:
            info = await provider.lookup_account(UID, game="ff")
            dt = time.monotonic() - t0
            nick = info.nickname or "<БЕ НОМ>"
            if info.nickname:
                ok += 1
            print(
                f"{i:2d}/10 found={info.found} nick={nick!r} "
                f"game={info.game!r} msg={info.message!r} {dt:.1f}s",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"{i:2d}/10 EXC {type(exc).__name__}: {exc}", flush=True)
    print(f"=== Ном дуруст баромад: {ok}/10 ===", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
