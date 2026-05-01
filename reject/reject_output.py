from debug_log import log_to_system


def reject_output_on(item=None):
    meta = item.get("meta", {}) if isinstance(item, dict) else {}
    log_to_system(
        f"REJECT AKTİF | {meta}",
        "OK",
        save_csv=True,
        show_ui=True
    )


def reject_output_off(item=None):
    meta = item.get("meta", {}) if isinstance(item, dict) else {}
    log_to_system(
        f"REJECT PASİF | {meta}",
        "INFO",
        save_csv=False,
        show_ui=True
    )