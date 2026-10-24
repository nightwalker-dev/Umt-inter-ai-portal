import pytest
import sys
import os

# Add the backend directory to sys.path so we can import from it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
