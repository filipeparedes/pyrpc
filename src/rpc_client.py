"""
cliente_rpc.py

Client-side implementation of the JSON-RPC 2.0 Protocol.
Supports dynamic function invocations and interactive arguments.

Author: Filipe Paredes
Student Number: 202300257

"""

import socket
import json
import ast
import uuid


class RPCClient:
    """
    A JSON-RPC 2.0 compliant client that dynamically invokes public functions
    available.
    """

    def __init__(self, host='localhost', port=8000):
        """Initializes the RPC client and connects to the specified server."""
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def __getattr__(self, attr):
        """Dynamically handles method calls to allow direct remote function calls."""
        def method(*args, **kwargs):
            if args and kwargs:
                return self.invoke(attr, {"__args__": args, **kwargs})
            if kwargs:
                return self.invoke(attr, kwargs)
            return self.invoke(attr, args)
        return method

    def invoke(self, function, arguments):
        """ ends a JSON-RPC request to invoke a remote function with the given arguments"""
        if not self.sock:
            raise ConnectionError("Socket não está conectado.")
        request = {
            "jsonrpc": "2.0",
            "method": function,
            "params": arguments,
            "id": str(uuid.uuid4())
        }
        self.sock.sendall((json.dumps(request) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            data += self.sock.recv(4096)
        response = json.loads(data.decode().strip())

        if isinstance(response, dict):
            if "result" in response:
                return response["result"]
            if "error" in response:
                raise AttributeError(f"Remote error: {response['error']}")
        raise AttributeError("Invalid response from the server.")

    def dynamic_menu(self):
        """
        Launches an interactive menu that lists available server functions,
        prompts for parameters and shows the result of invoking them.
        """
        try:
            funcs = self.invoke("list_functions", {})
        except Exception as e:
            print(f"An error occurred trying to get the list of functions: {format(e)}")
            return

        if not funcs:
            print("No functions found.")
            return

        while True:
            print("\n=== Functions List ===")
            for i, func in enumerate(funcs):
                name = func["name"]
                params = func["params"]
                desc = func["description"]
                params_info = ", ".join(params)
                print(f"{i+1}. {name}: {params_info} - {desc}")
            print("0. Shutdown")

            choice = input("Choose a function: ").strip()
            if choice == "0":
                print("Shutting down...")
                break

            # Testa se a opção escolhida é válida
            if not choice.isdigit() or not 1 <= int(choice) <= len(funcs):
                print("Invalid choice.")
                continue

            func = funcs[int(choice) - 1]
            name = func["name"]
            params = func["params"]

            params_pos = []
            params_named = {}

            for param in params:
                if "=" in param:
                    param_name, default = param.split("=", 1)
                    value = input(f"{param_name} (Optional, Default: {default}): ").strip()
                    if value:
                        try:
                            params_named[param_name] = ast.literal_eval(value)
                        except Exception:
                            params_named[param_name] = value
                else:
                    value = input(f"{param} (Mandatory): ").strip()
                    try:
                        params_pos.append(ast.literal_eval(value))
                    except Exception:
                        params_pos.append(value)

            if params_named:
                params_named['__args__'] = params_pos
                params_final = params_named
            else:
                params_final = params_pos

            try:
                result = self.invoke(name, params_final)
                print(f"Result: {result}")
            except Exception as e:
                print(f"An error occurred trying to get the result: {format(e)}")

if __name__ == "__main__":
    client = RPCClient()
    client.dynamic_menu()
