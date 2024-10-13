#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/8 21:06
@Author  : claudexie
@File    : azure_openai.py
@Software: PyCharm
"""


import requests
import base64

API_KEY = "xxxxx"


def send_image_and_text_to_gpt(image_path: str, text: str):
    """
    发送图片和文字到GPT模型
    :return:
    """
    model = "gpt-4o"
    # Configuration
    encoded_image = base64.b64encode(open(image_path, 'rb').read()).decode('ascii')
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
    }

    # Payload for the request
    payload = {
      "messages": [
        {
          "role": "system",
          "content": [
            {
              "type": "text",
              "text": "你是一个专业的网球动作分析系统, 目标是给网球动作进行分类和打分，并给出基于提供材料的回复"
            }
          ]
        },
        {
          "role": "user",
          "content": [
              {
                  "type": "text",
                  "text": text
              },
              {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}"
                  }
              },

          ]
        }
      ],
      "temperature": 0.7,
      "top_p": 0.95,
      "max_tokens": 800
    }

    endpoint = f"https://chatgpt3.openai.azure.com/openai/deployments/{model}/chat/completions?api-version=2024-02-15-preview"
    # Send request
    try:
        print("sending request...")
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")

    print(response.json()['choices'][0]['message']['content'])
    return str(response.json()['choices'][0]['message']['content']) + f"\nby Zacks({model})"


