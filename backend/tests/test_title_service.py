from app.services.title_service import should_refine_session_title


def test_should_refine_session_title_only_once():
    assert should_refine_session_title("New Chat", assistant_message_count=1) is True
    assert should_refine_session_title("Project Planning", assistant_message_count=1) is True
    assert should_refine_session_title("Project Planning", assistant_message_count=2) is False
    assert should_refine_session_title("Project Planning", assistant_message_count=5) is False
