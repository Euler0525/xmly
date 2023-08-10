import re
import time
import asyncio
import requests

from .ximalaya import Ximalaya


class User(object):
    def __init__(self):
        self.ximalaya = Ximalaya()
        self.loop = asyncio.get_event_loop()

    def main(self):
        print("欢迎使用喜马拉雅下载器：")
        cookie, path = self.ximalaya.analyzeConfig()
        if not cookie:
            username = False
        else:
            username = self.ximalaya.judgeCookie(cookie)
        response = requests.get(
            f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}?device=web&trackId=188017958&trackQualityLevel=1",
            headers=self.ximalaya.default_headers)

        # 登录信息
        if not username:
            while True:
                print("请选择是否要登录：")
                print("1. 登录")
                print("2. 不登录")
                print("q. 退出程序")
                choice = input()
                if choice == "1":
                    self.ximalaya.login()
                    headers = {
                        "user-agent": "Chrome/111.0.0.0 Edge/115.0.1901.200",
                        "cookie": self.ximalaya.analyzeConfig()[0]
                    }
                    break
                elif choice == "2":
                    headers = self.ximalaya.default_headers
                    break
                elif choice == "q":
                    exit()
        else:
            print(f"用户{username}已登录！")
            headers = {
                "user-agent": "Chrome/111.0.0.0 Edge/115.0.1901.200",
                "cookie": self.ximalaya.analyzeConfig()[0]
            }

        # 功能选择
        while True:
            print("请选择要使用的功能：")
            print("1. 下载音频")
            print("2. 下载专辑")
            print("q. 退出程序")
            choice = input()
            if choice == "1":
                while True:
                    print("请输入音频链接：")
                    _ = input()
                    if _ == "q":
                        exit()
                    # 提取链接中的音频ID
                    try:
                        audio_id = re.search(r"ximalaya.com/audio/(?P<audio_id>\d+)", _).group('audio_id')
                        break
                    except AttributeError:
                        print("输入有误，请重新输入！")
                        continue

                audio_info = self.ximalaya.analyzeAudio(audio_id, headers)
                if audio_info is False:
                    continue

                # 下载尽可能高的音质
                if audio_info[2] != "":
                    self.ximalaya.downloadAudio(audio_info["name"], audio_info[2])
                else:
                    self.ximalaya.downloadAudio(audio_info["name"], audio_info[1])

            elif choice == "2":
                while True:
                    print("请输入专辑链接：")
                    _ = input()
                    if _ == "q":
                        exit()
                    # 提取链接中的专辑ID
                    try:
                        album_id = re.search(r"ximalaya.com/album/(?P<album_id>\d+)", _).group("album_id")
                        break
                    except AttributeError:
                        print("输入有误，请重新输入！")
                        continue

                album_name, audios = self.ximalaya.analyzeAlbum(album_id)
                if not audios:
                    continue

                while True:
                    print("请选择要使用的功能：")
                    print("1. 下载专辑中全部音频")
                    print("2. 下载专辑中部分音频")
                    print("3. 显示专辑列表")
                    print("q. 退出程序")
                    choice = input()
                    if choice == "1" or choice == "2":
                        if choice == "1":
                            start = 1
                            end = len(audios)
                        else:
                            print("请输入要下载的声音范围，中间用\"-\"隔开：")
                            download_range = input()
                            start, end = download_range.split("-")
                            start = int(start)
                            end = int(end)
                        # 音频是否有序
                        while True:
                            print("是否需要添加序号：")
                            print("1. 是")
                            print("2. 否")
                            choice = input()
                            if choice == "1":
                                number = True
                                break
                            elif choice == "2":
                                number = False
                                break
                            else:
                                print("输入错误，请重新输入！")

                        self.loop.run_until_complete(
                            self.ximalaya.downloadSelectedAudio(audios, album_name, start, end, headers, 2, number))
                        break
                    # 输出专辑列表
                    elif choice == "3":
                        for audio in audios:
                            print(f"{audio['index']}. {audio['title']}")
                    elif choice == "q":
                        exit()
                    else:
                        print("输入错误，请重新输入!")
            elif choice == "q":
                exit()
