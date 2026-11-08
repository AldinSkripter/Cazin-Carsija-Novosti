import asyncio

from services import init_storage
from fb_import import run_import, import_author


async def main():
    init_storage()
    author = await import_author()
    if not author:
        print("Nema Super Admina – uvoz preskočen")
        return
    res = await run_import(author, 8, remove_samples=True, auto=True, max_age_hours=24)
    print(f"Obrisano probnih: {res['removed_samples']}, objavljeno sa Facebooka: {len(res['imported'])}")
    for t in res["imported"]:
        print(" -", t)


if __name__ == "__main__":
    asyncio.run(main())
