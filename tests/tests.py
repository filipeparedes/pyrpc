import time
import random
import threading
import pytest  
from multiprocessing import cpu_count

from src.rpc_client import RPCClient
from src.utils.calculations import (
    is_prime, find_max_prime_sequential, find_max_prime_parallel,
    find_next_twin_primes, is_mersenne_prime, prime_factors,
    next_prime, previous_prime
)
from src.utils.encryption import (
    generate_keys, encrypt, decrypt, crack_key
)

@pytest.fixture
def client_id():
    """Provides a default ID when running via pytest"""
    return "pytest_runner"

def test_rpc_client(client_id):
    client = RPCClient()
    print(f"[Client {client_id}] Running tests")

    assert client.is_prime(17) is True
    assert client.is_prime(18) is False
    assert client.next_prime(17) == 19
    assert client.previous_prime(17) == 13
    assert list(client.find_next_twin_primes(10)) == [11, 13] 
    assert client.is_mersenne_prime(31) is True
    assert client.prime_factors(60) == [2, 2, 3, 5]

    pub, priv = client.generate_keys(16)
    message = 42
    ciphertext = client.encrypt(message, pub)
    decrypted = client.decrypt(ciphertext, priv)
    assert decrypted == message

    cracked = client.crack_key(pub[0], pub[1], timeout=10)
    assert isinstance(cracked, (list, tuple)) and len(cracked) == 2

    print(f"[Client {client_id}] Tests passed")

def test_rpc():
    # Teste de um cliente
    print("\n[Main] Starting single-client RPC tests")
    test_rpc_client("main")

    # Teste com vários clientes
    print("\n[Main] Starting multi-client RPC tests")
    threads = []
    for i in range(5):  # 5 clientes em concorrencia
        t = threading.Thread(target=test_rpc_client, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("\n[Main] All RPC tests passed across multiple clients.")

def test_is_prime():
    assert is_prime(2)
    assert is_prime(3)
    assert is_prime(17)
    assert not is_prime(1)
    assert not is_prime(15)
    assert not is_prime(100)
    print("is_prime tests passed.")


def test_next_previous_prime():
    assert next_prime(17) == 19
    assert previous_prime(17) == 13
    assert previous_prime(2) is None
    print("next_prime / previous_prime tests passed.")


def test_find_next_twin_primes():
    assert find_next_twin_primes(10) == (11, 13)
    assert find_next_twin_primes(20) == (29, 31)
    print("find_next_twin_primes tests passed.")


def test_is_mersenne_prime():
    assert is_mersenne_prime(3)     # 2^2 - 1
    assert is_mersenne_prime(31)    # 2^5 - 1
    assert not is_mersenne_prime(15)  # 2^4 - 1, not prime
    print("is_mersenne_prime tests passed.")


def test_prime_factors():
    assert prime_factors(60) == [2, 2, 3, 5]
    assert prime_factors(13) == [13]
    assert prime_factors(1) == []
    print("prime_factors tests passed.")


def test_find_max_prime_timed():
    timeout = random.randint(1, 5)

    print(f"\nTesting find_max_prime with timeout={timeout}s")

    max_seq = find_max_prime_sequential(timeout)
    print(f"Sequential result: {max_seq}")

    max_par = find_max_prime_parallel(timeout)
    print(f"Parallel result:   {max_par}")

    assert is_prime(max_seq)
    assert is_prime(max_par)

    print("find_max_prime (timed) tests passed. \n")


def test_generate_keys_and_encrypt_decrypt():
    pub, priv = generate_keys(16)

    message = 42
    assert pub[0] > message

    ciphertext = encrypt(message, pub)
    decrypted = decrypt(ciphertext, priv)

    assert decrypted == message
    print("generate_keys, encrypt and decrypt tests passed.")


def test_encrypt_invalid_message():
    pub, _ = generate_keys(16)
    try:
        encrypt(0, pub)
        print("encrypt(0, pub) should have raised ValueError")
    except ValueError:
        print("ncrypt(0, pub) correctly raised ValueError")

    try:
        encrypt(pub[0], pub)
        print("encrypt(n, pub) with n == modulus should have raised ValueError")
    except ValueError:
        print("encrypt(n, pub) == n correctly raised ValueError")


def test_crack_key():
    pub, priv = generate_keys(32)
    n, e = pub

    message = 99
    ciphertext = encrypt(message, pub)

    start_time =  time.time()

    cracked_n, cracked_d = crack_key(n, e, timeout=10)

    end_time = time.time()

    decrypted = decrypt(ciphertext, (n, cracked_d))

    assert decrypted == message
    print(f"crack_key successfully recovered the private key in: {(end_time - start_time):.4f}s")
