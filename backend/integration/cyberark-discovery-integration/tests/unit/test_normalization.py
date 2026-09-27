import pytest
from src.normalization.transformer import Normalizer
from src.normalization.validator import DataValidator

@pytest.fixture
def rules():
    return {
        "excluded_usernames": ["guest", "sys_backup"],
        "platform_mappings": {"Windows Server 2022": "WinServerLocal"},
        "default_platform": "GenericPlatform"
    }

def test_validator_rules(rules):
    validator = DataValidator(rules)
    assert validator.is_valid_account({"userName": "admin", "address": "10.0.0.1"}) is True
    assert validator.is_valid_account({"userName": "guest", "address": "10.0.0.1"}) is False
    assert validator.is_valid_account({"userName": "", "address": "10.0.0.1"}) is False

def test_normalizer_transform(rules):
    normalizer = Normalizer(rules)
    raw = {"raw_username": "ADM_User1 ", "host": " SRV01.LOCAL ", "os_type": "Windows Server 2022", "ip": "10.0.0.5"}
    result = normalizer.transform_single(raw)
    
    assert result["userName"] == "adm_user1"
    assert result["address"] == "srv01.local"
    assert result["platformId"] == "WinServerLocal"
    assert result["customProperties"]["IPAddress"] == "10.0.0.5"

def test_normalizer_process_bulk(rules):
    normalizer = Normalizer(rules)
    raw_list = [
        {"raw_username": "adm_user1", "host": "srv01.local", "os_type": "Windows Server 2022"},
        {"raw_username": "guest", "host": "srv02.local", "os_type": "Windows Server 2022"}
    ]
    processed = normalizer.process(raw_list)
    assert len(processed) == 1
    assert processed[0]["userName"] == "adm_user1"
