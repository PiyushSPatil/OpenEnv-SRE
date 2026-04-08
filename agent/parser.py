def parse_action(text: str):
    text = text.lower()

    if "clear_cache" in text:
        return {"action_type": "clear_cache", "target": None}
    elif "fix_db_connection" in text:
        return {"action_type": "fix_db_connection", "target": None}
    elif "restart_service" in text:
        return {"action_type": "restart_service", "target": "backend"}
    elif "scale_service" in text:
        return {"action_type": "scale_service", "target": "api"}
    else:
        return {"action_type": "noop", "target": None}