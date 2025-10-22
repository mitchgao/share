import hashlib
import os
import base64
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Load environment variables from .env file
load_dotenv()
# Generate a random 32-byte key for AES-256
key = hashlib.sha256(os.getenv("ENCRYPTED_KEY").encode("utf-8")).digest()

# Generate a random 16-byte initialization vector (IV)
iv = hashlib.md5(os.getenv("ENCRYPTED_IV").encode("utf-8")).digest()


def encrypt_order_id(order_id):
    if order_id is None:
        return

    # Convert the order ID to bytes
    order_id_bytes = str(order_id).encode("utf-8")

    # Pad the order ID to be a multiple of the block size
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(order_id_bytes) + padder.finalize()

    # Create a cipher object and encrypt the data
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Encode the encrypted data as a Base64 string
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode("utf-8")
    return encrypted_data_base64


def decrypt_order_id(encrypted_data_base64):
    if encrypted_data_base64 is None:
        return
    # Decode the Base64 string to get the encrypted bytes
    encrypted_data = base64.b64decode(encrypted_data_base64)
    # Create a cipher object and decrypt the data
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Unpad the decrypted data
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    order_id_bytes = unpadder.update(padded_data) + unpadder.finalize()

    # Convert bytes back to string
    order_id = order_id_bytes.decode("utf-8")
    return order_id


if __name__ == "__main__":

    order_id = "12345"
    encrypted_order_id = encrypt_order_id(order_id)
    print(f"Encrypted Order ID: {encrypted_order_id}")

    decrypted_order_id = decrypt_order_id(encrypted_order_id)
    print(f"Decrypted Order ID: {decrypted_order_id}")
