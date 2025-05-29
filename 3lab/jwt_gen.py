from jose import jwt
SECRET = "secret-key"
payload = {"id": 1, "username": "user1"}
print(jwt.encode(payload, SECRET, algorithm="HS256"))
