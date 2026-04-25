# pyrpc

A JSON-RPC 2.0 server and client implementation in Python using raw sockets and threading — no frameworks, no external dependencies.

  > Originally developed as a university project for the *Parallel and Distributed Computing* course at [Instituto Politécnico de Setúbal](https://ips.pt/), later refactored and extended for public release.

---

## Features

- **JSON-RPC 2.0 compliant** — supports single and batch requests, proper error codes
- **Raw TCP sockets** — no HTTP, no frameworks, built from scratch
- **Multithreaded server** — handles multiple concurrent clients using Python's `threading` module
- **Dynamic function registration** — functions are automatically discovered and registered from modules
- **Interactive client menu** — lists available remote functions and prompts for arguments at runtime
- **RSA encryption module** — key generation, encryption, decryption and parallel key cracking
- **Prime number utilities** — sequential and parallel prime search, twin primes, Mersenne primes, and more
- **Graceful shutdown** — server waits for all active clients to disconnect before shutting down

---

## Requirements

- Python 3.10+
- No external dependencies.

---

## Running

### 1. Clone the repository

```bash
git clone https://github.com/filipeparedes/pyrpc.git
cd pyrpc
```

### 2. Start the server

```bash
python3 src/rpc_server.py
```

### 3. Start the client (in a separate terminal)

```bash
python3 src/rpc_client.py
```

The client will display an interactive menu listing all available remote functions.

---

## Usage

### Interactive menu

```
=== Functions List ===
1. is_prime: n - Checks if n is prime using 6k ± 1 optimization.
2. next_prime: n - Finds the next prime number larger than n.
3. generate_keys: bits - Randomly generates a pair of RSA keys.
4. encrypt: message, pub_key - Encrypts a message with a public key.
5. crack_key: n, e, timeout=15 - Tries to crack a private key from a public key.
...
0. Shutdown
```

### Programmatic usage

```python
from src.rpc_client import RPCClient

with RPCClient() as client:
    result = client.next_prime(97)
    print(result)  # 101

    pub_key, priv_key = client.generate_keys(512)
    ciphertext = client.encrypt(42, pub_key)
    message = client.decrypt(ciphertext, priv_key)
    print(message)  # 42
```

### Batch requests

The server supports JSON-RPC 2.0 batch requests — multiple calls in a single TCP message:

```python
import socket, json

batch = [
    {"jsonrpc": "2.0", "method": "next_prime", "params": [10], "id": "1"},
    {"jsonrpc": "2.0", "method": "is_prime", "params": [17], "id": "2"},
]

sock = socket.socket()
sock.connect(("localhost", 8000))
sock.sendall((json.dumps(batch) + "\n").encode())
response = sock.recv(4096)
print(json.loads(response))
```

---

## Available Functions

### calculations.py

| Function | Description |
|---|---|
| `is_prime(n)` | Checks if `n` is prime using 6k ± 1 optimization |
| `next_prime(n)` | Finds the next prime greater than `n` |
| `previous_prime(n)` | Finds the previous prime smaller than `n` |
| `prime_factors(n)` | Returns the prime factorization of `n` |
| `find_next_twin_primes(n)` | Finds the next twin prime pair after `n` |
| `is_mersenne_prime(n)` | Checks if `n` is a Mersenne prime |
| `find_max_prime_sequential(timeout)` | Finds the largest prime within a time limit (single process) |
| `find_max_prime_parallel(timeout)` | Finds the largest prime within a time limit (multiprocessing) |

### encryption.py

| Function | Description |
|---|---|
| `generate_keys(bits)` | Generates an RSA key pair of the given bit size |
| `encrypt(message, pub_key)` | Encrypts an integer message with a public key |
| `decrypt(ciphertext, priv_key)` | Decrypts a ciphertext with a private key |
| `crack_key(n, e, timeout)` | Attempts to factor `n` and recover the private key using parallel processes |

---

## JSON-RPC 2.0 Protocol

The server communicates over TCP using newline-delimited JSON messages (`\n` as delimiter).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "next_prime",
  "params": [97],
  "id": "abc-123"
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": 101,
  "id": "abc-123"
}
```

**Error response:**
```json
{
  "jsonrpc": "2.0",
  "error": { "code": -32601, "message": "Method not found" },
  "id": "abc-123"
}
```

---

## Running Tests

```bash
python3 -m pytest tests/
```

---

## Project Structure

```
pyrpc/
├── README.md
├── src/
│   ├── rpc_server.py       # JSON-RPC 2.0 server
│   ├── rpc_client.py       # JSON-RPC 2.0 client with interactive menu
│   └── utils/
│       ├── calculations.py # Prime number utilities (sequential & parallel)
│       └── encryption.py   # RSA key generation, encryption and key cracking
├── tests/
│   └── tests.py            # pytest test suite
└── docs/
    ├── technical_manual.md
    └── report.pdf
```

---

## Documentation

For detailed technical information about the code, check the [Technical Manual](docs/technical_manual.md).

You can also read the original university [Report](docs/report.pdf), but it is in Portuguese.

---

## Author

**Filipe Paredes** — [filipeparedes3@gmail.com](mailto:filipeparedes3@gmail.com)