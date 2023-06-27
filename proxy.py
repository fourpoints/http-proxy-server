import http.server
import importlib
import requests
from io import BytesIO
from pathlib import Path

# Most of this is copied from http.server:
# https://github.com/python/cpython/blob/3.9/Lib/http/server.py


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, proxy, **kwargs):
        self.proxy = proxy
        super().__init__(*args, **kwargs)

    @property
    def _proxy_url(self):
        # This will only be valid if self.path contains proxy pattern
        parts = self.path.split("/", maxsplit=2)
        if len(parts) >= 1 and parts[1] in self.proxy:
            return "/".join((self.proxy[parts[1]], *parts[2:]))
        else:
            return None

    def do_GET(self):
        if self._proxy_url is not None:
            # proxy
            url = self._proxy_url
            resp = requests.get(url)

            self.log_message('PROXY "%s" %s %s',
                f"GET {url} HTTP/{resp.raw.version / 10}",
                str(resp.status_code),
                str(resp.headers.get("content-length", "-")),
            )

            # send_head
            self.send_response(resp.status_code)
            for key, value in resp.headers.items():
                self.send_header(key, value)
            self.end_headers()

            # copyfile
            if resp.content:
                f = BytesIO(resp.content)
                self.copyfile(f, self.wfile)
        else:
            super().do_GET()


def _get_best_family(*address):
    import socket
    infos = socket.getaddrinfo(
        *address,
        type=socket.SOCK_STREAM,
        flags=socket.AI_PASSIVE,
    )
    family, _type, _proto, _canonname, sockaddr = next(iter(infos))
    return family, sockaddr


def serve(HandlerClass=http.server.BaseHTTPRequestHandler,
         ServerClass=http.server.ThreadingHTTPServer,
         protocol="HTTP/1.0", port=8000, bind=None, open=False):
    """Test the HTTP request handler class.
    This runs an HTTP server on port 8000 (or the port argument).
    """
    ServerClass.address_family, addr = _get_best_family(bind, port)

    HandlerClass.protocol_version = protocol
    with ServerClass(addr, HandlerClass) as httpd:
        host, port = httpd.socket.getsockname()[:2]
        url_host = f'[{host}]' if ':' in host else host
        url = f"http://{url_host}:{port}/".replace("[::]", "localhost")
        print(
            f"Serving HTTP on {host} port {port} "
            f"({url}) ..."
        )
        if open:
            import webbrowser
            webbrowser.open_new_tab(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            import sys; sys.exit(0)


if __name__ == "__main__":
    import argparse
    import os
    import socket
    import contextlib
    from functools import partial

    parser = argparse.ArgumentParser()
    parser.add_argument('--cgi', action='store_true',
                       help='Run as CGI Server')
    parser.add_argument('--bind', '-b', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Specify alternative directory '
                        '[default:current directory]')
    parser.add_argument('--proxy', '-p', action="append", nargs=2,
                        metavar=("proxy-url", "proxy-name"),
                        help='Specify proxy, Requests to /proxy_name will be redirected to proxy, e.g. requests to /PROXY/data.csv will be directed to https://proxy.com/data.csv, if proxy is set to "https://proxy.com" [default: "PROXY"]')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    parser.add_argument('--open', action='store_true',
                        default=False,
                        help='Open new tab')

    args = parser.parse_args()


    if args.cgi:
        handler_class = http.server.CGIHTTPRequestHandler
    else:
        handler_class = partial(ProxyHandler,
                                directory=args.directory,
                                proxy=dict(args.proxy),
                                )

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(http.server.ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    serve(
        HandlerClass=handler_class,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind,
        open=args.open,
    )


