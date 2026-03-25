import os
import subprocess
import tempfile
from datetime import datetime


class IdsCsetExportError(Exception):
    pass


def _safe_filename(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in str(text)) or "ids_camera"


def export_ids_camera_to_cset(selected_source):
    """
    Native ids_cset_exporter.exe kullanarak seçili IDS kameranın .cset dosyasını üretir.

    selected_source örneği:
    {
        "type": "ids",
        "index": 0,
        "display_name": "Hat 1 - IDS Kamera",
        ...
    }
    """
    if not selected_source:
        raise IdsCsetExportError("Seçili kamera yok.")

    if selected_source.get("type") != "ids":
        raise IdsCsetExportError("CSET export sadece IDS kameralar için kullanılabilir.")

    camera_index = selected_source.get("index", None)
    if camera_index is None:
        raise IdsCsetExportError("IDS kamera index bilgisi bulunamadı.")

    label = selected_source.get("display_name", "ids_camera")
    filename = f"{_safe_filename(label)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.cset"
    out_path = os.path.join(tempfile.gettempdir(), filename)

    helper_exe = r"C:\Users\Hande\Desktop\inkjet\tools\ids_cset_exporter.exe"

    if not os.path.exists(helper_exe):
        raise IdsCsetExportError(
            "Native exporter bulunamadı. tools klasörüne ids_cset_exporter.exe koyman gerekiyor."
        )

    cmd = [
        helper_exe,
        "--index", str(camera_index),
        "--out", out_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
    except Exception as e:
        raise IdsCsetExportError(f"Native exporter çalıştırılamadı: {e}")

    if result.returncode != 0:
        stdout_text = (result.stdout or "").strip()
        stderr_text = (result.stderr or "").strip()

        if result.returncode == 13:
            raise IdsCsetExportError(
                "IDS kamera bulunamadı. Kamera başka uygulama tarafından açık olabilir."
            )
        elif result.returncode == 16:
            raise IdsCsetExportError(
                "IDS kamera bulundu ama açılamadı. IDS peak Cockpit, Streamlit yayını "
                "veya başka bir uygulama kamerayı kullanıyor olabilir."
            )
        elif result.returncode == 17:
            raise IdsCsetExportError(
                "Kamera açıldı fakat .cset dosyası kaydedilemedi."
            )
        else:
            raise IdsCsetExportError(
                "Native exporter hata verdi.\n\n"
                f"Return code: {result.returncode}\n\n"
                f"STDOUT:\n{stdout_text}\n\n"
                f"STDERR:\n{stderr_text}"
            )

    if not os.path.exists(out_path):
        raise IdsCsetExportError("CSET dosyası oluşmadı.")

    with open(out_path, "rb") as f:
        data = f.read()

    if not data:
        raise IdsCsetExportError("CSET dosyası boş oluştu.")

    return {
        "filename": filename,
        "bytes": data,
        "meta": {
            "api_name": "ids_cset_exporter.exe",
            "signature": "subprocess"
        }
    }