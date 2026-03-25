from debug_log import log_to_system


def reject_output_on(item=None):
    meta = item.get("meta", {}) if isinstance(item, dict) else {}
    log_to_system(
        f"REJECT ON | {meta}",
        "OK",
        save_csv=True,
        show_ui=True
    )


def reject_output_off(item=None):
    meta = item.get("meta", {}) if isinstance(item, dict) else {}
    log_to_system(
        f"REJECT OFF | {meta}",
        "INFO",
        save_csv=False,
        show_ui=True
    )