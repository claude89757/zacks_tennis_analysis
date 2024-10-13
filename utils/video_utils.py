
import cv2
import numpy as np

def read_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    return frames[:300]  # 限制处理帧数


def save_video(output_video_frames, output_video_path):
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_video_path, fourcc, 24, (output_video_frames[0].shape[1], output_video_frames[0].shape[0]))
    for frame in output_video_frames:
        out.write(frame)
    out.release()


def save_video_to_images_with_sampling(output_video_frames, output_video_path, max_frame_id, num_samples=10,
                                       target_size_kb=500):
    """
    保存视频并在max_frame_id帧的左右各采样输出num_samples张图片，并将这些图片拼接成一个9宫格的图片
    :param output_video_frames: 视频帧列表
    :param output_video_path: 输出视频路径
    :param max_frame_id: 需要采样的中心帧ID
    :param num_samples: 每侧采样的帧数
    :param target_size_kb: 目标文件大小（KB）
    """
    # 采样输出图片
    total_frames = len(output_video_frames)
    output_frame_id_list = []

    # 采样左侧的帧
    for frame_id in range(max_frame_id, 0, -num_samples):
        output_frame_id_list.append(frame_id)
        if len(output_frame_id_list) >= 5:
            break

    # 采样右侧的帧
    for frame_id in range(max_frame_id, total_frames, num_samples):
        output_frame_id_list.append(frame_id)
        if len(output_frame_id_list) >= 10:
            break

    # 确保采样的帧数不超过9帧
    output_frame_id_list = output_frame_id_list[:9]

    print(f"output_frame_id_list: {output_frame_id_list}")

    # 按顺序保存采样的帧
    sampled_frames = [output_video_frames[i] for i in sorted(output_frame_id_list)]

    # 补帧
    if len(sampled_frames) <= 9:
        last_frame = sampled_frames[-1]
        for index in range(0, 9-len(sampled_frames)):
            sampled_frames.append(last_frame)
    else:
        pass

    # 拼接成九宫格图片
    if len(sampled_frames) == 9:
        # 获取每个帧的高度和宽度
        height, width, _ = sampled_frames[0].shape

        # 创建一个空白的九宫格图片
        grid_image = np.zeros((height * 3, width * 3, 3), dtype=np.uint8)

        # 将采样的帧填充到九宫格图片中
        for idx, frame in enumerate(sampled_frames):
            row = idx // 3
            col = idx % 3
            grid_image[row * height:(row + 1) * height, col * width:(col + 1) * width, :] = frame

        # # 调整图像分辨率
        # height, width = grid_image.shape[:2]
        # resized_image = cv2.resize(grid_image, (width // 2, height // 2), interpolation=cv2.INTER_AREA)
        #
        # # 将图像转换为PNG格式，并设置压缩级别
        # is_success, buffer = cv2.imencode(".png", resized_image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        # if not is_success:
        #     raise Exception("Could not encode image to PNG format")
        #
        # # 检查文件大小
        # file_size_kb = len(buffer) / 1024
        # if file_size_kb > target_size_kb:
        #     print("注意: 即使在调整分辨率和设置最高压缩级别后，PNG格式的文件大小仍可能超过目标大小。")
        #
        # # 保存压缩后的九宫格图片
        # grid_image_path = f"{output_video_path}_grid_compressed.png"
        # with open(grid_image_path, "wb") as f:
        #     f.write(buffer)
        # print(f"九宫格图片已保存到: {grid_image_path}，文件大小: {file_size_kb:.2f} KB")
        # return grid_image_path

        quality = 95  # 初始质量
        while True:
            # 将图像转换为JPEG格式并调整质量
            is_success, buffer = cv2.imencode(".jpg", grid_image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if not is_success:
                raise Exception("Could not encode image to JPEG format")

            # 检查文件大小
            file_size_kb = len(buffer) / 1024
            if file_size_kb <= target_size_kb or quality <= 10:
                break
            quality -= 5  # 逐步降低质量

        # 保存压缩后的九宫格图片
        grid_image_path = f"{output_video_path}_grid_compressed.jpg"
        with open(grid_image_path, "wb") as f:
            f.write(buffer)
        print(f"九宫格图片已保存到: {grid_image_path}，文件大小: {file_size_kb:.2f} KB")
        return grid_image_path

    else:
        print("采样的帧数不足9帧，无法生成九宫格图片。")
