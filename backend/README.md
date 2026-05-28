# -MHelpBackend
ΙΜMHelpBackend

//check stuff

1) python server.py

2) Invoke-WebRequest -Uri "http://localhost:5000/ask" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"name":"John","question":"Hello"}'

3) curl http://localhost:5000/ping



Windows Machine Setup 

1) Install Python
2) Install pip
3) pip install flask
4) pip install flask openai chromadb
5) pip install python-dotenv
6) pip install sqlalchemy psycopg2-binary
7) pip install bcrypt

8) Set up postgress


Testing
9) Invoke-WebRequest -Uri "http://localhost:5000/users" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"email": "test@test.com", "password": "123456", "username": "testuser"}'

8) Invoke-WebRequest -Uri "http://localhost:5000/chats" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"user_id": 1}'

10) Invoke-WebRequest -Uri "http://localhost:5000/ask" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"user_id": 1, "chat_id": 1, "question": "What documents are needed for Cyprus visa?"}'