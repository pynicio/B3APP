from http.server import BaseHTTPRequestHandler
from dash import Dash, html

app = Dash(__name__)
app.layout = html.Div("Hello, Vercel!")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(app.index().encode())

def handler(request):
    return Handler()
