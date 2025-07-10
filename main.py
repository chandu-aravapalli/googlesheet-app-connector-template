# Set environment variables BEFORE any imports to prevent PyO3 conflicts
import os
os.environ['CRYPTOGRAPHY_DONT_BUILD_RUST'] = '1'
os.environ['CRYPTOGRAPHY_USE_PURE_PYTHON'] = '1'

import traceback
from flask import Flask
from workflows_cdk import Router

# Test hash algorithm compatibility early
try:
    from cryptography.hazmat.primitives import hashes
    from google.auth.crypt._cryptography_rsa import _SHA256
    
    # Test that both are HashAlgorithm instances
    crypto_sha256 = hashes.SHA256()
    
    # Test they're compatible
    assert hasattr(crypto_sha256, 'name'), "Cryptography SHA256 missing 'name' attribute"
    assert hasattr(_SHA256, 'name'), "Google Auth SHA256 missing 'name' attribute"
    
except Exception as e:
    raise

# Create Flask app
app = Flask(__name__)
router = Router(app)

if __name__ == "__main__":
    router.run_app(app)