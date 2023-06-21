# http-proxy-server
Extension of Python's http.server with proxy support

## Example use

Include proxy url's in your HTML file:
```html
<img href="PROXY_NAME/image-name.webp" />
```

Run with:
```
py proxy.py --proxy PROXY_NAME "https://example.com"
```

When fetching data from the server, this will replace `PROXY_NAME` with `https://example.com`, so the HTML reference becomes `https://example.com/image-name.webp`.

Multiple proxies are supported:

```Py
py proxy.py --proxy PROXY_1 "https://example1.com" --proxy PROXY_2 "https://example2.com"
```

## Warning

The warning from [http.server docs](https://docs.python.org/3/library/http.server.html) still applies:

> http.server is not recommended for production. It only implements basic security checks. 
