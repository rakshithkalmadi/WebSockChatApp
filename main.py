from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List, Dict
import json

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form id="usernameForm" onsubmit="setUsername(event)">
            <input type="text" id="username" placeholder="Enter your name" autocomplete="off"/>
            <input type="text" id="room" placeholder="Enter room name" autocomplete="off"/>
            <button>Join</button>
        </form>
        <div id="chat" style="display:none;">
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" id="messageText" autocomplete="off"/>
                <button>Send</button>
            </form>
            <ul id='messages'></ul>
        </div>
        <script>
            var ws;
            var username;
            var room;

            function setUsername(event) {
                event.preventDefault();
                username = document.getElementById("username").value;
                room = document.getElementById("room").value;
                if (username && room) {
                    document.getElementById("usernameForm").style.display = "none";
                    document.getElementById("chat").style.display = "block";
                    ws = new WebSocket(`ws://localhost:8000/ws/${room}`);
                    ws.onmessage = function(event) {
                        var messages = document.getElementById('messages')
                        var message = document.createElement('li')
                        var content = document.createTextNode(event.data)
                        message.appendChild(content)
                        messages.appendChild(message)
                    };
                }
            }

            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(JSON.stringify({username: username, message: input.value}));
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        self.active_connections[room].remove(websocket)
        if not self.active_connections[room]:
            del self.active_connections[room]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, room: str):
        for connection in self.active_connections.get(room, []):
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            username = message_data['username']
            message = message_data['message']
            await manager.broadcast(f"{username}: {message}", room)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        await manager.broadcast("A client disconnected", room)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
