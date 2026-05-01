import pyads


CLIENT_NETID = "192.168.0.50.1.1"   # Bu PC'nin AMS NetID'si
CLIENT_IP = "192.168.0.50"          # Bu PC'nin IP adresi

TARGET_IP = "192.168.0.10"          # PLC'nin IP adresi
TARGET_USERNAME = "Administrator"  # PLC Windows kullanicisi
TARGET_PASSWD = "1"                 # PLC sifresi

# PLC icinde bu PC'nin gorunecegi isim
ROUTE_NAME = "INKJETPROJESI"

print("=== ROUTE EKLEME ISLEMI BASLADI ===\n")

print(f"Client (Bu PC) NetID : {CLIENT_NETID}")
print(f"Client (Bu PC) IP    : {CLIENT_IP}")
print(f"PLC (Target) IP      : {TARGET_IP}")
print(f"Route ismi PLC icinde: {ROUTE_NAME}\n")


status = pyads.add_route_to_plc(
    CLIENT_NETID,
    CLIENT_IP,
    TARGET_IP,
    TARGET_USERNAME,
    TARGET_PASSWD,
    route_name=ROUTE_NAME
)


if status:
    print("\n=== BASARILI ===")
else:
    print("\n=== HATA ===")
