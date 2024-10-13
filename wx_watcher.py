#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/8 21:43
@Author  : claude
@File    : wx_watcher.py
@Software: PyCharm
"""
import os
import time
import subprocess
import datetime

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from xml.etree import ElementTree

from video_to_images_demo import process_video_by_ai

FLICK_START_X = 300
FLICK_START_Y = 300
FLICK_DISTANCE = 700
SCROLL_SLEEP_TIME = 1


def save_date_to_local_file(filename: str, data: str):
    """
    数据缓存到本地文件
    """
    with open(f"./{filename}", 'w') as f:
        f.write(data)


def load_data_from_local_file(filename: str, expire_time: int = 72000):
    """
    从本地文件读取数据，若不存在或超时，则重新拉取
    """
    file_path = f"./{filename}"
    with open(file_path, 'r') as f:
        local_data = f.read().strip()
    # 获取文件的最后修改时间
    file_mod_time = os.path.getmtime(file_path)
    file_mod_date = datetime.datetime.fromtimestamp(file_mod_time)
    # 计算文件的年龄
    file_age_seconds = (datetime.datetime.now() - file_mod_date).seconds
    print(f"{file_path}: {file_mod_date}")

    if file_age_seconds > expire_time:
        print(f"data is expired, delete old data for {filename}")
        return ""
    else:
        return local_data


def is_video_time_less_than_x_seconds(time_text: str, max_seconds: int = 15) -> bool:
    """
    判断视频时间长度是否小于30秒
    :param time_text: 视频时间文本，格式为 "MM:SS"
    :return: 如果视频时间小于30秒，返回True；否则返回False
    """
    try:
        minutes, seconds = map(int, time_text.split(':'))
        total_seconds = minutes * 60 + seconds
        return total_seconds < max_seconds
    except ValueError:
        print("Invalid time format")
        return False


def clear_mp4_files_in_directory(directory_path):
    """
    清理指定目录下的所有MP4文件，并触发媒体库更新。
    :param directory_path: 设备中的目录路径
    """
    try:
        # 列出目录下所有的mp4文件
        list_command = ['adb', 'shell', 'ls', f'{directory_path}/*.mp4']
        list_result = subprocess.run(list_command, capture_output=True, text=True)

        if list_result.returncode != 0:
            print(f"Error listing files: {list_result.stderr}")
            return

        # 获取文件列表
        file_list = list_result.stdout.strip().split('\n')
        if file_list == ['']:
            print("No MP4 files found.")
            return

        # 删除每个文件
        for file in file_list:
            if file.strip():  # 确保文件名不是空字符串
                delete_command = ['adb', 'shell', 'rm', f'"{file}"']
                delete_result = subprocess.run(delete_command, capture_output=True, text=True)
                if delete_result.returncode == 0:
                    print(f"Deleted {file}")
                else:
                    print(f"Failed to delete {file}: {delete_result.stderr}")

        # 触发媒体扫描更新媒体库
        scan_command = ['adb', 'shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', f'file://{directory_path}']
        scan_result = subprocess.run(scan_command, capture_output=True, text=True)
        if scan_result.returncode == 0:
            print("Media scan triggered successfully.")
        else:
            print(f"Failed to trigger media scan: {scan_result.stderr}")

    except Exception as e:
        print(f"An error occurred: {e}")


def pull_file_from_device(device_path, local_path):
    """
    从设备中拉取文件到本地
    :param device_path: 设备中的文件路径
    :param local_path: 本地保存文件的路径
    """
    try:
        # 执行 adb pull 命令
        result = subprocess.run(['adb', 'pull', device_path, local_path], capture_output=True, text=True)

        # 检查命令是否成功执行
        if result.returncode == 0:
            print(f"File pulled successfully from {device_path} to {local_path}")
        else:
            print(f"Failed to pull file: {result.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")


def push_file_to_device(local_path, device_path):
    """
    将本地文件推送到设备中
    :param local_path: 本地文件路径
    :param device_path: 设备中的保存路径
    """
    try:
        # 执行 adb push 命令
        result = subprocess.run(['adb', 'push', local_path, device_path], capture_output=True, text=True)

        # 检查命令是否成功执行
        if result.returncode == 0:
            print(f"File pushed successfully from {local_path} to {device_path}")
            # 触发媒体扫描
            scan_command = ['adb', 'shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                            '-d', f'file://{device_path}']
            scan_result = subprocess.run(scan_command, capture_output=True, text=True)
            if scan_result.returncode == 0:
                print("Media scan triggered successfully.")
            else:
                print(f"Failed to trigger media scan: {scan_result.stderr}")
        else:
            print(f"Failed to push file: {result.stderr}")

    except Exception as e:
        print(f"An error occurred: {e}")


class WXAppOperator:
    def __init__(self):
        """
        初始化
        """
        capabilities = dict(
            platformName='Android',
            automationName='uiautomator2',
            deviceName='BH901V3R9E',
            appPackage='com.tencent.mm',  # 微信的包名
            appActivity='.ui.LauncherUI',  # 微信的启动活动
            noReset=True,  # 不重置应用的状态
            fullReset=False,  # 不完全重置应用
            forceAppLaunch=True  # 强制重新启动应用

        )
        appium_server_url = 'http://localhost:4723'
        print('Loading driver...')
        driver = webdriver.Remote(appium_server_url, options=UiAutomator2Options().load_capabilities(capabilities))
        self.driver = driver
        print('Driver loaded successfully.')
        self.cur_item_name_set = set()

    def enter_chat_page(self, chat_name: str):
        """
        进入聊天窗口
        :return:
        """
        # 使用显式完全加载
        WebDriverWait(self.driver, 60). \
            until(expected_conditions.presence_of_element_located((AppiumBy.XPATH, '//*[@text="微信"]')))

        WebDriverWait(self.driver, 60). \
            until(expected_conditions.presence_of_element_located((AppiumBy.XPATH,
                                                                   f'//*[@text="{chat_name}"]'))).click()

        print(f"enter chat ui of {chat_name} successfully")

    def find_video_element(self):
        """
        查找当前界面是否有触发指令消息文本或消息类型
        :return:
        """
        try:
            # 等待至少有一个指定ID的元素出现
            video_elements = WebDriverWait(self.driver, 5).until(
                expected_conditions.presence_of_all_elements_located((AppiumBy.ID, 'com.tencent.mm:id/boy'))
            )
            return video_elements[-1]
        except Exception as error:
            print(error)
            return None

    def save_video(self, element):
        """
        保存视频到本地
        :return:
        """
        video_time_text = element.text
        max_seconds = 60
        if is_video_time_less_than_x_seconds(video_time_text, max_seconds=max_seconds):
            element.click()
            time.sleep(1)
            WebDriverWait(self.driver, 60).until(
                expected_conditions.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, '更多信息'))).click()

            WebDriverWait(self.driver, 60). \
                until(expected_conditions.presence_of_element_located((AppiumBy.XPATH,
                                                                       f'//*[@text="保存视频"]'))).click()
            # 获取当前页面的 XML 结构
            page_source = self.driver.page_source
            # 解析 XML
            tree = ElementTree.fromstring(page_source)
            # 查找所有元素
            all_elements = tree.findall(".//*")
            print("Clickable elements on the current page:")
            for elem in all_elements:
                text = elem.attrib.get('text', 'N/A')
                if "视频已保存至" in text:
                    WebDriverWait(self.driver, 60).until(
                        expected_conditions.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, '关闭'))).click()
                    return text.strip("视频已保存至")
                else:
                    pass
            raise Exception(f"视频不见了？")
        else:
            print("The video time is not less than 30 seconds.")
            raise Exception(f"视频时长超过{max_seconds}秒, 太长了")

    def send_text_msg(self, msg: str):
        """
        输入文字消息并发送
        :param msg:
        :return:
        """
        input_box = WebDriverWait(self.driver, 60).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, 'com.tencent.mm:id/bkk')))
        input_box.click()
        input_box.send_keys(msg)
        WebDriverWait(self.driver, 60). \
            until(expected_conditions.presence_of_element_located((AppiumBy.XPATH, f'//*[@text="发送"]'))).click()

    def send_first_image_msg(self):
        """
        发送相册中的一张图片
        :return:
        """
        WebDriverWait(self.driver, 60).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, 'com.tencent.mm:id/bjz'))).click()

        WebDriverWait(self.driver, 60). \
            until(expected_conditions.presence_of_element_located((AppiumBy.XPATH, f'//*[@text="相册"]'))).click()

        WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((AppiumBy.ID, 'com.tencent.mm:id/jdh'))).click()

        WebDriverWait(self.driver, 30). \
            until(expected_conditions.presence_of_element_located((AppiumBy.XPATH, f'//*[@text="发送(1)"]'))).click()

    def print_clickable_elements(self):
        # 获取当前页面的 XML 结构
        page_source = self.driver.page_source
        # 解析 XML
        tree = ElementTree.fromstring(page_source)
        # 查找所有元素
        all_elements = tree.findall(".//*")
        print("Clickable elements on the current page:")
        for elem in all_elements:
            clickable = elem.attrib.get('clickable', 'false')
            resource_id = elem.attrib.get('resource-id', 'N/A')
            text = elem.attrib.get('text', 'N/A')
            class_name = elem.attrib.get('class', 'N/A')
            content_desc = elem.attrib.get('content-desc', 'N/A')
            bounds = elem.attrib.get('bounds', 'N/A')
            focusable = elem.attrib.get('focusable', 'N/A')
            enabled = elem.attrib.get('enabled', 'N/A')
            if clickable == 'true':
                print(f"**Resource ID: {resource_id}, Text: {text}, Class: {class_name}, Content-desc: {content_desc}, "
                      f"Bounds: {bounds}, Clickable: {clickable}, Focusable: {focusable}, Enabled: {enabled}")
            else:
                print(f"Resource ID: {resource_id}, Text: {text}, Class: {class_name}, Content-desc: {content_desc}, "
                      f"Bounds: {bounds}, Clickable: {clickable}, Focusable: {focusable}, Enabled: {enabled}")

    def close(self):
        self.driver.quit()
        print('Driver closed.')


import requests
import json
from datetime import datetime, timedelta


def get_chat_room_name(url="http://xxxx:5000/get_content"):
    """
    获取指定URL的内容，解析时间信息，并判断是否在最近3分钟内

    :param url: API的URL，默认为 http://xxxx:5000/get_content
    :return: 如果时间在最近3分钟内返回True，否则返回False。如果发生错误也返回False
    """
    try:
        # 发送GET请求到API
        response = requests.get(url)
        response.raise_for_status()  # 如果请求不成功，将引发异常
        # 解析JSON响应
        data = response.json()
        return data['content']['from_user_nickname']
    except Exception as e:
        print(f"发生未知错误: {e}")
        return ""


def call_clear_content_post():
    url = "http://43.156.183.71:5000/clear_content"
    try:
        response = requests.post(url)

        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Failed:", response.status_code, response.json())

    except requests.exceptions.RequestException as e:
        print("Error:", e)


def write_content_to_file(content):
    """
    调用API端点，将内容写入文件

    :param api_url: API端点的URL
    :param content: 要写入文件的内容
    :return: API响应
    """
    url = "http://xxxxx:5000/write_content"
    headers = {'Content-Type': 'application/json'}
    data = {'content': content}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # 如果响应状态码不是200，抛出HTTPError
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


if __name__ == '__main__':
    # 进入等待
    while True:
        chat_room_name = get_chat_room_name()
        if chat_room_name:
            print(f"{chat_room_name} 触发任务")
            write_content_to_file(f"{chat_room_name} RUNNING")
            try:
                wx_operator = WXAppOperator()
                wx_operator.enter_chat_page(chat_room_name)
                video_element = wx_operator.find_video_element()
            except Exception as error:
                print(error)
                continue
            if video_element:
                try:
                    video_text = video_element.text
                    video_path = wx_operator.save_video(video_element)
                    print(video_path)
                    video_name = video_path.split('/')[-1]
                    wx_operator.send_text_msg(f"{video_text} 视频AI分析中...请稍等")

                    local_video_path = f"/Users/xiezengtian/Desktop/{video_name}"
                    pull_file_from_device(video_path, local_video_path)

                    # 启动AI视频分析
                    response_msg, output_image_path = process_video_by_ai(local_video_path)
                    output_image_name = output_image_path.split('/')[-1]

                    # 推送图片到手机上
                    push_file_to_device(output_image_path, f"/storage/emulated/0/Pictures/WeiXin/{output_image_name}")

                    # 发送消息到手机上
                    wx_operator = WXAppOperator()
                    wx_operator.enter_chat_page(chat_room_name)
                    wx_operator.send_text_msg(response_msg)
                    wx_operator.send_first_image_msg()

                    # 清理视频缓存
                    clear_mp4_files_in_directory("/sdcard/DCIM/WeiXin/")
                except Exception as error:
                    print(error)
                    # 完成任务，清理标记
                    call_clear_content_post()
                    # 发送消息到手机上
                    wx_operator = WXAppOperator()
                    wx_operator.enter_chat_page(chat_room_name)
                    msg = F"Ops，出错了，晚点再试下😭"
                    wx_operator.send_text_msg(msg)
            else:
                # 未找到视频文件
                wx_operator = WXAppOperator()
                wx_operator.enter_chat_page(chat_room_name)
                msg = F"请发送30秒左右的网球视频"
                wx_operator.send_text_msg(msg)
            # wx_operator.send_text_msg("msg")
            wx_operator.close()

            # 完成任务，清理标记
            call_clear_content_post()
        else:
            print("no task, keeping watching")
            time.sleep(5)
