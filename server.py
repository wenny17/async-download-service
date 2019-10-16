import asyncio
import os
import logging
import argparse
from functools import partial

from aiohttp import web
import aiofiles


async def archivate(timeout, directory,  request):
    archive_name = request.match_info["archive_hash"]

    if not os.path.exists(f"{directory}/{archive_name}"):
        raise web.HTTPNotFound(text="<h1>Archive doesn't exist</h1>")


    response = web.StreamResponse()
    response.headers["Content-Disposition"] = f'attachment; filename="archive-{archive_name}.zip"'
    await response.prepare(request)

    zip_proccess = await asyncio.create_subprocess_exec(
        "zip", "-jr", "-", f"{directory}/{archive_name}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    try:
        while True:
            if timeout:
                await asyncio.sleep(timeout)
            archive_chunk = await zip_proccess.stdout.readline()
            if not archive_chunk:
                break
            logging.info("Sending archive chunk ...")
            await response.write(archive_chunk)

    except asyncio.CancelledError:
        logging.info("Download was interrupted")
        zip_proccess.kill()
        raise
    finally:
        response.force_close()

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logging",action="store_true", help="activate logging")
    parser.add_argument("-path", help="path to photo directory", default="test_photos")
    parser.add_argument("-timeout", action="store_true")
    return parser.parse_args()


def main():
    args = get_arguments()

    if args.logging:
        logging.basicConfig(level=logging.DEBUG)


    archivate_wrapper = partial(archivate, args.timeout, args.path)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate_wrapper),
    ])
    web.run_app(app)


if __name__ == '__main__':
    main()
