
import cv2

from utils import read_video
from utils import save_video_to_images_with_sampling

from trackers import PlayerTracker

from openai.azure_openai import send_image_and_text_to_gpt


def calculate_area(box: list):
    """
    计算bounding box的面积
    :param box: [x1, y1, x2, y2]
    :return: 面积
    """
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    return width * height


def calculate_width(box: list):
    """
    计算bounding box的宽度
    :param box: [x1, y1, x2, y2]
    :return: 宽度
    """
    x1, x2 = box[0], box[2]
    width = x2 - x1
    return width


def find_frame_id_with_max_box(player_detections: list):
    """
    找到bounding box面积最大的帧
    :param player_detections: 每一帧的bounding box数据，格式为 [{1: [x1, y1, x2, y2]}, ...]
    :return: 面积最大的帧号
    """
    max_width = 0
    max_frame_id = -1

    for frame_id, detection in enumerate(player_detections):
        for player_id, box in detection.items():
            width = calculate_width(box)
            # print(f"{frame_id}: {player_id} {width} {detection}")
            if width > max_width:
                max_width = width
                max_frame_id = frame_id
    return max_frame_id


def process_video_by_ai(input_video_path: str):
    """
    通过AI处理视频
    :param input_video_path:
    :return:
    """
    input_video_name = input_video_path.split('/')[0]
    # read video
    video_frames = read_video(input_video_path)
    print(f"video_frames: {len(video_frames)}")
    # Detect players and ball
    player_tracker = PlayerTracker(model_path='yolov8x.pt')
    player_detections = player_tracker.detect_frames(video_frames)

    # draw players bounding boxes
    output_video_frames = player_tracker.draw_bboxes(video_frames=video_frames, player_detections=player_detections)

    # find_frame_id_with_max_box
    max_box_frame_id = find_frame_id_with_max_box(player_detections[10:])  # 剔除前面几帧
    print(f"max_box_frame_id: {max_box_frame_id}")

    # Draw frame number on top left corner
    for i, frame in enumerate(output_video_frames):
        cv2.putText(frame, f"Frame: {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        if i >= max_box_frame_id:
            cv2.putText(frame, f"Frame: {i}*", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(frame, f"Frame: {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Save image
    image_path = f"/Users/xiezengtian/Desktop/{input_video_name}"
    output_image_path = save_video_to_images_with_sampling(output_video_frames, image_path,
                                                           max_box_frame_id, num_samples=10, target_size_kb=800)
    print("save image successfully")

    # send image to gpt
    text = "提供了一组网球运动员的动作照片\n" \
           "***回复格式示例***\n【动作】:xx\n【评分】:1~100分\n【优点】:xx\n【缺点】:xx\n\n" \
           "\n请根据[照片]，判断图片是哪一个网球动作（正手、单反、双反、正手切削、反手切削等），" \
           "并给这个网球动作打分, 打分的标准要参考图片动作和职业球员的标准动作的差距来确定, " \
           "并参考[回复格式示例]生成一份140字内的打分报告, 不要虚构数据和评语"
    response_msg = send_image_and_text_to_gpt(output_image_path, text)

    return response_msg, output_image_path


# test
if __name__ == "__main__":
    pass
    # input_video_name = "67_1723086456_raw"
    # # Read Video
    # input_video_path = f"input_videos/{input_video_name}.mp4"
    # process_video_by_ai(input_video_path)
