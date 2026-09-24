import json
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="QM Meet API")

# Lưu trữ User: { username: { "password": pw, "nickname": nick, "avatar": avt } }
users_db: Dict[str, dict] = {}

class RoomManager:
    def __init__(self):
        # self.rooms = { room_id: { "host_id": str, "peers": { user_id: { "ws": ws, ... } } } }
        self.rooms: Dict[str, dict] = {}

    def get_or_create_room(self, room_id: str, host_id: str):
        if room_id not in self.rooms:
            self.rooms[room_id] = {
                "host_id": host_id,
                "peers": {}
            }
        return self.rooms[room_id]

    async def connect_user(self, room_id: str, user_id: str, nickname: str, avatar: str, websocket: WebSocket):
        await websocket.accept()
        room = self.get_or_create_room(room_id, user_id)
        
        is_host = (room["host_id"] == user_id)
        
        room["peers"][user_id] = {
            "ws": websocket,
            "nickname": nickname,
            "avatar": avatar,
            "is_host": is_host
        }

        # Trả về danh sách thành viên hiện có cho người mới
        existing_users = [
            {"user_id": uid, "nickname": u["nickname"], "avatar": u["avatar"], "is_host": u["is_host"]}
            for uid, u in room["peers"].items() if uid != user_id
        ]
        
        await websocket.send_text(json.dumps({
            "type": "room_joined",
            "is_host": is_host,
            "existing_users": existing_users
        }))

        # Thông báo cho người trong phòng về thành viên mới
        await self.broadcast_to_others(room_id, user_id, {
            "type": "user_joined",
            "user_id": user_id,
            "nickname": nickname,
            "avatar": avatar,
            "is_host": is_host
        })

    async def disconnect_user(self, room_id: str, user_id: str, websocket: WebSocket):
        if room_id not in self.rooms:
            return

        room = self.rooms[room_id]
        if user_id in room["peers"]:
            # Chỉ gỡ bỏ nếu kết nối bị đứt chính là kết nối hiện tại
            if room["peers"][user_id]["ws"] != websocket:
                return

            leaving_user = room["peers"].pop(user_id)
            host_id = room["host_id"]

            # Báo cho Host biết ai vừa thoát hoặc mất mạng
            if host_id in room["peers"] and host_id != user_id:
                host_ws = room["peers"][host_id]["ws"]
                try:
                    await host_ws.send_text(json.dumps({
                        "type": "host_alert_disconnect",
                        "user_id": user_id,
                        "nickname": leaving_user["nickname"],
                        "message": f"Thành viên [{leaving_user['nickname']}] đã rời phòng hoặc mất mạng."
                    }))
                except Exception:
                    pass

            # Thông báo cho các máy khác dọn dẹp khung video
            await self.broadcast_to_others(room_id, user_id, {
                "type": "user_left",
                "user_id": user_id,
                "nickname": leaving_user["nickname"]
            })

            # Xóa phòng nếu không còn ai
            if len(room["peers"]) == 0:
                del self.rooms[room_id]

    async def relay_message(self, room_id: str, sender_id: str, data: dict):
        room = self.rooms.get(room_id)
        if not room:
            return

        target_id = data.get("target_id")
        data["sender_id"] = sender_id

        # Định tuyến đích danh (WebRTC SDP / Candidate)
        if target_id:
            if target_id in room["peers"]:
                target_ws = room["peers"][target_id]["ws"]
                try:
                    await target_ws.send_text(json.dumps(data))
                except Exception:
                    pass
            # Nếu có target_id cụ thể mà không tìm thấy peer, không broadcast nhầm
            return

        # Broadcast toàn phòng (trừ người gửi)
        await self.broadcast_to_others(room_id, sender_id, data)

    async def broadcast_to_others(self, room_id: str, sender_id: str, message: dict):
        room = self.rooms.get(room_id)
        if not room:
            return
        msg_str = json.dumps(message)
        for uid, user_info in list(room["peers"].items()):
            if uid != sender_id:
                try:
                    await user_info["ws"].send_text(msg_str)
                except Exception:
                    pass

manager = RoomManager()

# --- AUTH API ---
class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str
    avatar: str

class LoginRequest(BaseModel):
    username: str
    password: str

class QuickJoinRequest(BaseModel):
    nickname: str
    avatar: str = "👨‍💻"

@app.post("/api/register")
def register(req: RegisterRequest):
    if req.username in users_db:
        raise HTTPException(status_code=400, detail="Tài khoản này đã tồn tại!")
    users_db[req.username] = {
        "password": req.password,
        "nickname": req.nickname,
        "avatar": req.avatar
    }
    return {"message": "Đăng ký thành công!"}

@app.post("/api/login")
def login(req: LoginRequest):
    user = users_db.get(req.username)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu!")
    return {
        "username": req.username,
        "nickname": user["nickname"],
        "avatar": user["avatar"]
    }

@app.post("/api/quick-join")
def quick_join(req: QuickJoinRequest):
    import uuid
    uid = f"user_{uuid.uuid4().hex[:6]}"
    return {
        "username": uid,
        "nickname": req.nickname.strip() or "Thành viên",
        "avatar": req.avatar
    }

# --- WEBSOCKET SIGNALING & DIRECT STREAM RELAY ---
@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str, nickname: str = "Ẩn danh", avatar: str = "👤"):
    await manager.connect_user(room_id, user_id, nickname, avatar, websocket)
    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            await manager.relay_message(room_id, user_id, data)
    except WebSocketDisconnect:
        await manager.disconnect_user(room_id, user_id, websocket)
    except Exception:
        await manager.disconnect_user(room_id, user_id, websocket)

# --- STATIC FILES ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)