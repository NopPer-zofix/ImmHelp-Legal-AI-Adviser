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