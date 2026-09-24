// Global States
let currentUser = null;
let currentRoomId = null;
let isHost = false;
let socket = null;
let localStream = null;
let screenStream = null;
let isScreenSharing = false;

let isCamEnabled = true;
let isMicEnabled = true;
let isHandRaised = false;
let isCamMirrored = true;

const peerConnections = {};
const candidateQueues = {};

// Web Audio API Context for Volume Meter & Sound FX
let audioCtx = null;
let audioAnalyser = null;
let micSource = null;
let speakingInterval = null;

// Frame Streaming & Audio Streaming via WebSocket (Guaranteed Fail-Safe Relay)
let frameStreamInterval = null;
let audioRecorder = null;
const peerActiveEngine = {}; // { peerId: 'webrtc' | 'ws' }

// STUN Servers (Multiple high-availability servers)
const rtcConfig = {
  iceServers: [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" },
    { urls: "stun:stun2.l.google.com:19302" },
    { urls: "stun:stun3.l.google.com:19302" },
    { urls: "stun:stun4.l.google.com:19302" },
    { urls: "stun:stun.cloudflare.com:3478" }
  ]
};

// ----------------- AUDIO SYNTHESIZER & UNLOCK -----------------
function initAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
}

document.addEventListener("click", initAudioContext, { once: false });
document.addEventListener("touchstart", initAudioContext, { once: false });

function playSynthSound(type) {
  try {
    initAudioContext();
    if (!audioCtx) return;

    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    const now = audioCtx.currentTime;

    if (type === "join") {
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
      osc.start(now);
      osc.stop(now + 0.2);
    } else if (type === "reaction") {
      osc.frequency.setValueAtTime(600, now);
      osc.frequency.exponentialRampToValueAtTime(1200, now + 0.1);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
      osc.start(now);
      osc.stop(now + 0.15);
    } else if (type === "raise_hand") {
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.setValueAtTime(659, now + 0.1);
      gain.gain.setValueAtTime(0.09, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    }
  } catch (e) {}
}

// ----------------- TOAST NOTIFICATIONS -----------------
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "warning") icon = "⚠️";
  if (type === "error") icon = "❌";

  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ----------------- AUTHENTICATION & QUICK JOIN -----------------
let authMode = "quick";
let selectedAvatar = "👨‍💻";

function switchAuthTab(mode) {
  authMode = mode;
  document.getElementById("tab-quick").classList.toggle("active", mode === "quick");
  document.getElementById("tab-login").classList.toggle("active", mode === "login");
  document.getElementById("tab-register").classList.toggle("active", mode === "register");

  if (mode === "quick") {
    document.getElementById("form-quick").style.display = "block";
    document.getElementById("form-auth").style.display = "none";
  } else {
    document.getElementById("form-quick").style.display = "none";
    document.getElementById("form-auth").style.display = "block";
    document.getElementById("register-fields").style.display = mode === "register" ? "block" : "none";
    document.getElementById("btn-auth-submit").querySelector("span").innerText = mode === "register" ? "Tạo Tài Khoản" : "Đăng Nhập";
  }
}

function selectAvatar(avt) {
  selectedAvatar = avt;
  document.querySelectorAll(".avatar-option").forEach(el => {
    el.classList.toggle("selected", el.innerText === avt);
  });
}

function generateRandomQuickRoom() {
  const randomId = "phong-" + Math.floor(100 + Math.random() * 900);
  document.getElementById("quick-room").value = randomId;
}

function generateRandomRoom() {
  const randomId = "phong-" + Math.floor(100 + Math.random() * 900);
  document.getElementById("room-input").value = randomId;
}

// Vào nhanh không cần mật khẩu
async function submitQuickJoin() {
  const nickname = document.getElementById("quick-nickname").value.trim();
  const roomId = document.getElementById("quick-room").value.trim();

  if (!nickname) return showToast("Vui lòng nhập tên hiển thị!", "warning");
  if (!roomId) return showToast("Vui lòng nhập mã phòng!", "warning");

  try {
    const res = await fetch("/api/quick-join", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nickname, avatar: selectedAvatar })
    });
    const user = await res.json();
    currentUser = user;
    await joinRoom(roomId);
  } catch (e) {
    showToast("Không thể kết nối máy chủ!", "error");
  }
}

async function submitAuth() {
  const username = document.getElementById("auth-username").value.trim();
  const password = document.getElementById("auth-password").value.trim();

  if (!username || !password) return showToast("Vui lòng điền đầy đủ thông tin!", "warning");

  if (authMode === "register") {
    const nickname = document.getElementById("auth-nickname").value.trim() || username;
    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, nickname, avatar: selectedAvatar })
      });
      const data = await res.json();
      if (!res.ok) return showToast(data.detail || "Đăng ký thất bại", "error");
      showToast("Đăng ký thành công! Hãy đăng nhập.", "success");
      switchAuthTab("login");
    } catch (err) {
      showToast("Không thể kết nối máy chủ!", "error");
    }
  } else {
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (!res.ok) return showToast(data.detail || "Sai tài khoản hoặc mật khẩu!", "error");
      
      currentUser = data;
      showToast(`Xin chào ${currentUser.nickname}!`, "success");
      showRoomSelection();
    } catch (err) {
      showToast("Không thể kết nối máy chủ!", "error");
    }
  }
}

function showRoomSelection() {
  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("room-selection-screen").style.display = "flex";
  document.getElementById("user-display-avatar").innerText = currentUser.avatar;
  document.getElementById("user-display-name").innerText = currentUser.nickname;
  document.getElementById("user-display-handle").innerText = `@${currentUser.username}`;
}

function logout() {
  currentUser = null;
  document.getElementById("room-selection-screen").style.display = "none";
  document.getElementById("auth-screen").style.display = "flex";
}

// ----------------- MEDIA SETUP & JOIN ROOM -----------------
async function joinRoom(roomId) {
  if (!roomId) return showToast("Vui lòng nhập mã phòng!", "warning");
  currentRoomId = roomId;

  // Lấy Camera và Micro với cơ chế fallback tự động
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 24 } },
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        });
      } catch (err1) {
        try {
          localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        } catch (err2) {
          try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            isMicEnabled = false;
            showToast("Không tìm thấy micro! Đang dùng Camera.", "warning");
          } catch (err3) {
            try {
              localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
              isCamEnabled = false;
              showToast("Không tìm thấy camera! Đang dùng Micro.", "warning");
            } catch (err4) {
              console.warn("Không lấy được media:", err4);
              showToast("Không thể mở Camera/Mic: " + err4.message, "warning");
            }
          }
        }
      }
    } else {
      showToast("Trình duyệt chặn Camera do HTTP. Hãy dùng localhost hoặc HTTPS.", "warning");
    }
  } catch (e) {
    console.warn("Lỗi Media:", e);
  }

  // Khởi tạo Audio Analyser đo âm lượng
  if (localStream) {
    setupAudioAnalyser(localStream);
  }

  document.getElementById("auth-screen").style.display = "none";
  document.getElementById("room-selection-screen").style.display = "none";
  document.getElementById("call-screen").style.display = "flex";
  document.getElementById("current-room-text").innerText = currentRoomId;

  // Render video box của chính mình
  addVideoBox(currentUser.username, `${currentUser.nickname} (Bạn)`, currentUser.avatar, localStream, true);

  // Mở kết nối WebSocket
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/${currentRoomId}/${currentUser.username}?nickname=${encodeURIComponent(currentUser.nickname)}&avatar=${encodeURIComponent(currentUser.avatar)}`;
  
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    playSynthSound("join");
    updateConnectionStatus("🟢 Đã kết nối phòng họp", "var(--success)");

    // Kích hoạt Engine phát trực tiếp qua WebSocket (Bảo đảm 100% nhìn thấy nhau)
    startWebSocketMediaBroadcasting();
  };

  socket.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);
      await handleSignalingMessage(data);
    } catch (e) {
      console.error("Lỗi tin nhắn WebSocket:", e);
    }
  };

  socket.onclose = () => {
    updateConnectionStatus("🔴 Mất kết nối", "var(--danger)");
    showToast("Đã ngắt kết nối khỏi phòng họp.", "warning");
  };

  updateParticipantCount();
}

function updateConnectionStatus(text, color) {
  const pill = document.getElementById("conn-status-pill");
  const dot = pill.querySelector(".status-indicator-dot");
  const txt = document.getElementById("conn-status-text");
  if (dot) dot.style.background = color;
  if (dot) dot.style.boxShadow = `0 0 8px ${color}`;
  if (txt) txt.innerText = text;
}

// ----------------- DUAL-ENGINE: WEBSOCKET LIVE STREAM RELAY -----------------
// Phát trực tiếp khung hình qua WebSocket: bảo đảm nhìn thấy nhau 100% qua mọi tường lửa/NAT
function startWebSocketMediaBroadcasting() {
  const canvas = document.getElementById("capture-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  canvas.width = 360;
  canvas.height = 202;

  if (frameStreamInterval) clearInterval(frameStreamInterval);

  frameStreamInterval = setInterval(() => {
    if (!localStream || !isCamEnabled) return;
    const videoTracks = localStream.getVideoTracks();
    if (videoTracks.length === 0 || !videoTracks[0].enabled) return;

    const localVideo = document.getElementById(`video-${currentUser.username}`);
    if (!localVideo || localVideo.videoWidth === 0) return;

    try {
      ctx.drawImage(localVideo, 0, 0, canvas.width, canvas.height);
      const frameData = canvas.toDataURL("image/jpeg", 0.45);
      sendWS({
        type: "video_frame",
        frame: frameData
      });
    } catch (e) {}
  }, 80); // ~13 FPS mượt mà và nhẹ nhàng

  // Ghi và gửi audio qua WebSocket nếu micro bật
  if (localStream && localStream.getAudioTracks().length > 0 && typeof MediaRecorder !== "undefined") {
    try {
      const audioStream = new MediaStream(localStream.getAudioTracks());
      let mimeType = "";
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) mimeType = "audio/webm;codecs=opus";
      else if (MediaRecorder.isTypeSupported("audio/webm")) mimeType = "audio/webm";
      else if (MediaRecorder.isTypeSupported("audio/mp4")) mimeType = "audio/mp4";

      if (mimeType) {
        audioRecorder = new MediaRecorder(audioStream, { mimeType });
        audioRecorder.ondataavailable = async (e) => {
          if (e.data && e.data.size > 0 && isMicEnabled) {
            const reader = new FileReader();
            reader.onloadend = () => {
              sendWS({
                type: "audio_frame",
                audio: reader.result
              });
            };
            reader.readAsDataURL(e.data);
          }
        };
        audioRecorder.start(300); // Gửi gói âm thanh mỗi 300ms
      }
    } catch (e) {
      console.warn("Không bật được WebSocket Audio recorder:", e);
    }
  }
}

// Nhận và hiển thị khung hình từ bạn bè
function handleRemoteVideoFrame(peerId, frameData) {
  let streamCanvas = document.getElementById(`canvas-${peerId}`);
  if (!streamCanvas) {
    addVideoBox(peerId, "Thành viên", "👤", null, false);
    streamCanvas = document.getElementById(`canvas-${peerId}`);
  }

  if (streamCanvas) {
    const img = new Image();
    img.onload = () => {
      const ctx = streamCanvas.getContext("2d");
      ctx.drawImage(img, 0, 0, streamCanvas.width, streamCanvas.height);
    };
    img.src = frameData;

    // Đánh dấu nhận thành công
    const box = document.getElementById(`box-${peerId}`);
    if (box) {
      box.classList.remove("cam-off");
      const tag = document.getElementById(`conn-tag-${peerId}`);
      if (tag && peerActiveEngine[peerId] !== "webrtc") {
        tag.innerText = "🟢 Trực tiếp";
        tag.style.color = "var(--accent)";
      }
    }
  }
}

// Nhận và phát âm thanh từ bạn bè qua WebSocket
function handleRemoteAudioFrame(peerId, audioData) {
  // Nếu WebRTC đã kết nối âm thanh, bỏ qua để tránh trùng âm thanh
  if (peerActiveEngine[peerId] === "webrtc") return;

  try {
    const audio = new Audio(audioData);
    audio.play().catch(() => {});
  } catch (e) {}
}

// ----------------- AUDIO ANALYSER -----------------
function setupAudioAnalyser(stream) {
  if (!stream || stream.getAudioTracks().length === 0) return;
  try {
    initAudioContext();
    if (!audioCtx) return;

    micSource = audioCtx.createMediaStreamSource(stream);
    audioAnalyser = audioCtx.createAnalyser();
    audioAnalyser.fftSize = 256;
    micSource.connect(audioAnalyser);

    const dataArray = new Uint8Array(audioAnalyser.frequencyBinCount);
    let isSpeakingCurrently = false;

    if (speakingInterval) clearInterval(speakingInterval);

    speakingInterval = setInterval(() => {
      if (!isMicEnabled) {
        if (isSpeakingCurrently) {
          isSpeakingCurrently = false;
          setSpeakingState(currentUser.username, false);
        }
        return;
      }
      audioAnalyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      const average = sum / dataArray.length;
      const speaking = average > 18;

      if (speaking !== isSpeakingCurrently) {
        isSpeakingCurrently = speaking;
        setSpeakingState(currentUser.username, speaking);
        sendWS({ type: "speaking_status", speaking: speaking });
      }
    }, 200);
  } catch (e) {
    console.warn("Lỗi khởi tạo Audio Analyser:", e);
  }
}

// ----------------- SIGNALING MESSAGE HANDLER -----------------
async function handleSignalingMessage(data) {
  switch (data.type) {
    case "room_joined":
      isHost = data.is_host;
      if (isHost) document.getElementById("host-badge").style.display = "inline-block";

      for (const peer of data.existing_users) {
        addVideoBox(peer.user_id, peer.nickname, peer.avatar, null, false);
        await createPeerConnection(peer.user_id, true);
      }
      updateParticipantCount();
      break;

    case "user_joined":
      showToast(`${data.nickname} vừa tham gia phòng`, "info");
      playSynthSound("join");
      addVideoBox(data.user_id, data.nickname, data.avatar, null, false);
      updateParticipantCount();
      break;

    case "video_frame":
      handleRemoteVideoFrame(data.sender_id, data.frame);
      break;

    case "audio_frame":
      handleRemoteAudioFrame(data.sender_id, data.audio);
      break;

    case "offer":
      await handleOffer(data.sender_id, data.offer);
      break;

    case "answer":
      await handleAnswer(data.sender_id, data.answer);
      break;

    case "candidate":
      await handleCandidate(data.sender_id, data.candidate);
      break;

    case "toggle_cam":
      updatePeerCamStatus(data.sender_id, data.enabled);
      break;

    case "toggle_mic":
      updatePeerMicStatus(data.sender_id, data.enabled);
      break;

    case "raise_hand":
      updatePeerHandStatus(data.sender_id, data.raised);
      if (data.raised) playSynthSound("raise_hand");
      break;

    case "speaking_status":
      setSpeakingState(data.sender_id, data.speaking);
      break;

    case "reaction":
      showFloatingIcon(data.emoji);
      playSynthSound("reaction");
      break;

    case "chat_msg":
      receiveChatMessage(data.sender_nickname, data.sender_avatar, data.message, false);
      break;

    case "host_alert_disconnect":
      showToast(data.message, "warning");
      break;

    case "user_left":
      showToast(`${data.nickname} đã rời phòng`, "info");
      removeVideoBox(data.user_id);
      if (peerConnections[data.user_id]) {
        peerConnections[data.user_id].close();
        delete peerConnections[data.user_id];
      }
      delete candidateQueues[data.user_id];
      delete peerActiveEngine[data.user_id];
      updateParticipantCount();
      break;
  }
}

// ----------------- WEBRTC PEER CONNECTION -----------------
async function createPeerConnection(peerId, isInitiator) {
  if (peerConnections[peerId]) {
    return peerConnections[peerId];
  }

  const pc = new RTCPeerConnection(rtcConfig);
  peerConnections[peerId] = pc;
  candidateQueues[peerId] = candidateQueues[peerId] || [];

  // Gắn track của máy mình vào PeerConnection
  const activeStream = isScreenSharing && screenStream ? screenStream : localStream;
  if (activeStream) {
    activeStream.getTracks().forEach(track => {
      pc.addTrack(track, activeStream);
    });
  } else {
    pc.addTransceiver("audio", { direction: "sendrecv" });
    pc.addTransceiver("video", { direction: "sendrecv" });
  }

  // Nhận track remote
  pc.ontrack = (event) => {
    let remoteVideo = document.getElementById(`video-${peerId}`);
    if (!remoteVideo) {
      addVideoBox(peerId, "Thành viên", "👤", null, false);
      remoteVideo = document.getElementById(`video-${peerId}`);
    }

    if (remoteVideo) {
      const incomingStream = (event.streams && event.streams[0]) ? event.streams[0] : null;
      if (incomingStream) {
        if (remoteVideo.srcObject !== incomingStream) {
          remoteVideo.srcObject = incomingStream;
        }
      } else {
        if (!remoteVideo.srcObject) {
          remoteVideo.srcObject = new MediaStream();
        }
        remoteVideo.srcObject.addTrack(event.track);
      }

      remoteVideo.play().then(() => {
        // Đã kích hoạt WebRTC thành công -> Ẩn Canvas dự phòng
        peerActiveEngine[peerId] = "webrtc";
        const streamCanvas = document.getElementById(`canvas-${peerId}`);
        if (streamCanvas) streamCanvas.style.display = "none";
        remoteVideo.style.display = "block";

        const tag = document.getElementById(`conn-tag-${peerId}`);
        if (tag) {
          tag.innerText = "⚡ WebRTC";
          tag.style.color = "var(--success)";
        }
        updateConnectionStatus("⚡ WebRTC P2P Hoạt Động", "var(--success)");
      }).catch(e => {
        console.warn("Chờ người dùng mở khóa âm thanh:", e);
      });
    }
  };

  pc.onicecandidate = (event) => {
    if (event.candidate) {
      sendWS({
        type: "candidate",
        target_id: peerId,
        candidate: event.candidate
      });
    }
  };

  pc.oniceconnectionstatechange = () => {
    console.log(`[ICE State - ${peerId}]:`, pc.iceConnectionState);
    if (pc.iceConnectionState === "connected") {
      peerActiveEngine[peerId] = "webrtc";
      const tag = document.getElementById(`conn-tag-${peerId}`);
      if (tag) {
        tag.innerText = "⚡ WebRTC";
        tag.style.color = "var(--success)";
      }
    }
  };

  if (isInitiator) {
    try {
      const offer = await pc.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: true
      });
      await pc.setLocalDescription(offer);
      sendWS({
        type: "offer",
        target_id: peerId,
        offer: offer
      });
    } catch (err) {
      console.error("Lỗi tạo Offer:", err);
    }
  }

  return pc;
}

async function handleOffer(peerId, offer) {
  const pc = await createPeerConnection(peerId, false);
  try {
    await pc.setRemoteDescription(new RTCSessionDescription(offer));
    await processCandidateQueue(peerId);

    const answer = await pc.createAnswer({
      offerToReceiveAudio: true,
      offerToReceiveVideo: true
    });
    await pc.setLocalDescription(answer);

    sendWS({
      type: "answer",
      target_id: peerId,
      answer: answer
    });
  } catch (err) {
    console.error("Lỗi xử lý Offer:", err);
  }
}

async function handleAnswer(peerId, answer) {
  const pc = peerConnections[peerId];
  if (pc && pc.signalingState !== "closed") {
    try {
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
      await processCandidateQueue(peerId);
    } catch (err) {
      console.error("Lỗi xử lý Answer:", err);
    }
  }
}

async function handleCandidate(peerId, candidate) {
  const pc = peerConnections[peerId];
  if (pc && pc.remoteDescription && pc.remoteDescription.type) {
    try {
      await pc.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (e) {
      console.error("Lỗi addIceCandidate:", e);
    }
  } else {
    if (!candidateQueues[peerId]) {
      candidateQueues[peerId] = [];
    }
    candidateQueues[peerId].push(candidate);
  }
}

async function processCandidateQueue(peerId) {
  const pc = peerConnections[peerId];
  if (pc && candidateQueues[peerId]) {
    while (candidateQueues[peerId].length > 0) {
      const cand = candidateQueues[peerId].shift();
      try {
        await pc.addIceCandidate(new RTCIceCandidate(cand));
      } catch (e) {
        console.error("Lỗi giải phóng candidate:", e);
      }
    }
  }
}

function sendWS(data) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(data));
  }
}

// ----------------- UI DOM RENDERERS -----------------
function addVideoBox(id, label, avatar, stream, isMuted) {
  if (document.getElementById(`box-${id}`)) return;

  const isSelf = (currentUser && id === currentUser.username);
  const box = document.createElement("div");
  box.id = `box-${id}`;
  box.className = "video-box";

  const localClass = isSelf ? "local-video" : "";
  const connTagText = isSelf ? "Bạn" : "Đang kết nối...";

  box.innerHTML = `
    <canvas id="canvas-${id}" class="stream-canvas ${localClass}" width="360" height="202"></canvas>
    <video id="video-${id}" class="${localClass}" autoplay playsinline webkit-playsinline ${isMuted ? "muted" : ""}></video>
    <div class="avatar-fallback">${avatar}</div>
    <div class="video-label">
      <span id="mic-status-${id}" class="mic-icon">🎙️</span>
      <span>${label}</span>
      <span class="conn-tag" id="conn-tag-${id}">${connTagText}</span>
    </div>
    <div class="hand-badge">✋ Giơ tay</div>
  `;

  document.getElementById("video-grid").appendChild(box);

  if (stream) {
    const videoEl = document.getElementById(`video-${id}`);
    videoEl.srcObject = stream;
    videoEl.play().catch(e => console.log("Local video play error:", e));
  }
}

function removeVideoBox(id) {
  const box = document.getElementById(`box-${id}`);
  if (box) box.remove();
}

function updateParticipantCount() {
  const count = document.querySelectorAll(".video-box").length;
  const badge = document.getElementById("participant-count");
  if (badge) badge.innerText = `👥 ${count} thành viên`;
}

function setSpeakingState(id, speaking) {
  const box = document.getElementById(`box-${id}`);
  if (box) {
    box.classList.toggle("speaking", speaking);
  }
}

// ----------------- CONTROLS & TOGGLES -----------------
function toggleCamera() {
  if (!localStream) return;
  const videoTracks = localStream.getVideoTracks();
  if (videoTracks.length === 0) return;

  isCamEnabled = !isCamEnabled;
  videoTracks.forEach(track => {
    track.enabled = isCamEnabled;
  });

  const btn = document.getElementById("btn-toggle-cam");
  btn.classList.toggle("off", !isCamEnabled);
  btn.querySelector(".btn-text").innerText = isCamEnabled ? "Cam" : "Tắt Cam";

  document.getElementById(`box-${currentUser.username}`).classList.toggle("cam-off", !isCamEnabled);

  sendWS({
    type: "toggle_cam",
    enabled: isCamEnabled
  });
}

function updatePeerCamStatus(peerId, enabled) {
  const box = document.getElementById(`box-${peerId}`);
  if (box) {
    box.classList.toggle("cam-off", !enabled);
  }
}

function toggleCameraMirror() {
  const videoEl = document.getElementById(`video-${currentUser.username}`);
  const canvasEl = document.getElementById(`canvas-${currentUser.username}`);

  isCamMirrored = !isCamMirrored;
  if (isCamMirrored) {
    if (videoEl) videoEl.classList.remove("unmirrored");
    if (canvasEl) canvasEl.classList.remove("unmirrored");
    showToast("Đã bật góc nhìn gương (Gương)", "info");
  } else {
    if (videoEl) videoEl.classList.add("unmirrored");
    if (canvasEl) canvasEl.classList.add("unmirrored");
    showToast("Đã tắt góc nhìn gương", "info");
  }
}

function toggleMicrophone() {
  if (!localStream) return;
  const audioTracks = localStream.getAudioTracks();
  if (audioTracks.length === 0) return;

  isMicEnabled = !isMicEnabled;
  audioTracks.forEach(track => {
    track.enabled = isMicEnabled;
  });

  const btn = document.getElementById("btn-toggle-mic");
  btn.classList.toggle("off", !isMicEnabled);
  btn.querySelector(".btn-text").innerText = isMicEnabled ? "Mic" : "Tắt Mic";

  const myMicIcon = document.getElementById(`mic-status-${currentUser.username}`);
  if (myMicIcon) {
    myMicIcon.innerText = isMicEnabled ? "🎙️" : "🔇";
    myMicIcon.classList.toggle("mic-icon-off", !isMicEnabled);
  }

  sendWS({
    type: "toggle_mic",
    enabled: isMicEnabled
  });
}

function updatePeerMicStatus(peerId, enabled) {
  const peerMicIcon = document.getElementById(`mic-status-${peerId}`);
  if (peerMicIcon) {
    peerMicIcon.innerText = enabled ? "🎙️" : "🔇";
    peerMicIcon.classList.toggle("mic-icon-off", !enabled);
  }
}

function toggleRaiseHand() {
  isHandRaised = !isHandRaised;
  document.getElementById(`box-${currentUser.username}`).classList.toggle("hand-raised", isHandRaised);

  if (isHandRaised) playSynthSound("raise_hand");

  sendWS({
    type: "raise_hand",
    raised: isHandRaised
  });
}

function updatePeerHandStatus(peerId, raised) {
  const box = document.getElementById(`box-${peerId}`);
  if (box) box.classList.toggle("hand-raised", raised);
}

// ----------------- SCREEN SHARING -----------------
async function toggleScreenShare() {
  const btn = document.getElementById("btn-share-screen");

  if (!isScreenSharing) {
    try {
      screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const screenTrack = screenStream.getVideoTracks()[0];

      for (const peerId in peerConnections) {
        const pc = peerConnections[peerId];
        const senders = pc.getSenders();
        const videoSender = senders.find(s => s.track && s.track.kind === "video");
        if (videoSender) {
          videoSender.replaceTrack(screenTrack);
        }
      }

      const localVideo = document.getElementById(`video-${currentUser.username}`);
      if (localVideo) {
        localVideo.srcObject = screenStream;
        localVideo.classList.add("unmirrored");
      }

      screenTrack.onended = () => {
        stopScreenShare();
      };

      isScreenSharing = true;
      btn.classList.add("active-share");
      showToast("Đang chia sẻ màn hình", "success");
    } catch (e) {
      showToast("Hủy chia sẻ màn hình", "info");
    }
  } else {
    stopScreenShare();
  }
}

function stopScreenShare() {
  if (screenStream) {
    screenStream.getTracks().forEach(t => t.stop());
    screenStream = null;
  }
  if (localStream) {
    const videoTrack = localStream.getVideoTracks()[0];
    for (const peerId in peerConnections) {
      const pc = peerConnections[peerId];
      const senders = pc.getSenders();
      const videoSender = senders.find(s => s.track && s.track.kind === "video");
      if (videoSender && videoTrack) {
        videoSender.replaceTrack(videoTrack);
      }
    }
    const localVideo = document.getElementById(`video-${currentUser.username}`);
    if (localVideo) {
      localVideo.srcObject = localStream;
      if (isCamMirrored) localVideo.classList.remove("unmirrored");
    }
  }

  isScreenSharing = false;
  const btn = document.getElementById("btn-share-screen");
  if (btn) btn.classList.remove("active-share");
  showToast("Đã dừng chia sẻ màn hình", "info");
}

// ----------------- CHAT & REACTIONS -----------------
function sendReaction(emoji) {
  showFloatingIcon(emoji);
  playSynthSound("reaction");
  sendWS({
    type: "reaction",
    emoji: emoji
  });
}

function showFloatingIcon(emoji) {
  const container = document.getElementById("reaction-container");
  const el = document.createElement("div");
  el.className = "floating-icon";
  el.innerText = emoji;
  el.style.left = `${(Math.random() - 0.5) * 220}px`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 2200);
}

function toggleChatPanel() {
  const panel = document.getElementById("chat-panel");
  const badge = document.getElementById("chat-unread-badge");
  const isOpen = panel.style.display !== "none";

  panel.style.display = isOpen ? "none" : "flex";
  if (!isOpen) {
    badge.style.display = "none";
    badge.innerText = "0";
  }
}

function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;

  receiveChatMessage(currentUser.nickname, currentUser.avatar, text, true);

  sendWS({
    type: "chat_msg",
    sender_nickname: currentUser.nickname,
    sender_avatar: currentUser.avatar,
    message: text
  });

  input.value = "";
}

function receiveChatMessage(senderNickname, avatar, message, isMe) {
  const chatMessages = document.getElementById("chat-messages");
  const msgItem = document.createElement("div");
  msgItem.className = `chat-msg-item ${isMe ? "me" : ""}`;

  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  msgItem.innerHTML = `
    <div class="chat-msg-header">
      <span>${avatar} ${senderNickname}</span>
      <span>${timeStr}</span>
    </div>
    <div class="chat-msg-bubble">${escapeHTML(message)}</div>
  `;

  chatMessages.appendChild(msgItem);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  const panel = document.getElementById("chat-panel");
  if (panel.style.display === "none" && !isMe) {
    const badge = document.getElementById("chat-unread-badge");
    const count = parseInt(badge.innerText || "0") + 1;
    badge.innerText = count;
    badge.style.display = "flex";
  }
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

// ----------------- UTILITIES -----------------
function copyRoomCode() {
  if (!currentRoomId) return;
  navigator.clipboard.writeText(currentRoomId).then(() => {
    showToast(`Đã sao chép mã phòng: ${currentRoomId}`, "success");
  }).catch(() => {
    showToast(`Mã phòng: ${currentRoomId}`, "info");
  });
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(e => console.log(e));
  } else {
    document.exitFullscreen().catch(e => console.log(e));
  }
}

function leaveRoom() {
  if (frameStreamInterval) clearInterval(frameStreamInterval);
  if (speakingInterval) clearInterval(speakingInterval);
  if (audioRecorder && audioRecorder.state !== "inactive") {
    try { audioRecorder.stop(); } catch (e) {}
  }
  if (socket) socket.close();
  if (localStream) {
    localStream.getTracks().forEach(t => t.stop());
  }
  if (screenStream) {
    screenStream.getTracks().forEach(t => t.stop());
  }
  Object.values(peerConnections).forEach(pc => pc.close());

  document.getElementById("video-grid").innerHTML = "";
  document.getElementById("chat-messages").innerHTML = '<div class="chat-system-msg">Chào mừng bạn đến phòng họp! Chúc buổi họp vui vẻ 🎉</div>';
  document.getElementById("call-screen").style.display = "none";
  document.getElementById("auth-screen").style.display = "flex";
  switchAuthTab("quick");
}