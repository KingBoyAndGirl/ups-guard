"""Tests for crypto utilities"""
import pytest
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.crypto import CryptoManager, init_crypto_manager, get_crypto_manager


def test_crypto_manager_encrypt_decrypt():
    """Test basic encryption and decryption"""
    crypto = CryptoManager(encryption_key=None, key_file="/tmp/test_encryption_key")
    
    plaintext = "sensitive_password_123"
    
    # Encrypt
    ciphertext = crypto.encrypt(plaintext)
    assert ciphertext != plaintext
    assert len(ciphertext) > 0
    
    # Decrypt
    decrypted = crypto.decrypt(ciphertext)
    assert decrypted == plaintext


def test_crypto_manager_empty_string():
    """Test encryption/decryption of empty string"""
    crypto = CryptoManager(encryption_key=None, key_file="/tmp/test_encryption_key2")
    
    plaintext = ""
    
    ciphertext = crypto.encrypt(plaintext)
    assert ciphertext == plaintext
    
    decrypted = crypto.decrypt(ciphertext)
    assert decrypted == plaintext


def test_crypto_manager_with_custom_key():
    """Test using a custom encryption key"""
    from cryptography.fernet import Fernet
    
    custom_key = Fernet.generate_key().decode()
    crypto = CryptoManager(encryption_key=custom_key, key_file="/tmp/test_key3")
    
    plaintext = "test_data"
    ciphertext = crypto.encrypt(plaintext)
    decrypted = crypto.decrypt(ciphertext)
    
    assert decrypted == plaintext


def test_crypto_manager_mask_sensitive():
    """Test masking sensitive data"""
    crypto = CryptoManager(encryption_key=None, key_file="/tmp/test_key4")
    
    # Test with default masking
    masked = crypto.mask_sensitive("password123")
    assert masked == "***"
    
    # Test with show_length
    masked = crypto.mask_sensitive("password123", show_length=3)
    assert masked == "pas***"
    
    # Test with empty string
    masked = crypto.mask_sensitive("")
    assert masked == ""
    
    # Test with None
    masked = crypto.mask_sensitive(None)
    assert masked == ""


def test_crypto_manager_key_persistence():
    """Test that encryption key is persisted to file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / ".encryption_key"
        
        # Create crypto manager - should generate and save key
        crypto1 = CryptoManager(encryption_key=None, key_file=str(key_file))
        
        # Verify key file exists
        assert key_file.exists()
        
        # Encrypt data with first manager
        plaintext = "test_persistence"
        ciphertext = crypto1.encrypt(plaintext)
        
        # Create new manager - should load existing key
        crypto2 = CryptoManager(encryption_key=None, key_file=str(key_file))
        
        # Should be able to decrypt with loaded key
        decrypted = crypto2.decrypt(ciphertext)
        assert decrypted == plaintext


def test_crypto_manager_init_and_get():
    """Test global crypto manager initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        key_file = Path(tmpdir) / ".test_key"
        
        # Initialize global manager
        manager = init_crypto_manager(encryption_key=None, key_file=str(key_file))
        assert manager is not None
        
        # Get manager
        retrieved = get_crypto_manager()
        assert retrieved is manager
        
        # Test encryption/decryption through global manager
        plaintext = "global_test"
        ciphertext = retrieved.encrypt(plaintext)
        decrypted = retrieved.decrypt(ciphertext)
        assert decrypted == plaintext


def test_crypto_manager_different_keys_produce_different_ciphertexts():
    """Test that different keys produce different ciphertexts"""
    crypto1 = CryptoManager(encryption_key=None, key_file="/tmp/test_key_a")
    crypto2 = CryptoManager(encryption_key=None, key_file="/tmp/test_key_b")
    
    plaintext = "same_plaintext"
    
    ciphertext1 = crypto1.encrypt(plaintext)
    ciphertext2 = crypto2.encrypt(plaintext)
    
    # Different keys should produce different ciphertexts
    assert ciphertext1 != ciphertext2
    
    # Each should decrypt with its own key
    assert crypto1.decrypt(ciphertext1) == plaintext
    assert crypto2.decrypt(ciphertext2) == plaintext
