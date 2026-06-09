from app.services.group_service import GroupService


def test_stock_groups_are_loadable() -> None:
    service = GroupService()
    assert "BBCA" in service.get_codes("LQ45")
    assert "BBCA" in service.get_codes("ALL")
    assert "LQ45" in service.find_groups_for_stock("BBCA")

