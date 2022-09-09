#!/usr/bin/env python
import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)
define("secret", help="upstream secret token", type=str)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/upload/(.*)", StreamHandler),
            (r"/live.ts", SocketHandler),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
        )
        super(Application, self).__init__(handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('view-stream.html')


@tornado.web.stream_request_body
class StreamHandler(tornado.web.RequestHandler):
    def data_received(self, data):
        if options.secret and self.request.path != '/upload/' + options.secret:
            logging.info(
                'Failed Stream Connection: %s - wrong secret.',
                self.request.remote_ip
            )
            self.write_error(403)
            return
        SocketHandler.broadcast(data)


class SocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()

    def check_origin(self, origin):
        return True

    def open(self):
        SocketHandler.waiters.add(self)
        logging.info(
            'New WebSocket Connection: %d total',
            len(SocketHandler.waiters)
        )

    def select_subprotocol(self, subprotocol):
        if len(subprotocol):
            return subprotocol[0]
        return super().select_subprotocol(subprotocol)

    def on_message(self, message):
        pass

    def on_close(self):
        SocketHandler.waiters.remove(self)
        logging.info(
            'Disconnected WebSocket (%d total)',
            len(SocketHandler.waiters)
        )

    @classmethod
    def broadcast(cls, data):
        for waiter in cls.waiters:
            try:
                waiter.write_message(data, binary=True)
            except tornado.websocket.WebSocketClosedError:
                logging.error("Error sending message", exc_info=True)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
