from app import app  # app.py'den Flask uygulamasını içe aktar
from models import db  # models.py'den db nesnesini içe aktar

# Veritabanını yeniden oluştur
with app.app_context():
    print("Veritabanı tabloları siliniyor...")
    db.drop_all()
    print("Yeni veritabanı tabloları oluşturuluyor...")
    db.create_all()
    print("Veritabanı başarıyla sıfırlandı!")