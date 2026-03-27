"""Cryptography utilities for sensitive data encryption"""
import os
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from typing import Optional

logger = logging.getLogger(__name__)

# 项目根目录和数据目录（与 config.py 保持一致）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class CryptoManager:
    """Manager for encrypting and decrypting sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None, key_file: Optional[str] = None):
        """
        Initialize crypto manager
        
        Args:
            encryption_key: Base64-encoded encryption key. If None, will be loaded or generated.
            key_file: Path to store the encryption key if it needs to be generated
        """
        self.key_file = Path(key_file) if key_file else DATA_DIR / ".encryption_key"

        if encryption_key:
            # Use provided key
            self._key = encryption_key.encode()
        else:
            # Load or generate key
            self._key = self._load_or_generate_key()
        
        try:
            self._fernet = Fernet(self._key)
        except Exception as e:
            logger.error(f"Failed to initialize Fernet cipher: {e}")
            raise
    
    def _load_or_generate_key(self) -> bytes:
        """Load encryption key from file or generate a new one"""
        # Try to load existing key
        if self.key_file.exists():
            try:
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                return key
            except Exception as e:
                logger.error(f"Failed to load encryption key from {self.key_file}: {e}")
        
        # Generate new key
        logger.warning("Generating new encryption key...")
        key = Fernet.generate_key()
        
        # Save key to file
        try:
            # Ensure parent directory exists
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            
            logger.warning("IMPORTANT: Backup the encryption key file! Data encrypted with this key cannot be recovered if the key is lost.")
        except Exception as e:
            logger.error(f"Failed to save encryption key to {self.key_file}: {e}")
            logger.warning("Key will only be available for this session")
        
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return plaintext
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt encrypted string
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ciphertext
        
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def mask_sensitive(self, value: Optional[str], show_length: int = 0) -> str:
        """
        Mask sensitive information for display
        
        Args:
            value: Sensitive string to mask
            show_length: Number of characters to show at the beginning (default: 0)
            
        Returns:
            Masked string like "abc***" or "***"
        """
        if not value:
            return ""
        
        if show_length > 0 and len(value) > show_length:
            return value[:show_length] + "***"
        else:
            return "***"


# Global crypto manager instance
_crypto_manager: Optional[CryptoManager] = None


def get_crypto_manager() -> CryptoManager:
    """Get the global crypto manager instance"""
    global _crypto_manager
    if _crypto_manager is None:
        raise RuntimeError("Crypto manager not initialized")
    return _crypto_manager


def init_crypto_manager(encryption_key: Optional[str] = None, key_file: Optional[str] = None):
    """Initialize the global crypto manager"""
    global _crypto_manager
    _crypto_manager = CryptoManager(encryption_key, key_file)
    return _crypto_manager
