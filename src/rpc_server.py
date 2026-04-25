"""
servidor_rpc.py

Server implementation of the JSON-RPC 2.0 Protocol.
Supports function registration, batch requests and multiple concurrent clients
using sockets and threading.

Author: Filipe Paredes
Student Number: 202300257

"""
import socket
import json
import threading
import time
import inspect
import logging

try:
    from utils import calculations, encryption
except ImportError:
    from src.utils import calculations, encryption

class RPCServer:
    """
    A JSON-RPC 2.0 compliant server that handles client requests
    and executes registered functions concurrently.
    """

    logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s"
            )
    logger = logging.getLogger(__name__)

    def __init__(self, host='localhost', port=8000):
        """Initializes the RPC Server"""
        self.host = host
        self.port = port
        self.funcs = {}
        self.running = True
        self.server_socket = None
        self.active_clients = 0
        self.lock = threading.Lock()
        self.shutdown_requested = False
        self.register_functions()

    def register_functions(self):
        """Automatically register all public functions from calculo.py and criptografia.py"""
        for module in (calculations, encryption):
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith('_'):
                    self.register(name, func)

    def register(self, name, func):
        """Register a single function with a given name"""
        self.funcs[name] = func
        RPCServer.logger.info(f"[SERVER] Registered function: {name}")

    def list_functions(self):
        """Returns a detailed list of the registered functions"""
        functions = []
        for name, func in self.funcs.items():
            sig = inspect.signature(func)
            params = []
            for p in sig.parameters.values():
                if p.default != inspect.Parameter.empty:
                    # !r -> se p.default for string junta o delimitador,  '<p.default>'
                    params.append(f"{p.name}={p.default!r}")
                else:
                    params.append(p.name)
            functions.append({
                "name": name,
                "params": params,
                "description": inspect.getdoc(func) or ""
            })
        return functions

    def make_response(self, result=None, error=None, id=None):
        """Creates a JSON-RPC 2.0 response object."""
        response = {"jsonrpc": "2.0", "id": id}
        if error:
            response["error"] = error
        else:
            response["result"] = result
        return response

    def handle_single_request(self, req):
        """Handle a single JSON-RPC 2.0 request"""
        response = None

        if not isinstance(req, dict):
            response = self.make_response(error={"code": -32600, "message": "Invalid Request"}, id=None)

        else:
            jsonrpc = req.get("jsonrpc")
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id")

            if jsonrpc != "2.0" or not method:
                response = self.make_response(error={"code": -32600, "message": "Invalid Request"}, id=req_id)

            elif method == "list_functions":
                response = self.make_response(result=self.list_functions(), id=req_id)

            elif method == "shutdown":
                self.shutdown_requested = True
                response = self.make_response(result="Server will shut down after all clients disconnect.", id=req_id)

            else:
                func = self.funcs.get(method)
                if not func:
                    response = self.make_response(error={"code": -32601, "message": "Method not found"}, id=req_id)
                else:
                    try:
                        if isinstance(params, dict) and '__args__' in params:
                            params = params.copy()
                            real_args = params.pop('__args__')
                            result = func(*real_args, **params)
                        elif isinstance(params, dict):
                            result = func(**params)
                        elif isinstance(params, list):
                            result = func(*params)
                        else:
                            result = func(params)

                        response = self.make_response(result=result, id=req_id)
                    except Exception as e:
                        response = self.make_response(error={"code": -32603, "message": f"Internal error: {str(e)}"}, id=req_id)

        return response


    def handle_request(self, request_json):
        """Parses and handle a single or a batch of JSON-RPC 2.0 requests."""
        try:
            parsed = json.loads(request_json)

            # Batch request
            if isinstance(parsed, list):
                if not parsed:
                    return json.dumps([self.make_response(error={"code": -32600, "message": "Invalid Request"}, id=None)])
                responses = [self.handle_single_request(req) for req in parsed]
                return json.dumps(responses)

            # Single request
            return json.dumps(self.handle_single_request(parsed))

        except json.JSONDecodeError:
            return json.dumps(self.make_response(error={"code": -32700, "message": "Parse error"}, id=None))

    def client_thread(self, conn, addr):
        """Serve a single client connection."""
        with self.lock:
            self.active_clients += 1
        RPCServer.logger.info(f"[SERVER] New connection from {addr}")

        with conn:
            buffer = ""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode()
                """Read each message in buffer (messages are separated by "\n")""" 
                while "\n" in buffer:
                    message, buffer = buffer.split("\n", 1)
                    RPCServer.logger.debug(f"[SERVER] Received {message}")
                    response = self.handle_request(message)
                    RPCServer.logger.debug(f"[SERVER] Sent {response}")
                    conn.sendall((response + "\n").encode())

        with self.lock:
            self.active_clients -= 1

    def start(self):
        """Starts the server."""
        RPCServer.logger.info("[SERVER] Starting server...")
        print(f"[SERVER] Listening on {self.host}:{self.port}.")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            self.server_socket = s
            s.settimeout(1)

            while not self.shutdown_requested:
                try:
                    conn, addr = s.accept()
                    RPCServer.logger.info(f"[SERVER] Accepted connection from {addr}")
                    threading.Thread(target=self.client_thread, args=(conn, addr)).start()
                except socket.timeout:
                    continue

            RPCServer.logger.info("[SERVER] Waiting to conclude client connections...")
            while True:
                with self.lock:
                    if self.active_clients == 0:
                        break
                time.sleep(0.5)
            RPCServer.logger.info("[SERVER] Shutting down server.")


if __name__ == '__main__':
    server = RPCServer()
    server.start()
