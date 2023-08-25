import os
import re
import json
import math
import time
import base64
import aiohttp
import asyncio
import aiofiles
import binascii
import requests

from Crypto.Cipher import AES
from selenium import webdriver

path = "./Downloads"  # 默认保存位置


def replaceInvalidChars(string):
    invalid_chars = [
        "*", "\"", "/", "\\", ":", "?", "|", "<", ">"
    ]

    for char in invalid_chars:
        if char in string:
            string = string.replace(char, " ")

    return string


def decryptUrl(ciphertext):
    key = binascii.unhexlify("aaad3e4fd540b0f79dca95606e72bf93")
    ciphertext = base64.urlsafe_b64decode(ciphertext + '=' * (4 - len(ciphertext) % 4))
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = cipher.decrypt(ciphertext)
    plaintext = re.sub(r"[^\x20-\x7E]", "", plaintext.decode("utf-8"))
    return plaintext


class Download(object):
    def __init__(self):
        self.default_headers = \
            {
                "user-agent": "Chrome/111.0.0.0 Edge/115.0.1901.200"
            }

    # 解析音频
    def analyzeAudio(self, audio_id, headers):
        """
        :param audio_id:音频ID
        :param headers:
        :return: 音频名称和链接 / 解析失败：Flase
        """
        url = f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}"

        params = \
            {
                "device": "web",
                "trackId": audio_id,
                "trackQualityLevel": 2
            }

        # 解析音频
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            audio_name = response.json()["trackInfo"]["title"]
            encrypted_url_list = response.json()["trackInfo"]["playUrlList"]
        except Exception as e:
            print(f"ID为{audio_id}的音频解析失败！")
            return False

        audio_info = \
            {
                "name": audio_name,
                0: "",
                1: "",
                2: ""
            }

        for encrypted_url in encrypted_url_list:
            if encrypted_url["type"] == "M4A_128":
                audio_info[2] = decryptUrl(encrypted_url["url"])
            elif encrypted_url["type"] == "M4A_64":
                audio_info[1] = decryptUrl(encrypted_url["url"])
            elif encrypted_url["type"] == "M4A_24":
                audio_info[0] = decryptUrl(encrypted_url["url"])

        return audio_info

    # 并发解析音频
    async def asyncAnalyzeAudio(self, audio_id, session, headers):
        """
        同 analyzeAudio()
        :param audio_id:
        :param session:
        :param headers:
        :return:
        """
        url = f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}"
        params = \
            {
                "device": "web",
                "trackId": audio_id,
                "trackQualityLevel": 2
            }

        try:
            async with session.get(url, headers=headers, params=params, timeout=60) as response:
                response_json = json.loads(await response.text())
                audio_name = response_json["trackInfo"]["title"]
                encrypted_url_list = response_json["trackInfo"]["playUrlList"]
        except:
            print(f"ID为{audio_id}的音频解析失败！")
            return False

        audio_info = \
            {
                "name": audio_name,
                0: "",
                1: "",
                2: ""
            }

        for encrypted_url in encrypted_url_list:
            if encrypted_url["type"] == "M4A_128":
                audio_info[2] = decryptUrl(encrypted_url["url"])
            elif encrypted_url["type"] == "M4A_64":
                audio_info[1] = decryptUrl(encrypted_url["url"])
            elif encrypted_url["type"] == "M4A_24":
                audio_info[0] = decryptUrl(encrypted_url["url"])

        return audio_info

    # 解析专辑
    def analyzeAlbum(self, album_id):
        """
        :param album_id: 专辑ID
        :return: 专辑名和音频列表 / False, False
        """
        url = "https://www.ximalaya.com/revision/album/v1/getTracksList"
        params = \
            {
                "albumId": album_id,
                "pageNum": 1,
                "pageSize": 100
            }

        # 开始解析专辑
        try:
            response = requests.get(url, headers=self.default_headers, params=params, timeout=15)
        except:
            print(f"ID为{album_id}的专辑解析失败！")
            return False, False

        # 计算数据页数
        pages = math.ceil(response.json()["data"]["trackTotalCount"] / 100)
        audios = []

        for page in range(pages):
            params = \
                {
                    "albumId": album_id,
                    "pageNum": page,
                    "pageSize": 100
                }
            try:
                response = requests.get(url, headers=self.default_headers, params=params, timeout=30)
            except:
                print(f"ID为{album_id}的专辑解析失败！")
                return False, False

            audios += response.json()["data"]["tracks"]
            album_name = audios[0]["albumTitle"]

            return album_name, audios

    # 下载音频
    def downloadAudio(self, audio_name, audio_url):
        """
        :param audio_name: 音频名称
        :param audio_url:  音频链接
        :return:
        """
        retries = 3
        audio_name = replaceInvalidChars(audio_name)
        if os.path.exists(f"{path}/{audio_name}.m4a"):
            print(f"{audio_name}已存在！")
            return
        while retries > 0:
            try:
                response = requests.get(audio_url, headers=self.default_headers, timeout=60)
                break
            except:
                retries -= 1
        if retries == 0:
            print(f"下载{audio_name}失败！")
            return False

        audio_file = response.content
        if not os.path.exists(path):
            os.mkdir(path)

        with open(f"{path}/{audio_name}.m4a", mode="wb") as f:
            f.write(audio_file)
        print(f"{audio_name}下载完成！")

    # 并发下载音频
    async def asyncDownloadAudio(self, audio_name, audio_url, album_name, session, num=None):
        """
        :param audio_name:
        :param audio_url:
        :param album_name:
        :param session:
        :param num: 考虑专辑音频是否有序
        :return:
        """
        retries = 3
        audio_name = replaceInvalidChars(audio_name) if num is None else replaceInvalidChars(
            f"{num}-{audio_name}")  # 音频有序
        album_name = replaceInvalidChars(album_name)

        if not os.path.exists(f"{path}/{album_name}"):
            os.makedirs(f"{path}/{album_name}")
        if os.path.exists(f"{path}/{album_name}/{audio_name}.m4a"):
            print(f"{audio_name}已存在！")
        while retries > 0:
            try:
                async with session.get(audio_url, headers=self.default_headers, timeout=120) as response:
                    async with aiofiles.open(f"{path}/{album_name}/{audio_name}.m4a", mode="wb") as f:
                        await f.write(await response.content.read())
                print(f"{audio_name}下载完成！")
                break
            except:
                retries -= 1
        if retries == 0:
            print(f"{audio_name}下载失败！")

    async def downloadSelectedAudio(self, audios, album_name, start, end, headers, quality, number):
        tasks = []
        session = aiohttp.ClientSession()
        digits = len(str(len(audios)))
        for i in range(start - 1, end):
            audio_id = audios[i]["trackId"]
            tasks.append(asyncio.create_task(self.asyncAnalyzeAudio(audio_id, session, headers)))
        audios_info = await asyncio.gather(*tasks)
        tasks = []
        if number:
            num = start
            for audio_info in audios_info:
                if audio_info is False or audio_info == 0:
                    continue
                num_ = str(num).zfill(digits)
                if quality == 2 and audio_info[2] == "":
                    quality = 1
                tasks.append(asyncio.create_task(
                    self.asyncDownloadAudio(audio_info["name"], audio_info[quality], album_name, session, num_)))
                num += 1
        else:
            for audio_info in audios_info:
                if audio_info is False or audio_info == 0:
                    continue
                if quality == 2 and audio_info[2] == "":
                    quality = 1
                tasks.append(asyncio.create_task(
                    self.asyncDownloadAudio(audio_info["name"], audio_info[quality], album_name, session)))
        await asyncio.wait(tasks)
        await session.close()
        print("专辑选定声音下载完成！")


class Ximalaya(Download):
    # 登录
    def login(self):
        driver = webdriver.Chrome()
        try:
            driver.get("https://passport.ximalaya.com/page/web/login")
            input("登陆完成后按Enter继续...")
            cookies = driver.get_cookies()
        except:
            exit()
        finally:
            # 关闭 WebDriver
            driver.quit()

        cookie = ""
        for c in cookies:
            cookie += f"{c['name']}={c['value']}; "
        with open("xmly_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        config["cookie"] = cookie
        with open("xmly_config.json", "w", encoding="utf-8") as f:
            json.dump(config, f)

        username = self.judgeCookie(cookie)
        print(f"已登录账号{username}！")

    # 解析配置文件
    def analyzeConfig(self):
        """
        :return: 返回cookie和保存位置
        """
        try:
            with open("xmly_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            with open("xmly_config.json", "w", encoding="utf-8") as f:
                config = \
                    {
                        "cookie": "",
                        "path": ""
                    }
                json.dump(config, f)
            return False, False
        try:
            cookie = config["cookie"]
        except Exception:
            config["cookie"] = ""
            with open("xmly_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f)
            cookie = False
        try:
            path = config["path"]
        except Exception:
            config["path"] = "./Downloads"
            with open("xmly_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f)
            path = False
        return cookie, path

    # 判断cookie是否有效
    def judgeCookie(self, cookie):
        url = "https://www.ximalaya.com/revision/my/getCurrentUserInfo"
        headers = \
            {
                "user-agent": "Chrome/111.0.0.0 Edge/115.0.1901.200",
                "cookie": cookie
            }
        try:
            response = requests.get(url, headers=headers, timeout=15)
        except Exception as e:
            print("无法获取用户数据！")
        if response.json()["ret"] == 200:
            return response.json()["data"]["userName"]
        else:
            return False
