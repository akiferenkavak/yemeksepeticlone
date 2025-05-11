from flask import app
from models import Restaurant  # modelin tanımlı olduğu yerden import et
from app import db, app  # db ve app nesnelerini import et

with app.app_context():  # Doğru kullanım: app.app_context()
    paths = db.session.query(Restaurant.image_path).all()
    for path in paths:
        print(path[0])  # çünkü query sonucu [(...), (...)] şeklinde tuple döner