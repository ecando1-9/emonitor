import os
import pyzipper # <-- Using pyzipper
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from logger_setup import log

BACKEND = default_backend()
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE_BITS = 256
KEY_SIZE_BYTES = KEY_SIZE_BITS // 8
PBKDF2_ITERATIONS = 100000

class Encryptor:
    
    def create_zip_file(self, file_path, password):
        """
        Creates a password-protected ZIP file using pyzipper.
        """
        if not password:
            log.error("Error: Password for ZIP file is empty.")
            return None
            
        zip_path = f"{file_path}.zip"
        file_name_in_zip = os.path.basename(file_path)
        
        try:
            with pyzipper.AESZipFile(zip_path, 'w', 
                                     compression=pyzipper.ZIP_LZMA, 
                                     encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(password.encode('utf-8'))
                zf.write(file_path, arcname=file_name_in_zip)
                
            log.info(f"Created password-protected zip: {zip_path}")
            return zip_path
        except Exception as e:
            log.error(f"Error creating zip file: {e}")
            return None

    def _get_derived_key(self, password, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE_BYTES,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=BACKEND
        )
        return kdf.derive(password.encode('utf-8'))

    def encrypt_file(self, file_path, password):
        """
        Encrypts a file using AES-GCM (High Security).
        """
        if not password:
            raise ValueError("Encryption password cannot be empty")
            
        try:
            with open(file_path, 'rb') as f:
                plaintext = f.read()

            salt = os.urandom(SALT_SIZE)
            key = self._get_derived_key(password, salt)
            aesgcm = AESGCM(key)
            nonce = os.urandom(NONCE_SIZE)
            ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
            encrypted_file_path = f"{file_path}.enc"
            with open(encrypted_file_path, 'wb') as f:
                f.write(salt)
                f.write(nonce)
                f.write(ciphertext_with_tag)
            
            return encrypted_file_path
        except Exception as e:
            log.error(f"Error encrypting file {file_path}: {e}")
            return None

    def decrypt_data(self, encrypted_file_path, password):
        if not password:
            log.error("Decryption password cannot be empty")
            return None
        try:
            with open(encrypted_file_path, 'rb') as f:
                salt = f.read(SALT_SIZE)
                nonce = f.read(NONCE_SIZE)
                ciphertext_with_tag = f.read()

            key = self._get_derived_key(password, salt)
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
            
            return plaintext
        except Exception as e:
            log.error(f"Error decrypting data: {e}")
            return None

encryptor = Encryptor()