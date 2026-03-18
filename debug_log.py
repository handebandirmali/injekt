import datetime
import csv
import os

log_file_path = r"C:\Users\Hande\Desktop\inkjet\log.txt"
csv_file_path = r"C:\Users\Hande\Desktop\inkjet\denetim_kayitlari.csv"

def log(msg):
    # 1. Mevcut TXT Loglama 
    try: 
        with open(log_file_path, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass 

    # 2. Yeni CSV Loglama 
    try:
        # Mesajın içeriğine göre durum belirleyelim
        status = "OK" if "detected" in msg.lower() else "NG"
        if "not found" in msg.lower(): status = "NG"
        
        file_exists = os.path.isfile(csv_file_path)
        
        with open(csv_file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Dosya ilk kez oluşturuluyorsa başlıkları yaz
            if not file_exists:
                writer.writerow(['Tarih_Saat', 'Mesaj', 'Durum'])
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([timestamp, msg, status])
    except Exception:
        pass