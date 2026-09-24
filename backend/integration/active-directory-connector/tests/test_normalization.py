from active_directory_connector.normalization import normalize_group, normalize_user


def test_normalize_user_maps_core_fields_and_enabled_true():
    entry = {
        "dn": "CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com",
        "attributes": {
            "objectGUID": "guid-user-1",
            "distinguishedName": "CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com",
            "sAMAccountName": "jdoe",
            "displayName": "Jane Doe",
            "mail": "jdoe@corp.example.com",
            "userAccountControl": "512",  # NORMAL_ACCOUNT, not disabled
            "memberOf": ["CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com"],
            "whenChanged": "20260101120000.0Z",
        },
    }

    asset = normalize_user(entry)

    assert asset.external_id == "guid-user-1"
    assert asset.name == "jdoe"
    assert asset.type == "ad_user"
    assert asset.attributes["email"] == "jdoe@corp.example.com"
    assert asset.attributes["enabled"] is True
    assert asset.attributes["member_of"] == ["CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com"]
    assert asset.tags == {"source": "active_directory", "object_class": "user"}


def test_normalize_user_detects_disabled_account():
    entry = {
        "dn": "CN=Old User,OU=Users,DC=corp,DC=example,DC=com",
        "attributes": {
            "sAMAccountName": "olduser",
            "userAccountControl": "514",  # 512 | ACCOUNTDISABLE (0x2)
        },
    }

    asset = normalize_user(entry)

    assert asset.attributes["enabled"] is False


def test_normalize_user_falls_back_to_dn_when_no_object_guid_or_sam_name():
    entry = {"dn": "CN=No GUID,OU=Users,DC=corp,DC=example,DC=com", "attributes": {}}

    asset = normalize_user(entry)

    assert asset.external_id == "CN=No GUID,OU=Users,DC=corp,DC=example,DC=com"
    assert asset.name == "CN=No GUID,OU=Users,DC=corp,DC=example,DC=com"


def test_normalize_group_maps_member_count():
    entry = {
        "dn": "CN=Engineering,OU=Groups,DC=corp,DC=example,DC=com",
        "attributes": {
            "objectGUID": "guid-group-1",
            "cn": "Engineering",
            "member": [
                "CN=Jane Doe,OU=Users,DC=corp,DC=example,DC=com",
                "CN=John Smith,OU=Users,DC=corp,DC=example,DC=com",
            ],
            "groupType": "-2147483646",
        },
    }

    asset = normalize_group(entry)

    assert asset.external_id == "guid-group-1"
    assert asset.name == "Engineering"
    assert asset.type == "ad_group"
    assert asset.attributes["member_count"] == 2
    assert asset.tags == {"source": "active_directory", "object_class": "group"}


def test_normalize_group_handles_single_valued_member_not_returned_as_list():
    # Some directory schemas/servers return a single-valued attribute as a
    # bare string rather than a one-item list.
    entry = {
        "dn": "CN=Solo,OU=Groups,DC=corp,DC=example,DC=com",
        "attributes": {"cn": "Solo", "member": "CN=Only One,OU=Users,DC=corp,DC=example,DC=com"},
    }

    asset = normalize_group(entry)

    assert asset.attributes["member_count"] == 1
    assert asset.attributes["members"] == ["CN=Only One,OU=Users,DC=corp,DC=example,DC=com"]
