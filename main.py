import soundcard as sc
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from pythonosc import udp_client
import time

# サンプリングレートとバッファサイズの設定
SAMPLERATE = 44100
BUFFER_SIZE = 1024
NUM_PARAMETERS = 16

# OSC設定
OSC_IP = "127.0.0.1"  # localhost
OSC_PORT = 9000  # VRChatのデフォルトOSCポート

# デフォルトのスピーカーを取得
default_speaker = sc.default_speaker()
print(f"デフォルトスピーカー: {default_speaker.name}")

# OSCクライアントの初期化
osc_client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)

# グラフの初期化
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
line1, = ax1.plot([], [], lw=2)
bars = ax2.bar(range(NUM_PARAMETERS), np.zeros(NUM_PARAMETERS))
ax1.set_ylim(-1, 1)
ax1.set_xlim(0, BUFFER_SIZE)
ax2.set_ylim(0, 1)
ax2.set_xlim(0, NUM_PARAMETERS)
ax1.grid()
ax2.grid()

# データの初期化
audio_data = np.zeros(BUFFER_SIZE)
param_data = np.zeros(NUM_PARAMETERS)

def process_audio(data):
    # データを16個のセグメントに分割
    segments = np.array_split(data, NUM_PARAMETERS)
    # 各セグメントの絶対値の平均を計算
    abs_mean_values = [np.mean(np.abs(segment)) for segment in segments]
    # 0-1の範囲に正規化
    max_value = max(abs_mean_values)
    if max_value > 0:
        normalized = [min(value / max_value, 1.0) for value in abs_mean_values]
    else:
        normalized = [0] * NUM_PARAMETERS
    return np.array(normalized)

def send_osc(params):
    for i, value in enumerate(params):
        osc_client.send_message(f"/avatar/parameters/audio_{i}", float(value))

# アニメーション用の関数
def init():
    line1.set_data(range(BUFFER_SIZE), np.zeros(BUFFER_SIZE))
    for bar in bars:
        bar.set_height(0)
    return [line1] + list(bars)

def animate(frame):
    line1.set_ydata(audio_data)
    for bar, h in zip(bars, param_data):
        bar.set_height(h)
    return [line1] + list(bars)

# メインの録音ループ
def record_loop():
    global audio_data, param_data
    last_send_time = 0
    with sc.get_microphone(id=str(default_speaker.name), include_loopback=True).recorder(samplerate=SAMPLERATE) as mic:
        while True:
            audio_data = mic.record(numframes=BUFFER_SIZE)
            audio_data = np.mean(audio_data, axis=1)  # ステレオの場合、モノラルに変換
            param_data = process_audio(audio_data)
            
            # OSCメッセージを0.05秒ごとに送信（20Hz）
            current_time = time.time()
            if current_time - last_send_time >= 0.05:
                send_osc(param_data)
                last_send_time = current_time
            
            yield

# アニメーションの設定と開始
ani = FuncAnimation(fig, animate, frames=record_loop, init_func=init, blit=True, interval=30, cache_frame_data=False)

plt.tight_layout()
plt.show()