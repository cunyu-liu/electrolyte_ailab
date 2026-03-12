
#确保网卡在192.168.80网段 初次可浏览器访问192.168.80.44网页
import cv2

def try1():
    import cv2
    # RTSP URL格式
    rtsp_url = "rtsp://admin:SZKJ2025@192.168.80.44:554/Streaming/Channels/201/"

    cap = cv2.VideoCapture(rtsp_url)

    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow('Hikvision Video', frame)
            # 按q退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("无法获取视频流")
            break

    cap.release()
    cv2.destroyAllWindows()




def get_camera_stream(channel: int,
                      ip="192.168.80.44",
                      username="admin",
                      password="SZKJ2025"):
    """

    获取海康威视 RTSP 视频流生成器
    :param channel: 102 / 202 / 302 / 402 等子码流编号
    :return: 连续返回视频帧（numpy array）
    """
    rtsp_url = f"rtsp://{username}:{password}@{ip}:554/Streaming/Channels/{channel}"

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        raise Exception(f"无法打开 RTSP 通道 {channel}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"RTSP 通道 {channel} 读取失败")
            break
        yield frame  # 返回一帧

    cap.release()



if __name__ == '__main__':
    for frame in get_camera_stream(102):
        # 在这里处理frame，例如做AI推理
        try1()        