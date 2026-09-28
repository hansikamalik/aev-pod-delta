import os
import pytest
from unittest.mock import MagicMock
import psycopg

os.environ["DATABASE_URL"] = "postgresql://mock:mock@localhost:5432/mockdb"
psycopg.connect = MagicMock()
