"""

"""
import asyncio
import signal
from ._utils import *
from io import BytesIO
from tendermint.abci.types_pb2 import (
    Request,
    Response,
    ResponseException,
    ResponseFlush,
)
from ._application import BaseApplication

DefaultABCIPort = 26658
MaxReadInBytes = 64 * 1024

log = get_logger()


class ProtocolHandler:
    """
    Internal handler called by the server to process requests from
    Tendermint.  The handler delegates calls to your application
    """

    def __init__(self, app):
        self.app = app

    def process(self, req_type, req):
        handler = getattr(self, req_type, self.no_match)
        return handler(req)

    def flush(self, req):
        response = Response(flush=ResponseFlush())
        return write_message(response)

    def info(self, req):
        result = self.app.info(req.info)
        response = Response(info=result)
        return write_message(response)

    def check_tx(self, req):
        result = self.app.check_tx(req.check_tx.tx)
        response = Response(check_tx=result)
        return write_message(response)

    def deliver_tx(self, req):
        result = self.app.deliver_tx(req.deliver_tx.tx)
        response = Response(deliver_tx=result)
        return write_message(response)

    def query(self, req):
        result = self.app.query(req.query)
        response = Response(query=result)
        return write_message(response)

    def commit(self, req):
        result = self.app.commit()
        response = Response(commit=result)
        return write_message(response)

    def begin_block(self, req):
        result = self.app.begin_block(req.begin_block)
        response = Response(begin_block=result)
        return write_message(response)

    def end_block(self, req):
        result = self.app.end_block(req.end_block)
        response = Response(end_block=result)
        return write_message(response)

    def init_chain(self, req):
        result = self.app.init_chain(req.init_chain)
        response = Response(init_chain=result)
        return write_message(response)

    def list_snapshots(self, req):
        result = self.app.list_snapshots(req.list_snapshots)
        response = Response(list_snapshots=result)
        return write_message(response)

    def offer_snapshot(self, req):
        result = self.app.offer_snapshot(req.offer_snapshot)
        response = Response(offer_snapshot=result)
        return write_message(response)

    def load_snapshot_chunk(self, req):
        result = self.app.load_snapshot_chunk(req.load_snapshot_chunk)
        response = Response(load_snapshot_chunk=result)
        return write_message(response)

    def apply_snapshot_chunk(self, req):
        result = self.app.apply_snapshot_chunk(req.apply_snapshot_chunk)
        response = Response(apply_snapshot_chunk=result)
        return write_message(response)

    def no_match(self, req):
        response = Response(exception=ResponseException(error="ABCI request not found"))
        return write_message(response)


class ABCIServer:
    port: int
    protocol: ProtocolHandler

    def __init__(self, app: BaseApplication, port=DefaultABCIPort) -> None:
        if not app or not isinstance(app, BaseApplication):
            log.error(
                " Application missing or not an instance of ABCI Base Application"
            )
            raise TypeError(
                "Application missing or not an instance of ABCI Base Application"
            )
        self.port = port
        self.protocol = ProtocolHandler(app)

    def run(self) -> None:
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(stop()))
        try:
            log.info(" ~ running app - press CTRL-C to stop ~")
            loop.run_until_complete(self.start())
        except:
            log.warn(" ... shutting down")
        finally:
            loop.stop()

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self._handler,
            host="0.0.0.0",
            port=self.port,
        )
        await self.server.serve_forever()

    async def _handler(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        ip, socket, *_ = writer.get_extra_info("peername")
        log.info(f" ... connection @ {ip}:{socket}")

        data = BytesIO()
        last_pos = 0

        while True:
            if last_pos == data.tell():
                data = BytesIO()
                last_pos = 0

            bits = await reader.read(MaxReadInBytes)
            print(bits)
            if len(bits) == 0:
                log.error(" ... tendermint closed connection")
                break

            data.write(bits)
            data.seek(last_pos)

            for message in read_messages(data, Request):
                req_type = message.WhichOneof("value")
                response = self.protocol.process(req_type, message)
                writer.write(response)
                last_pos = data.tell()

        await stop()


async def stop() -> None:
    log.warn(" ... received exit signal")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)